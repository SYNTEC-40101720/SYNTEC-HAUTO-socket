"""
HTK-TCPServer - 自定义 UI 组件
包含 LED 指示灯、LED 面板等控件
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QPushButton
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QFont, QPaintEvent


class LEDWidget(QWidget):
    """
    自定义绘制圆形 LED 指示灯
    """

    def __init__(self, name: str = "", on_color: str = "#4CAF50", off_color: str = "#ccc", parent=None):
        super().__init__(parent)
        self._name = name
        self._on_color = QColor(on_color)
        self._off_color = QColor(off_color)
        self._is_on = False
        self.setFixedSize(22, 22)
        self.setToolTip(name)

    @property
    def is_on(self) -> bool:
        return self._is_on

    @is_on.setter
    def is_on(self, value: bool):
        self._is_on = value
        self.update()

    def set_on(self) -> None:
        self._is_on = True
        self.update()

    def set_off(self) -> None:
        self._is_on = False
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width() - 2, self.height() - 2
        rect = QRectF(1, 1, w, h)
        color = self._on_color if self._is_on else self._off_color

        gradient = QRadialGradient(w / 2 + 1, h / 2 + 1, w * 0.4)
        gradient.setColorAt(0, color.lighter(140))
        gradient.setColorAt(1, color.darker(120))

        painter.setBrush(gradient)
        painter.setPen(QColor(color.darker(150)))
        painter.drawEllipse(rect)

        if self._name:
            painter.setPen(QColor("#666") if not self._is_on else QColor("#fff"))
            painter.setFont(QFont("Arial", 6, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, self._name)


class BuzzerWidget(LEDWidget):
    """蜂鸣器指示灯"""

    def __init__(self, parent=None):
        super().__init__(name="BUZ", on_color="#f44336", off_color="#ccc", parent=parent)
        self.setFixedSize(28, 22)


class LEDFrame(QFrame):
    """
    LED + 蜂鸣器状态面板
    9 个 LED 排成一行 + 蜂鸣器
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #f5f5f5; border: 1px solid #e0e0e0; border-radius: 6px; padding: 6px; }"
        )
        self._leds: list[LEDWidget] = []
        self._buzzer = BuzzerWidget()
        self._build_ui()

    @property
    def leds(self) -> list[LEDWidget]:
        return self._leds

    @property
    def buzzer(self) -> BuzzerWidget:
        return self._buzzer

    def update_state(self, state: int) -> None:
        for i in range(9):
            self._leds[i].is_on = bool(state & (1 << i))
        self._buzzer.is_on = bool(state & 0x8000)

    def reset_all(self) -> None:
        for led in self._leds:
            led.set_off()
        self._buzzer.set_off()

    def _build_ui(self) -> None:
        h = QHBoxLayout(self)
        h.setSpacing(6)
        h.setContentsMargins(8, 4, 8, 4)

        for i in range(9):
            led = LEDWidget(name=f"L{i+1}")
            self._leds.append(led)
            h.addWidget(led, alignment=Qt.AlignCenter)

        h.addWidget(self._buzzer, alignment=Qt.AlignCenter)
        h.addStretch()


class TwoLineButton(QPushButton):
    """
    两行文本按钮，支持两种背景模式
    full_bg: True - 整个方块都是组合键颜色 #61CBF4
    full_bg: False - 上半部分组合键颜色，下半部分白色
    所有文字：黑色
    """

    def __init__(self, text: str, bg_color: str = "#f0f0f0", full_bg: bool = False, parent=None):
        super().__init__(parent)
        self._bg_color = bg_color
        self._text_lines = text.split('\n') if '\n' in text else [text]
        self._full_bg = full_bg
        self._is_pressed = False
        self.setMinimumHeight(42)
        self.setMaximumHeight(42)

    def set_pressed(self, pressed: bool):
        """设置按下状态"""
        self._is_pressed = pressed
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """自定义绘制，实现两种背景模式"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        line_height = rect.height() // 2
        
        if self._full_bg:
            # 整个方块都是组合键颜色
            if self._is_pressed:
                painter.fillRect(rect, QColor("#81C784"))
            else:
                painter.fillRect(rect, QColor("#61CBF4"))
        else:
            # 上半部分组合键颜色，下半部分白色
            if self._is_pressed:
                painter.fillRect(0, 0, rect.width(), line_height, QColor("#81C784"))
                painter.fillRect(0, line_height, rect.width(), line_height, QColor("#81C784"))
            else:
                painter.fillRect(0, 0, rect.width(), line_height, QColor("#61CBF4"))
                painter.fillRect(0, line_height, rect.width(), line_height, QColor("#FFFFFF"))
        
        # 绘制边框
        if self._is_pressed:
            painter.setPen(QColor("#4CAF50"))
        else:
            painter.setPen(QColor("#bbb"))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        
        if len(self._text_lines) >= 2:
            # 上半部分文字：黑色
            painter.setPen(QColor("#000000"))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(
                QRectF(0, 2, rect.width(), line_height),
                Qt.AlignCenter,
                self._text_lines[0]
            )
            
            # 下半部分文字：黑色
            painter.setPen(QColor("#000000"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(
                QRectF(0, line_height, rect.width(), line_height),
                Qt.AlignCenter,
                self._text_lines[1]
            )
        else:
            # 单行文字：黑色
            painter.setPen(QColor("#000000"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(rect, Qt.AlignCenter, self._text_lines[0])
