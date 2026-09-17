"""
Фабрики для создания элементов на холсте.

Содержит функции add_card, add_image_text_card, add_video_text_card,
add_image, add_file, add_arrow — вынесены из класса Canvas.
"""

import os
import shutil
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..utils import ensure_project_folder
from .card_ids import generate_card_id

from ..cards.text.text_card import TextCard
from ..cards.heading.heading_card import HeadingCard
from ..cards.image_text.image_card import ImageTextCard
from ..cards.comment.comment_card import CommentCard
from ..cards.color.color_item import ColorItem
from ..cards.video.video_text_item import VideoTextItem
from ..cards.image.image_item import ImageItem

from ..items.file_item import FileItem
from ..items.routed_arrow import RoutedArrowItem


def add_card(
    canvas,
    title="Новая карточка",
    text="",
    x=None,
    y=None,
    width=280,
    height=180,
    color="#FFFFFF",
    card_type="text",
    image_path="",
    card_id=None,
):

    # Если позиция не указана — поставим по центру
    if x is None or y is None:

        center = canvas.mapToScene(
            canvas.viewport().rect().center()
        )

        x = center.x() - width / 2
        y = center.y() - height / 2

    if card_type == "color":

        card = ColorItem(
            color=color,
            width=width,
            height=height,
        )

        card.setPos(x, y)

    elif card_type == "comment":

        card = CommentCard(
            title=title,
            text=text,
            width=width,
            height=height,
            color=color,
        )

        card.setPos(x, y)

    elif card_type == "heading":

        card = HeadingCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    elif card_type == "text":

        card = TextCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    elif card_type == "image_text":

        card = ImageTextCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    else:

        raise ValueError(
            f"Unknown card_type: {card_type!r}"
        )

    canvas.scene.addItem(
        card
    )

    # -------------------------------------------------
    # Card ID
    # -------------------------------------------------

    if card_id is not None:

        card.card_id = card_id

    else:

        card.card_id = generate_card_id()

    # -------------------------------------------------
    # Image + text
    # -------------------------------------------------

    if (
        card_type == "image_text"
        and image_path
    ):

        if os.path.isabs(
            image_path
        ):

            full_image_path = image_path

        else:

            project_folder = ensure_project_folder(
                canvas.main_window.project_name
            )

            full_image_path = os.path.join(
                project_folder,
                image_path,
            )

        if os.path.exists(
            full_image_path
        ):

            pixmap = QPixmap(
                full_image_path
            )

            if not pixmap.isNull():

                card.set_image(
                    pixmap,
                    image_path,
                )

    return card


def add_image_text_card(canvas):

    path, _ = QFileDialog.getOpenFileName(
        canvas.main_window,
        "Выберите изображение",
        "",
        "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
    )

    if not path:
        return

    pixmap = QPixmap(
        path
    )

    if pixmap.isNull():

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка",
            "Не удалось загрузить изображение.",
        )

        return

    if not canvas.main_window.project_name:

        QMessageBox.warning(
            canvas.main_window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    project_folder = ensure_project_folder(
        canvas.main_window.project_name
    )

    images_folder = os.path.join(
        project_folder,
        "images",
    )

    os.makedirs(
        images_folder,
        exist_ok=True,
    )

    filename = (
        str(uuid.uuid4())
        +
        os.path.splitext(path)[1]
    )

    destination = os.path.join(
        images_folder,
        filename
    )

    try:

        shutil.copy2(
            path,
            destination,
        )

    except Exception as e:

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка копирования",
            str(e),
        )

        return

    relative_path = os.path.join(
        "images",
        filename,
    )

    card = add_card(
        canvas,
        title="",
        text="",
        width=360,
        height=420,
        color="#FFFFFF",
        card_type="image_text",
    )

    card.set_image(
        pixmap,
        relative_path,
    )

    card.setSelected(
        True
    )

    canvas.save_board()

    canvas.main_window.update_status(
        "Добавлена карточка с изображением"
    )


