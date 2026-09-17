"""
Модуль сохранения и восстановления стрелок.

Отвечает только за persistence RoutedArrowItem.

Для подключенной стрелки сохраняются:
- card_id источника;
- card_id цели;
- bend_offset.

Для стрелки со свободным концом сохраняются:
- card_id источника;
- координаты свободного конца;
- bend_offset.

Старое поле control_point поддерживается
только для совместимости со старыми board.json.
"""

from PySide6.QtCore import QPointF

from ..items.routed_arrow import RoutedArrowItem


# ============================================================
# HELPERS
# ============================================================

def _get_item_id(item):
    """
    Возвращает стабильный card_id объекта.
    """

    if item is None:
        return None

    card_id = getattr(
        item,
        "card_id",
        None,
    )

    if card_id is None:
        return None

    value = str(card_id).strip()

    if not value:
        return None

    return value


def _point_to_data(point):
    """
    Преобразует QPointF в JSON-совместимый словарь.
    """

    if point is None:
        return None

    try:
        return {
            "x": float(point.x()),
            "y": float(point.y()),
        }
    except (
        TypeError,
        AttributeError,
    ):
        return None


def _data_to_point(data):
    """
    Преобразует сохраненные координаты в QPointF.
    """

    if not isinstance(data, dict):
        return None

    try:
        return QPointF(
            float(data.get("x", 0.0)),
            float(data.get("y", 0.0)),
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# BEND
# ============================================================

def _get_bend_offset(arrow):
    """
    Возвращает текущее смещение точки изгиба.
    """

    controller = getattr(
        arrow,
        "_bend_controller",
        None,
    )

    if controller is None:
        return 0.0

    try:
        return float(
            controller.offset
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return 0.0


def _restore_bend(
    arrow,
    bend_offset,
):
    """
    Восстанавливает изгиб стрелки.
    """

    controller = getattr(
        arrow,
        "_bend_controller",
        None,
    )

    if controller is None:
        return

    try:
        controller.offset = float(
            bend_offset
        )
    except (
        TypeError,
        ValueError,
    ):
        return


def _restore_legacy_control_point(
    arrow,
    control_point,
):
    """
    Восстанавливает старый формат control_point.

    Используется только для старых board.json.
    """

    if control_point is None:
        return

    point = _data_to_point(
        control_point
    )

    if point is None:
        return

    route_points = getattr(
        arrow,
        "_route_points",
        None,
    )

    if not route_points:
        return

    if len(route_points) < 2:
        return

    controller = getattr(
        arrow,
        "_bend_controller",
        None,
    )

    if controller is None:
        return

    try:
        start = QPointF(
            route_points[0]
        )

        end = QPointF(
            route_points[-1]
        )

        controller.offset = (
            controller.offset_from_point(
                start,
                end,
                point,
            )
        )
    except Exception:
        return


# ============================================================
# FREE END
# ============================================================

def _get_free_end(arrow):
    """
    Возвращает координаты свободного конца стрелки.

    Для подключенной стрелки возвращается None.
    """

    target_item = getattr(
        arrow,
        "target_item",
        None,
    )

    if target_item is not None:
        return None

    try:
        point = (
            arrow._get_end_scene_point()
        )

        return _point_to_data(
            point
        )

    except Exception:
        pass

    free_end = getattr(
        arrow,
        "free_end",
        None,
    )

    return _point_to_data(
        free_end
    )


# ============================================================
# SERIALIZE
# ============================================================

def serialize_arrow(arrow):
    """
    Преобразует RoutedArrowItem
    в словарь для board.json.
    """

    if not isinstance(
        arrow,
        RoutedArrowItem,
    ):
        print(
            f"[SER] SKIP: not RoutedArrowItem, "
            f"type={type(arrow).__name__}"
        )
        return None

    source_item = getattr(
        arrow,
        "source_item",
        None,
    )

    target_item = getattr(
        arrow,
        "target_item",
        None,
    )

    src_cid = getattr(
        source_item,
        "card_id",
        "NO-ATTR",
    )

    tgt_cid = getattr(
        target_item,
        "card_id",
        "NO-ATTR",
    )

    print(
        f"[SER] arrow id={id(arrow)} "
        f"source_type={type(source_item).__name__ if source_item else None} "
        f"source_card_id={src_cid!r} "
        f"target_type={type(target_item).__name__ if target_item else None} "
        f"target_card_id={tgt_cid!r}"
    )

    source_id = _get_item_id(
        source_item
    )

    if source_id is None:
        print(
            f"[SER] REJECT: source_id is None "
            f"(source_card_id={src_cid!r})"
        )
        return None

    target_id = _get_item_id(
        target_item
    )

    if target_item is not None:

        if target_id is None:
            print(
                f"[SER] REJECT: target_id is None "
                f"(target_card_id={tgt_cid!r})"
            )
            return None

        result = {
            "type": "arrow",
            "source_id": source_id,
            "target_id": target_id,
            "bend_offset": (
                _get_bend_offset(
                    arrow
                )
            ),
            "free_end": None,
        }

        print(f"[SER] OK (connected): {result}")
        return result

    result = {
        "type": "arrow",
        "source_id": source_id,
        "target_id": None,
        "bend_offset": (
            _get_bend_offset(
                arrow
            )
        ),
        "free_end": _get_free_end(
            arrow
        ),
    }

    print(f"[SER] OK (free end): {result}")
    return result


# ============================================================
# SAVE ALL
# ============================================================

def collect_arrows(scene):
    """
    Собирает все RoutedArrowItem
    из сцены.
    """

    if scene is None:
        print("[COLLECT] scene is None")
        return []

    all_items = scene.items()

    routed = [
        item
        for item in all_items
        if isinstance(item, RoutedArrowItem)
    ]

    print(
        f"[COLLECT] scene items: {len(all_items)}, "
        f"RoutedArrowItem on scene: {len(routed)}"
    )

    # Проверим, есть ли на сцене другие стрелки (не Routed)
    try:
        from ..items.arrow_item import ArrowItem

        plain = [
            item
            for item in all_items
            if isinstance(item, ArrowItem)
            and not isinstance(item, RoutedArrowItem)
        ]

        if plain:
            print(
                f"[COLLECT] !! plain ArrowItem on scene: {len(plain)}"
            )

            for p in plain:
                print(
                    f"[COLLECT]    plain type={type(p).__name__} "
                    f"id={id(p)}"
                )
    except Exception as exc:
        print(f"[COLLECT] import ArrowItem failed: {exc!r}")

    arrows = []

    for item in routed:
        data = serialize_arrow(
            item
        )

        if data is not None:
            arrows.append(data)

    print(
        f"[COLLECT] RESULT: {len(arrows)} arrows serialized"
    )

    return arrows


# ============================================================
# RESTORE ONE
# ============================================================

def restore_arrow(
    canvas,
    arrow_data,
    item_by_id,
):
    """
    Восстанавливает одну стрелку
    из board.json.
    """

    if not isinstance(
        arrow_data,
        dict,
    ):
        print(f"[REST] skip: not dict: {arrow_data!r}")
        return None

    source_id = arrow_data.get(
        "source_id"
    )

    if source_id is None:
        print(f"[REST] skip: no source_id: {arrow_data!r}")
        return None

    source_id = str(
        source_id
    ).strip()

    if not source_id:
        print(f"[REST] skip: empty source_id")
        return None

    source_item = item_by_id.get(
        source_id
    )

    if source_item is None:
        print(
            f"[REST] skip: source_item not found for id={source_id!r} "
            f"(known ids: {list(item_by_id.keys())})"
        )
        return None

    target_id = arrow_data.get(
        "target_id"
    )

    target_item = None

    if target_id is not None:

        target_id = str(
            target_id
        ).strip()

        if not target_id:
            print(f"[REST] skip: empty target_id")
            return None

        target_item = item_by_id.get(
            target_id
        )

        if target_item is None:
            print(
                f"[REST] skip: target_item not found for id={target_id!r}"
            )
            return None

    free_end = None

    if target_item is None:
        free_end = _data_to_point(
            arrow_data.get(
                "free_end"
            )
        )

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

        except Exception as exc:
            print(f"[REST] create TypeError->fallback failed: {exc!r}")
            return None

    except Exception as exc:
        print(f"[REST] create failed: {exc!r}")
        return None

    canvas.scene.addItem(
        arrow
    )

    try:
        arrow.update_position()
    except Exception:
        pass

    if "bend_offset" in arrow_data:

        _restore_bend(
            arrow,
            arrow_data.get(
                "bend_offset",
                0.0,
            ),
        )

    elif (
        arrow_data.get(
            "control_point"
        ) is not None
    ):

        _restore_legacy_control_point(
            arrow,
            arrow_data.get(
                "control_point"
            ),
        )

    try:
        arrow.update_position()
    except Exception:
        pass

    try:
        arrow.setSelected(
            False
        )
    except Exception:
        pass

    print(
        f"[REST] OK arrow restored: "
        f"source={source_id!r} target={target_id!r}"
    )

    return arrow


# ============================================================
# RESTORE ALL
# ============================================================

def restore_arrows(
    canvas,
    arrows_data,
    item_by_id,
):
    """
    Восстанавливает все стрелки
    после загрузки карточек.
    """

    if not isinstance(
        arrows_data,
        list,
    ):
        print(f"[REST] arrows_data not list: {type(arrows_data).__name__}")
        return 0

    print(
        f"[REST] restoring {len(arrows_data)} arrows, "
        f"item_by_id keys: {len(item_by_id)}"
    )

    restored_count = 0

    for arrow_data in arrows_data:

        arrow = restore_arrow(
            canvas,
            arrow_data,
            item_by_id,
        )

        if arrow is not None:
            restored_count += 1

    print(f"[REST] restored {restored_count}/{len(arrows_data)} arrows")

    return restored_count