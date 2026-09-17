import sys
import json
import os
import shutil
import uuid

from PySide6.QtCore import (
    Qt,
    QTimer,
    QRectF,
    QPointF,
)

from PySide6.QtGui import (
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QPainter,
    QFont,
)

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QGraphicsPixmapItem,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QDialog,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
    QMenu,
    QColorDialog,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

APP_NAME = "DevJournal"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

BOARDS_DIR = os.path.join(
    BASE_DIR,
    "boards",
)

os.makedirs(
    BOARDS_DIR,
    exist_ok=True,
)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def safe_project_name(name):

    invalid = '<>:"/\\|?*'

    result = "".join(
        "_"
        if c in invalid
        else c
        for c in name
    )

    result = result.strip()

    if not result:
        result = "Project"

    return result


def ensure_project_folder(name):

    name = safe_project_name(name)

    folder = os.path.join(
        BOARDS_DIR,
        name,
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    os.makedirs(
        os.path.join(
            folder,
            "images",
        ),
        exist_ok=True,
    )

    return folder


# ============================================================
# РЕДАКТИРУЕМЫЙ ТЕКСТ
# ============================================================

class EditableText(QGraphicsTextItem):

    def __init__(
        self,
        text="",
        parent=None,
    ):

        super().__init__(
            text,
            parent,
        )

        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )

        self.setDefaultTextColor(
            QColor("#202124")
        )

        font = QFont(
            "Segoe UI",
            10,
        )

        self.setFont(font)


# ============================================================
# КАРТОЧКА
# ============================================================

