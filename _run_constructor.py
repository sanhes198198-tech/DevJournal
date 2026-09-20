import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from app.constructor.constructor_window import ConstructorWindow


def main():
    app = QApplication(sys.argv)
    w = ConstructorWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())