from PySide6.QtCore import QObject


class FormatToolbarController(QObject):
    """
    Управляет положением и состоянием плавающей панели
    форматирования относительно активной текстовой карточки.
    """

    GAP = 8

    def __init__(self, main_window):
        super().__init__(main_window)

        self.main_window = main_window
        self.toolbar = main_window.format_toolbar
        self.canvas = main_window.canvas

        self.canvas.horizontalScrollBar().valueChanged.connect(
            self.update_position
        )

        self.canvas.verticalScrollBar().valueChanged.connect(
            self.update_position
        )

    def show_for_item(self, text_item):
        if text_item is None:
            return

        self.toolbar.set_active_item(text_item)
        self.toolbar.adjustSize()
        self.toolbar.show()
        self.toolbar.raise_()

        self.update_position()

    def hide(self):
        self.toolbar.hide()

    def update_position(self, *args):
        text_item = self.main_window.active_text_item

        if text_item is None:
            return

        if text_item.scene() is None:
            return

        if not self.toolbar.isVisible():
            return

        # ---------------------------------------------------------
        # Определяем границу самой карточки.
        # ---------------------------------------------------------

        card_item = text_item.parentItem()

        if card_item is not None:
            card_rect = card_item.sceneBoundingRect()
        else:
            card_rect = text_item.sceneBoundingRect()

        # ---------------------------------------------------------
        # Левая верхняя точка карточки -> viewport.
        # ---------------------------------------------------------

        viewport_point = self.canvas.mapFromScene(
            card_rect.topLeft()
        )

        # ---------------------------------------------------------
        # viewport -> глобальные координаты.
        # ---------------------------------------------------------

        global_point = self.canvas.viewport().mapToGlobal(
            viewport_point
        )

        # ---------------------------------------------------------
        # Глобальные координаты -> главное окно.
        # ---------------------------------------------------------

        window_point = self.main_window.mapFromGlobal(
            global_point
        )

        # ---------------------------------------------------------
        # Панель ставим ПОЛНОСТЬЮ слева от карточки.
        #
        # Левая граница панели:
        #
        #     левая граница карточки
        #     - ширина панели
        #     - зазор
        #
        # Поэтому панель физически не пересекает карточку.
        # ---------------------------------------------------------

        x = (
            window_point.x()
            - self.toolbar.width()
            - self.GAP
        )

        y = window_point.y()

        self.toolbar.move(
            x,
            y,
        )