def add_video_text_card(canvas):

    path, _ = QFileDialog.getOpenFileName(
        canvas.main_window,
        "Выберите видео",
        "",
        "Videos (*.mp4 *.mov *.avi *.mkv *.webm)",
    )

    if not path:
        return

    if not canvas.main_window.project_name:

        QMessageBox.warning(
            canvas.main_window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    project_folder = ensure_project_folder(
        canvas.main_window.project_name
    )

    videos_folder = os.path.join(
        project_folder,
        "videos",
    )

    os.makedirs(
        videos_folder,
        exist_ok=True,
    )

    filename = (
        str(uuid.uuid4())
        +
        os.path.splitext(path)[1]
    )

    destination = os.path.join(
        videos_folder,
        filename
    )

    try:

        shutil.copy2(
            path,
            destination,
        )

    except Exception as e:

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка копирования",
            str(e),
        )

        return

    relative_path = os.path.join(
        "videos",
        filename,
    )

    item = VideoTextItem(
        title="",
        text="",
        video_path=destination,
        width=360,
        height=420,
    )

    item.video_path = relative_path

    item.runtime_video_path = destination

    center = canvas.mapToScene(
        canvas.viewport().rect().center()
    )

    item.setPos(
        center.x() - 180,
        center.y() - 210,
    )

    canvas.scene.addItem(
        item
    )

    item.setSelected(
        True
    )

    canvas.save_board()

    canvas.main_window.update_status(
        "Добавлена карточка с видео"
    )


def add_image(canvas):

    path, _ = QFileDialog.getOpenFileName(
        canvas.main_window,
        "Выберите изображение",
        "",
        "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
    )

    if not path:
        return

    pixmap = QPixmap(
        path
    )

    if pixmap.isNull():

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка",
            "Не удалось загрузить изображение.",
        )

        return

    max_width = 600
    max_height = 500

    if (
        pixmap.width() > max_width
        or
        pixmap.height() > max_height
    ):

        pixmap = pixmap.scaled(
            max_width,
            max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    if canvas.main_window.project_name:

        project_folder = ensure_project_folder(
            canvas.main_window.project_name
        )

        images_folder = os.path.join(
            project_folder,
            "images",
        )

        os.makedirs(
            images_folder,
            exist_ok=True,
        )

        filename = (
            str(uuid.uuid4())
            +
            os.path.splitext(path)[1]
        )

        destination = os.path.join(
            images_folder,
            filename
        )

        try:

            shutil.copy2(
                path,
                destination,
            )

        except Exception as e:

            QMessageBox.warning(
                canvas.main_window,
                "Ошибка копирования",
                str(e),
            )

            return

        relative_path = os.path.join(
            "images",
            filename,
        )

    else:

        relative_path = path

    item = ImageItem(
        pixmap,
        relative_path,
    )

    center = canvas.mapToScene(
        canvas.viewport().rect().center()
    )

    item.setPos(
        center.x()
        -
        pixmap.width() / 2,
        center.y()
        -
        pixmap.height() / 2,
    )

    canvas.scene.addItem(
        item
    )

    item.setSelected(
        True
    )

    canvas.save_board()

    canvas.main_window.update_status(
        "Добавлено изображение"
    )


def add_file(canvas):

    path, _ = QFileDialog.getOpenFileName(
        canvas.main_window,
        "Выберите файл",
        "",
        "Все файлы (*.*)",
    )

    if not path:
        return

    if not canvas.main_window.project_name:

        QMessageBox.warning(
            canvas.main_window,
            "Проект не выбран",
            "Сначала создайте или откройте проект.",
        )

        return

    project_folder = ensure_project_folder(
        canvas.main_window.project_name
    )

    files_folder = os.path.join(
        project_folder,
        "files",
    )

    os.makedirs(
        files_folder,
        exist_ok=True,
    )

    extension = os.path.splitext(
        path
    )[1]

    filename = (
        str(uuid.uuid4())
        +
        extension
    )

    destination = os.path.join(
        files_folder,
        filename
    )

    try:

        shutil.copy2(
            path,
            destination,
        )

    except Exception as e:

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка копирования",
            str(e),
        )

        return

    relative_path = os.path.join(
        "files",
        filename,
    )

    original_name = os.path.basename(
        path
    )

    item = FileItem(
        file_path=relative_path,
        file_name=original_name,
    )

    item.runtime_file_path = destination

    center = canvas.mapToScene(
        canvas.viewport().rect().center()
    )

    item.setPos(
        center.x()
        -
        item.WIDTH / 2,
        center.y()
        -
        item.HEIGHT / 2,
    )

    canvas.scene.addItem(
        item
    )

    item.setSelected(
        True
    )

    canvas.save_board()

    canvas.main_window.update_status(
        "Добавлен файл: "
        +
        original_name
    )


def add_arrow(
    canvas,
    source_item,
    target_item,
):

    if source_item is None or target_item is None:
        return None

    arrow = RoutedArrowItem(
        source_item=source_item,
        target_item=target_item,
    )

    canvas.scene.addItem(
        arrow
    )

    return arrow