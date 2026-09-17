import sys
import locale
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication, QLabel

print("=== Python ===")
print("locale.getpreferredencoding:", locale.getpreferredencoding(False))
print("sys.getfilesystemencoding:", sys.getfilesystemencoding())

app = QApplication(sys.argv)

print("=== Qt ===")
q = QLocale()
print("QLocale.name():", q.name())
print("QLocale.system().name():", QLocale.system().name())

s = "Комментарий"
print("Python repr(s):", repr(s))

label = QLabel(s)
print("QLabel.text() repr:", repr(label.text()))