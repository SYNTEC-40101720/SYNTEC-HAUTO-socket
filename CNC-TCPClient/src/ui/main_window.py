"""
CNC-TCPClient - 主窗口 UI
"""

from __future__ import annotations

import os
import time

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QSpinBox, QLineEdit,
    QCheckBox, QPushButton, QTextEdit,
    QFormLayout, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QSettings

from client import TeachboxClient
from protocol import (
    CMD, frame_hex, parse_key_data, parse_mpg_data,
    parse_joystick_data, parse_io_data, parse_led_buzzer_byte,
    build_version_frame, build_led_buzzer_frame,
    led_buzzer_decode, led_buzzer_encode
)
from ui.widgets import LEDFrame

STYLESHEET = """
QMainWindow { background: #ffffff; }

QGroupBox {
    font-weight: bold;
    font-size: 11pt;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 16px;
    color: #333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #555;
}

QPushButton {
    background: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 10pt;
    font-weight: bold;
}
QPushButton:hover { background: #43A047; }
QPushButton:pressed { background: #388E3C; }
QPushButton:disabled { background: #ccc; color: #888; }

QSpinBox, QDoubleSpinBox {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 10pt;
    font-family: Consolas;
    background: #fafafa;
}
QSpinBox:focus {
    border-color: #4CAF50;
    background: #fff;
}

QLineEdit {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 10pt;
    font-family: Consolas;
    background: #fafafa;
}
QLineEdit:focus {
    border-color: #4CAF50;
    background: #fff;
}

QCheckBox {
    font-size: 10pt;
    spacing: 6px;
}

QLabel {
    font-size: 10pt;
    color: #333;
}

QTextEdit {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    background: #fafafa;
    font-family: Consolas;
    font-size: 9pt;
}

QScrollBar:vertical {
    width: 8px;
    background: #f0f0f0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #ccc;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #bbb;
}
"""


