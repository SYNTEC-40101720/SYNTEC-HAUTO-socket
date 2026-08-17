"""Threaded TCP transport for the browser-based teachbox simulator."""

from __future__ import annotations

import socket
import threading
from collections.abc import Callable

from src.protocol import FrameBuffer, build_version_frame, parse_frame


FrameReceivedCallback = Callable[[int, bytes], None]
ClientConnectedCallback = Callable[[str, int], None]
ClientDisconnectedCallback = Callable[[], None]
ErrorCallback = Callable[[str], None]


class TeachboxTcpServer:
    """Single-client TCP server used by the web application."""

    def __init__(
        self,
        on_frame_received: FrameReceivedCallback | None = None,
        on_client_connected: ClientConnectedCallback | None = None,
        on_client_disconnected: ClientDisconnectedCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._on_frame_received = on_frame_received
        self._on_client_connected = on_client_connected
        self._on_client_disconnected = on_client_disconnected
        self._on_error = on_error

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._listen_socket: socket.socket | None = None
        self._client_socket: socket.socket | None = None
        self._client_address: tuple[str, int] | None = None
        self._port = 0
        self._last_error: str | None = None
        self._accept_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None

    def start(self, port: int = 802) -> bool:
        """Start listening for one TCP client."""
        with self._lock:
            if self.is_listening():
                return True

            listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listen_socket.bind(("0.0.0.0", port))
                listen_socket.listen(1)
                listen_socket.settimeout(0.5)
            except OSError as exc:
                listen_socket.close()
                self._set_error(f"监听失败: {exc}")
                return False

            self._stop_event.clear()
            self._listen_socket = listen_socket
            self._port = port
            self._last_error = None
            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                args=(listen_socket,),
                name="htk-tcp-accept",
                daemon=True,
            )
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name="htk-tcp-heartbeat",
                daemon=True,
            )
            self._accept_thread.start()
            self._heartbeat_thread.start()
            return True

    def stop(self) -> None:
        """Stop listening and close the current client connection."""
        with self._lock:
            self._stop_event.set()
            listen_socket = self._listen_socket
            client_socket = self._client_socket
            self._listen_socket = None
            self._client_socket = None
            self._client_address = None
            self._port = 0

        self._close_socket(listen_socket)
        self._close_socket(client_socket)

        current_thread = threading.current_thread()
        for thread in (self._accept_thread, self._heartbeat_thread):
            if thread and thread is not current_thread:
                thread.join(timeout=1.0)
        self._accept_thread = None
        self._heartbeat_thread = None

    def is_listening(self) -> bool:
        with self._lock:
            return self._listen_socket is not None

    def send_frame(self, frame: bytes) -> bool:
        """Send one complete protocol frame to the connected client."""
        if len(frame) != 9:
            raise ValueError(f"Expected 9 bytes, got {len(frame)}")

        with self._lock:
            client_socket = self._client_socket
        if client_socket is None:
            return False

        try:
            client_socket.sendall(frame)
            return True
        except OSError as exc:
            self._set_error(f"发送失败: {exc}")
            self._close_socket(client_socket)
            return False

    def client_info(self) -> tuple[str | None, int | None]:
        with self._lock:
            if self._client_address is None:
                return None, None
            return self._client_address

    def status(self) -> dict[str, object]:
        ip, port = self.client_info()
        with self._lock:
            return {
                "listening": self._listen_socket is not None,
                "port": self._port,
                "client": {"ip": ip, "port": port} if ip is not None else None,
                "last_error": self._last_error,
            }

    def _accept_loop(self, listen_socket: socket.socket) -> None:
        while not self._stop_event.is_set():
            try:
                client_socket, address = listen_socket.accept()
            except socket.timeout:
                continue
            except OSError as exc:
                if not self._stop_event.is_set():
                    self._set_error(f"监听异常: {exc}")
                break

            self._replace_client(client_socket, address)
            threading.Thread(
                target=self._client_loop,
                args=(client_socket,),
                name="htk-tcp-client",
                daemon=True,
            ).start()

    def _replace_client(
        self, client_socket: socket.socket, address: tuple[str, int]
    ) -> None:
        with self._lock:
            old_socket = self._client_socket
            self._client_socket = client_socket
            self._client_address = address

        self._close_socket(old_socket)
        self._notify(self._on_client_connected, address[0], address[1])

    def _client_loop(self, client_socket: socket.socket) -> None:
        frame_buffer = FrameBuffer()
        client_socket.settimeout(0.5)
        try:
            while not self._stop_event.is_set():
                try:
                    data = client_socket.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break

                frame_buffer.feed(data)
                while True:
                    frame = frame_buffer.pop_frame()
                    if frame is None:
                        break
                    command, payload = parse_frame(frame)
                    self._notify(self._on_frame_received, command, payload)
        except OSError as exc:
            if not self._stop_event.is_set():
                self._set_error(f"Socket 错误: {exc}")
        finally:
            with self._lock:
                is_current = self._client_socket is client_socket
                if is_current:
                    self._client_socket = None
                    self._client_address = None
            self._close_socket(client_socket)
            if is_current:
                self._notify(self._on_client_disconnected)

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(1.0):
            self.send_frame(build_version_frame())

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message
        self._notify(self._on_error, message)

    @staticmethod
    def _close_socket(sock: socket.socket | None) -> None:
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def _notify(self, callback: Callable[..., None] | None, *args: object) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception as exc:
            self._set_error(f"回调处理失败: {exc}")