"""HTK-TCPServer standalone desktop application entry point."""

from __future__ import annotations

import argparse
import threading

from src.web_app import create_app
from werkzeug.serving import make_server


def _window_geometry(webview) -> tuple[int, int, int | None, int | None, tuple[int, int]]:
    """Calculate a centered initial window that fits the primary display."""
    screens = getattr(webview, "screens", [])
    if not screens:
        return 800, 900, None, None, (520, 520)

    screen = screens[0]
    available_width = max(480, int(screen.width * 0.92))
    available_height = max(520, int(screen.height * 0.90))
    target_aspect = 800 / 1100

    height = min(1100, available_height)
    width = round(height * target_aspect)
    minimum_width = min(680, available_width)
    if width < minimum_width:
        width = minimum_width

    width = min(width, available_width)
    height = min(height, round(width / target_aspect), available_height)
    x = screen.x + max(0, (screen.width - width) // 2)
    y = screen.y + max(0, (screen.height - height) // 2)
    minimum_size = (
        min(600, available_width),
        min(600, available_height),
    )
    return width, height, x, y, minimum_size


def main() -> None:
    parser = argparse.ArgumentParser(description="HTK 示教器 TCP Web 模拟端")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务监听地址")
    parser.add_argument("--web-port", type=int, default=8080, help="Web 服务端口")
    args = parser.parse_args()

    app = create_app()
    try:
        import webview
    except ImportError as exc:
        raise SystemExit("缺少 pywebview，请先安装 requirements.txt 中的依赖") from exc

    http_server = make_server(args.host, args.web_port, app, threaded=True)
    server_thread = threading.Thread(
        target=http_server.serve_forever,
        name="htk-web-server",
        daemon=True,
    )
    server_thread.start()
    url = f"http://127.0.0.1:{args.web_port}"
    width, height, x, y, minimum_size = _window_geometry(webview)
    webview.create_window(
        "SYNTEC-HTK-TCPServer",
        url,
        width=width,
        height=height,
        x=x,
        y=y,
        min_size=minimum_size,
        resizable=True,
    )

    try:
        webview.start()
    finally:
        http_server.shutdown()
        server_thread.join(timeout=2)
        app.extensions["htk_web_state"].close()


if __name__ == "__main__":
    main()
