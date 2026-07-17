"""
CNC-TCPClient 入口点
启动PyQt5应用程序
"""

from __future__ import annotations

import sys
import os

# Add src directory to path when running as script
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.abspath(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

from PyQt5.QtWidgets import QApplication

from ui.main_window import ClientWindow


def main() -> int:
    """
    应用程序主入口
    
    返回:
        应用程序退出代码
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ClientWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
