import sys
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QFont, QFontDatabase

app = QApplication(sys.argv)

print("=== Доступные шрифты (первые 10) ===")
for fam in QFontDatabase.families()[:10]:
    print(fam)

print()
print("=== Segoe UI есть? ===")
print("Segoe UI" in QFontDatabase.families())

label = QLabel("Проверка русского: Комментарий Заголовок Автор")
label.setFont(QFont("Segoe UI", 14))
label.setFixedSize(700, 100)
label.show()

sys.exit(app.exec())