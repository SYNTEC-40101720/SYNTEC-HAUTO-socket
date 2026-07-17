"""
CNC-TCPClient - 自定义 UI 组件
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QFont


class LEDWidget(QWidget):
    clicked = pyqtSignal()

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

    def set_on(self):
        self._is_on = True
        self.update()

    def set_off(self):
        self._is_on = False
        self.update()

    def toggle(self):
        self._is_on = not self._is_on
        self.update()
        self.clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
        super().mousePressEvent(event)

    def paintEvent(self, event):
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
    def __init__(self, parent=None):
        super().__init__(name="BUZ", on_color="#f44336", off_color="#ccc", parent=parent)
        self.setFixedSize(28, 22)


class LEDFrame(QFrame):
    state_changed = pyqtSignal()

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

    def get_state(self) -> int:
        state = 0
        for i in range(9):
            if self._leds[i].is_on:
                state |= (1 << i)
        if self._buzzer.is_on:
            state |= 0x8000
        return state

    def update_state(self, state: int):
        for i in range(9):
            self._leds[i].is_on = bool(state & (1 << i))
        self._buzzer.is_on = bool(state & 0x8000)

    def reset_all(self):
        for led in self._leds:
            led.set_off()
        self._buzzer.set_off()

    def _build_ui(self):
        h = QHBoxLayout(self)
        h.setSpacing(6)
        h.setContentsMargins(8, 4, 8, 4)

        for i in range(9):
            led = LEDWidget(name=f"L{i+1}")
            led.clicked.connect(self.state_changed.emit)
            self._leds.append(led)
            h.addWidget(led, alignment=Qt.AlignCenter)

        self._buzzer.clicked.connect(self.state_changed.emit)
        h.addWidget(self._buzzer, alignment=Qt.AlignCenter)
        h.addStretch()
