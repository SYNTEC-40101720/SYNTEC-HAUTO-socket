"""Flask application for the HTK teachbox TCP simulator."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template, request

from src.protocol import (
    CMD,
    build_io_frame,
    build_key_frame,
    build_mpg_frame,
    parse_led_buzzer_byte,
)
from src.tcp_server import TeachboxTcpServer


SHIFT_KEYS = {14, 20}
DEFAULT_PORT = 802
DEFAULT_KEY_COLOR = "#FFFFFF"
VALID_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _resource_path(*parts: str) -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    root = Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[1]
    return root.joinpath(*parts)


def load_key_config() -> list[dict[str, object]]:
    """Load key labels and colors from the project configuration."""
    defaults = [
        {
            "index": index,
            "id": f"K{index + 1}",
            "name": f"K{index + 1}",
            "lines": [f"K{index + 1}"],
            "color": DEFAULT_KEY_COLOR,
            "shift": index in SHIFT_KEYS,
        }
        for index in range(63)
    ]
    config_path = _resource_path("keys.json")
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return defaults

    if not isinstance(config, dict):
        return defaults

    for index, key in enumerate(defaults):
        value = config.get(key["id"], {})
        if isinstance(value, dict):
            name = str(value.get("name", key["name"]))
            color = str(value.get("color", DEFAULT_KEY_COLOR))
        else:
            name = str(value) if value else str(key["name"])
            color = DEFAULT_KEY_COLOR
        key["name"] = name
        key["lines"] = name.splitlines() or [str(key["id"])]
        key["color"] = color if VALID_COLOR.fullmatch(color) else DEFAULT_KEY_COLOR
    return defaults


class TeachboxWebState:
    """Thread-safe application state shared by Flask and the TCP worker."""

    def __init__(self) -> None:
        self.keys = load_key_config()
        self._lock = Lock()
        self._key_state = [False] * 63
        self._mpg_total = 0
        self._io_mode = 0
        self._led_state = 0
        self._last_error: str | None = None
        self._configured_port = DEFAULT_PORT
        self.tcp_server = TeachboxTcpServer(
            on_frame_received=self._on_frame_received,
            on_client_connected=self._on_client_connected,
            on_client_disconnected=self._on_client_disconnected,
            on_error=self._on_error,
        )

    def start_server(self, port: int) -> bool:
        started = self.tcp_server.start(port)
        if started:
            with self._lock:
                self._configured_port = port
        return started

    def stop_server(self) -> None:
        self.tcp_server.stop()

    def set_key(self, index: int, action: str) -> None:
        self._validate_key_index(index)
        if action not in {"press", "release"}:
            raise ValueError("无效的按键动作")

        with self._lock:
            if index in SHIFT_KEYS:
                if action == "press":
                    self._key_state[index] = not self._key_state[index]
                else:
                    return
            else:
                self._key_state[index] = action == "press"
            self._send_key_locked()

    def release_keys(self) -> None:
        with self._lock:
            changed = any(
                pressed and index not in SHIFT_KEYS
                for index, pressed in enumerate(self._key_state)
            )
            if not changed:
                return
            for index in range(63):
                if index not in SHIFT_KEYS:
                    self._key_state[index] = False
            self._send_key_locked()

    def set_io_mode(self, mode: int) -> None:
        if mode not in {0, 1, 2}:
            raise ValueError("无效的 IO 模式")
        with self._lock:
            self._io_mode = mode
            self.tcp_server.send_frame(build_io_frame(mode, 0))

    def step_mpg(self, direction: int) -> None:
        if direction not in {-1, 1}:
            raise ValueError("无效的 MPG 方向")
        with self._lock:
            self._mpg_total = max(
                -(2**31), min(2**31 - 1, self._mpg_total + direction)
            )
            self.tcp_server.send_frame(
                build_mpg_frame(self._mpg_total, direction)
            )

    def snapshot(self) -> dict[str, object]:
        tcp_status = self.tcp_server.status()
        with self._lock:
            led_state = self._led_state
            return {
                "server": tcp_status,
                "configured_port": self._configured_port,
                "key_states": list(self._key_state),
                "mpg_total": self._mpg_total,
                "io_mode": self._io_mode,
                "leds": [bool(led_state & (1 << index)) for index in range(9)],
                "buzzer": bool(led_state & 0x8000),
                "last_error": self._last_error or tcp_status["last_error"],
            }

    def close(self) -> None:
        self.tcp_server.stop()

    def _send_key_locked(self) -> None:
        key1 = key2 = 0
        for index, pressed in enumerate(self._key_state):
            if pressed:
                if index < 32:
                    key1 |= 1 << index
                else:
                    key2 |= 1 << (index - 32)
        self.tcp_server.send_frame(build_key_frame(key1, key2))

    def _on_frame_received(self, command: int, payload: bytes) -> None:
        if command != CMD.LED_BUZZER:
            return
        with self._lock:
            self._led_state = parse_led_buzzer_byte(payload)

    def _on_client_connected(self, _ip: str, _port: int) -> None:
        with self._lock:
            self._last_error = None

    def _on_client_disconnected(self) -> None:
        with self._lock:
            self._led_state = 0

    def _on_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

    @staticmethod
    def _validate_key_index(index: int) -> None:
        if not 0 <= index < 63:
            raise ValueError("无效的按键索引")


def create_app(state: TeachboxWebState | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_resource_path("web", "templates")),
        static_folder=str(_resource_path("web", "static")),
    )
    web_state = state or TeachboxWebState()
    app.extensions["htk_web_state"] = web_state

    @app.get("/")
    def index():
        return render_template("index.html", keys=web_state.keys)

    @app.get("/api/state")
    def get_state():
        return jsonify(web_state.snapshot())

    @app.post("/api/server/start")
    def start_server():
        payload = request.get_json(silent=True) or {}
        try:
            port = int(payload.get("port", DEFAULT_PORT))
        except (TypeError, ValueError):
            return _error_response("端口必须是数字")
        if not 1 <= port <= 65535:
            return _error_response("端口范围必须是 1-65535")
        if not web_state.start_server(port):
            return _error_response(
                web_state.snapshot().get("last_error") or "服务启动失败"
            )
        return jsonify({"ok": True, "state": web_state.snapshot()})

    @app.post("/api/server/stop")
    def stop_server():
        web_state.stop_server()
        return jsonify({"ok": True, "state": web_state.snapshot()})

    @app.post("/api/keys/<int:index>")
    def set_key(index: int):
        payload = request.get_json(silent=True) or {}
        try:
            web_state.set_key(index, str(payload.get("action", "press")))
        except ValueError as exc:
            return _error_response(str(exc))
        return jsonify({"ok": True, "state": web_state.snapshot()})

    @app.post("/api/keys/release-all")
    def release_keys():
        web_state.release_keys()
        return jsonify({"ok": True, "state": web_state.snapshot()})

    @app.post("/api/io")
    def set_io():
        payload = request.get_json(silent=True) or {}
        raw_mode = payload.get("mode")
        mode_names = {"manual": 0, "auto": 1, "remote": 2}
        try:
            mode = mode_names[str(raw_mode)] if str(raw_mode) in mode_names else int(raw_mode)
        except (TypeError, ValueError):
            return _error_response("无效的 IO 模式")
        try:
            web_state.set_io_mode(mode)
        except ValueError as exc:
            return _error_response(str(exc))
        return jsonify({"ok": True, "state": web_state.snapshot()})

    @app.post("/api/mpg")
    def step_mpg():
        payload = request.get_json(silent=True) or {}
        try:
            direction = int(payload.get("direction"))
            web_state.step_mpg(direction)
        except (TypeError, ValueError) as exc:
            return _error_response(str(exc) or "无效的 MPG 方向")
        return jsonify({"ok": True, "state": web_state.snapshot()})

    return app


def _error_response(message: object):
    return jsonify({"ok": False, "message": str(message)}), 400