"""
HTK-TCPServer - 示教器 TCP 服务端模拟器
模拟示教器（服务端）行为，用于测试 CNC-TCPClient
用法: python main.py
"""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import ServerWindow


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ServerWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
