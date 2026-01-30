#!/usr/bin/env python3

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app import MetaFolderApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetaFolderApp()
    window.show()
    sys.exit(app.exec())