"""
Удаление элементов с холста.

Содержит функции delete_item и delete_selected,
которые раньше были методами класса Canvas.

Добавлена защита объектов, находящихся внутри рамки:
такие объекты нельзя удалить, пока они привязаны к рамке.

Рамку удалять можно — при этом её содержимое освобождается.
"""


# ============================================================
# FRAME HELPERS
# ============================================================

def _is_frame(item):
    """Является ли объект рамкой (FrameItem)."""

    try:
        from .frame_item import FrameItem
        return isinstance(item, FrameItem)
    except Exception:
        return False


def _is_protected_by_frame(item):
    """
    True, если item привязан к рамке и не является самой рамкой.

    Такие объекты удалять нельзя.
    """

    if item is None:
        return False

    if _is_frame(item):
        return False

    try:
        frame = getattr(item, "_frame", None)
    except Exception:
        frame = None

    return frame is not None


def _detach_frame_members(frame):
    """
    Освобождает всех участников рамки.

    Вызывается перед удалением самой рамки.
    """

    if frame is None:
        return

    try:
        from .frame_containment import detach_all_members
        detach_all_members(frame)
    except Exception:
        pass


# ============================================================
# ARROW HELPERS
# ============================================================

def _is_arrow_for_item(arrow, item):
    """
    Проверяет, связана ли стрелка с указанным элементом.
    """

    if arrow is None or item is None:
        return False

    try:
        source = getattr(arrow, "source_item", None)
    except Exception:
        source = None

    try:
        target = getattr(arrow, "target_item", None)
    except Exception:
        target = None

    return source is item or target is item


def _safe_remove_arrow(canvas, arrow):
    """
    Безопасно удаляет одну стрелку со сцены и из списков карточек.
    """

    if arrow is None:
        return

    source = None
    target = None

    try:
        source = getattr(arrow, "source_item", None)
    except Exception:
        pass

    try:
        target = getattr(arrow, "target_item", None)
    except Exception:
        pass

    for other in (source, target):

        if other is None:
            continue

        try:
            other_arrows = getattr(other, "arrows", None)
        except Exception:
            other_arrows = None

        if other_arrows is None:
            continue

        try:
            while arrow in other_arrows:
                other_arrows.remove(arrow)
        except Exception:
            pass

    try:
        scene = arrow.scene()
    except Exception:
        scene = None

    if scene is not None:

        # Вызываем cleanup() до удаления со сцены —
        # чтобы RoutedArrowItem удалил свою ручку изгиба.
        try:
            cleanup = getattr(arrow, "cleanup", None)

            if callable(cleanup):
                cleanup()
        except Exception:
            pass

        try:
            scene.removeItem(arrow)
        except (RuntimeError, ReferenceError):
            pass
        except Exception:
            pass

    try:
        arrow.source_item = None
    except Exception:
        pass

    try:
        arrow.target_item = None
    except Exception:
        pass


def _get_all_arrows(canvas):
    """
    Возвращает все стрелки, реально находящиеся на сцене.
    """

    result = []

    try:
        scene_items = canvas.scene.items()
    except Exception:
        return result

    for scene_item in scene_items:

        try:
            source = getattr(scene_item, "source_item", None)
            target = getattr(scene_item, "target_item", None)
        except Exception:
            continue

        if source is not None or target is not None:

            if scene_item not in result:
                result.append(scene_item)

    return result


def _remove_arrows_of(canvas, item):
    """
    Удаляет все стрелки, привязанные к элементу.
    """

    if item is None:
        return

    arrows_to_remove = []

    try:
        item_arrows = getattr(item, "arrows", None)
    except Exception:
        item_arrows = None

    if item_arrows:

        try:
            for arrow in list(item_arrows):

                if arrow not in arrows_to_remove:
                    arrows_to_remove.append(arrow)

        except Exception:
            pass

    for arrow in _get_all_arrows(canvas):

        if _is_arrow_for_item(arrow, item):

            if arrow not in arrows_to_remove:
                arrows_to_remove.append(arrow)

    for arrow in arrows_to_remove:
        _safe_remove_arrow(canvas, arrow)

    try:
        arrows = getattr(item, "arrows", None)

        if arrows is not None:
            arrows.clear()

    except Exception:
        pass


# ============================================================
# DELETE SINGLE ITEM
# ============================================================