class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._client = TeachboxClient(self)
        self._led_buzzer = 0
        self._tx_count = 0
        self._rx_count = 0
        self._ver_count = 0
        self._connect_signals()
        self._build_ui()
        self._apply_stylesheet()
        self._load_config()
        self._update_led_ui()

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

        QTimer.singleShot(200, lambda: self._log("系统就绪，点击「连接」开始"))

    def _apply_stylesheet(self):
        self.setStyleSheet(STYLESHEET)

    def _config_path(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, "..", "..")
        return os.path.join(project_root, "config.ini")

    def _load_config(self) -> None:
        s = QSettings(self._config_path(), QSettings.IniFormat)
        self._le_ip.setText(s.value("hostIP", "192.168.0.21"))
        self._sp_port.setValue(int(s.value("port", "502")))

    def _save_config(self) -> None:
        s = QSettings(self._config_path(), QSettings.IniFormat)
        s.setValue("hostIP", self._le_ip.text().strip())
        s.setValue("port", self._sp_port.value())

    def _connect_signals(self) -> None:
        c = self._client
        c.connected.connect(self._on_connected)
        c.disconnected.connect(self._on_disconnected)
        c.frame_received.connect(self._on_frame_rx)
        c.frame_sent.connect(lambda cmd, f: self._on_frame_tx(cmd, f))
        c.error_occurred.connect(self._on_error)

    def _build_ui(self) -> None:
        self.setWindowTitle("CNC-TCPClient - 上位机模拟端")
        self.setMinimumSize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        root.addWidget(self._build_left_panel(), 1)
        root.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self):
        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setFrameShape(QFrame.NoFrame)

        lay = QVBoxLayout(container)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(self._build_conn_group())
        lay.addWidget(self._build_version_group())
        lay.addWidget(self._build_key_group())
        lay.addWidget(self._build_mpg_group())
        lay.addWidget(self._build_joystick_group())
        lay.addWidget(self._build_io_group())
        lay.addWidget(self._build_led_group())
        lay.addStretch()
        return scroll

    def _build_right_panel(self):
        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setFrameShape(QFrame.NoFrame)

        lay = QVBoxLayout(container)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(self._build_stats_group())
        lay.addWidget(self._build_log_group(), 1)
        return scroll

    def _build_conn_group(self) -> QGroupBox:
        g = QGroupBox("连接配置")
        lay = QHBoxLayout(g)

        lay.addWidget(QLabel("IP:"))
        self._le_ip = QLineEdit("192.168.0.21")
        self._le_ip.setFixedWidth(130)
        lay.addWidget(self._le_ip)

        lay.addWidget(QLabel("端口:"))
        self._sp_port = QSpinBox()
        self._sp_port.setRange(1, 65535)
        self._sp_port.setValue(502)
        self._sp_port.setFixedWidth(80)
        lay.addWidget(self._sp_port)

        self._btn_connect = QPushButton("连接")
        self._btn_connect.setFixedWidth(80)
        self._btn_connect.clicked.connect(self._on_connect_clicked)
        lay.addWidget(self._btn_connect)

        self._cb_auto_reconnect = QCheckBox("自动重连")
        self._cb_auto_reconnect.setChecked(True)
        lay.addWidget(self._cb_auto_reconnect)

        self._lb_conn_status = QLabel("未连接")
        self._lb_conn_status.setStyleSheet("color: #f44336; font-weight: bold;")
        lay.addWidget(self._lb_conn_status)
        lay.addStretch()
        return g

    def _build_version_group(self) -> QGroupBox:
        g = QGroupBox("版本 (0x01)")
        lay = QVBoxLayout(g)
        lay.setSpacing(6)

        self._lb_version = self._data_label("-")
        lay.addWidget(self._lb_version)

        row = QHBoxLayout()
        self._cb_ver_auto = QCheckBox("自动响应")
        self._cb_ver_auto.setChecked(True)
        row.addWidget(self._cb_ver_auto)
        self._btn_ver_send = QPushButton("手动发送")
        self._btn_ver_send.setFixedWidth(100)
        self._btn_ver_send.clicked.connect(self._send_version)
        row.addWidget(self._btn_ver_send)
        row.addStretch()
        lay.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("握手次数:"))
        self._lb_ver_count = QLabel("0")
        self._lb_ver_count.setStyleSheet("color: #666;")
        row2.addWidget(self._lb_ver_count)
        row2.addStretch()
        lay.addLayout(row2)
        return g

    def _build_key_group(self) -> QGroupBox:
        g = QGroupBox("按键 (0x02)")
        lay = QFormLayout(g)
        lay.setSpacing(4)

        self._lb_key_hex = self._data_label("0x00000000 00000000")
        self._lb_key_parsed = QLabel("无按键")
        self._lb_key_parsed.setStyleSheet("color: #4CAF50; font-family: Consolas; font-size: 9pt;")
        lay.addRow("原始:", self._lb_key_hex)
        lay.addRow("解析:", self._lb_key_parsed)
        return g

    def _build_mpg_group(self) -> QGroupBox:
        g = QGroupBox("MPG (0x03)")
        lay = QFormLayout(g)
        self._lb_mpg_hex = self._data_label("0x00000000 00000000")
        self._lb_mpg_parsed = QLabel("Total:0  Inc:0")
        self._lb_mpg_parsed.setStyleSheet("color: #FF9800; font-family: Consolas; font-size: 9pt;")
        lay.addRow("原始:", self._lb_mpg_hex)
        lay.addRow("解析:", self._lb_mpg_parsed)
        return g

    def _build_joystick_group(self) -> QGroupBox:
        g = QGroupBox("摇杆 (0x04)")
        lay = QFormLayout(g)
        self._lb_joy_hex = self._data_label("0x00000000 00000000")
        self._lb_joy_parsed = QLabel("x:0  y:0  z:0  key:0")
        self._lb_joy_parsed.setStyleSheet("color: #2196F3; font-family: Consolas; font-size: 9pt;")
        lay.addRow("原始:", self._lb_joy_hex)
        lay.addRow("解析:", self._lb_joy_parsed)
        return g

    def _build_io_group(self) -> QGroupBox:
        g = QGroupBox("IO/钥匙 (0x05)")
        lay = QFormLayout(g)
        self._lb_io_hex = self._data_label("0x00000000 00000000")
        self._lb_io_parsed = QLabel("IO1:0  IO2:0")
        self._lb_io_parsed.setStyleSheet("color: #666; font-family: Consolas; font-size: 9pt;")
        lay.addRow("原始:", self._lb_io_hex)
        lay.addRow("解析:", self._lb_io_parsed)
        return g

    def _build_led_group(self) -> QGroupBox:
        g = QGroupBox("LED / 蜂鸣器 (0x07)")
        lay = QFormLayout(g)
        lay.setSpacing(4)

        self._led_frame = LEDFrame()
        self._led_frame.state_changed.connect(self._send_led_buzzer)
        lay.addRow(self._led_frame)

        self._lb_led_hex = self._data_label("0x00 00 00 00 00 00 00 00")
        self._lb_led_parsed = QLabel("全关")
        self._lb_led_parsed.setStyleSheet("color: #4CAF50; font-family: Consolas; font-size: 9pt;")
        lay.addRow("原始:", self._lb_led_hex)
        lay.addRow("解析:", self._lb_led_parsed)
        return g

    def _build_log_group(self) -> QGroupBox:
        g = QGroupBox("日志")
        lay = QVBoxLayout(g)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        lay.addWidget(self._log_text)
        btn_clear = QPushButton("清除")
        btn_clear.setFixedWidth(80)
        btn_clear.clicked.connect(self._log_text.clear)
        h = QHBoxLayout()
        h.addWidget(btn_clear)
        h.addStretch()
        lay.addLayout(h)
        return g

    def _build_stats_group(self) -> QGroupBox:
        g = QGroupBox("统计")
        lay = QFormLayout(g)
        self._lb_tx = QLabel("0")
        self._lb_rx = QLabel("0")
        lay.addRow("发送:", self._lb_tx)
        lay.addRow("接收:", self._lb_rx)
        return g

    def _data_label(self, text: str) -> QLabel:
        lb = QLabel(text)
        lb.setStyleSheet(
            "background: #f5f5f5; border: 1px solid #e0e0e0; "
            "border-radius: 4px; padding: 4px 8px; "
            "font-family: Consolas; font-size: 10pt; color: #333;"
        )
        return lb

    # ─── 信号处理 ──────────────────────────────

    def _on_frame_rx(self, cmd: int, payload: bytes) -> None:
        self._lb_rx.setText(str(int(self._lb_rx.text()) + 1))
        name = CMD.NAMES.get(cmd, f"0x{cmd:02X}")
        hex_str = frame_hex(bytes([cmd]) + payload)

        handlers = {
            CMD.VERSION: self._on_rx_version,
            CMD.KEY: self._on_rx_key,
            CMD.MPG: self._on_rx_mpg,
            CMD.JOYSTICK: self._on_rx_joystick,
            CMD.IO: self._on_rx_io,
            CMD.LED_BUZZER: self._on_rx_led_buzzer,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(payload, hex_str)
        else:
            self._log(f"[RX] 未知功能码 0x{cmd:02X}  {hex_str}")

    def _on_rx_version(self, payload: bytes, hex_str: str) -> None:
        self._lb_version.setText("v1.0 (已握手)")
        self._ver_count += 1
        self._lb_ver_count.setText(str(self._ver_count))
        self._log(f"[RX] 0x01 版本  {hex_str}")
        if self._cb_ver_auto.isChecked():
            self._client.send_frame(build_version_frame())
            self._log(f"[TX] 0x01 版本响应")

    def _on_rx_key(self, payload: bytes, hex_str: str) -> None:
        k1, k2 = parse_key_data(payload)
        raw_hex = f"0x{payload[0]:02X}{payload[1]:02X}{payload[2]:02X}{payload[3]:02X} {payload[4]:02X}{payload[5]:02X}{payload[6]:02X}{payload[7]:02X}"
        self._lb_key_hex.setText(raw_hex)
        active = []
        combined = k1 | (k2 << 32)
        for i in range(63):
            if combined & (1 << i):
                active.append(f"K{i+1}")
        self._lb_key_parsed.setText(', '.join(active) if active else '无按键')
        self._log(f"[RX] 0x02 按键  Key1=0x{k1:08X}  Key2=0x{k2:08X}")
        self._send_0x07_response()

    def _on_rx_mpg(self, payload: bytes, hex_str: str) -> None:
        total, inc = parse_mpg_data(payload)
        raw_hex = f"0x{payload[0]:02X}{payload[1]:02X}{payload[2]:02X}{payload[3]:02X} {payload[4]:02X}{payload[5]:02X}{payload[6]:02X}{payload[7]:02X}"
        self._lb_mpg_hex.setText(raw_hex)
        self._lb_mpg_parsed.setText(f"Total:{total}  Inc:{inc}")
        self._log(f"[RX] 0x03 MPG  total={total}  inc={inc}")
        self._send_0x07_response()

    def _on_rx_joystick(self, payload: bytes, hex_str: str) -> None:
        x, y, z, key = parse_joystick_data(payload)
        raw_hex = f"0x{payload[0]:02X}{payload[1]:02X}{payload[2]:02X}{payload[3]:02X} {payload[4]:02X}{payload[5]:02X}{payload[6]:02X}{payload[7]:02X}"
        self._lb_joy_hex.setText(raw_hex)
        self._lb_joy_parsed.setText(f"x:{x}  y:{y}  z:{z}  key:{key}")
        self._log(f"[RX] 0x04 摇杆  x={x} y={y} z={z} key={key}")
        self._send_0x07_response()

    def _on_rx_io(self, payload: bytes, hex_str: str) -> None:
        io1, io2 = parse_io_data(payload)
        raw_hex = f"0x{payload[0]:02X}{payload[1]:02X}{payload[2]:02X}{payload[3]:02X} {payload[4]:02X}{payload[5]:02X}{payload[6]:02X}{payload[7]:02X}"
        self._lb_io_hex.setText(raw_hex)
        self._lb_io_parsed.setText(f"IO1:{io1}  IO2:{io2}")
        self._log(f"[RX] 0x05 IO  IO1=0x{io1:08X}  IO2=0x{io2:08X}")
        self._send_0x07_response()

    def _on_rx_led_buzzer(self, payload: bytes, hex_str: str) -> None:
        x2 = parse_led_buzzer_byte(payload)
        raw_hex = f"0x{payload[0]:02X} {payload[1]:02X} {payload[2]:02X} {payload[3]:02X} {payload[4]:02X} {payload[5]:02X} {payload[6]:02X} {payload[7]:02X}"
        self._lb_led_hex.setText(raw_hex)
        state = led_buzzer_decode(x2)
        bits = [f"LED{i}" for i in range(1, 10) if state[f'led{i}']]
        if state['buzzer']:
            bits.append("蜂鸣器")
        self._lb_led_parsed.setText(', '.join(bits) if bits else '全关')
        self._led_frame.update_state(x2)
        self._log(f"[RX] 0x07 LED/蜂鸣器(服务端)  X2=0x{x2:04X}")

    def _send_version(self) -> None:
        self._client.send_frame(build_version_frame())
        self._log(f"[TX] 0x01 版本响应（手动）")

    def _send_0x07_response(self) -> None:
        self._led_buzzer = self._led_frame.get_state()
        frame = build_led_buzzer_frame(self._led_buzzer)
        self._client.send_frame(frame)
        raw_hex = f"0x{frame[0]:02X} {frame[1]:02X} {frame[2]:02X} {frame[3]:02X} {frame[4]:02X} {frame[5]:02X} {frame[6]:02X} {frame[7]:02X}"
        self._lb_led_hex.setText(raw_hex)
        state = led_buzzer_decode(self._led_buzzer)
        bits = [f"LED{i}" for i in range(1, 10) if state[f'led{i}']]
        if state['buzzer']:
            bits.append("蜂鸣器")
        self._lb_led_parsed.setText(', '.join(bits) if bits else '全关')
        self._log(f"[TX] 0x07 LED/蜂鸣器  X2=0x{self._led_buzzer:04X}")

    def _send_led_buzzer(self) -> None:
        self._send_0x07_response()

    def _on_connect_clicked(self) -> None:
        if self._client.is_connected():
            self._client.stop()
            self._save_config()
        else:
            self._client.set_target(self._le_ip.text().strip(), self._sp_port.value())
            self._client.enable_auto_reconnect(self._cb_auto_reconnect.isChecked())
            self._client.start()
            self._save_config()

    def _on_connected(self) -> None:
        self._btn_connect.setText("断开")
        self._lb_conn_status.setText("已连接")
        self._lb_conn_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self._log(f"★ 已连接到 {self._le_ip.text()}:{self._sp_port.value()}")

    def _on_disconnected(self) -> None:
        self._btn_connect.setText("连接")
        self._lb_conn_status.setText("未连接")
        self._lb_conn_status.setStyleSheet("color: #f44336; font-weight: bold;")
        self._log("✗ 连接已断开")
        self._led_frame.reset_all()

    def _on_error(self, msg: str) -> None:
        self._log(f"⚠ {msg}")

    def _on_frame_tx(self, cmd: int, frame: bytes) -> None:
        self._lb_tx.setText(str(int(self._lb_tx.text()) + 1))

    def _update_led_ui(self) -> None:
        state = led_buzzer_decode(self._led_buzzer)
        for i, led in enumerate(self._led_frame.leds):
            led.is_on = state[f'led{i + 1}']
        self._led_frame.buzzer.is_on = state['buzzer']

    def _update_stats(self) -> None:
        tx, rx = self._client.stats()
        self._lb_tx.setText(str(tx))
        self._lb_rx.setText(str(rx))

    def _log(self, msg: str) -> None:
        t = time.strftime("%H:%M:%S")
        self._log_text.append(f"[{t}] {msg}")

    def closeEvent(self, e) -> None:
        self._client.stop()
        self._save_config()
        e.accept()
