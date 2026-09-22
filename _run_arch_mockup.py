"""
Лончер макета Architecture.
"""

import sys

from PySide6.QtWidgets import QApplication

from app.architecture.architecture_mockup import ArchitectureMockup


def main() -> int:
    app = QApplication(sys.argv)
    w = ArchitectureMockup()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
