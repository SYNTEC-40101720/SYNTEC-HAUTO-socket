"""
CNC-TCPClient - 示教器 TCP 客户端（上位机模拟）
完整实现协议：收到 0x01~0x05 后正确回帧，LED/蜂鸣器控制发送 0x07
用法: python main.py
"""

from __future__ import annotations

import sys
import os

# Add src directory to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from ui.main_window import ClientWindow


def main() -> int:
    """
    应用程序主入口
    
    返回:
        应用程序退出代码
    """
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ClientWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