def delete_item(canvas, item):
    """
    Удаляет один элемент с холста и сохраняет доску.

    Если элемент внутри рамки — удаление запрещено.
    Если элемент это рамка — сначала освобождаются
    все её участники, потом рамка удаляется.
    """

    if item is None:
        return

    # --------------------------------------------------
    # защита: объект внутри рамки
    # --------------------------------------------------

    if _is_protected_by_frame(item):

        if canvas.main_window:

            canvas.main_window.update_status(
                "Элемент находится внутри рамки — "
                "удаление запрещено"
            )

        return

    # --------------------------------------------------
    # если это рамка — сначала освободить участников
    # --------------------------------------------------

    if _is_frame(item):
        _detach_frame_members(item)

    # --------------------------------------------------
    # удалить стрелки и сам элемент
    # --------------------------------------------------

    _remove_arrows_of(canvas, item)

    try:
        if item.scene() is canvas.scene:
            canvas.scene.removeItem(item)
    except (RuntimeError, ReferenceError):
        pass
    except Exception:
        pass

    canvas.save_board()

    if canvas.main_window:

        canvas.main_window.update_status(
            "Элемент удален"
        )


# ============================================================
# DELETE SELECTED
# ============================================================

def delete_selected(canvas):
    """
    Удаляет все выделенные элементы с холста и сохраняет доску.

    Объекты внутри рамок пропускаются (не удаляются).
    Рамки удаляются с освобождением содержимого.
    """

    selected = canvas.scene.selectedItems()

    if not selected:
        return

    selected_items = list(selected)

    # ---------------------------------------------------------
    # ШАГ 0. Фильтрация по защите рамок.
    # ---------------------------------------------------------

    frames_to_delete = []
    items_to_delete = []
    protected_count = 0

    for item in selected_items:

        if _is_frame(item):
            frames_to_delete.append(item)
            continue

        if _is_protected_by_frame(item):
            protected_count += 1
            continue

        items_to_delete.append(item)

    # Если всё, что было выделено — защищено, не делаем ничего.
    if not frames_to_delete and not items_to_delete:

        if protected_count and canvas.main_window:

            canvas.main_window.update_status(
                "Выделенные элементы находятся внутри рамок — "
                "удаление запрещено"
            )

        return

    # ---------------------------------------------------------
    # ШАГ 1. Собираем все стрелки, связанные с удаляемыми.
    # ---------------------------------------------------------

    arrows_to_remove = []

    all_to_delete = frames_to_delete + items_to_delete

    for item in all_to_delete:

        try:
            item_arrows = getattr(item, "arrows", None)
        except Exception:
            item_arrows = None

        if item_arrows:

            try:
                for arrow in list(item_arrows):

                    if arrow not in arrows_to_remove:
                        arrows_to_remove.append(arrow)

            except Exception:
                pass

    for arrow in _get_all_arrows(canvas):

        for item in all_to_delete:

            if _is_arrow_for_item(arrow, item):

                if arrow not in arrows_to_remove:
                    arrows_to_remove.append(arrow)

                break

    # ---------------------------------------------------------
    # ШАГ 2. Удаляем стрелки.
    # ---------------------------------------------------------

    for arrow in arrows_to_remove:
        _safe_remove_arrow(canvas, arrow)

    # ---------------------------------------------------------
    # ШАГ 3. Очищаем списки стрелок.
    # ---------------------------------------------------------

    for item in all_to_delete:

        try:
            arrows = getattr(item, "arrows", None)

            if arrows is not None:
                arrows.clear()

        except Exception:
            pass

    # ---------------------------------------------------------
    # ШАГ 4. Освобождаем участников удаляемых рамок
    #         (до удаления самих рамок).
    # ---------------------------------------------------------

    for frame in frames_to_delete:
        _detach_frame_members(frame)

    # ---------------------------------------------------------
    # ШАГ 5. Удаляем сами элементы.
    # ---------------------------------------------------------

    for item in all_to_delete:

        # Вызываем cleanup() перед удалением — чтобы стрелка
        # удалила свой bend handle, если он у неё есть.
        try:
            cleanup = getattr(item, "cleanup", None)

            if callable(cleanup):
                cleanup()
        except Exception:
            pass

        try:
            if item.scene() is canvas.scene:
                canvas.scene.removeItem(item)

        except (RuntimeError, ReferenceError):
            pass

        except Exception:
            pass

    # ---------------------------------------------------------
    # ШАГ 6. Сохраняем.
    # ---------------------------------------------------------

    canvas.save_board()

    if canvas.main_window:

        if protected_count:

            canvas.main_window.update_status(
                f"Удалено: {len(all_to_delete)}. "
                f"Пропущено (внутри рамок): {protected_count}."
            )

        else:

            canvas.main_window.update_status(
                "Элементы удалены"
            )