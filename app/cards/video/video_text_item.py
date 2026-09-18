import os

from PySide6.QtCore import (
    Qt,
    QRectF,
    QPointF,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
    QBrush,
    QPen,
    QPixmap,
)
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput,
    QVideoSink,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QGraphicsObject,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QGraphicsPixmapItem,
    QWidget,
    QVBoxLayout,
    QMenu,
)


# =========================================================
# Текстовый элемент
# =========================================================

class CardTextItem(QGraphicsTextItem):

    def __init__(
        self,
        text,
        parent_card,
    ):
        super().__init__(
            text,
            parent_card,
        )

        self.parent_card = parent_card

        self._editing_enabled = False

    # =========================================================
    # MOUSE / FOCUS
    # =========================================================

    def mousePressEvent(
        self,
        event,
    ):
        self.parent_card.setSelected(
            True
        )

        super().mousePressEvent(
            event
        )

        self.parent_card.update()

        # Активируем редактирование + тулбар
        self.set_editing_enabled(True)
        self._register_for_format_toolbar()

    def mouseDoubleClickEvent(
        self,
        event,
    ):
        super().mouseDoubleClickEvent(event)

        self.set_editing_enabled(True)
        self._register_for_format_toolbar()

    def focusInEvent(
        self,
        event,
    ):
        super().focusInEvent(event)

        self.set_editing_enabled(True)
        self._register_for_format_toolbar()

    def focusOutEvent(
        self,
        event,
    ):
        self.set_editing_enabled(False)

        super().focusOutEvent(event)

    # =========================================================
    # EDITING STATE
    # =========================================================

    # =========================================================
    # FORMAT TOOLBAR FOCUS GUARD
    # =========================================================

    def _is_format_toolbar_interaction(self):
        """
        Проверяет, является ли текущая потеря фокуса
        результатом взаимодействия с плавающей панелью
        форматирования.

        Важно:
        CardTextItem является QGraphicsTextItem, а toolbar
        является обычным QWidget. Поэтому проверять QWidget-фокус
        напрямую здесь нельзя.

        Вместо этого проверяем положение курсора мыши,
        popup ComboBox и модальное окно QColorDialog.
        """

        from PySide6.QtGui import QCursor
        from PySide6.QtCore import QRect
        from PySide6.QtWidgets import QApplication

        scene = self.scene()

        if scene is None:
            return False

        views = scene.views()

        if not views:
            return False

        main_window = getattr(
            views[0],
            "main_window",
            None,
        )

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

    def is_editing_enabled(self):
        return (
            self.textInteractionFlags()
            != Qt.TextInteractionFlag.NoTextInteraction
        )

    def set_editing_enabled(
        self,
        enabled,
    ):
        self._editing_enabled = bool(enabled)

        scene = self.scene()

        main_window = None

        if scene is not None:
            views = scene.views()

            if views:
                main_window = getattr(
                    views[0],
                    "main_window",
                    None,
                )

        if enabled:

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

            self.setCursor(
                Qt.CursorShape.IBeamCursor
            )

            self.setFocus(
                Qt.FocusReason.MouseFocusReason
            )

            if main_window is not None:
                activator = getattr(
                    main_window,
                    "activate_text",
                    None,
                )

                if callable(activator):
                    try:
                        activator(self)
                    except Exception:
                        pass

        else:

            cursor = self.textCursor()

            if cursor is not None:
                cursor.clearSelection()
                self.setTextCursor(cursor)

            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )

            # НЕ отключаем фокус полностью — иначе повторный клик не сработает.
            self.setFlag(
                QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable,
                True,
            )

            # ВАЖНО: не ставим NoButton — иначе повторный клик не сработает.
            self.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton
            )

            self.unsetCursor()

            # ВАЖНО: если потеря фокуса — это клик в тулбар или его popup,
            # НЕ вызываем deactivate_text (иначе тулбар закроется).
            is_toolbar_interaction = False

            try:
                is_toolbar_interaction = self._is_format_toolbar_interaction()
            except Exception:
                is_toolbar_interaction = False

            if not is_toolbar_interaction:
                self.clearFocus()

                if main_window is not None:
                    deactivator = getattr(
                        main_window,
                        "deactivate_text",
                        None,
                    )

                    if callable(deactivator):
                        try:
                            deactivator()
                        except Exception:
                            pass
            else:
                # Фокус ушёл в тулбар — оставляем всё как есть,
                # тулбар продолжает работать.
                self.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable,
                    True,
                )

    # =========================================================
    # TOOLBAR REGISTRATION
    # =========================================================

    def _register_for_format_toolbar(self):
        scene = self.scene()

        if scene is None:
            return

        views = scene.views()

        if not views:
            return

        view = views[0]

        main_window = getattr(
            view,
            "main_window",
            None,
        )

        if main_window is None:
            return

        activator = getattr(
            main_window,
            "activate_text",
            None,
        )

        if callable(activator):
            try:
                activator(self)
            except Exception:
                pass


