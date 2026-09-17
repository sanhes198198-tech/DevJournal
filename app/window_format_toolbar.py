"""
Компактная вертикальная панель форматирования текста.

Появляется рядом с активным текстом.
Содержит:
- жирный;
- курсив;
- подчёркивание;
- шрифт;
- размер;
- цвет текста;
- цвет фона;
- выравнивание.
"""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import (
    QFont,
    QColor,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QComboBox,
    QFrame,
    QFontComboBox,
)


class FormatToolbar(QWidget):
    """
    Компактная вертикальная панель форматирования.

    Скрыта по умолчанию.
    Показывается, когда активен EditableText.
    """

    format_bold = Signal(bool)
    format_italic = Signal(bool)
    format_underline = Signal(bool)
    format_family = Signal(str)
    format_size = Signal(int)
    format_color = Signal(QColor)
    format_background = Signal(QColor)
    format_align = Signal(Qt.AlignmentFlag)

    FONT_SIZES = [
        8,
        9,
        10,
        11,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        28,
        32,
    ]

    PANEL_WIDTH = 122

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName(
            "formatToolbar"
        )

        self.setFixedWidth(
            self.PANEL_WIDTH
        )

        # =========================================================
        # Панель не должна сама забирать фокус.
        # =========================================================

        self.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.active_item = None

        # =========================================================
        # Белая подложка панели
        # =========================================================

        self.substrate = QFrame(
            self
        )

        self.substrate.setObjectName(
            "formatToolbarSubstrate"
        )

        self.substrate.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.substrate.lower()

        # =========================================================
        # Основной layout
        # =========================================================

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            7,
            7,
            7,
            7,
        )

        layout.setSpacing(
            5
        )

        # =========================================================
        # Жирный / Курсив / Подчёркивание
        # =========================================================

        text_style_row = QHBoxLayout()

        text_style_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        text_style_row.setSpacing(
            3
        )

        self.btn_bold = self._toggle_button(
            "Ж",
            "Жирный",
        )

        self.btn_italic = self._toggle_button(
            "К",
            "Курсив",
        )

        self.btn_underline = self._toggle_button(
            "Ч",
            "Подчёркнутый",
        )

        self.btn_bold.toggled.connect(
            self.format_bold.emit
        )

        self.btn_italic.toggled.connect(
            self.format_italic.emit
        )

        self.btn_underline.toggled.connect(
            self.format_underline.emit
        )

        text_style_row.addWidget(
            self.btn_bold
        )

        text_style_row.addWidget(
            self.btn_italic
        )

        text_style_row.addWidget(
            self.btn_underline
        )

        layout.addLayout(
            text_style_row
        )

        # =========================================================
        # Разделитель
        # =========================================================

        layout.addWidget(
            self._separator()
        )

        # =========================================================
        # Шрифт
        # =========================================================

        self.font_combo = QFontComboBox()

        self.font_combo.setFixedHeight(
            28
        )

        self.font_combo.setMinimumWidth(
            0
        )

        self.font_combo.setEditable(
            False
        )

        self.font_combo.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        # Popup списка также не должен оставлять фокус
        # на самом ComboBox.
        self.font_combo.view().setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.font_combo.currentFontChanged.connect(
            self._on_font_changed
        )

        layout.addWidget(
            self.font_combo
        )

        # =========================================================
        # Размер
        # =========================================================

        self.size_combo = QComboBox()

        self.size_combo.setFixedHeight(
            28
        )

        self.size_combo.setEditable(
            False
        )

        self.size_combo.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        # Popup списка также не должен забирать фокус.
        self.size_combo.view().setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        for size in self.FONT_SIZES:
            self.size_combo.addItem(
                str(size)
            )

        self.size_combo.setCurrentText(
            "12"
        )

        self.size_combo.currentTextChanged.connect(
            self._on_size_changed
        )

        layout.addWidget(
            self.size_combo
        )

        # =========================================================
        # Разделитель
        # =========================================================

        layout.addWidget(
            self._separator()
        )

        # =========================================================
        # Цвет текста / цвет фона
        # =========================================================

        color_row = QHBoxLayout()

        color_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        color_row.setSpacing(
            3
        )

        self.btn_color = self._color_button(
            "A",
            "Цвет текста",
        )

        self.btn_bg = self._color_button(
            "Ф",
            "Цвет фона",
        )

        self.btn_color.clicked.connect(
            self._pick_color
        )

        self.btn_bg.clicked.connect(
            self._pick_bg
        )

        color_row.addWidget(
            self.btn_color
        )

        color_row.addWidget(
            self.btn_bg
        )

        layout.addLayout(
            color_row
        )

        # =========================================================
        # Разделитель
        # =========================================================

        layout.addWidget(
            self._separator()
        )

        # =========================================================
        # Выравнивание
        # =========================================================

        align_row = QHBoxLayout()

        align_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        align_row.setSpacing(
            3
        )

        self.btn_align_left = self._tool_button(
            "⇤",
            "По левому краю",
        )

        self.btn_align_center = self._tool_button(
            "⇔",
            "По центру",
        )

        self.btn_align_right = self._tool_button(
            "⇥",
            "По правому краю",
        )

        self.btn_align_left.clicked.connect(
            lambda: self.format_align.emit(
                Qt.AlignmentFlag.AlignLeft
            )
        )

        self.btn_align_center.clicked.connect(
            lambda: self.format_align.emit(
                Qt.AlignmentFlag.AlignHCenter
            )
        )

        self.btn_align_right.clicked.connect(
            lambda: self.format_align.emit(
                Qt.AlignmentFlag.AlignRight
            )
        )

        align_row.addWidget(
            self.btn_align_left
        )

        align_row.addWidget(
            self.btn_align_center
        )

        align_row.addWidget(
            self.btn_align_right
        )

        layout.addLayout(
            align_row
        )

        # =========================================================
        # Фильтр событий для элементов панели
        # =========================================================

        toolbar_widgets = (
            self.btn_bold,
            self.btn_italic,
            self.btn_underline,
            self.font_combo,
            self.size_combo,
            self.btn_color,
            self.btn_bg,
            self.btn_align_left,
            self.btn_align_center,
            self.btn_align_right,
        )

        for widget in toolbar_widgets:
            widget.installEventFilter(
                self
            )

        # =========================================================
        # Стиль панели
        # =========================================================

        self.setStyleSheet(
            """
            /* =====================================================
               Сама панель прозрачная.
               Фон рисует отдельная подложка.
               ===================================================== */

            QWidget#formatToolbar {
                background: transparent;
                border: none;
            }

            /* =====================================================
               Белая подложка
               ===================================================== */

            QFrame#formatToolbarSubstrate {
                background-color: #FFFFFF;

                border: 1px solid rgba(
                    170,
                    170,
                    165,
                    170
                );

                border-radius: 16px;
            }

            /* =====================================================
               Кнопки
               ===================================================== */

            QToolButton {
                background: #FAFAF8;

                border: 1px solid transparent;
                border-radius: 7px;

                color: #333333;

                min-width: 28px;
                max-width: 28px;

                min-height: 28px;
                max-height: 28px;

                padding: 0px;

                font-size: 12px;
                font-weight: 600;
            }

            QToolButton:hover {
                background: #F1F1EE;
                border-color: #D8D8D2;
            }

            QToolButton:pressed {
                background: #E9E9E4;
            }

            QToolButton:checked {
                background: #E6EEFF;

                border-color: #B8CFFF;

                color: #3355BB;
            }

            /* =====================================================
               Поля выбора
               ===================================================== */

            QComboBox,
            QFontComboBox {
                background: #FAFAF8;

                border: 1px solid #DCDCD7;
                border-radius: 7px;

                padding: 2px 6px;

                color: #333333;

                font-size: 11px;
            }

            QComboBox:hover,
            QFontComboBox:hover {
                background: #F1F1EE;
                border-color: #D2D2CC;
            }

            QComboBox:focus,
            QFontComboBox:focus {
                border-color: #C8C8C2;
            }

            QComboBox::drop-down,
            QFontComboBox::drop-down {
                width: 18px;
                border: none;
            }

            QComboBox QAbstractItemView,
            QFontComboBox QAbstractItemView {
                background: #FFFFFF;

                border: 1px solid #DCDCD7;
                border-radius: 7px;

                padding: 3px;

                selection-background-color: #E6EEFF;
                selection-color: #333333;
            }

            /* =====================================================
               Разделители
               ===================================================== */

            QFrame#formatSeparator {
                background: #E5E5E0;

                border: none;

                min-height: 1px;
                max-height: 1px;
            }
            """
        )

        # =========================================================
        # Первичная геометрия подложки
        # =========================================================

        self.substrate.setGeometry(
            self.rect()
        )

        self.substrate.lower()

    # =============================================================
    # Защита фокуса активного текста
    # =============================================================

    def eventFilter(
        self,
        watched,
        event,
    ):
        """
        Не даёт элементам панели форматирования
        завершать редактирование активного текста.

        Особенно важно для ComboBox:
        Qt создаёт отдельный popup для списка,
        который может участвовать в смене фокуса.
        """

        if (
            event.type()
            == QEvent.Type.MouseButtonPress
        ):
            if self.active_item is not None:
                self.active_item.setFocus(
                    Qt.FocusReason.OtherFocusReason
                )

        return super().eventFilter(
            watched,
            event,
        )

    # =============================================================
    # Геометрия
    # =============================================================

    def resizeEvent(
        self,
        event,
    ):
        """
        Подгоняет белую подложку под размер панели.
        """

        super().resizeEvent(
            event
        )

        if hasattr(
            self,
            "substrate",
        ):
            self.substrate.setGeometry(
                self.rect()
            )

            self.substrate.lower()

    # =============================================================
    # Состояние активного текста
    # =============================================================

    def set_active_item(
        self,
        item,
    ):
        self.active_item = item

        if item is None:
            return

        try:
            font = item.font()

            self.btn_bold.blockSignals(
                True
            )

            self.btn_italic.blockSignals(
                True
            )

            self.btn_underline.blockSignals(
                True
            )

            self.btn_bold.setChecked(
                font.bold()
            )

            self.btn_italic.setChecked(
                font.italic()
            )

            self.btn_underline.setChecked(
                font.underline()
            )

            self.btn_bold.blockSignals(
                False
            )

            self.btn_italic.blockSignals(
                False
            )

            self.btn_underline.blockSignals(
                False
            )

        except Exception:
            pass

    # =============================================================
    # Применение форматирования
    # =============================================================

    def _apply_to_selection(
        self,
        item,
        char_format,
    ):
        cursor = item.textCursor()

        if not cursor.hasSelection():
            cursor.select(
                QTextCursor.SelectionType.Document
            )

        cursor.mergeCharFormat(
            char_format
        )

        item.setTextCursor(
            cursor
        )

        # Возвращаем фокус текстовому объекту.
        item.setFocus(
            Qt.FocusReason.OtherFocusReason
        )

    def toggle_bold(
        self,
        item,
        checked,
    ):
        fmt = QTextCharFormat()

        fmt.setFontWeight(
            QFont.Weight.Bold
            if checked
            else QFont.Weight.Normal
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def toggle_italic(
        self,
        item,
        checked,
    ):
        fmt = QTextCharFormat()

        fmt.setFontItalic(
            checked
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def toggle_underline(
        self,
        item,
        checked,
    ):
        fmt = QTextCharFormat()

        fmt.setFontUnderline(
            checked
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def apply_family(
        self,
        item,
        family,
    ):
        fmt = QTextCharFormat()

        fmt.setFontFamilies(
            [family]
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def apply_size(
        self,
        item,
        size,
    ):
        fmt = QTextCharFormat()

        fmt.setFontPointSize(
            float(size)
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def apply_color(
        self,
        item,
        color,
    ):
        fmt = QTextCharFormat()

        fmt.setForeground(
            color
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def apply_background(
        self,
        item,
        color,
    ):
        fmt = QTextCharFormat()

        fmt.setBackground(
            color
        )

        self._apply_to_selection(
            item,
            fmt,
        )

    def apply_align(
        self,
        item,
        alignment,
    ):
        cursor = item.textCursor()

        if not cursor.hasSelection():
            cursor.select(
                QTextCursor.SelectionType.Document
            )

        block_fmt = cursor.blockFormat()

        block_fmt.setAlignment(
            alignment
        )

        cursor.mergeBlockFormat(
            block_fmt
        )

        item.setTextCursor(
            cursor
        )

        item.setFocus(
            Qt.FocusReason.OtherFocusReason
        )

    # =============================================================
    # Создание кнопок
    # =============================================================

    def _toggle_button(
        self,
        text,
        tooltip,
    ):
        button = QToolButton()

        button.setText(
            text
        )

        button.setToolTip(
            tooltip
        )

        button.setCheckable(
            True
        )

        button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        return button

    def _tool_button(
        self,
        text,
        tooltip,
    ):
        button = QToolButton()

        button.setText(
            text
        )

        button.setToolTip(
            tooltip
        )

        button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        return button

    def _color_button(
        self,
        text,
        tooltip,
    ):
        button = QToolButton()

        button.setText(
            text
        )

        button.setToolTip(
            tooltip
        )

        button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        return button

    def _separator(self):
        frame = QFrame()

        frame.setObjectName(
            "formatSeparator"
        )

        frame.setFrameShape(
            QFrame.Shape.HLine
        )

        frame.setFrameShadow(
            QFrame.Shadow.Plain
        )

        return frame

    # =============================================================
    # События
    # =============================================================

    def _on_font_changed(
        self,
        font,
    ):
        self.format_family.emit(
            font.family()
        )

        if self.active_item is not None:
            self.active_item.setFocus(
                Qt.FocusReason.OtherFocusReason
            )

    def _on_size_changed(
        self,
        text,
    ):
        try:
            size = int(text)
        except ValueError:
            return

        self.format_size.emit(
            size
        )

        if self.active_item is not None:
            self.active_item.setFocus(
                Qt.FocusReason.OtherFocusReason
            )

    def _pick_color(self):
        """
        Открывает палитру для текста
        и применяет выбранный цвет.
        """

        from .canvas.color import show_palette

        color = show_palette(
            self,
            "#000000",
            palette_type="text",
        )

        if color.isValid():
            self.format_color.emit(
                color
            )

        if self.active_item is not None:
            self.active_item.setFocus(
                Qt.FocusReason.OtherFocusReason
            )

    def _pick_bg(self):
        """
        Открывает палитру для фона текста
        и применяет выбранный цвет.
        """

        from .canvas.color import show_palette

        color = show_palette(
            self,
            "#FFFFFF",
            palette_type="text",
        )

        if color.isValid():
            self.format_background.emit(
                color
            )

        if self.active_item is not None:
            self.active_item.setFocus(
                Qt.FocusReason.OtherFocusReason
            )