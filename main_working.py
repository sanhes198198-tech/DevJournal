import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from app.window import DevJournal


def main():
    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)

    window = DevJournal()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()