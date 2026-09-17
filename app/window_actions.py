"""
Actions for DevJournal window.

All methods of the DevJournal class that perform actions
(new_project, open_project, add_card, etc.) are moved here
as free functions taking `window` as the first argument.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QGraphicsTextItem,
)

from .config import BOARDS_DIR
from .utils import safe_project_name, ensure_project_folder
from .settings import SettingsDialog

from .cards.text.text_card import TextCard
from .cards.heading.heading_card import HeadingCard
from .cards.image_text.image_card import ImageTextCard
from .cards.comment.comment_card import CommentCard
from .cards.video.video_text_item import VideoTextItem


def remember_selected_item(window):

    selected = window.canvas.scene.selectedItems()

    if selected:
        window.last_selected_item = selected[0]


def set_grid_mode(window, mode):

    window.canvas.grid_mode = mode

    window.canvas.viewport().update()

    window.canvas.save_board()

    update_status(
        window,
        "Настройка сетки изменена",
    )


def zoom_in(window):

    window.canvas.zoom_in()


def zoom_out(window):

    window.canvas.zoom_out()


def update_zoom_label(window, value):

    window.zoom_label.setText(
        f"{value}%"
    )


def update_status(window, text):

    window.status_label.setText(
        text
    )


def new_project(window):

    name, ok = QInputDialog.getText(
        window,
        "Новый проект",
        "Название проекта:",
    )

    if not ok:
        return

    name = safe_project_name(name)

    if not name:
        return

    window.project_name = name

    ensure_project_folder(name)

    window.project_name_label.setText(name)

    window.canvas.scene.clear()

    window.last_selected_item = None

    window.canvas.grid_mode = "dots"

    window.canvas.set_zoom(100)

    update_status(
        window,
        "Создан новый проект",
    )

    window.canvas.save_board()


def open_project(window):

    if not os.path.exists(BOARDS_DIR):
        os.makedirs(BOARDS_DIR)

    folder = QFileDialog.getExistingDirectory(
        window,
        "Выберите папку проекта",
        BOARDS_DIR,
    )

    if not folder:
        return

    project_name = os.path.basename(
        os.path.normpath(folder)
    )

    window.project_name = project_name

    window.project_name_label.setText(project_name)

    window.last_selected_item = None

    window.canvas.load_board(project_name)


def save_project(window):

    if not window.project_name:
        new_project(window)
        return

    window.canvas.save_board()

    update_status(
        window,
        "Проект сохранен",
    )


def add_card(window, card_type="text"):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    card_titles = {
        "text": "Новая карточка",
        "comment": "Комментарий",
        "heading": "Заголовок",
        "image_text": "Текст + изображение",
        "color": "Цвет",
    }

    title = card_titles.get(
        card_type,
        "Новая карточка",
    )

    card = window.canvas.add_card(
        title=title,
        card_type=card_type,
    )

    if card is None:
        return

    card.setSelected(True)

    window.last_selected_item = card

    update_status(
        window,
        "Добавлена карточка: " + title,
    )

    window.canvas.save_board()


def add_color_card(window):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    card = window.canvas.add_card(
        title="Цвет",
        card_type="color",
    )

    if card is None:
        return

    card.setSelected(True)

    window.last_selected_item = card

    update_status(
        window,
        "Добавлена цветовая ячейка",
    )

    window.canvas.save_board()


def change_selected_color(window):

    item = None

    selected = window.canvas.scene.selectedItems()

    if selected:
        item = selected[0]
    elif window.last_selected_item is not None:
        item = window.last_selected_item

    if item is None:

        update_status(
            window,
            "Сначала выберите элемент",
        )

        return

    from .canvas.color import show_palette

    if isinstance(
        item,
        (
            TextCard,
            HeadingCard,
            ImageTextCard,
            CommentCard,
        ),
    ):

        current_color = getattr(
            item,
            "card_color",
            "#FFFFFF",
        )

        color = show_palette(
            window,
            current_color,
        )

        if not color.isValid():
            return

        item.card_color = color.name(
            QColor.NameFormat.HexArgb
        )

        if hasattr(item, "background"):

            item.background.setBrush(
                QBrush(color)
            )

        item.update()

        window.last_selected_item = item

        window.canvas.save_board()

        update_status(
            window,
            "Цвет изменен",
        )

        return

    if isinstance(item, VideoTextItem):

        current_color = getattr(
            item,
            "card_color",
            "#FFFFFF",
        )

        color = show_palette(
            window,
            current_color,
        )

        if not color.isValid():
            return

        item.set_card_color(color.name())

        item.setSelected(True)

        window.last_selected_item = item

        window.canvas.save_board()

        update_status(
            window,
            "Цвет изменен",
        )

        return

    update_status(
        window,
        "Для этого элемента цвет не поддерживается",
    )


def add_image_text_card(window):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    window.canvas.add_image_text_card()


def add_video_text_card(window):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    window.canvas.add_video_text_card()


def add_image(window):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    window.canvas.add_image()


def add_file(window):

    if not window.project_name:

        QMessageBox.information(
            window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    window.canvas.add_file()


def delete_selected(window):

    selected = window.canvas.scene.selectedItems()

    if selected:

        window.canvas.delete_selected()

        window.last_selected_item = None

        return

    item = window.last_selected_item

    if item is None:
        return

    if item.scene() is None:

        window.last_selected_item = None

        return

    item.setSelected(True)

    window.canvas.delete_selected()

    window.last_selected_item = None


def open_settings(window):

    dialog = SettingsDialog(
        window.canvas,
        window,
    )

    if dialog.exec():

        window.canvas.save_board()

        update_status(
            window,
            "Настройки сохранены",
        )


# ============================================================
# UNLOCK ALL FRAMES
# ============================================================

def unlock_all_frames(window):
    """
    Снимает блокировку со всех рамок на сцене.
    Возвращает количество разблокированных рамок.
    """

    if window is None:
        return 0

    canvas = getattr(window, "canvas", None)

    if canvas is None:
        return 0

    scene = getattr(canvas, "scene", None)

    if scene is None:
        return 0

    try:
        from .canvas.frame_item import FrameItem
    except Exception:
        return 0

    count = 0

    try:
        items = scene.items()
    except Exception:
        return 0

    for item in items:
        if not isinstance(item, FrameItem):
            continue

        try:
            if getattr(item, "locked", False):
                item.set_locked(False)
                count += 1
        except Exception:
            continue

    if count:
        try:
            canvas.save_board()
        except Exception:
            pass

    try:
        update_status(
            window,
            f"Разблокировано рамок: {count}",
        )
    except Exception:
        pass

    return count


def unlock_frame_under_cursor(window):
    """
    Р В Р В°Р В·Р В±Р В»Р С•Р С”Р С‘РЎР‚РЎС“Р ВµРЎвЂљ РЎР‚Р В°Р СР С”РЎС“, Р С”Р С•РЎвЂљР С•РЎР‚Р В°РЎРЏ Р Р…Р В°РЎвЂ¦Р С•Р Т‘Р С‘РЎвЂљРЎРѓРЎРЏ Р С—Р С•Р Т‘ Р С”РЎС“РЎР‚РЎРѓР С•РЎР‚Р С•Р С Р СРЎвЂ№РЎв‚¬Р С‘.

    Р ВРЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµРЎвЂљРЎРѓРЎРЏ, Р С”Р С•Р С–Р Т‘Р В° РЎР‚Р В°Р СР С”Р В° Р В·Р В°Р В±Р В»Р С•Р С”Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р В° Р С‘ Р Р…Р Вµ Р СР С•Р В¶Р ВµРЎвЂљ Р В±РЎвЂ№РЎвЂљРЎРЉ
    Р Р†РЎвЂ№Р В±РЎР‚Р В°Р Р…Р В° Р С•Р В±РЎвЂ№РЎвЂЎР Р…РЎвЂ№Р С Р С”Р В»Р С‘Р С”Р С•Р С.
    """

    if window is None:
        return 0

    canvas = getattr(window, "canvas", None)

    if canvas is None:
        return 0

    scene = getattr(canvas, "scene", None)

    if scene is None:
        return 0

    try:
        from .canvas.frame_item import FrameItem
    except Exception:
        return 0

    # Р СџР С•Р В·Р С‘РЎвЂ Р С‘РЎРЏ Р С”РЎС“РЎР‚РЎРѓР С•РЎР‚Р В° Р СРЎвЂ№РЎв‚¬Р С‘ Р Р† Р С”Р С•Р С•РЎР‚Р Т‘Р С‘Р Р…Р В°РЎвЂљР В°РЎвЂ¦ РЎРѓРЎвЂ Р ВµР Р…РЎвЂ№.
    try:
        from PySide6.QtGui import QCursor

        global_pos = QCursor.pos()

        view_pos = canvas.viewport().mapFromGlobal(global_pos)

        scene_pos = canvas.mapToScene(view_pos)

    except Exception:
        return 0

    # Р ВРЎвЂ°Р ВµР С РЎР‚Р В°Р СР С”РЎС“, РЎРѓР С•Р Т‘Р ВµРЎР‚Р В¶Р В°РЎвЂ°РЎС“РЎР‹ РЎРЊРЎвЂљРЎС“ РЎвЂљР С•РЎвЂЎР С”РЎС“.
    count = 0

    try:
        items = scene.items(scene_pos)
    except Exception:
        return 0

    for item in items:

        if not isinstance(item, FrameItem):
            continue

        try:
            if getattr(item, "locked", False):
                item.set_locked(False)
                count += 1

                # Р вЂќР С•РЎРѓРЎвЂљР В°РЎвЂљР С•РЎвЂЎР Р…Р С• Р С•Р Т‘Р Р…Р С•Р в„– РІР‚вЂќ Р С—Р ВµРЎР‚Р Р†Р В°РЎРЏ Р С—Р С•Р Т‘ Р С”РЎС“РЎР‚РЎРѓР С•РЎР‚Р С•Р С.
                break

        except Exception:
            continue

    if count:
        try:
            canvas.save_board()
        except Exception:
            pass

    try:
        if count:
            update_status(
                window,
                "Р В Р В°Р СР С”Р В° РЎР‚Р В°Р В·Р В±Р В»Р С•Р С”Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р В°",
            )
        else:
            update_status(
                window,
                "Р СџР С•Р Т‘ Р С”РЎС“РЎР‚РЎРѓР С•РЎР‚Р С•Р С Р Р…Р ВµРЎвЂљ Р В·Р В°Р В±Р В»Р С•Р С”Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р Р…Р С•Р в„– РЎР‚Р В°Р СР С”Р С‘",
            )
    except Exception:
        pass

    return count


def event_filter(window, watched, event):

    if (
        event.type() == event.Type.KeyPress
        and event.key() == Qt.Key.Key_Delete
    ):

        focus_item = window.canvas.scene.focusItem()

        if isinstance(focus_item, QGraphicsTextItem):
            return False

        delete_selected(window)

        return True

    return None


def key_press_event(window, event):

    modifiers = event.modifiers()

    if modifiers & Qt.KeyboardModifier.ControlModifier:

        # Ctrl+Shift+L — разблокировать все рамки.
        if (
            event.key() == Qt.Key.Key_L
            and modifiers & Qt.KeyboardModifier.ShiftModifier
        ):
            unlock_all_frames(window)

            event.accept()
            return

        if event.key() == Qt.Key.Key_S:

            save_project(window)

            event.accept()

            return

        if event.key() == Qt.Key.Key_O:

            open_project(window)

            event.accept()

            return

        if event.key() == Qt.Key.Key_N:

            new_project(window)

            event.accept()

            return

    # default behavior: let the base class handle it
    # we call super via the caller, so return None


def close_event(window, event):

    if window.project_name:
        window.canvas.save_board()