class Card(QGraphicsRectItem):

    MIN_WIDTH = 220
    MIN_HEIGHT = 140

    def __init__(
        self,
        title="Новая карточка",
        text="",
        width=280,
        height=180,
        color="#FFFFFF",
    ):

        super().__init__(
            0,
            0,
            width,
            height,
        )

        self.card_id = str(
            uuid.uuid4()
        )

        self.card_color = color

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.setAcceptHoverEvents(
            True
        )

        self.resizing = False
        self.resize_start = QPointF()

        self.original_width = width
        self.original_height = height

        # ----------------------------------------------------
        # Заголовок
        # ----------------------------------------------------

        self.title_item = EditableText(
            title,
            self,
        )

        title_font = QFont(
            "Segoe UI",
            13,
        )

        title_font.setBold(
            True
        )

        self.title_item.setFont(
            title_font
        )

        self.title_item.setDefaultTextColor(
            QColor("#171717")
        )

        self.title_item.setPos(
            16,
            14,
        )

        self.title_item.setTextWidth(
            width - 32
        )

        # ----------------------------------------------------
        # Основной текст
        # ----------------------------------------------------

        self.body_item = EditableText(
            text,
            self,
        )

        body_font = QFont(
            "Segoe UI",
            10,
        )

        self.body_item.setFont(
            body_font
        )

        self.body_item.setDefaultTextColor(
            QColor("#555555")
        )

        self.body_item.setPos(
            16,
            55,
        )

        self.body_item.setTextWidth(
            width - 32
        )

    # ========================================================
    # РАЗМЕР
    # ========================================================

    def set_card_size(
        self,
        width,
        height,
    ):

        width = max(
            self.MIN_WIDTH,
            width,
        )

        height = max(
            self.MIN_HEIGHT,
            height,
        )

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            width,
            height,
        )

        self.title_item.setTextWidth(
            width - 32
        )

        self.body_item.setTextWidth(
            width - 32
        )

        self.update()

    # ========================================================
    # ЦВЕТ
    # ========================================================

    def set_color(
        self,
        color,
    ):

        self.card_color = color
        self.update()

    # ========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # ========================================================

    def contextMenuEvent(
        self,
        event,
    ):

        menu = QMenu()

        change_color_action = menu.addAction(
            "Изменить цвет"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Удалить"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == change_color_action:

            color = QColorDialog.getColor(
                QColor(self.card_color),
                self.scene().views()[0]
                if self.scene() and self.scene().views()
                else None,
                "Цвет карточки",
            )

            if color.isValid():

                self.set_color(
                    color.name()
                )

                if self.scene():

                    view = self.scene().views()[0]

                    if view.main_window:
                        view.main_window.canvas.save_board()
                        view.main_window.update_status(
                            "Цвет карточки изменен"
                        )

        elif action == delete_action:

            if self.scene():

                view = self.scene().views()[0]

                if view.main_window:

                    view.delete_item(
                        self
                    )

        event.accept()

    # ========================================================
    # BOUNDING RECT
    # ========================================================

    def boundingRect(self):

        rect = self.rect()

        return rect.adjusted(
            -6,
            -6,
            6,
            8,
        )

    # ========================================================
    # ЗОНА RESIZE
    # ========================================================

    def resize_zone(
        self,
        pos,
    ):

        rect = self.rect()

        return (
            pos.x()
            >= rect.width() - 24
            and
            pos.y()
            >= rect.height() - 24
        )

    # ========================================================
    # HOVER
    # ========================================================

    def hoverMoveEvent(
        self,
        event,
    ):

        if self.resize_zone(
            event.pos()
        ):

            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor
            )

        else:

            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        super().hoverMoveEvent(
            event
        )

    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
            and
            self.resize_zone(
                event.pos()
            )
        ):

            self.resizing = True

            self.resize_start = (
                event.pos()
            )

            rect = self.rect()

            self.original_width = (
                rect.width()
            )

            self.original_height = (
                rect.height()
            )

            event.accept()

            return

        super().mousePressEvent(
            event
        )

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(
        self,
        event,
    ):

        if self.resizing:

            delta = (
                event.pos()
                - self.resize_start
            )

            new_width = (
                self.original_width
                + delta.x()
            )

            new_height = (
                self.original_height
                + delta.y()
            )

            self.set_card_size(
                new_width,
                new_height,
            )

            event.accept()

            return

        super().mouseMoveEvent(
            event
        )

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(
        self,
        event,
    ):

        if self.resizing:

            self.resizing = False

            if self.scene():

                view = self.scene().views()[0]

                if view.main_window:
                    view.main_window.canvas.save_board()

            event.accept()

            return

        super().mouseReleaseEvent(
            event
        )

    # ========================================================
    # ОТРИСОВКА
    # ========================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):

        rect = self.rect()

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        # ----------------------------------------------------
        # Тень
        # ----------------------------------------------------

        shadow_rect = rect.adjusted(
            3,
            4,
            3,
            4,
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QColor(
                0,
                0,
                0,
                18,
            )
        )

        painter.drawRoundedRect(
            shadow_rect,
            12,
            12,
        )

        # ----------------------------------------------------
        # Основная карточка
        # ----------------------------------------------------

        painter.setBrush(
            QBrush(
                QColor(
                    self.card_color
                )
            )
        )

        if self.isSelected():

            pen = QPen(
                QColor("#4F7CFF"),
                2,
            )

        else:

            pen = QPen(
                QColor("#E3E3E0"),
                1,
            )

        painter.setPen(
            pen
        )

        painter.drawRoundedRect(
            rect,
            12,
            12,
        )

        # ----------------------------------------------------
        # Верхняя полоска
        # ----------------------------------------------------

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QColor("#4F7CFF")
        )

        painter.drawRoundedRect(
            QRectF(
                0,
                0,
                rect.width(),
                4,
            ),
            2,
            2,
        )

        # ----------------------------------------------------
        # Индикатор resize
        # ----------------------------------------------------

        if self.isSelected():

            painter.setPen(
                QPen(
                    QColor("#999999"),
                    1,
                )
            )

            for i in range(3):

                x = (
                    rect.width()
                    - 8
                    - i * 5
                )

                y = (
                    rect.height()
                    - 8
                )

                painter.drawLine(
                    QPointF(
                        x,
                        y,
                    ),
                    QPointF(
                        x + 4,
                        y - 4,
                    ),
                )


# ============================================================
# ИЗОБРАЖЕНИЕ
# ============================================================

