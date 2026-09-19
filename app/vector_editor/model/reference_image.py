"""
ReferenceImage — картинка-подложка под контур Asset'а.

Хранит имя файла в assets/ + позицию (x,y в МЕТРАХ) + масштаб
(pixels_per_meter) + opacity + флаг видимости.

Формат файла всегда PNG. Конвертацию из произвольного формата
делает editor перед вызовом io.save_reference_image_png.

Модель чистая, без Qt.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReferenceImage:
    """Подложка под контур."""

    filename: str = ""
    x: float = 0.0
    y: float = 0.0
    pixels_per_meter: float = 50.0
    opacity: float = 0.5
    visible: bool = True

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        return bool(self.filename)

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "x": self.x,
            "y": self.y,
            "pixels_per_meter": self.pixels_per_meter,
            "opacity": self.opacity,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReferenceImage":
        return cls(
            filename=str(d.get("filename", "")),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            pixels_per_meter=float(
                d.get("pixels_per_meter", 50.0)
            ),
            opacity=float(d.get("opacity", 0.5)),
            visible=bool(d.get("visible", True)),
        )
