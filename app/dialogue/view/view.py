"""
QGraphicsView для редактора диалогов.

Поведение:
- колесо → zoom относительно курсора
- middle mouse → pan
- ЛКМ по пустому → rubber band selection
- ЛКМ по узлу → drag узла
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QShortcut, QKeySequence
from PySide6.QtWidgets import QGraphicsView, QFrame, QInputDialog, QMessageBox

from .scene import DialogueScene
from .floating_toolbar import FloatingToolbar


class DialogueView(QGraphicsView):
    """Виджет просмотра и редактирования диалогового графа."""

    MIN_ZOOM = 25
    MAX_ZOOM = 300
    ZOOM_STEP = 5          # % за одно деление колеса

    def __init__(self, parent=None):
        super().__init__(parent)

        # Своя сцена
        self.dialogue_scene = DialogueScene(self)
        self.setScene(self.dialogue_scene)

        # Внешний вид
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )

        # Скроллбары — не показываем, но используем
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Режим drag: rubber band по пустому
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
        )

        # Фокус — чтобы Delete и другие клавиши работали
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Zoom
        self.zoom_factor = 1.0

        # Pan (middle mouse)
        self._panning = False
        self._pan_start = QPoint()

        # Delete shortcut — надёжнее чем keyPressEvent
        self._setup_delete_shortcut()

        # Ctrl+D — дублирование узлов
        self._setup_duplicate_shortcut()

        # Ctrl+C / Ctrl+X / Ctrl+V — копирование/вырезание/вставка
        self._setup_clipboard_shortcuts()

        # Плавающий toolbar внизу справа
        self._setup_floating_toolbar()

        # Ctrl+0 и Ctrl+F настраиваются в DialogueEditorWindow,
        # чтобы не конфликтовать с QShortcut главного окна DevJournal

    def _setup_delete_shortcut(self):
        """QShortcut для Delete — работает вне зависимости от фокуса."""
        sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._on_delete_shortcut)

    def _on_delete_shortcut(self):
        scene = self.dialogue_scene
        delete = getattr(scene, "delete_selected", None)
        if callable(delete):
            delete()

    def _setup_duplicate_shortcut(self):
        """QShortcut для Ctrl+D — дублирование выделенных узлов."""
        sc = QShortcut(QKeySequence("Ctrl+D"), self)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._on_duplicate_shortcut)

    def _on_duplicate_shortcut(self):
        scene = self.dialogue_scene
        dup = getattr(scene, "duplicate_selected", None)
        if callable(dup):
            dup()

    def _setup_floating_toolbar(self):
        """Создаёт плавающий toolbar и подключает кнопки."""
        self._floating_toolbar = FloatingToolbar(self)

        self._floating_toolbar.btn_zoom_out.clicked.connect(
            self.zoom_out
        )
        self._floating_toolbar.btn_zoom_in.clicked.connect(
            self.zoom_in
        )
        self._floating_toolbar.btn_zoom_fit.clicked.connect(
            self.zoom_to_fit
        )
        self._floating_toolbar.btn_find.clicked.connect(
            self.find_node_dialog
        )

        self._floating_toolbar.raise_()
        self._position_floating_toolbar()

    def _position_floating_toolbar(self):
        """Ставит toolbar в правый-нижний угол."""
        tb = getattr(self, "_floating_toolbar", None)
        if tb is None:
            return

        tb.adjustSize()
        margin = 16
        x = self.width() - tb.width() - margin
        y = self.height() - tb.height() - margin
        tb.move(x, y)
        tb.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_floating_toolbar()

    def _setup_clipboard_shortcuts(self):
        """QShortcut для Ctrl+C / Ctrl+X / Ctrl+V."""
        sc_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        sc_copy.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_copy.activated.connect(self._on_copy_shortcut)

        sc_cut = QShortcut(QKeySequence("Ctrl+X"), self)
        sc_cut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_cut.activated.connect(self._on_cut_shortcut)

        sc_paste = QShortcut(QKeySequence("Ctrl+V"), self)
        sc_paste.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_paste.activated.connect(self._on_paste_shortcut)

    def _on_copy_shortcut(self):
        scene = self.dialogue_scene
        f = getattr(scene, "copy_selected", None)
        if callable(f):
            f()

    def _on_cut_shortcut(self):
        scene = self.dialogue_scene
        f = getattr(scene, "cut_selected", None)
        if callable(f):
            f()

    def _on_paste_shortcut(self):
        scene = self.dialogue_scene
        f = getattr(scene, "paste_clipboard", None)
        if callable(f):
            f()

    def zoom_to_fit(self):
        """Вписывает все узлы в viewport. Если узлов нет — reset zoom."""
        scene = self.dialogue_scene

        # Собираем boundingRect всех узлов (без соединений)
        node_items = list(scene.node_items.values())

        if not node_items:
            self.reset_zoom()
            return

        from PySide6.QtCore import QRectF

        bounding = QRectF()
        first = True

        for item in node_items:
            item_rect = item.sceneBoundingRect()
            if first:
                bounding = item_rect
                first = False
            else:
                bounding = bounding.united(item_rect)

        # Отступ 80px
        bounding = bounding.adjusted(-80, -80, 80, 80)

        self.fitInView(
            bounding,
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        # Обновляем zoom_factor по текущему transform
        try:
            m = self.transform()
            self.zoom_factor = float(m.m11())
        except Exception:
            pass

    # =========================================================
    # ПОИСК (Ctrl+F)
    # =========================================================

    def find_node_dialog(self):
        """Открывает диалог поиска, центрирует view на первом совпадении."""
        scene = self.dialogue_scene

        if scene.dialogue is None:
            return

        query, ok = QInputDialog.getText(
            self,
            "Найти узел",
            "Что искать? (текст реплики, speaker, вопрос, вариант)",
        )

        if not ok:
            return

        query = query.strip()
        if not query:
            return

        matches = scene.find_nodes(query)

        if not matches:
            QMessageBox.information(
                self,
                "Поиск",
                f"Ничего не найдено по запросу «{query}».",
            )
            return

        # Выделяем и центрируем на первом совпадении
        first_id = matches[0]
        first_item = scene.node_items.get(first_id)

        if first_item is not None:
            scene.clearSelection()
            first_item.setSelected(True)
            self.centerOn(first_item)

        if len(matches) > 1:
            QMessageBox.information(
                self,
                "Поиск",
                f"Найдено: {len(matches)}. Показан первый.",
            )

    # =========================================================
    # ZOOM
    # =========================================================

    def wheelEvent(self, event):
        """Zoom относительно курсора."""
        delta = event.angleDelta().y()

        if delta == 0:
            event.accept()
            return

        # Шаг в процентах
        step = self.ZOOM_STEP if delta > 0 else -self.ZOOM_STEP

        self._zoom_by(step, event.position().toPoint())
        event.accept()

    def _zoom_by(self, step_percent, viewport_pos):
        """Изменяет зум на step_percent относительно позиции."""
        current = int(self.zoom_factor * 100)
        target = current + step_percent
        target = max(self.MIN_ZOOM, min(self.MAX_ZOOM, target))

        if target == current:
            return

        new_factor = target / 100.0

        # Точка сцены под курсором до zoom
        scene_pos_before = self.mapToScene(viewport_pos)

        # Применяем zoom
        self.scale(
            new_factor / self.zoom_factor,
            new_factor / self.zoom_factor,
        )

        self.zoom_factor = new_factor

        # Точка сцены под курсором после zoom
        scene_pos_after = self.mapToScene(viewport_pos)

        # Сдвигаем view, чтобы под курсором была та же точка
        delta = scene_pos_after - scene_pos_before
        self.translate(delta.x(), delta.y())

    def zoom_in(self):
        center = self.viewport().rect().center()
        self._zoom_by(self.ZOOM_STEP * 2, center)

    def zoom_out(self):
        center = self.viewport().rect().center()
        self._zoom_by(-self.ZOOM_STEP * 2, center)

    def reset_zoom(self):
        """Сброс зума в 100%."""
        self.resetTransform()
        self.zoom_factor = 1.0

    # =========================================================
    # PAN — MIDDLE MOUSE
    # =========================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()

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
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # =========================================================
    # КЛАВИАТУРА
    # =========================================================

    def keyPressEvent(self, event):
        """Delete — удаляет выделенные узлы и связи."""
        if event.key() == Qt.Key.Key_Delete:
            scene = self.dialogue_scene
            delete = getattr(scene, "delete_selected", None)
            if callable(delete):
                delete()
            event.accept()
            return

        super().keyPressEvent(event)

    # =========================================================
    # УДОБНЫЕ ОБЁРТКИ
    # =========================================================

    def rebuild_from_model(self, dialogue):
        """Пересобирает сцену из модели."""
        self.dialogue_scene.rebuild_from_model(dialogue)

    def get_dialogue(self):
        return self.dialogue_scene.dialogue

    def sync_positions_to_model(self):
        self.dialogue_scene.sync_positions_to_model()