class ImageItem(QGraphicsPixmapItem):

    def __init__(
        self,
        pixmap,
        image_path="",
    ):

        super().__init__(
            pixmap
        )

        self.image_path = image_path

        self.image_id = str(
            uuid.uuid4()
        )

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.setShapeMode(
            QGraphicsPixmapItem.ShapeMode.BoundingRectShape
        )

        self.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )

    # ========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # ========================================================

    def contextMenuEvent(
        self,
        event,
    ):

        menu = QMenu()

        delete_action = menu.addAction(
            "Удалить"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == delete_action:

            if self.scene():

                view = self.scene().views()[0]

                if view.main_window:

                    view.delete_item(
                        self
                    )

        event.accept()


# ============================================================
# CANVAS
# ============================================================

class Canvas(QGraphicsView):

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.main_window = parent

        self.scene = QGraphicsScene(
            self
        )

        self.setScene(
            self.scene
        )

        self.scene.setSceneRect(
            -5000,
            -5000,
            10000,
            10000,
        )

        # ----------------------------------------------------
        # Вид
        # ----------------------------------------------------

        self.setBackgroundBrush(
            QColor("#FAFAF8")
        )

        self.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setDragMode(
            QGraphicsView.DragMode.ScrollHandDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            |
            QPainter.RenderHint.SmoothPixmapTransform
        )

        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        # ----------------------------------------------------
        # Zoom
        # ----------------------------------------------------

        self.zoom_factor = 1.0

        # ----------------------------------------------------
        # Сетка
        # ----------------------------------------------------

        self.grid_mode = "dots"

        # ----------------------------------------------------
        # Автосохранение
        # ----------------------------------------------------

        self.autosave_timer = QTimer(
            self
        )

        self.autosave_timer.timeout.connect(
            self.autosave
        )

        self.autosave_timer.start(
            30000
        )

    # ========================================================
    # СЕТКА
    # ========================================================

    def drawBackground(
        self,
        painter,
        rect,
    ):

        painter.fillRect(
            rect,
            QColor("#FAFAF8")
        )

        if self.grid_mode == "none":
            return

        painter.save()

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        grid_size = 24

        left = (
            int(rect.left())
            -
            (
                int(rect.left())
                % grid_size
            )
        )

        top = (
            int(rect.top())
            -
            (
                int(rect.top())
                % grid_size
            )
        )

        if self.grid_mode == "dots":

            painter.setPen(
                Qt.PenStyle.NoPen
            )

            painter.setBrush(
                QColor("#D9D9D5")
            )

            x = left

            while x <= rect.right():

                y = top

                while y <= rect.bottom():

                    painter.drawEllipse(
                        QPointF(
                            x,
                            y,
                        ),
                        1.2,
                        1.2,
                    )

                    y += grid_size

                x += grid_size

        elif self.grid_mode == "grid":

            pen = QPen(
                QColor("#E8E8E4"),
                1,
            )

            painter.setPen(
                pen
            )

            x = left

            while x <= rect.right():

                painter.drawLine(
                    x,
                    rect.top(),
                    x,
                    rect.bottom(),
                )

                x += grid_size

            y = top

            while y <= rect.bottom():

                painter.drawLine(
                    rect.left(),
                    y,
                    rect.right(),
                    y,
                )

                y += grid_size

        painter.restore()

    # ========================================================
    # ZOOM
    # ========================================================

    def set_zoom(
        self,
        value,
    ):

        value = max(
            25,
            min(
                200,
                value,
            )
        )

        factor = value / 100.0

        self.resetTransform()

        self.scale(
            factor,
            factor,
        )

        self.zoom_factor = factor

        if self.main_window:

            self.main_window.update_zoom_label(
                value
            )

    def zoom_in(self):

        current = int(
            self.zoom_factor * 100
        )

        self.set_zoom(
            current + 10
        )

    def zoom_out(self):

        current = int(
            self.zoom_factor * 100
        )

        self.set_zoom(
            current - 10
        )

    def wheelEvent(
        self,
        event,
    ):

        if (
            event.modifiers()
            &
            Qt.KeyboardModifier.ControlModifier
        ):

            delta = (
                event.angleDelta().y()
            )

            if delta > 0:
                self.zoom_in()

            elif delta < 0:
                self.zoom_out()

            event.accept()

            return

        super().wheelEvent(
            event
        )

    # ========================================================
    # ДОБАВЛЕНИЕ КАРТОЧКИ
    # ========================================================

    def add_card(
        self,
        title="Новая карточка",
        text="",
        x=None,
        y=None,
        width=280,
        height=180,
        color="#FFFFFF",
    ):

        card = Card(
            title=title,
            text=text,
            width=width,
            height=height,
            color=color,
        )

        if x is None or y is None:

            center = self.mapToScene(
                self.viewport()
                .rect()
                .center()
            )

            x = (
                center.x()
                - width / 2
            )

            y = (
                center.y()
                - height / 2
            )

        card.setPos(
            x,
            y,
        )

        self.scene.addItem(
            card
        )

        return card

    # ========================================================
    # ДОБАВЛЕНИЕ ИЗОБРАЖЕНИЯ
    # ========================================================

    def add_image(self):

        path, _ = QFileDialog.getOpenFileName(
            self.main_window,
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
                self.main_window,
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

        if self.main_window.project_name:

            project_folder = ensure_project_folder(
                self.main_window.project_name
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
                filename,
            )

            shutil.copy2(
                path,
                destination,
            )

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

        center = self.mapToScene(
            self.viewport()
            .rect()
            .center()
        )

        item.setPos(
            center.x()
            - pixmap.width() / 2,
            center.y()
            - pixmap.height() / 2,
        )

        self.scene.addItem(
            item
        )

        self.save_board()

    # ========================================================
    # УДАЛЕНИЕ ОДНОГО ОБЪЕКТА
    # ========================================================

    def delete_item(
        self,
        item,
    ):

        if item is None:
            return

        self.scene.removeItem(
            item
        )

        self.save_board()

        self.main_window.update_status(
            "Элемент удален"
        )

    # ========================================================
    # УДАЛЕНИЕ ВЫБРАННЫХ
    # ========================================================

    def delete_selected(self):

        selected = (
            self.scene.selectedItems()
        )

        if not selected:
            return

        for item in selected:

            self.scene.removeItem(
                item
            )

            del item

        self.save_board()

        self.main_window.update_status(
            "Элементы удалены"
        )

    # ========================================================
    # СОХРАНЕНИЕ
    # ========================================================

    def save_board(self):

        if not self.main_window.project_name:
            return

        project_folder = ensure_project_folder(
            self.main_window.project_name
        )

        board_path = os.path.join(
            project_folder,
            "board.json",
        )

        data = {
            "version": 3,
            "project_name":
                self.main_window.project_name,
            "grid_mode":
                self.grid_mode,
            "items": [],
        }

        for item in self.scene.items():

            if isinstance(
                item,
                Card,
            ):

                rect = item.rect()

                data["items"].append({
                    "type": "card",

                    "x":
                        item.pos().x(),

                    "y":
                        item.pos().y(),

                    "width":
                        rect.width(),

                    "height":
                        rect.height(),

                    "title":
                        item.title_item.toPlainText(),

                    "text":
                        item.body_item.toPlainText(),

                    "color":
                        item.card_color,
                })

            elif isinstance(
                item,
                ImageItem,
            ):

                data["items"].append({
                    "type": "image",

                    "x":
                        item.pos().x(),

                    "y":
                        item.pos().y(),

                    "path":
                        item.image_path,
                })

        try:

            with open(
                board_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4,
                )

            self.main_window.update_status(
                "Сохранено"
            )

        except Exception as e:

            QMessageBox.warning(
                self.main_window,
                "Ошибка сохранения",
                str(e),
            )

    # ========================================================
    # ЗАГРУЗКА
    # ========================================================

    def load_board(
        self,
        project_name,
    ):

        project_folder = ensure_project_folder(
            project_name
        )

        board_path = os.path.join(
            project_folder,
            "board.json",
        )

        self.scene.clear()

        if not os.path.exists(
            board_path
        ):

            self.main_window.project_name = (
                project_name
            )

            return

        try:

            with open(
                board_path,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(
                    file
                )

            self.grid_mode = data.get(
                "grid_mode",
                "dots",
            )

            items = data.get(
                "items",
                [],
            )

            for item_data in items:

                item_type = item_data.get(
                    "type"
                )

                if item_type == "card":

                    self.add_card(
                        title=item_data.get(
                            "title",
                            "Новая карточка",
                        ),

                        text=item_data.get(
                            "text",
                            "",
                        ),

                        x=item_data.get(
                            "x",
                            0,
                        ),

                        y=item_data.get(
                            "y",
                            0,
                        ),

                        width=item_data.get(
                            "width",
                            280,
                        ),

                        height=item_data.get(
                            "height",
                            180,
                        ),

                        color=item_data.get(
                            "color",
                            "#FFFFFF",
                        ),
                    )

                elif item_type == "image":

                    relative_path = (
                        item_data.get(
                            "path",
                            "",
                        )
                    )

                    if os.path.isabs(
                        relative_path
                    ):

                        image_path = (
                            relative_path
                        )

                    else:

                        image_path = os.path.join(
                            project_folder,
                            relative_path,
                        )

                    if not os.path.exists(
                        image_path
                    ):
                        continue

                    pixmap = QPixmap(
                        image_path
                    )

                    if pixmap.isNull():
                        continue

                    item = ImageItem(
                        pixmap,
                        relative_path,
                    )

                    item.setPos(
                        item_data.get(
                            "x",
                            0,
                        ),

                        item_data.get(
                            "y",
                            0,
                        ),
                    )

                    self.scene.addItem(
                        item
                    )

            self.main_window.project_name = (
                project_name
            )

            self.main_window.update_status(
                "Проект загружен"
            )

            self.viewport().update()

        except Exception as e:

            QMessageBox.warning(
                self.main_window,
                "Ошибка загрузки",
                str(e),
            )

    # ========================================================
    # АВТОСОХРАНЕНИЕ
    # ========================================================

    def autosave(self):

        if self.main_window.project_name:

            self.save_board()


# ============================================================
# НАСТРОЙКИ
# ============================================================

class SettingsDialog(QDialog):

    def __init__(
        self,
        canvas,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.canvas = canvas

        self.setWindowTitle(
            "Настройки рабочего пространства"
        )

        self.setMinimumWidth(
            420
        )

        self.setModal(
            True
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(
            18
        )

        # ----------------------------------------------------
        # Заголовок
        # ----------------------------------------------------

        title = QLabel(
            "Настройки рабочего пространства"
        )

        title.setObjectName(
            "settingsTitle"
        )

        layout.addWidget(
            title
        )

        # ----------------------------------------------------
        # Сетка
        # ----------------------------------------------------

        grid_label = QLabel(
            "Фон холста"
        )

        grid_combo = QComboBox()

        grid_combo.addItem(
            "Точки",
            "dots",
        )

        grid_combo.addItem(
            "Сетка",
            "grid",
        )

        grid_combo.addItem(
            "Без сетки",
            "none",
        )

        current_index = (
            grid_combo.findData(
                self.canvas.grid_mode
            )
        )

        if current_index >= 0:

            grid_combo.setCurrentIndex(
                current_index
            )

        layout.addWidget(
            grid_label
        )

        layout.addWidget(
            grid_combo
        )

        # ----------------------------------------------------
        # Масштаб
        # ----------------------------------------------------

        zoom_label = QLabel(
            "Масштаб"
        )

        zoom_spin = QSpinBox()

        zoom_spin.setRange(
            25,
            200,
        )

        zoom_spin.setSingleStep(
            25
        )

        zoom_spin.setValue(
            int(
                self.canvas.zoom_factor
                * 100
            )
        )

        layout.addWidget(
            zoom_label
        )

        layout.addWidget(
            zoom_spin
        )

        # ----------------------------------------------------
        # Кнопки
        # ----------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(
            self.accept
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        self.grid_combo = grid_combo
        self.zoom_spin = zoom_spin

    def accept(self):

        self.canvas.grid_mode = (
            self.grid_combo.currentData()
        )

        self.canvas.set_zoom(
            self.zoom_spin.value()
        )

        self.canvas.viewport().update()

        super().accept()


# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================

class DevJournal(QMainWindow):

    def __init__(self):

        super().__init__()

        self.project_name = ""
        self.project_file_path = ""

        self.setWindowTitle(
            APP_NAME
        )

        self.resize(
            1440,
            900,
        )

        self.setMinimumSize(
            1100,
            700,
        )

        self.setup_style()
        self.setup_ui()

    # ========================================================
    # СТИЛЬ
    # ========================================================

    def setup_style(self):

        self.setStyleSheet("""

        QMainWindow {
            background: #F7F7F5;
        }

        QWidget {
            font-family: "Segoe UI";
            color: #202124;
        }

        QFrame#sidebar {
            background: #FFFFFF;
            border-right: 1px solid #E7E7E3;
        }

        QLabel#appTitle {
            font-size: 18px;
            font-weight: 700;
            color: #171717;
        }

        QLabel#projectLabel {
            font-size: 11px;
            font-weight: 600;
            color: #999999;
        }

        QLabel#sectionLabel {
            font-size: 10px;
            font-weight: 700;
            color: #A0A09B;
        }

        QLabel#statusLabel {
            color: #8A8A85;
            font-size: 11px;
        }

        QPushButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 9px 12px;
            text-align: left;
            color: #343434;
            font-size: 13px;
        }

        QPushButton:hover {
            background: #F1F1EE;
        }

        QPushButton:pressed {
            background: #EAEAE6;
        }

        QPushButton#activeSection {
            background: #F0F3FF;
            color: #315EDB;
            font-weight: 600;
        }

        QFrame#toolbar {
            background: #FFFFFF;
            border-bottom: 1px solid #E7E7E3;
        }

        QToolButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 7px;
            padding: 6px 9px;
            color: #4A4A47;
            font-size: 12px;
        }

        QToolButton:hover {
            background: #F1F1EE;
            border-color: #E3E3DE;
        }

        QToolButton:pressed {
            background: #EAEAE6;
        }

        QToolButton#menuButton {
            font-weight: 600;
            padding-left: 10px;
            padding-right: 10px;
        }

        QLabel#zoomLabel {
            min-width: 52px;
            color: #666660;
            font-size: 12px;
        }

        QDialog {
            background: #FFFFFF;
        }

        QLabel#settingsTitle {
            font-size: 18px;
            font-weight: 700;
        }

        QComboBox,
        QSpinBox {
            background: #FAFAF8;
            border: 1px solid #DCDCD7;
            border-radius: 8px;
            padding: 8px;
        }

        QMenu {
            background: #FFFFFF;
            border: 1px solid #DCDCD7;
            padding: 5px;
        }

        QMenu::item {
            padding: 8px 24px 8px 12px;
            border-radius: 5px;
        }

        QMenu::item:selected {
            background: #F1F1EE;
        }

        """)

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(
            0
        )

        # ====================================================
        # SIDEBAR
        # ====================================================

        self.sidebar = QFrame()

        self.sidebar.setObjectName(
            "sidebar"
        )

        self.sidebar.setFixedWidth(
            235
        )

        sidebar_layout = QVBoxLayout(
            self.sidebar
        )

        sidebar_layout.setContentsMargins(
            16,
            18,
            16,
            16,
        )

        sidebar_layout.setSpacing(
            5
        )

        # ----------------------------------------------------
        # Название программы
        # ----------------------------------------------------

        app_title = QLabel(
            "DevJournal"
        )

        app_title.setObjectName(
            "appTitle"
        )

        sidebar_layout.addWidget(
            app_title
        )

        project_label = QLabel(
            "ЛИЧНЫЙ ДНЕВНИК РАЗРАБОТЧИКА"
        )

        project_label.setObjectName(
            "projectLabel"
        )

        sidebar_layout.addWidget(
            project_label
        )

        sidebar_layout.addSpacing(
            22
        )

        # ----------------------------------------------------
        # Проект
        # ----------------------------------------------------

        project_section = QLabel(
            "PROJECT"
        )

        project_section.setObjectName(
            "sectionLabel"
        )

        sidebar_layout.addWidget(
            project_section
        )

        self.project_name_label = QLabel(
            "Проект не выбран"
        )

        self.project_name_label.setStyleSheet(
            """
            font-weight: 600;
            padding: 7px 0;
            """
        )

        sidebar_layout.addWidget(
            self.project_name_label
        )

        sidebar_layout.addSpacing(
            18
        )

        # ----------------------------------------------------
        # Разделы
        # ----------------------------------------------------

        sections_label = QLabel(
            "РАЗДЕЛЫ"
        )

        sections_label.setObjectName(
            "sectionLabel"
        )

        sidebar_layout.addWidget(
            sections_label
        )

        sections = [
            "📖  Дневник",
            "🌍  Мир",
            "👤  Персонажи",
            "🏙  Локации",
            "🎮  Геймплей",
            "🎨  Арт",
            "🔧  Техника",
        ]

        self.section_buttons = []

        for i, name in enumerate(
            sections
        ):

            button = QPushButton(
                name
            )

            if i == 0:

                button.setObjectName(
                    "activeSection"
                )

            sidebar_layout.addWidget(
                button
            )

            self.section_buttons.append(
                button
            )

        sidebar_layout.addStretch()

        # ====================================================
        # ПРАВАЯ ЧАСТЬ
        # ====================================================

        right_widget = QWidget()

        right_layout = QVBoxLayout(
            right_widget
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_layout.setSpacing(
            0
        )

        # ====================================================
        # ВЕРХНЯЯ ПАНЕЛЬ
        # ====================================================

        toolbar = QFrame()

        toolbar.setObjectName(
            "toolbar"
        )

        toolbar_layout = QHBoxLayout(
            toolbar
        )

        toolbar_layout.setContentsMargins(
            12,
            4,
            12,
            4,
        )

        toolbar_layout.setSpacing(
            4
        )

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        file_button = QToolButton()

        file_button.setText(
            "File"
        )

        file_button.setObjectName(
            "menuButton"
        )

        file_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        file_menu = QMenu(
            file_button
        )

        new_action = file_menu.addAction(
            "Создать проект"
        )

        open_action = file_menu.addAction(
            "Открыть проект"
        )

        file_menu.addSeparator()

        save_action = file_menu.addAction(
            "Сохранить"
        )

        new_action.triggered.connect(
            self.new_project
        )

        open_action.triggered.connect(
            self.open_project
        )

        save_action.triggered.connect(
            self.save_project
        )

        file_button.setMenu(
            file_menu
        )

        toolbar_layout.addWidget(
            file_button
        )

        # ----------------------------------------------------
        # EDIT
        # ----------------------------------------------------

        edit_button = QToolButton()

        edit_button.setText(
            "Edit"
        )

        edit_button.setObjectName(
            "menuButton"
        )

        edit_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        edit_menu = QMenu(
            edit_button
        )

        settings_action = edit_menu.addAction(
            "Настройки рабочего пространства"
        )

        edit_menu.addSeparator()

        grid_dots_action = edit_menu.addAction(
            "Сетка: точки"
        )

        grid_lines_action = edit_menu.addAction(
            "Сетка: линии"
        )

        grid_none_action = edit_menu.addAction(
            "Сетка: выключена"
        )

        settings_action.triggered.connect(
            self.open_settings
        )

        grid_dots_action.triggered.connect(
            lambda: self.set_grid_mode("dots")
        )

        grid_lines_action.triggered.connect(
            lambda: self.set_grid_mode("grid")
        )

        grid_none_action.triggered.connect(
            lambda: self.set_grid_mode("none")
        )

        edit_button.setMenu(
            edit_menu
        )

        toolbar_layout.addWidget(
            edit_button
        )

        toolbar_layout.addSpacing(
            12
        )

        # ----------------------------------------------------
        # ДОБАВЛЕНИЕ
        # ----------------------------------------------------

        add_text_button = self.toolbar_button(
            "+ Текст",
            "Добавить карточку",
            self.add_card,
        )

        toolbar_layout.addWidget(
            add_text_button
        )

        image_button = self.toolbar_button(
            "Image",
            "Добавить изображение",
            self.add_image,
        )

        toolbar_layout.addWidget(
            image_button
        )

        toolbar_layout.addStretch()

        # ----------------------------------------------------
        # ZOOM
        # ----------------------------------------------------

        zoom_minus = self.toolbar_button(
            "−",
            "Уменьшить масштаб",
            self.zoom_out,
        )

        toolbar_layout.addWidget(
            zoom_minus
        )

        self.zoom_label = QLabel(
            "100%"
        )

        self.zoom_label.setObjectName(
            "zoomLabel"
        )

        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        toolbar_layout.addWidget(
            self.zoom_label
        )

        zoom_plus = self.toolbar_button(
            "+",
            "Увеличить масштаб",
            self.zoom_in,
        )

        toolbar_layout.addWidget(
            zoom_plus
        )

        right_layout.addWidget(
            toolbar
        )

        # ====================================================
        # CANVAS
        # ====================================================

        self.canvas = Canvas(
            self
        )

        right_layout.addWidget(
            self.canvas
        )

        # ====================================================
        # STATUS BAR
        # ====================================================

        self.status_label = QLabel(
            "Готово"
        )

        self.status_label.setObjectName(
            "statusLabel"
        )

        self.statusBar().addWidget(
            self.status_label
        )

        # ====================================================
        # СОБИРАЕМ
        # ====================================================

        main_layout.addWidget(
            self.sidebar
        )

        main_layout.addWidget(
            right_widget
        )

    # ========================================================
    # TOOLBAR BUTTON
    # ========================================================

    def toolbar_button(
        self,
        text,
        tooltip,
        callback,
    ):

        button = QToolButton()

        button.setText(
            text
        )

        button.setToolTip(
            tooltip
        )

        button.clicked.connect(
            callback
        )

        return button

    # ========================================================
    # СЕТКА
    # ========================================================

    def set_grid_mode(
        self,
        mode,
    ):

        self.canvas.grid_mode = mode

        self.canvas.viewport().update()

        self.canvas.save_board()

        self.update_status(
            "Настройка сетки изменена"
        )

    # ========================================================
    # ZOOM
    # ========================================================

    def zoom_in(self):

        self.canvas.zoom_in()

    def zoom_out(self):

        self.canvas.zoom_out()

    # ========================================================
    # СТАТУС
    # ========================================================

    def update_status(
        self,
        text,
    ):

        self.status_label.setText(
            text
        )

    # ========================================================
    # ZOOM LABEL
    # ========================================================

    def update_zoom_label(
        self,
        value,
    ):

        self.zoom_label.setText(
            f"{value}%"
        )

    # ========================================================
    # НОВЫЙ ПРОЕКТ
    # ========================================================

    def new_project(self):

        name, ok = QInputDialog.getText(
            self,
            "Новый проект",
            "Название проекта:",
        )

        if not ok:
            return

        name = safe_project_name(
            name
        )

        if not name:
            return

        self.project_name = name

        ensure_project_folder(
            name
        )

        self.project_name_label.setText(
            name
        )

        self.canvas.scene.clear()

        self.canvas.grid_mode = "dots"

        self.canvas.set_zoom(
            100
        )

        self.update_status(
            "Создан новый проект"
        )

        self.canvas.save_board()

    # ========================================================
    # ОТКРЫТЬ ПРОЕКТ
    # ========================================================

    def open_project(self):

        if not os.path.exists(
            BOARDS_DIR
        ):

            os.makedirs(
                BOARDS_DIR
            )

        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку проекта",
            BOARDS_DIR,
        )

        if not folder:
            return

        project_name = os.path.basename(
            os.path.normpath(
                folder
            )
        )

        self.project_name = project_name

        self.project_name_label.setText(
            project_name
        )

        self.canvas.load_board(
            project_name
        )

    # ========================================================
    # СОХРАНИТЬ
    # ========================================================

    def save_project(self):

        if not self.project_name:

            self.new_project()

            return

        self.canvas.save_board()

    # ========================================================
    # ДОБАВИТЬ КАРТОЧКУ
    # ========================================================

    def add_card(self):

        card = self.canvas.add_card()

        card.setSelected(
            True
        )

        self.update_status(
            "Добавлена новая карточка"
        )

        self.canvas.save_board()

    # ========================================================
    # ИЗОБРАЖЕНИЕ
    # ========================================================

    def add_image(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        self.canvas.add_image()

    # ========================================================
    # УДАЛЕНИЕ
    # ========================================================

    def delete_selected(self):

        self.canvas.delete_selected()

    # ========================================================
    # НАСТРОЙКИ
    # ========================================================

    def open_settings(self):

        dialog = SettingsDialog(
            self.canvas,
            self,
        )

        if dialog.exec():

            self.canvas.save_board()

            self.update_status(
                "Настройки сохранены"
            )

    # ========================================================
    # KEYBOARD
    # ========================================================

    def keyPressEvent(
        self,
        event,
    ):

        modifiers = event.modifiers()

        if (
            modifiers
            &
            Qt.KeyboardModifier.ControlModifier
        ):

            if event.key() == Qt.Key.Key_S:

                self.save_project()

                event.accept()

                return

            if event.key() == Qt.Key.Key_O:

                self.open_project()

                event.accept()

                return

            if event.key() == Qt.Key.Key_N:

                self.new_project()

                event.accept()

                return

        if event.key() == Qt.Key.Key_Delete:

            self.delete_selected()

            event.accept()

            return

        super().keyPressEvent(
            event
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event,
    ):

        if self.project_name:

            self.canvas.save_board()

        event.accept()


# ============================================================
# ЗАПУСК
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    window = DevJournal()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()