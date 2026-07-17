"""
HTK-TCPServer - 示教器 TCP 服务端核心逻辑
模拟示教器（服务端）行为，用于测试 CNC-TCPClient
"""

from __future__ import annotations

from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtNetwork import QTcpServer, QAbstractSocket, QHostAddress

from src.protocol import FrameBuffer, parse_frame


class TeachboxServer(QObject):
    """
    模拟示教器 TCP 服务端

    信号:
        client_connected: 客户端连接 (ip, port)
        client_disconnected: 客户端断开
        frame_received: 收到帧 (cmd, payload)
        frame_sent: 发送帧 (cmd, frame_bytes)
        socket_error: Socket 错误信息
    """

    client_connected = pyqtSignal(str, int)
    client_disconnected = pyqtSignal()
    frame_received = pyqtSignal(int, bytes)
    frame_sent = pyqtSignal(int, bytes)
    socket_error = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None):
        """
        初始化服务端

        参数:
            parent: Qt 父对象
        """
        super().__init__(parent)
        self._server = QTcpServer(self)
        self._client: QAbstractSocket | None = None
        self._frame_buf = FrameBuffer()
        self._server.newConnection.connect(self._on_new_conn)

    def is_listening(self) -> bool:
        """
        检查服务是否在监听

        返回:
            bool: 是否在监听
        """
        return self._server.isListening()

    def listen_port(self) -> int:
        """
        获取监听端口

        返回:
            int: 端口号
        """
        return self._server.serverPort()

    def start(self, port: int = 502) -> bool:
        """
        启动 TCP 监听

        参数:
            port: 监听端口号

        返回:
            bool: 是否启动成功
        """
        if self._server.listen(QHostAddress.Any, port):
            return True
        self.socket_error.emit(f"监听失败: {self._server.errorString()}")
        return False

    def stop(self) -> None:
        """停止服务并清理连接"""
        if self._client:
            self._client.disconnectFromHost()
            self._client = None
        self._server.close()
        self._frame_buf.clear()

    def send_frame(self, frame: bytes) -> None:
        """
        发送帧到客户端

        参数:
            frame: 帧字节数据
        """
        if self._client and self._client.state() == QAbstractSocket.ConnectedState:
            self._client.write(frame)
            self._client.flush()
            cmd = frame[0]
            self.frame_sent.emit(cmd, frame)

    def client_info(self) -> tuple[str | None, int | None]:
        """
        获取当前客户端信息

        返回:
            tuple: (ip, port) 或 (None, None)
        """
        if self._client and self._client.state() == QAbstractSocket.ConnectedState:
            return self._client.peerAddress().toString(), self._client.peerPort()
        return None, None

    # ─── 内部回调 ───────────────────────────────

    def _on_new_conn(self):
        """处理新连接"""
        if self._client:
            self._client.blockSignals(True)
            self._client.disconnectFromHost()
            self._client.deleteLater()
            self._client = None

        client_sock = self._server.nextPendingConnection()
        peer = client_sock.peerAddress().toString()
        port = client_sock.peerPort()
        self._client = client_sock
        self._frame_buf.clear()
        client_sock.readyRead.connect(self._on_ready_read)
        client_sock.disconnected.connect(self._on_disconnected)
        client_sock.error.connect(
            lambda e: self.socket_error.emit(f"Socket错误: {client_sock.errorString()}")
        )
        self.client_connected.emit(peer, port)

    def _on_ready_read(self):
        """处理数据读取"""
        data = bytes(self._client.readAll())
        self._frame_buf.feed(data)
        while True:
            frame = self._frame_buf.pop_frame()
            if frame is None:
                break
            cmd, payload = parse_frame(frame)
            if cmd is not None:
                self.frame_received.emit(cmd, payload)

    def _on_disconnected(self):
        """处理断开连接"""
        self._client = None
        self.client_disconnected.emit()
