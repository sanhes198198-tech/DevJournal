from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
)


class SettingsDialog(QDialog):

    def __init__(self, canvas, parent=None):
        super().__init__(parent)

        self.canvas = canvas

        self.setWindowTitle(
            "Настройки рабочего пространства"
        )

        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(18)

        title = QLabel(
            "Настройки рабочего пространства"
        )

        title.setObjectName(
            "settingsTitle"
        )

        layout.addWidget(title)

        grid_label = QLabel("Фон холста")
        grid_combo = QComboBox()

        grid_combo.addItem("Точки", "dots")
        grid_combo.addItem("Сетка", "grid")
        grid_combo.addItem("Без сетки", "none")

        current_index = grid_combo.findData(
            self.canvas.grid_mode
        )

        if current_index >= 0:
            grid_combo.setCurrentIndex(
                current_index
            )

        layout.addWidget(grid_label)
        layout.addWidget(grid_combo)

        zoom_label = QLabel("Масштаб")
        zoom_spin = QSpinBox()

        zoom_spin.setRange(25, 200)
        zoom_spin.setSingleStep(25)

        zoom_spin.setValue(
            int(
                self.canvas.zoom_factor * 100
            )
        )

        layout.addWidget(zoom_label)
        layout.addWidget(zoom_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

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