from pathlib import Path

p = Path(r".\app\canvas\canvas.py")
s = p.read_text(encoding="utf-8-sig")

old = '''                    "path":
                        item.image_path,
                })'''

new = '''                    "path":
                        item.image_path,
                    "width":
                        item.pixmap().width(),
                    "height":
                        item.pixmap().height(),
                })'''

if old not in s:
    raise SystemExit("ОШИБКА: блок сохранения изображения не найден")

s = s.replace(old, new, 1)

start = s.index('                elif item_type == "image":')
end = s.index('                elif item_type == "file":', start)

block = s[start:end]

marker = '''                    item = ImageItem(
                        pixmap,
                        relative_path,
                    )'''

if marker not in block:
    raise SystemExit("ОШИБКА: создание ImageItem не найдено")

replacement = '''                    item = ImageItem(
                        pixmap,
                        relative_path,
                    )

                    saved_width = item_data.get("width")
                    saved_height = item_data.get("height")

                    if saved_width and saved_height:
                        scaled = pixmap.scaled(
                            int(saved_width),
                            int(saved_height),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                        item.setPixmap(scaled)

                    item.saved_scale = (
                        item.pixmap().width()
                        / max(1, item.original_width)
                    )'''

block = block.replace(marker, replacement, 1)

s = s[:start] + block + s[end:]

p.write_text(s, encoding="utf-8")

print("canvas.py успешно исправлен")
