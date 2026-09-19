"""
Render-слой. Рисует архитектурные элементы.

Не знает про view (scene/canvas/items).
Получает painter и данные — рисует.
"""

from .plan_renderer import PlanRenderer

__all__ = ["PlanRenderer"]
