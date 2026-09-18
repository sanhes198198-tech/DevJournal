import re

path = "app/window.py"

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

changes = []

# Regex: находим блок Ctrl+C/V/A в eventFilter и заменяем
pattern = re.compile(
    r'(          if event\.type\(\) == event\.Type\.KeyPress:\n'
    r'\n'
    r'              mods = event\.modifiers\(\)\n'
    r'\n'
    r'              if mods & Qt\.KeyboardModifier\.ControlModifier:\n'
    r'\n'
    r'                  key = event\.key\(\)\n'
    r'(?:.*?\n)*?'
    r'                      return True\n)'
)

new = '''          if event.type() == event.Type.KeyPress:

              mods = event.modifiers()

              if mods & Qt.KeyboardModifier.ControlModifier:

                  key = event.key()

                  # =================================================
                  # Если фокус в тексте — НЕ перехватываем.
                  # =================================================

                  try:
                      focus_item = self.canvas.scene.focusItem()

                      if focus_item is not None:
                          type_name = type(focus_item).__name__

                          if type_name in (
                              "EditableText",
                              "CardTextItem",
                              "QGraphicsTextItem",
                          ):
                              return False
                  except Exception:
                      pass

                  if getattr(self, "active_text_item", None) is not None:
                      return False

                  # =================================================
                  # Иначе — карточки.
                  # =================================================

                  if key == Qt.Key.Key_C:

                      self._handle_ctrl_c()
                      return True

                  if key == Qt.Key.Key_V:

                      self._handle_ctrl_v()
                      return True

                  if key == Qt.Key.Key_A:

                      self._handle_ctrl_a()
                      return True
'''

new_src, count = pattern.subn(new, src, count=1)

if count > 0:
    src = new_src
    changes.append(f"eventFilter Ctrl block replaced (count={count})")
else:
    changes.append("WARN: regex did not match")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("Changes:", changes)