class VideoWindow(QWidget):

    def __init__(
        self,
        video_path,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.setWindowTitle(
            "Видео"
        )

        self.resize(
            900,
            600,
        )

        self.video_widget = QVideoWidget()

        self.player = QMediaPlayer(
            self
        )

        self.audio_output = QAudioOutput(
            self
        )

        self.player.setAudioOutput(
            self.audio_output
        )

        self.player.setVideoOutput(
            self.video_widget
        )

        self.audio_output.setVolume(
            1.0
        )

        self.player.setSource(
            QUrl.fromLocalFile(
                video_path
            )
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addWidget(
            self.video_widget
        )

        self.player.play()

    def closeEvent(
        self,
        event,
    ):
        self.player.stop()

        event.accept()


# =========================================================
# Видео + текст
# =========================================================

class VideoTextItem(QGraphicsObject):

    MIN_WIDTH = 260
    MIN_HEIGHT = 280
    SNAP_THRESHOLD = 5.0

    CONNECTION_POINT_RADIUS = 5

    def __init__(
        self,
        title="",
        text="",
        video_path="",
        width=360,
        height=420,
    ):
        super().__init__()

        self.item_width = float(
            width
        )

        self.card_id = None

        self.item_height = float(
            height
        )

        self.video_path = video_path

        self.runtime_video_path = video_path

        self.card_color = "#FFFFFF"

        self.video_window = None

        self.dragging_resize = False

        self.resize_start_pos = QPointF()

        self.resize_start_width = (
            self.item_width
        )

        self.resize_start_height = (
            self.item_height
        )

        self.setFlag(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable,
            True,
        )

        self.setFlag(
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable,
            True,
        )

        self.setFlag(
            QGraphicsObject.GraphicsItemFlag.ItemIsFocusable,
            True,
        )

        # Snap guides: без этого флага itemChange не вызывается при движении
        self.setFlag(
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setAcceptHoverEvents(
            True
        )

        self.background = QGraphicsRectItem(
            self
        )

        self.background.setBrush(
            QBrush(
                QColor(
                    self.card_color
                )
            )
        )

        self.background.setPen(
            QPen(
                QColor("#D9D9D5"),
                1,
            )
        )

        self.background.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )

        self.video_background = QGraphicsRectItem(
            self
        )

        self.video_background.setBrush(
            Qt.BrushStyle.NoBrush
        )

        self.video_background.setPen(
            Qt.PenStyle.NoPen
        )

        self.video_background.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )

        self.video_preview = QGraphicsPixmapItem(
            self
        )

        self.video_preview.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )

        self.video_preview.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )

        self.title_item = CardTextItem(
            title,
            self,
        )

        self.title_item.setDefaultTextColor(
            QColor("#222222")
        )

        self.title_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )

        self.body_item = CardTextItem(
            text,
            self,
        )

        self.body_item.setDefaultTextColor(
            QColor("#444444")
        )

        self.body_item.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )

        self.title_item.document().contentsChanged.connect(
            self.on_text_changed
        )

        self.body_item.document().contentsChanged.connect(
            self.on_text_changed
        )

        self.resize_handle = QGraphicsRectItem(
            self
        )

        self.resize_handle.setBrush(
            Qt.BrushStyle.NoBrush
        )

        self.resize_handle.setPen(
            Qt.PenStyle.NoPen
        )

        self.resize_handle.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )

        self.preview_pixmap = QPixmap()

        self.video_sink = QVideoSink(
            self
        )

        self.video_player = QMediaPlayer(
            self
        )

        self.video_audio = QAudioOutput(
            self
        )

        self.video_audio.setVolume(
            0.0
        )

        self.video_player.setAudioOutput(
            self.video_audio
        )

        self.video_player.setVideoSink(
            self.video_sink
        )

        self.video_sink.videoFrameChanged.connect(
            self.on_video_frame
        )

        self.preview_loaded = False

        if self.runtime_video_path:

            self.load_preview(
                self.runtime_video_path
            )

        self.update_layout(
            auto_resize=False
        )

        self.arrows = []

        # Привязка к рамке (устанавливается frame_containment)
        self._frame = None

    # =====================================================
    # Геометрия
    # =====================================================

    def boundingRect(self):

        return QRectF(
            0,
            0,
            self.item_width,
            self.item_height,
        )

    def has_connection_point(self):
        return True

    def connection_point(self):

        radius = self.CONNECTION_POINT_RADIUS

        return QPointF(
            self.item_width - radius,
            self.item_height - radius,
        )

    # =====================================================
    # Layout
    # =====================================================

    def update_layout(
        self,
        auto_resize=True,
    ):

        width = self.item_width
        height = self.item_height

        margin = 16

        video_height = min(
            220,
            max(
                120,
                height * 0.52,
            ),
        )

        self.video_rect = QRectF(
            margin,
            margin,
            width - margin * 2,
            video_height,
        )

        self.video_background.setRect(
            self.video_rect
        )

        if not self.preview_pixmap.isNull():

            target_width = int(
                self.video_rect.width()
            )

            target_height = int(
                self.video_rect.height()
            )

            scaled = self.preview_pixmap.scaled(
                target_width,
                target_height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

            crop_x = max(
                0,
                (
                    scaled.width()
                    -
                    target_width
                ) // 2
            )

            crop_y = max(
                0,
                (
                    scaled.height()
                    -
                    target_height
                ) // 2
            )

            cropped = scaled.copy(
                crop_x,
                crop_y,
                target_width,
                target_height,
            )

            self.video_preview.setPixmap(
                cropped
            )

            self.video_preview.setPos(
                self.video_rect.x(),
                self.video_rect.y(),
            )

        else:

            self.video_preview.setPixmap(
                QPixmap()
            )

        title_y = (
            self.video_rect.bottom()
            + 12
        )

        text_width = max(
            50,
            width - margin * 2,
        )

        self.title_item.setTextWidth(
            text_width
        )

        self.title_item.setPos(
            margin,
            title_y,
        )

        title_height = (
            self.title_item
            .boundingRect()
            .height()
        )

        body_y = (
            title_y
            +
            title_height
            +
            6
        )

        self.body_item.setTextWidth(
            text_width
        )

        self.body_item.setPos(
            margin,
            body_y,
        )

        if auto_resize:

            body_height = (
                self.body_item
                .boundingRect()
                .height()
            )

            required_height = (
                body_y
                +
                body_height
                +
                24
            )

            required_height = max(
                self.MIN_HEIGHT,
                required_height,
            )

            if abs(
                required_height
                -
                self.item_height
            ) > 1:

                self.prepareGeometryChange()

                self.item_height = (
                    required_height
                )

                height = (
                    self.item_height
                )

        self.background.setRect(
            0,
            0,
            width,
            self.item_height,
        )

        handle_size = 14

        self.resize_handle.setRect(
            width
            -
            handle_size
            -
            4,
            self.item_height
            -
            handle_size
            -
            4,
            handle_size,
            handle_size,
        )

        self.update()

    def on_text_changed(self):

        self.update_layout(
            auto_resize=True
        )

    def set_card_color(
        self,
        color,
    ):

        qcolor = QColor(color)

        if not qcolor.isValid():
            qcolor = QColor("#FFFFFF")

        self.card_color = qcolor.name(
            QColor.NameFormat.HexArgb
        )

        self.background.setBrush(
            QBrush(
                qcolor
            )
        )

        self.background.update()

        self.update()

    def get_card_color(self):

        qcolor = QColor(
            self.card_color
        )

        if not qcolor.isValid():
            qcolor = QColor("#FFFFFF")

        return qcolor.name(
            QColor.NameFormat.HexArgb
        )

    # =====================================================
    # Контекстное меню
    # =====================================================

    def contextMenuEvent(
        self,
        event,
    ):

        self.setSelected(
            True
        )

        self.setFocus(
            Qt.FocusReason.MouseFocusReason
        )

        menu = QMenu()

        color_action = menu.addAction(
            "Цвет"
        )

        delete_action = menu.addAction(
            "Удалить"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == color_action:

            scene = self.scene()

            if scene is not None:

                if not scene.views():
                    event.accept()
                    return

                window = (
                    scene.views()[0].window()
                )

                if hasattr(
                    window,
                    "change_selected_color",
                ):

                    window.change_selected_color()

        elif action == delete_action:

            scene = self.scene()

            if scene is not None:

                if not scene.views():
                    event.accept()
                    return

                window = (
                    scene.views()[0].window()
                )

                if hasattr(
                    window,
                    "delete_selected",
                ):

                    window.delete_selected()

        event.accept()

    # =====================================================
    # Видео-превью
    # =====================================================

    def load_preview(
        self,
        video_path,
    ):

        if not video_path:
            return

        if not os.path.exists(
            video_path
        ):
            return

        try:

            self.video_player.setSource(
                QUrl.fromLocalFile(
                    video_path
                )
            )

            self.video_player.play()

        except Exception:

            pass

    def on_video_frame(
        self,
        frame,
    ):

        if self.preview_loaded:
            return

        if not frame.isValid():
            return

        image = frame.toImage()

        if image.isNull():
            return

        self.preview_pixmap = (
            QPixmap.fromImage(
                image
            )
        )

        self.preview_loaded = True

        self.video_player.pause()

        self.update_layout(
            auto_resize=False
        )

    def open_video(self):

        video_path = (
            self.runtime_video_path
        )

        if not video_path:

            video_path = (
                self.video_path
            )

        if not video_path:
            return

        if not os.path.isabs(
            video_path
        ):
            return

        if not os.path.exists(
            video_path
        ):
            return

        self.video_window = VideoWindow(
            video_path
        )

        self.video_window.show()

        self.video_window.raise_()

        self.video_window.activateWindow()

    # =====================================================
    # Наведение
    # =====================================================

    def hoverMoveEvent(
        self,
        event,
    ):

        pos = event.pos()

        handle_rect = (
            self.resize_handle.rect()
        )

        if handle_rect.contains(
            pos
        ):

            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor
            )

        elif (
            hasattr(
                self,
                "video_rect",
            )
            and
            self.video_rect.contains(
                pos
            )
        ):

            self.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        else:

            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        super().hoverMoveEvent(
            event
        )

    # =====================================================
    # Нажатие мыши
    # =====================================================

    def mousePressEvent(
        self,
        event,
    ):

        pos = event.pos()

        if (
            event.button()
            ==
            Qt.MouseButton.RightButton
        ):

            self.setSelected(
                True
            )

            self.contextMenuEvent(
                event
            )

            return

        if (
            event.button()
            ==
            Qt.MouseButton.LeftButton
            and
            self.resize_handle.rect().contains(
                pos
            )
        ):

            self.dragging_resize = True

            self.resize_start_pos = pos

            self.resize_start_width = (
                self.item_width
            )

            self.resize_start_height = (
                self.item_height
            )

            self.setSelected(
                True
            )

            self.setFocus(
                Qt.FocusReason.MouseFocusReason
            )

            event.accept()

            return

        self.setSelected(
            True
        )

        self.setFocus(
            Qt.FocusReason.MouseFocusReason
        )

        super().mousePressEvent(
            event
        )

    # =====================================================
    # Движение мыши
    # =====================================================

    def mouseMoveEvent(
        self,
        event,
    ):

        if self.dragging_resize:

            delta = (
                event.pos()
                -
                self.resize_start_pos
            )

            new_width = (
                self.resize_start_width
                +
                delta.x()
            )

            new_height = (
                self.resize_start_height
                +
                delta.y()
            )

            new_width = max(
                self.MIN_WIDTH,
                new_width,
            )

            new_height = max(
                self.MIN_HEIGHT,
                new_height,
            )

            self.prepareGeometryChange()

            self.item_width = (
                new_width
            )

            self.item_height = (
                new_height
            )

            self.update_layout(
                auto_resize=False
            )

            event.accept()

            return

        super().mouseMoveEvent(
            event
        )

    # =====================================================
    # Отпускание мыши
    # =====================================================

    def mouseReleaseEvent(
        self,
        event,
    ):

        # Snap guides: убираем направляющие при отпускании
        try:
            scene = self.scene()

            if scene is not None:
                views = scene.views()

                if views:
                    view = views[0]
                    clearer = getattr(view, "clear_snap_guides", None)

                    if callable(clearer):
                        clearer()
        except Exception:
            pass

        if self.dragging_resize:

            self.dragging_resize = False

            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

            event.accept()

            return

        super().mouseReleaseEvent(
            event
        )

        # =====================================================
        # FRAME MEMBERSHIP
        # =====================================================

        if event.button() == Qt.MouseButton.LeftButton:

            try:
                from ...canvas.frame_containment import (
                    update_item_membership,
                )

                update_item_membership(
                    self,
                    self.scene(),
                )

            except Exception as exc:
                print(
                    f"[VIDEO] membership update failed: {exc!r}"
                )

    # =====================================================
    # Двойной клик
    # =====================================================

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        pos = event.pos()

        if (
            hasattr(
                self,
                "video_rect",
            )
            and
            self.video_rect.contains(
                pos
            )
        ):

            self.open_video()

            event.accept()

            return

        super().mouseDoubleClickEvent(
            event
        )

    # =====================================================
    # Изменение состояния
    # =====================================================

    def itemChange(
        self,
        change,
        value,
    ):

        if (
            change
            ==
            QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged
        ):

            arrows = getattr(self, "arrows", None)

            if arrows:

                for arrow in list(arrows):

                    try:
                        arrow.update_position()

                    except Exception:
                        pass

            # Snap guides: прилипание к другим карточкам
            try:
                from ..base.card import Card

                Card._apply_snap(self)
            except Exception:
                pass

        if (
            change
            ==
            QGraphicsObject.GraphicsItemChange.ItemSelectedChange
        ):

            selected = bool(
                value
            )

            if selected:

                self.background.setPen(
                    QPen(
                        QColor("#777777"),
                        2,
                    )
                )

            else:

                self.background.setPen(
                    QPen(
                        QColor("#D9D9D5"),
                        1,
                    )
                )

        return super().itemChange(
            change,
            value,
        )

    # =====================================================
    # Отрисовка
    # =====================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):

        painter.setRenderHint(
            painter.RenderHint.Antialiasing
        )

        if self.isSelected():

            painter.setPen(
                QPen(
                    QColor("#777777"),
                    2,
                )
            )

        else:

            painter.setPen(
                QPen(
                    QColor("#D9D9D5"),
                    1,
                )
            )

        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )

        painter.drawRoundedRect(
            self.boundingRect(),
            10,
            10,
        )

        point = self.connection_point()

        radius = self.CONNECTION_POINT_RADIUS

        painter.setPen(
            QPen(
                QColor("#777777"),
                1,
            )
        )

        painter.setBrush(
            QBrush(
                QColor("#FFFFFF")
            )
        )

        painter.drawEllipse(
            point,
            radius,
            radius,
        )