"""
Работа с цветом карточек на холсте.

Содержит функции get_item_color и change_selected_color,
которые раньше были методами класса Canvas.
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
    QFrame,
    QApplication,
)


# Фиксированная палитра цветов карточек.
CARD_COLORS = [
    "#FFFFFF",  # White
    "#F2F2F2",  # Light Gray
    "#000000",  # Black

    "#AACC96",  # Tea Green
    "#25533F",  # Forest
    "#F4BEAE",  # Peach Frost

    "#52A5CE",  # Blue Berry
    "#FF7BAC",  # Bubble-Gum
    "#876029",  # Dry Earth

    "#6D1F42",  # Grape Juice
    "#D3B6D3",  # Lilacs
    "#EFCE7B",  # Butter Yellow

    "#B8CEE8",  # Iced Blue
    "#EF6F3C",  # Blood Orange
    "#AFAB23",  # Olive Green
]


# Палитра для цвета текста и фона текста.
TEXT_COLORS = [
    "#000000",  # Black
    "#FFFFFF",  # White
    "#333333",  # Dark Gray

    "#FF0000",  # Red
    "#FF7F00",  # Orange
    "#FFD700",  # Gold

    "#00AA00",  # Green
    "#00AAAA",  # Teal
    "#0000FF",  # Blue

    "#8A2BE2",  # Violet
    "#FF69B4",  # Pink
    "#8B4513",  # Brown
]


def get_item_color(item):
    """
    Возвращает цвет элемента в формате '#AARRGGBB'.

    Работает с любым элементом: пытается вызвать get_card_color(),
    если такого метода нет — читает атрибут card_color.
    """

    if hasattr(item, "get_card_color"):

        try:
            result = item.get_card_color()

            if isinstance(result, QColor):

                if not result.isValid():
                    return "#FFFFFFFF"

                return result.name(
                    QColor.NameFormat.HexArgb
                )

            qcolor = QColor(str(result))

            if qcolor.isValid():

                return qcolor.name(
                    QColor.NameFormat.HexArgb
                )

        except Exception:
            pass

    color = getattr(
        item,
        "card_color",
        "#FFFFFFFF",
    )

    if isinstance(color, QColor):

        if not color.isValid():
            return "#FFFFFFFF"

        return color.name(
            QColor.NameFormat.HexArgb
        )

    color = str(color)

    qcolor = QColor(color)

    if qcolor.isValid():

        return qcolor.name(
            QColor.NameFormat.HexArgb
        )

    return "#FFFFFFFF"


def _normalize_color(color):
    """
    Приводит цвет к единому формату '#AARRGGBB'.
    """

    qcolor = QColor(color)

    if not qcolor.isValid():
        return "#FFFFFFFF"

    return qcolor.name(
        QColor.NameFormat.HexArgb
    ).upper()


def _apply_color(canvas, item, color):
    """
    Применяет выбранный цвет к элементу.
    """

    if hasattr(item, "set_card_color"):

        try:
            item.set_card_color(color)

        except Exception:
            pass

    elif hasattr(item, "set_color"):

        try:
            item.set_color(color)

        except Exception:
            pass

    else:

        try:
            item.card_color = color.name(
                QColor.NameFormat.HexArgb
            )

        except Exception:
            return

        if hasattr(item, "update"):
            item.update()

    if canvas is not None:
        canvas.save_board()

    if canvas is not None and canvas.main_window:
        canvas.main_window.update_status(
            "Цвет карточки изменен"
        )


class ColorPalette(QWidget):
    """
    Минимальная плавающая палитра.

    Содержит 12 цветных квадратов 3x4.
    Без названий, без hex-кодов, без текста.
    """

    # Размер одного квадрата
    SWATCH_SIZE = 44

    # Скругление квадрата
    SWATCH_RADIUS = 8

    # Отступы между квадратами
    SPACING = 6

    # Внутренний паддинг панели
    PADDING = 8

    def __init__(
        self,
        canvas,
        item,
        parent=None,
        colors=None,
    ):
        super().__init__(
            parent,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint,
        )

        self.canvas = canvas
        self.item = item

        # Если None — используем CARD_COLORS.
        self._override_colors = colors

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        self.setObjectName(
            "colorPalette"
        )

        self._build_palette()

    def _current_colors(self):

        if self._override_colors is not None:
            return self._override_colors

        return CARD_COLORS

    def _rebuild_with_colors(self, colors):
        """
        Пересобирает палитру с новым набором цветов.
        Полностью удаляет старый layout и всех детей.
        """

        self._override_colors = colors

        # Удаляем всех детей напрямую
        for child in self.findChildren(QWidget):
            child.setParent(None)
            child.deleteLater()

        # Удаляем старый layout (если был)
        old_layout = self.layout()

        if old_layout is not None:
            old_layout.deleteLater()

        # Пересобираем
        self._build_palette()

        self.adjustSize()

    def _build_palette(self):

        colors = self._current_colors()

        current_color = get_item_color(self.item)

        # Внешний контейнер с фоном и скруглением
        outer = QFrame(self)

        outer.setObjectName("colorPaletteFrame")

        outer.setStyleSheet(
            """
            QFrame#colorPaletteFrame {
                background: #F5F0E8;
                border: 1px solid #E0D9CC;
                border-radius: 10px;
            }
            """
        )

        outer_layout = QGridLayout(outer)

        outer_layout.setContentsMargins(
            self.PADDING,
            self.PADDING,
            self.PADDING,
            self.PADDING,
        )

        outer_layout.setHorizontalSpacing(
            self.SPACING
        )

        outer_layout.setVerticalSpacing(
            self.SPACING
        )

        for index, color in enumerate(colors):

            row = index // 3
            column = index % 3

            button = self._create_button(
                color,
                current_color,
            )

            outer_layout.addWidget(
                button,
                row,
                column,
            )

        # Внешний layout у самого виджета — без отступов
        wrapper = QGridLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(outer)

    def _create_button(self, color, selected_color):

        button = QPushButton(self)

        button.setFixedSize(
            self.SWATCH_SIZE,
            self.SWATCH_SIZE,
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        normalized_color = _normalize_color(color)
        normalized_selected = _normalize_color(selected_color)

        selected = (
            normalized_color == normalized_selected
        )

        if selected:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {color};
                    border: 2px solid #30302E;
                    border-radius: {self.SWATCH_RADIUS}px;
                    padding: 0px;
                    margin: 0px;
                }}

                QPushButton:hover {{
                    border: 2px solid #111111;
                }}
                """
            )

        else:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {color};
                    border: 1px solid rgba(0, 0, 0, 40);
                    border-radius: {self.SWATCH_RADIUS}px;
                    padding: 0px;
                    margin: 0px;
                }}

                QPushButton:hover {{
                    border: 1px solid #555550;
                }}
                """
            )

        button.clicked.connect(
            lambda checked=False,
                   selected_color=color:
                self._select_color(selected_color)
        )

        return button

    def _select_color(self, color):

        _apply_color(
            self.canvas,
            self.item,
            QColor(color),
        )

        self.close()

    def show_at_cursor(self):

        self.adjustSize()

        position = (
            QCursor.pos()
            + QPoint(8, 8)
        )

        self.move(position)

        self.show()


def _show_color_palette(canvas, item):
    """
    Показывает палитру из 12 цветов.
    """

    palette = ColorPalette(
        canvas,
        item,
        canvas.main_window,
    )

    palette.show_at_cursor()

    canvas._color_palette = palette


def change_selected_color(canvas):
    """
    Открывает палитру из 12 цветов
    и применяет выбранный цвет
    к выделенному элементу.
    """

    selected = (
        canvas.scene.selectedItems()
    )

    if not selected:
        return

    item = selected[0]

    _show_color_palette(
        canvas,
        item,
    )


# =========================================================
# УНИВЕРСАЛЬНАЯ ПАЛИТРА
# =========================================================

class _FakeColorItem:
    """
    Заглушка для элемента, чтобы ColorPalette работала
    без карточки (для цветов текста, фона и т.п.).
    """

    def __init__(self, color):

        self.card_color = (
            color if color is not None else "#FFFFFF"
        )


def show_palette(
    parent,
    current_color=None,
    palette_type="card",
):
    """
    Универсальная палитра.

    Показывает палитру из 12 цветов, НЕ привязываясь к карточке.
    Возвращает QColor — выбранный или невалидный
    (если пользователь закрыл без выбора).

    palette_type:
        "card" — 12 цветов для карточки (по умолчанию).
        "text" — палитра для текста и фона текста.
    """

    if palette_type == "text":
        colors = TEXT_COLORS
    else:
        colors = CARD_COLORS

    fake_item = _FakeColorItem(current_color)

    # Создаём палитру СРАЗУ с нужными цветами
    palette = ColorPalette(
        canvas=None,
        item=fake_item,
        parent=parent,
        colors=colors,
    )

    # Контейнер для результата
    palette._picked_color = None

    def _on_select(color_str):

        palette._picked_color = color_str
        palette.close()

    # Подменяем поведение выбора цвета
    palette._select_color = _on_select

    palette.show_at_cursor()

    # Ждём, пока палитра закроется
    while palette.isVisible():

        QApplication.processEvents()

    if palette._picked_color is not None:

        return QColor(palette._picked_color)

    return QColor()