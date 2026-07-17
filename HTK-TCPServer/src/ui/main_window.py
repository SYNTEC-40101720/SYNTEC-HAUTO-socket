"""
HTK-TCPServer - 主窗口 UI
"""

from __future__ import annotations

import os
import json
import sys

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QSpinBox,
    QCheckBox, QPushButton,
    QFrame, QRadioButton
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCloseEvent

from src.server import TeachboxServer
from src.protocol import (
    CMD,
    build_version_frame, build_key_frame, build_mpg_frame,
    build_io_frame,
    parse_led_buzzer_byte,
)
from src.ui.widgets import LEDFrame, TwoLineButton

# ─── 全局样式 ──────────────────────────────────

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
QSpinBox:focus, QDoubleSpinBox:focus {
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
QRadioButton {
    font-size: 10pt;
    spacing: 6px;
}

QLabel {
    font-size: 10pt;
    color: #333;
}

QScrollArea {
    border: none;
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

.data-box {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: Consolas;
}
.data-label {
    font-size: 9pt;
    color: #666;
}
"""


KEY_BTN_STYLE_TEMPLATE = """\
QPushButton {
    background: #f0f0f0;
    border: 2px solid #bbb;
    border-radius: 3px;
    padding: 1px 3px;
    font-size: 9pt;
    color: #333;
}
QPushButton:checked {
    background: #4CAF50;
    color: white;
    font-weight: bold;
    border: 2px solid #388E3C;
}
QPushButton:pressed {
    background: #81C784;
    color: white;
}
"""


class ServerWindow(QMainWindow):
    """示教器模拟端主窗口"""

    def __init__(self):
        super().__init__()
        self._server = TeachboxServer(self)
        self._connect_signals()
        self._mpg_dir = 1
        self._key_names, self._key_colors = self._load_key_config()
        self._build_ui()
        self._apply_stylesheet()

        self._ver_timer = QTimer(self)
        self._ver_timer.timeout.connect(self._send_version)
        self._ver_timer.start(1000)

        self._mpg_timer = QTimer(self)
        self._mpg_timer.timeout.connect(self._on_mpg_tick)

        self._mpg_hold_timer = QTimer(self)
        self._mpg_hold_timer.setSingleShot(True)
        self._mpg_hold_timer.timeout.connect(self._start_mpg_continuous)

    def _apply_stylesheet(self):
        self.setStyleSheet(STYLESHEET)

    def _load_key_config(self) -> tuple[list[str], list[str]]:
        """
        加载按键配置

        从项目根目录 keys.json 读取自定义按键名称和颜色。
        文件不存在或格式错误时返回默认配置。

        返回:
            tuple[list[str], list[str]]: (按键名称列表, 颜色列表)
        """
        default_names = [f"K{i+1}" for i in range(63)]
        default_colors = ["#f0f0f0"] * 63
        try:
            config_path = None
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包后，尝试多个可能的路径
                possible_paths = [
                    os.path.join(sys._MEIPASS, "keys.json"),
                    os.path.join(os.path.dirname(sys.executable), "keys.json"),
                    os.path.join(os.path.dirname(sys.executable), "_internal", "keys.json"),
                ]
                for path in possible_paths:
                    if os.path.isfile(path):
                        config_path = path
                        break
            else:
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "keys.json"
                )
            if not config_path or not os.path.isfile(config_path):
                return default_names, default_colors
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return default_names, default_colors
            
            names = []
            colors = []
            for i in range(63):
                key_data = data.get(f"K{i+1}", {})
                if isinstance(key_data, dict):
                    names.append(key_data.get("name", f"K{i+1}"))
                    colors.append(key_data.get("color", "#f0f0f0"))
                else:
                    # 兼容旧格式
                    names.append(str(key_data) if key_data else f"K{i+1}")
                    colors.append("#f0f0f0")
            return names, colors
        except (json.JSONDecodeError, OSError):
            return default_names, default_colors

    def _get_key_name(self, index: int) -> str:
        """
        获取按键显示名称

        参数:
            index: 按键索引 (0-62)

        返回:
            str: 按键显示名称
        """
        return self._key_names[index] if 0 <= index < 63 else f"K{index+1}"

    def _connect_signals(self):
        s = self._server
        s.client_connected.connect(self._on_client_conn)
        s.client_disconnected.connect(self._on_client_disc)
        s.frame_received.connect(self._on_frame_rx)
        s.socket_error.connect(self._on_socket_err)

    def _build_ui(self):
        self.setWindowTitle("HTK-TCPServer - 示教器模拟端")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(4, 4, 4, 4)

        root.addWidget(self._build_control_group())
        root.addWidget(self._build_key_group(), 1)

    def _build_control_group(self) -> QGroupBox:
        g = QGroupBox("控制面板")
        lay = QGridLayout(g)
        lay.setSpacing(4)
        lay.setContentsMargins(6, 2, 6, 6)

        self._build_server_section(lay, 0, 0, 1, 2)
        self._build_led_section(lay, 1, 0, 1, 2)
        self._build_io_section(lay, 2, 0)
        self._build_mpg_section(lay, 2, 1)

        lay.setColumnStretch(0, 1)
        lay.setColumnStretch(1, 1)
        lay.setRowStretch(0, 0)
        lay.setRowStretch(1, 0)
        lay.setRowStretch(2, 0)
        return g

    def _build_server_section(self, lay: QGridLayout, row_idx, col_idx, row_span=1, col_span=1):
        r1 = QHBoxLayout()
        r1.setSpacing(6)
        self._btn_start = QPushButton("启动服务")
        self._btn_start.setMinimumWidth(80)
        self._btn_start.clicked.connect(self._on_start_stop)
        r1.addWidget(self._btn_start)
        r1.addWidget(QLabel("端口:"))
        self._sp_port = QSpinBox()
        self._sp_port.setRange(1, 65535)
        self._sp_port.setValue(802)
        self._sp_port.setFixedWidth(70)
        r1.addWidget(self._sp_port)
        self._lb_server_status = QLabel("已停止")
        self._lb_server_status.setStyleSheet("color: #f44336; font-weight: bold;")
        r1.addWidget(self._lb_server_status)
        r1.addStretch()
        lay.addLayout(r1, row_idx, col_idx, row_span, col_span, Qt.AlignVCenter)

    def _build_led_section(self, lay: QGridLayout, row_idx, col_idx, row_span=1, col_span=1):
        v = QVBoxLayout()
        v.setSpacing(0)
        v.setContentsMargins(0, 0, 0, 0)
        self._led_frame = LEDFrame()
        self._led_frame.setFixedHeight(40)
        v.addWidget(self._led_frame)
        lay.addLayout(v, row_idx, col_idx, row_span, col_span, Qt.AlignTop)

    def _build_io_section(self, lay: QGridLayout, row_idx, col_idx, row_span=1, col_span=1):
        v = QHBoxLayout()
        v.setSpacing(8)
        self._rb_io_auto = QRadioButton("自动")
        self._rb_io_manual = QRadioButton("手动")
        self._rb_io_remote = QRadioButton("远程")
        self._rb_io_manual.setChecked(True)
        self._rb_io_auto.toggled.connect(self._on_io_mode_changed)
        self._rb_io_manual.toggled.connect(self._on_io_mode_changed)
        self._rb_io_remote.toggled.connect(self._on_io_mode_changed)
        v.addWidget(self._rb_io_auto)
        v.addWidget(self._rb_io_manual)
        v.addWidget(self._rb_io_remote)
        v.addStretch()
        lay.addLayout(v, row_idx, col_idx, row_span, col_span, Qt.AlignVCenter)

    def _build_mpg_section(self, lay: QGridLayout, row_idx, col_idx, row_span=1, col_span=1):
        v = QHBoxLayout()
        v.setSpacing(6)

        self._sp_mpg_total = QSpinBox()
        self._sp_mpg_total.setRange(-2147483648, 2147483647)
        self._sp_mpg_total.setReadOnly(True)
        self._sp_mpg_total.setAlignment(Qt.AlignCenter)
        self._sp_mpg_total.setFixedWidth(120)
        v.addWidget(self._sp_mpg_total)

        self._btn_mpg_reverse = QPushButton("反向")
        self._btn_mpg_reverse.setFixedHeight(32)
        self._btn_mpg_reverse.setStyleSheet(
            "background: #FF9800; color: white; font-weight: bold; "
            "border: none; border-radius: 4px; font-size: 11pt;"
        )
        self._btn_mpg_reverse.pressed.connect(lambda: self._on_mpg_btn_press(-1))
        self._btn_mpg_reverse.released.connect(self._on_mpg_btn_release)
        v.addWidget(self._btn_mpg_reverse)

        self._btn_mpg_forward = QPushButton("正向")
        self._btn_mpg_forward.setFixedHeight(32)
        self._btn_mpg_forward.setStyleSheet(
            "background: #4CAF50; color: white; font-weight: bold; "
            "border: none; border-radius: 4px; font-size: 11pt;"
        )
        self._btn_mpg_forward.pressed.connect(lambda: self._on_mpg_btn_press(1))
        self._btn_mpg_forward.released.connect(self._on_mpg_btn_release)
        v.addWidget(self._btn_mpg_forward)
        v.addStretch()
        lay.addLayout(v, row_idx, col_idx, row_span, col_span, Qt.AlignVCenter)

    def _build_key_group(self) -> QGroupBox:
        g = QGroupBox("按键模拟")
        lay = QVBoxLayout(g)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)

        grid = QGridLayout()
        grid.setVerticalSpacing(3)
        grid.setHorizontalSpacing(4)
        grid.setAlignment(Qt.AlignTop)
        
        # 预分配按键列表，确保 _key_btns[i] 对应逻辑 K(i+1)
        self._key_btns: list = [None] * 63
        # 普通按键按下状态跟踪
        self._key_state = [False] * 63

        # 按键布局：9行×7列简单矩阵排列，K1-K63 顺序排列
        for i in range(63):
            row = i // 7
            col = i % 7
            
            key_name = self._get_key_name(i)
            color = self._key_colors[i]
            
            # 两行文本的按键使用 TwoLineButton
            if '\n' in key_name:
                # K15 和 K21 是组合键，整个方块都是组合键颜色
                full_bg = i in [14, 20]  # K15=14, K21=20
                btn = TwoLineButton(key_name, color, full_bg)
            else:
                btn = QPushButton(key_name)
                btn.setMinimumHeight(42)
                btn.setMaximumHeight(42)
                btn.setStyleSheet(
                    f"QPushButton {{ background: {color}; border: 2px solid #bbb; "
                    f"border-radius: 3px; padding: 1px 3px; font-size: 9pt; color: #333; }}"
                )
            
            self._key_btns[i] = btn

            btn.pressed.connect(lambda idx=i: self._on_key_press(idx))
            btn.released.connect(lambda idx=i: self._on_key_release(idx))

            grid.addWidget(btn, row, col)

        lay.addLayout(grid)
        return g

    # Shift 组合键索引（自锁按键：单击保持，再单击解除）
    _SHIFT_KEYS = {14, 20}  # K15=14, K21=20

    def _on_key_press(self, index: int):
        """
        普通按键按下处理
        Shift 键（K15/K21）为自锁模式：单击切换锁定/解锁状态

        参数:
            index: 按键索引 (0-62)
        """
        if index in self._SHIFT_KEYS:
            # 自锁模式：切换状态
            self._key_state[index] = not self._key_state[index]
            btn = self._key_btns[index]
            if isinstance(btn, TwoLineButton):
                btn.set_pressed(self._key_state[index])
            self._send_key()
            return

        self._key_state[index] = True
        btn = self._key_btns[index]
        
        # 处理 TwoLineButton
        if isinstance(btn, TwoLineButton):
            btn.set_pressed(True)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: #81C784;
                    color: white;
                    border: 2px solid #4CAF50;
                    border-radius: 3px;
                    padding: 1px 3px;
                    font-size: 9pt;
                }
            """)
        self._send_key()

    def _on_key_release(self, index: int):
        """
        普通按键释放处理
        Shift 键（K15/K21）为自锁模式，松开时不释放状态

        参数:
            index: 按键索引 (0-62)
        """
        if index in self._SHIFT_KEYS:
            # 自锁键：鼠标松开不作为，保留当前锁定状态
            return

        self._key_state[index] = False
        btn = self._key_btns[index]
        
        # 处理 TwoLineButton
        if isinstance(btn, TwoLineButton):
            btn.set_pressed(False)
        else:
            # 恢复为配置的颜色
            color = self._key_colors[index]
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; border: 2px solid #bbb; "
                f"border-radius: 3px; padding: 1px 3px; font-size: 9pt; color: #333; }}"
            )
        self._send_key()

    # ─── 槽函数 ────────────────────────────────────

    def _on_start_stop(self):
        if self._server.is_listening():
            self._server.stop()
            self._btn_start.setText("启动服务")
            self._btn_start.setStyleSheet("")
            self._lb_server_status.setText("已停止")
            self._lb_server_status.setStyleSheet("color: #f44336;")
        else:
            port = self._sp_port.value()
            if self._server.start(port):
                self._btn_start.setText("停止服务")
                self._btn_start.setStyleSheet("background: #f44336;")
                self._lb_server_status.setText(f"监听 :{port}")
                self._lb_server_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _on_client_conn(self, ip: str, port: int):
        self._lb_server_status.setText(f"已连接 {ip}:{port}")
        self._lb_server_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _on_client_disc(self):
        port = self._sp_port.value()
        self._lb_server_status.setText(f"监听 :{port}")
        self._lb_server_status.setStyleSheet("color: #4CAF50;")
        self._led_frame.reset_all()

    def _on_frame_rx(self, cmd: int, payload: bytes):
        if cmd == CMD.LED_BUZZER:
            state_int = parse_led_buzzer_byte(payload)
            self._led_frame.update_state(state_int)

    def _on_socket_err(self, msg: str):
        # Socket errors are handled by UI feedback; no additional action needed
        pass

    def _send_version(self):
        frame = build_version_frame()
        self._server.send_frame(frame)

    def _send_key(self):
        """
        根据当前按键状态发送按键帧
        """
        k1 = k2 = 0
        for i in range(63):
            if self._key_state[i]:
                if i < 32:
                    k1 |= (1 << i)
                else:
                    k2 |= (1 << (i - 32))
        frame = build_key_frame(k1, k2)
        self._server.send_frame(frame)

    def _on_mpg_btn_press(self, direction: int):
        """短按一次，长按后持续"""
        self._mpg_dir = direction
        self._on_mpg_tick()
        self._mpg_hold_timer.start(300)

    def _on_mpg_btn_release(self):
        self._mpg_hold_timer.stop()
        self._mpg_timer.stop()

    def _start_mpg_continuous(self):
        self._mpg_timer.start(100)

    def _on_mpg_tick(self):
        total = self._sp_mpg_total.value() + self._mpg_dir
        self._sp_mpg_total.setValue(total)
        frame = build_mpg_frame(total, self._mpg_dir)
        self._server.send_frame(frame)

    def _on_io_mode_changed(self, checked: bool):
        if not checked:
            return
        self._send_io()

    def _send_io(self):
        mode = 1 if self._rb_io_auto.isChecked() else (0 if self._rb_io_manual.isChecked() else 2)
        frame = build_io_frame(mode, 0)
        self._server.send_frame(frame)

    def closeEvent(self, e: QCloseEvent):
        self._server.stop()
        e.accept()
