path = "app/canvas/canvas.py"

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

changes = []

old = '''class Canvas(QGraphicsView):'''

new = '''class Canvas(QGraphicsView):

    def mousePressEvent(self, event):

        # DEACTIVATE TEXT ON EMPTY CLICK
        try:
            item = self.itemAt(event.pos())

            if item is None:

                window = getattr(self, "main_window", None)

                if window is None:
                    window = getattr(
                        getattr(self, "parent", None),
                        "main_window",
                        None,
                    )

                if window is not None:

                    deactivator = getattr(
                        window,
                        "deactivate_text",
                        None,
                    )

                    if callable(deactivator):
                        deactivator()

        except Exception:
            pass

        super().mousePressEvent(event)'''

if old in src and "DEACTIVATE TEXT ON EMPTY CLICK" not in src:
    src = src.replace(old, new, 1)
    changes.append("Canvas.mousePressEvent added")
else:
    changes.append("WARN: marker not found or exists")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("Changes:", changes)