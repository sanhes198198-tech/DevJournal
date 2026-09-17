import os
import traceback

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QGraphicsTextItem,
    QApplication,
)


class EditableText(QGraphicsTextItem):
    """
    Редактируемый текстовый элемент карточки.

    По умолчанию редактирование выключено.
    Включается двойным кликом по тексту.
    При потере фокуса редактирование завершается
    сразу, а выделение текста очищается.
    """

    def __init__(self, text="", parent=None):
        super().__init__(parent)

        self.setPlainText(text)

        self.setFont(
            QFont(
                "Roboto",
                10,
            )
        )

        from PySide6.QtGui import QColor

        self.setDefaultTextColor(
            QColor("#444444")
        )

        # Защита от повторного входа в focusOutEvent.
        self._ending_editing = False

        # По умолчанию редактирование выключено.
        self.set_editing_enabled(False)

    # =========================================================
    # MAIN WINDOW LOOKUP
    # =========================================================

    def _get_main_window(self):

        if not self.scene():
            return None

        views = self.scene().views()

        if not views:
            return None

        view = views[0]

        return getattr(view, "main_window", None)

    # =========================================================
    # FORMAT TOOLBAR FOCUS GUARD
    # =========================================================

    def _is_format_toolbar_interaction(self):
        """
        Проверяет, является ли текущая потеря фокуса
        результатом взаимодействия с плавающей панелью
        форматирования.

        Важно:
        EditableText является QGraphicsTextItem, а toolbar
        является обычным QWidget. Поэтому проверять QWidget-фокус
        напрямую здесь нельзя.

        Вместо этого проверяем положение курсора мыши,
        popup ComboBox и модальное окно QColorDialog.
        """

        main_window = self._get_main_window()

        if main_window is None:
            return False

        toolbar = getattr(
            main_window,
            "format_toolbar",
            None,
        )

        if toolbar is None:
            return False

        if not toolbar.isVisible():
            return False

        global_pos = QCursor.pos()

        # -----------------------------------------------------
        # Сам FormatToolbar
        # -----------------------------------------------------

        toolbar_top_left = toolbar.mapToGlobal(
            toolbar.rect().topLeft()
        )

        toolbar_rect = QRect(
            toolbar_top_left,
            toolbar.size(),
        )

        if toolbar_rect.contains(global_pos):
            return True

        # -----------------------------------------------------
        # Popup ComboBox / QFontComboBox
        # -----------------------------------------------------

        popup = QApplication.activePopupWidget()

        if popup is not None and popup.isVisible():

            popup_top_left = popup.mapToGlobal(
                popup.rect().topLeft()
            )

            popup_rect = QRect(
                popup_top_left,
                popup.size(),
            )

            if popup_rect.contains(global_pos):
                return True

        # -----------------------------------------------------
        # Модальный диалог цвета
        # -----------------------------------------------------

        modal = QApplication.activeModalWidget()

        if modal is not None and modal.isVisible():

            current = modal

            while current is not None:

                if current is toolbar:
                    return True

                current = current.parentWidget()

        return False

    # =========================================================
    # SELECTION
    # =========================================================

    def _clear_selection(self):
        """
        Полностью снимает выделение текста.
        """

        cursor = self.textCursor()

        if not cursor.hasSelection():
            return

        cursor.clearSelection()

        self.setTextCursor(cursor)

    # =========================================================
    # EDITING MODE
    # =========================================================

    def keyPressEvent(self, event):
        """
        После каждой нажатой клавиши применяем цвет.
        Qt при вводе символа подставляет свой дефолт (чёрный),
        игнорируя defaultTextColor.
        """

        super().keyPressEvent(event)

        try:
            self.apply_text_color()
        except Exception:
            pass

    def inputMethodEvent(self, event):
        """
        То же для IME (китайский, японский и т.п.).
        """

        super().inputMethodEvent(event)

        try:
            self.apply_text_color()
        except Exception:
            pass

    def insertFromMimeData(self, source):
        """
        То же для вставки из буфера (Ctrl+V).
        """

        super().insertFromMimeData(source)

        try:
            self.apply_text_color()
        except Exception:
            pass

    def set_editing_enabled(self, enabled):

        if enabled:

            self._ending_editing = False

            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )

            self.setFlag(
                QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable,
                True,
            )

            self.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton
            )

            # I-beam как в текстовом редакторе.
            self.setCursor(
                Qt.CursorShape.IBeamCursor
            )

            self.setFocus(
                Qt.FocusReason.MouseFocusReason
            )

            # Уведомляем главное окно.
            main_window = self._get_main_window()

            if main_window and hasattr(
                main_window,
                "activate_text",
            ):
                main_window.activate_text(self)

        else:

            # Если уже завершаем редактирование,
            # повторно ничего не делаем.
            if self._ending_editing:
                return

            self._ending_editing = True

            # Сначала снимаем выделение.
            # Это важно делать ДО отключения взаимодействия.
            self._clear_selection()

            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )

            self.setFlag(
                QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable,
                False,
            )

            self.setAcceptedMouseButtons(
                Qt.MouseButton.NoButton
            )

            self.unsetCursor()

            # Убираем фокус.
            self.clearFocus()

            # Уведомляем главное окно.
            main_window = self._get_main_window()

            if main_window and hasattr(
                main_window,
                "deactivate_text",
            ):
                main_window.deactivate_text()

            self._ending_editing = False

    def is_editing_enabled(self):
        return (
            self.textInteractionFlags()
            != Qt.TextInteractionFlag.NoTextInteraction
        )

    # =========================================================
    # FOCUS
    # =========================================================

    def apply_text_color(self, color=None):
        """
        Применяет цвет ко всему документу.
        Используется для принудительной установки цвета
        после набора текста (Qt сбрасывает defaultTextColor
        при вводе первого символа).
        """

        from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor

        # HARDCODE: всегда применяем #444444.
        # self.defaultTextColor() может вернуть чёрный,
        # потому что Qt подставляет чёрный при наборе текста.
        if color is None:
            color = QColor("#444444")

        try:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)

            fmt = QTextCharFormat()
            fmt.setForeground(color)

            cursor.mergeCharFormat(fmt)

            cursor.clearSelection()
            self.setTextCursor(cursor)
        except Exception:
            pass

    def focusOutEvent(self, event):
        """
        Завершает редактирование сразу после потери фокуса.

        Исключение:
        если потеря фокуса вызвана взаимодействием
        с плавающей панелью форматирования, редактирование
        НЕ завершается.

        Это позволяет нажимать кнопки форматирования,
        выбирать шрифт/размер и открывать диалог цвета,
        не закрывая режим редактирования текста.
        """

        if (
            self.is_editing_enabled()
            and not self._ending_editing
        ):
            if not self._is_format_toolbar_interaction():
                self.set_editing_enabled(False)

        # Принудительно применяем цвет ко всему документу —
        # иначе Qt оставляет чёрный цвет от ввода первого символа.
        try:
            self.apply_text_color()
        except Exception:
            pass

        super().focusOutEvent(event)