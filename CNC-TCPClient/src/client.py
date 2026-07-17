"""
TeachboxClient - TCP客户端封装
负责与服务端建立TCP连接，收发协议帧，管理连接状态和统计
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket

from protocol import FrameBuffer, parse_frame


class TeachboxClient(QObject):
    """模拟上位机 TCP 客户端（协议正确实现版）"""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    frame_received = pyqtSignal(int, bytes)   # (cmd, payload)
    frame_sent = pyqtSignal(int, bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None):
        """
        初始化客户端

        参数:
            parent: Qt父对象
        """
        super().__init__(parent)
        self._sock: QTcpSocket | None = None
        self._buf = FrameBuffer()
        self._tx_count = 0
        self._rx_count = 0
        self._addr = "192.168.0.21"
        self._port = 502
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._do_connect)
        self._auto_reconnect = True

    def set_target(self, addr: str, port: int) -> None:
        """
        设置目标服务器地址和端口

        参数:
            addr: 服务器IP地址
            port: 服务器端口号
        """
        self._addr = addr
        self._port = port

    def enable_auto_reconnect(self, on: bool) -> None:
        """
        启用/禁用自动重连

        参数:
            on: True启用自动重连，False禁用
        """
        self._auto_reconnect = on

    def start(self) -> None:
        """启动客户端，开始连接"""
        self._do_connect()

    def stop(self) -> None:
        """停止客户端，断开连接"""
        self._auto_reconnect = False
        self._reconnect_timer.stop()
        if self._sock:
            self._sock.blockSignals(True)
            self._sock.disconnectFromHost()
            self._sock = None
        self._buf.clear()

    def send_frame(self, frame: bytes) -> None:
        """
        发送协议帧

        参数:
            frame: 9字节协议帧数据

        异常:
            无实际异常抛出，连接断开时静默忽略
        """
        if self._sock and self._sock.state() == QAbstractSocket.ConnectedState:
            self._sock.write(frame)
            self._sock.flush()
            self._tx_count += 1
            self.frame_sent.emit(frame[0], frame)

    def is_connected(self) -> bool:
        """
        检查当前是否已连接

        返回:
            True表示已连接，False表示未连接
        """
        return self._sock is not None and self._sock.state() == QAbstractSocket.ConnectedState

    def stats(self) -> tuple[int, int]:
        """
        获取收发统计

        返回:
            (发送帧数, 接收帧数)元组
        """
        return self._tx_count, self._rx_count

    def _do_connect(self) -> None:
        """执行实际TCP连接操作"""
        if self._sock:
            self._sock.deleteLater()
            self._sock = None
        self._sock = QTcpSocket(self)
        self._sock.connected.connect(self._on_connected)
        self._sock.disconnected.connect(self._on_disconnected)
        self._sock.readyRead.connect(self._on_ready_read)
        self._sock.error.connect(self._on_error)
        self._buf.clear()
        self._sock.connectToHost(self._addr, self._port)

    def _on_connected(self) -> None:
        """连接成功回调"""
        self._reconnect_timer.stop()
        self.connected.emit()

    def _on_disconnected(self) -> None:
        """连接断开回调"""
        self._sock = None
        self.disconnected.emit()
        if self._auto_reconnect:
            self._reconnect_timer.start(3000)

    def _on_ready_read(self) -> None:
        """数据到达回调，处理粘包/拆包并解析帧"""
        data = bytes(self._sock.readAll())
        self._buf.feed(data)
        while True:
            frame = self._buf.pop_frame()
            if frame is None:
                break
            cmd, payload = parse_frame(frame)
            if cmd is not None:
                self._rx_count += 1
                self.frame_received.emit(cmd, payload)

    def _on_error(self, socket_error: QAbstractSocket.SocketError) -> None:
        """
        Socket错误回调

        参数:
            socket_error: Qt Socket错误码
        """
        err = self._sock.errorString() if self._sock else "未知错误"
        self.error_occurred.emit(err)
