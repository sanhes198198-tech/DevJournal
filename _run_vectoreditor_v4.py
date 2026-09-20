import sys
from PySide6.QtWidgets import QApplication
from app.vector_editor.editor import VectorEditor

def main():
    app = QApplication(sys.argv)
    w = VectorEditor()
    w.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())