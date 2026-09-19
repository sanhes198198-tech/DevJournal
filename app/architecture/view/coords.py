"""
Y-конвертация между моделью и сценой.

ЕДИНСТВЕННОЕ место в проекте, где мы знаем что:
    Model:  Y ↑ (архитектурно)
    Scene:  Y ↓ (Qt-нативно)

Правило: любой код, переводящий координаты, использует эти
функции. Никаких -y в других местах.
"""

from __future__ import annotations


def model_pos_to_scene(model_x: float, model_y: float) -> tuple[float, float]:
    """Model Y↑ → Scene Y↓."""
    return (model_x, -model_y)


def scene_pos_to_model(scene_x: float, scene_y: float) -> tuple[float, float]:
    """Scene Y↓ → Model Y↑."""
    return (scene_x, -scene_y)
