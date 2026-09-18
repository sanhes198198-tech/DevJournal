import os

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPointF,
)

from PySide6.QtGui import (
    QColor,
    QPen,
    QPainter,
)

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QFrame,
)

from .board_io import (
    save_board as _save_board,
    load_board as _load_board,
)

from .factories import (
    add_card as _add_card,
    add_image_text_card as _add_image_text_card,
    add_video_text_card as _add_video_text_card,
    add_image as _add_image,
    add_file as _add_file,
    add_arrow as _add_arrow,
)

from .color import (
    get_item_color as _get_item_color,
    change_selected_color as _change_selected_color,
)

from .delete import (
    delete_item as _delete_item,
    delete_selected as _delete_selected,
)

from ..items.arrow_ui import (
    create_free_arrow,
)


class Canvas(QGraphicsView):

    def mousePressEvent(self, event):

        # =====================================================
        # MIDDLE MOUSE — панорамирование
        # =====================================================

        if event.button() == Qt.MouseButton.MiddleButton:

            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

            event.accept()
            return

        # DEACTIVATE TEXT ON EMPTY CLICK
        try:
            item = self.itemAt(event.pos())

            if item is None:

                window = getattr(self, "main_window", None)

                if window is None:
                    window = getattr(
                        getattr(self, "parent", None),
                        "main_window",
                        None,
                    )

                if window is not None:

                    deactivator = getattr(
                        window,
                        "deactivate_text",
                        None,
                    )

                    if callable(deactivator):
                        deactivator()

        except Exception:
            pass

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        # Панорамирование при зажатом middle mouse
        if getattr(self, "_panning", False):

            if self._pan_start is not None:

                delta = event.pos() - self._pan_start

                self._pan_start = event.pos()

                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() - delta.x()
                )

                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() - delta.y()
                )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        # Завершение панорамирования
        if event.button() == Qt.MouseButton.MiddleButton:

            self._panning = False
            self._pan_start = None
            self.unsetCursor()

            event.accept()
            return

        super().mouseReleaseEvent(event)

    MIN_ZOOM = 25
    MAX_ZOOM = 200
    ZOOM_STEP = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent

        # =================================================
        # Scene
        # =================================================

        self.scene = QGraphicsScene(self)

        self.setScene(self.scene)

        self.scene.setSceneRect(
            -5000,
            -5000,
            10000,
            10000,
        )

        # =================================================
        # Snap-направляющие (рисуются через drawForeground)
        # =================================================

        self._snap_v_lines = []
        self._snap_h_lines = []

        # =================================================
        # Внешний вид
        # =================================================

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

        # ЛКМ на пустом месте — выделение рамкой (RubberBand).
        # Панорамирование — через колёсико мыши (middle button).
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
        )

        self._panning = False
        self._pan_start = None

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
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

        # =================================================
        # Zoom / grid
        # =================================================

        self.zoom_factor = 1.0

        self.grid_mode = "dots"

        # =================================================
        # Autosave
        # =================================================

        self.autosave_timer = QTimer(self)

        self.autosave_timer.timeout.connect(
            self.autosave
        )

        self.autosave_timer.start(
            30000
        )

    # =====================================================
    # COLOR
    # =====================================================

    def _get_item_color(self, item):
        return _get_item_color(item)

    def change_selected_color(self):
        return _change_selected_color(self)

    # =====================================================
    # BACKGROUND / GRID
    # =====================================================

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
            int(rect.left()) % grid_size
        )

        top = (
            int(rect.top())
            -
            int(rect.top()) % grid_size
        )

        # -------------------------------------------------
        # Dots
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Grid
        # -------------------------------------------------

        elif self.grid_mode == "grid":

            painter.setPen(
                QPen(
                    QColor("#E8E8E4"),
                    1,
                )
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

    # =====================================================
    # ZOOM
    # =====================================================

    def set_zoom(
        self,
        value,
    ):

        value = max(
            self.MIN_ZOOM,
            min(
                self.MAX_ZOOM,
                int(value),
            ),
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

    def set_zoom_at(
        self,
        value,
        viewport_pos,
    ):
        """
        Меняет масштаб относительно указанной точки
        viewport.

        Точка под курсором остаётся под курсором после
        изменения масштаба.
        """

        value = max(
            self.MIN_ZOOM,
            min(
                self.MAX_ZOOM,
                int(value),
            ),
        )

        new_factor = value / 100.0

        if abs(
            new_factor - self.zoom_factor
        ) < 0.0001:
            return

        # Точка сцены, которая сейчас находится под курсором.
        scene_pos_before = self.mapToScene(
            viewport_pos
        )

        # Полностью пересоздаём transform.
        self.resetTransform()

        self.scale(
            new_factor,
            new_factor,
        )

        self.zoom_factor = new_factor

        # После изменения масштаба определяем,
        # куда попала та же точка сцены.
        scene_pos_after = self.mapToScene(
            viewport_pos
        )

        delta = (
            scene_pos_before
            -
            scene_pos_after
        )

        self.translate(
            delta.x(),
            delta.y(),
        )

        if self.main_window:

            self.main_window.update_zoom_label(
                value
            )

        self.viewport().update()

    def zoom_in(self):

        current = int(
            self.zoom_factor * 100
        )

        center = self.viewport().rect().center()

        self.set_zoom_at(
            current + self.ZOOM_STEP,
            center,
        )

    def zoom_out(self):

        current = int(
            self.zoom_factor * 100
        )

        center = self.viewport().rect().center()

        self.set_zoom_at(
            current - self.ZOOM_STEP,
            center,
        )

    def wheelEvent(
        self,
        event,
    ):
        """
        Колесо мыши управляет масштабом.

        Масштабирование происходит относительно курсора,
        поэтому пользователь не теряет текущую точку обзора.
        """

        delta = event.angleDelta().y()

        if delta == 0:
            event.accept()
            return

        current = int(
            self.zoom_factor * 100
        )

        if delta > 0:

            new_value = (
                current
                +
                self.ZOOM_STEP
            )

        else:

            new_value = (
                current
                -
                self.ZOOM_STEP
            )

        self.set_zoom_at(
            new_value,
            event.position().toPoint(),
        )

        event.accept()

    # =====================================================
    # VIEW STATE
    # =====================================================

    def get_view_state(self):
        """
        Возвращает текущее состояние камеры Canvas.

        Сохраняются:
        - масштаб;
        - горизонтальная позиция;
        - вертикальная позиция.
        """

        return {
            "zoom": float(
                self.zoom_factor
            ),
            "scroll_x": int(
                self.horizontalScrollBar().value()
            ),
            "scroll_y": int(
                self.verticalScrollBar().value()
            ),
        }

    def restore_view_state(
        self,
        view_state,
    ):
        """
        Восстанавливает состояние камеры.

        Старые проекты могут не иметь блока view.
        В таком случае используется текущее состояние Canvas.
        """

        if not isinstance(
            view_state,
            dict,
        ):
            return

        zoom = view_state.get(
            "zoom",
            1.0,
        )

        try:
            zoom = float(zoom)
        except (
            TypeError,
            ValueError,
        ):
            zoom = 1.0

        zoom_percent = int(
            round(
                zoom * 100
            )
        )

        zoom_percent = max(
            self.MIN_ZOOM,
            min(
                self.MAX_ZOOM,
                zoom_percent,
            ),
        )

        scroll_x = view_state.get(
            "scroll_x",
            0,
        )

        scroll_y = view_state.get(
            "scroll_y",
            0,
        )

        try:
            scroll_x = int(scroll_x)
        except (
            TypeError,
            ValueError,
        ):
            scroll_x = 0

        try:
            scroll_y = int(scroll_y)
        except (
            TypeError,
            ValueError,
        ):
            scroll_y = 0

        # Сначала восстанавливаем масштаб.
        self.set_zoom(
            zoom_percent
        )

        # Затем положение.
        self.horizontalScrollBar().setValue(
            scroll_x
        )

        self.verticalScrollBar().setValue(
            scroll_y
        )

        self.viewport().update()

    # =====================================================
    # ADD CARD
    # =====================================================

    def add_card(
        self,
        title="",
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
        return _add_card(
            self,
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
            card_type=card_type,
            image_path=image_path,
            card_id=card_id,
        )

    # =====================================================
    # ADD IMAGE + TEXT
    # =====================================================

    def add_image_text_card(self):
        return _add_image_text_card(self)

    # =====================================================
    # ADD VIDEO + TEXT
    # =====================================================

    def add_video_text_card(self):
        return _add_video_text_card(self)

    # =====================================================
    # ADD IMAGE
    # =====================================================

    def add_image(self):
        return _add_image(self)

    # =====================================================
    # ADD FILE
    # =====================================================

    def add_file(self):
        return _add_file(self)

    # =====================================================
    # ADD ARROW
    # =====================================================

    def add_arrow(
        self,
        source_item,
        target_item,
    ):
        return _add_arrow(
            self,
            source_item,
            target_item,
        )

    # =====================================================
    # ARROW FROM UI (ПКМ)
    # =====================================================

    def start_arrow_from(self, source_item):
        """
        Создаёт стрелку от source_item
        через отдельный UI-модуль.
        """

        if source_item is None:
            return None

        from PySide6.QtGui import QCursor
        from ..cards.base.connection import nearest_point_index

        point_index = None

        try:
            cursor_pos = QCursor.pos()
            view_pos = self.mapFromGlobal(cursor_pos)
            scene_pos = self.mapToScene(view_pos)
            source_local = source_item.mapFromScene(scene_pos)
            point_index = nearest_point_index(source_item, source_local)
        except Exception:
            point_index = None

        arrow = create_free_arrow(
            scene=self.scene,
            source_item=source_item,
            source_point_index=point_index,
        )

        if arrow is None:
            return None

        try:
            arrow.setSelected(True)
        except Exception:
            pass

        self.save_board()

        return arrow

    # =====================================================
    # DELETE
    # =====================================================

    def delete_item(
        self,
        item,
    ):
        return _delete_item(self, item)

    def delete_selected(self):
        return _delete_selected(self)

    # =====================================================
    # SAVE
    # =====================================================

    # =====================================================
    # SNAP GUIDES
    # =====================================================

    def set_snap_guides(self, vertical=None, horizontal=None):
        """
        Устанавливает линии-направляющие для выравнивания.
        """

        new_v = list(vertical or [])
        new_h = list(horizontal or [])


        if self._snap_v_lines == new_v and self._snap_h_lines == new_h:
            return

        self._snap_v_lines = new_v
        self._snap_h_lines = new_h

        self.viewport().update()

    def clear_snap_guides(self):
        """
        Убирает все направляющие.
        """

        if not self._snap_v_lines and not self._snap_h_lines:
            return

        self._snap_v_lines = []
        self._snap_h_lines = []

        self.viewport().update()

    def drawForeground(self, painter, rect):
        """
        Рисует линии-направляющие ПОВЕРХ всей сцены.
        Вызывается Qt автоматически после отрисовки сцены.
        """

        super().drawForeground(painter, rect)

        if not self._snap_v_lines and not self._snap_h_lines:
            return

        from PySide6.QtGui import QColor, QPen, QPainter
        from PySide6.QtCore import QLineF, Qt

        painter.save()

        pen = QPen(QColor("#9A9A9A"), 1.0)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)

        painter.setPen(pen)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            False,
        )

        top = rect.top()
        bottom = rect.bottom()
        left = rect.left()
        right = rect.right()

        for x in self._snap_v_lines:
            painter.drawLine(QLineF(x, top, x, bottom))

        for y in self._snap_h_lines:
            painter.drawLine(QLineF(left, y, right, y))

        painter.restore()

    def dump_scene_items(self):
        """
        Debug: печатает все items на сцене.
        """

        print("=== SCENE DUMP ===")
        print(f"Total items: {len(self.scene.items())}")

        for item in self.scene.items():
            try:
                name = type(item).__name__
                pos = item.pos()
                print(
                    f"  {name} id={id(item)} "
                    f"pos=({pos.x():.1f}, {pos.y():.1f}) "
                    f"visible={item.isVisible()} "
                    f"z={item.zValue()}"
                )
            except Exception as exc:
                print(f"  ERROR: {exc!r}")

        print("=== END DUMP ===")

    def save_board(self):
        return _save_board(self)

    # =====================================================
    # LOAD
    # =====================================================

    def load_board(
        self,
        project_name,
    ):
        return _load_board(
            self,
            project_name,
        )

    # =====================================================
    # AUTOSAVE
    # =====================================================

    def autosave(self):

        if self.main_window.project_name:

            self.save_board()