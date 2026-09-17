from PySide6.QtCore import QPointF

from .routed_arrow import RoutedArrowItem


def create_arrow(
    scene,
    source_item,
    target_item=None,
    free_end=None,
):
    """
    Создаёт стрелку через новый UI-модуль.

    Вся логика создания стрелки находится здесь,
    чтобы Canvas не содержал реализацию новой системы.
    """

    if scene is None:
        return None

    if source_item is None:
        return None

    if target_item is None and free_end is None:
        try:
            scene_rect = source_item.sceneBoundingRect()

            free_end = QPointF(
                scene_rect.right() + 120.0,
                scene_rect.center().y(),
            )

        except Exception:
            try:
                free_end = QPointF(
                    source_item.x() + 200.0,
                    source_item.y() + 100.0,
                )
            except Exception:
                return None

    try:
        arrow = RoutedArrowItem(
            source_item=source_item,
            target_item=target_item,
            free_end=free_end,
        )
    except TypeError:
        try:
            arrow = RoutedArrowItem(
                source_item,
                target_item,
                free_end,
            )
        except Exception:
            return None
    except Exception:
        return None

    try:
        scene.addItem(arrow)
    except Exception:
        return None

    try:
        arrow.setSelected(True)
    except Exception:
        pass

    return arrow


def create_free_arrow(
    scene,
    source_item,
):
    """
    Создаёт стрелку со свободным концом.
    """

    return create_arrow(
        scene=scene,
        source_item=source_item,
        target_item=None,
        free_end=None,
    )


def create_connected_arrow(
    scene,
    source_item,
    target_item,
):
    """
    Создаёт стрелку между двумя карточками.
    """

    if target_item is None:
        return None

    return create_arrow(
        scene=scene,
        source_item=source_item,
        target_item=target_item,
    )