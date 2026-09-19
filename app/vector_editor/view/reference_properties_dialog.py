"""
ReferencePropertiesDialog — свойства картинки-подложки.

Возможности:
  - scale (pixels_per_meter)
  - opacity (0..1, слайдер 0..100%)
  - visible (чекбокс)
  - удалить подложку (с подтверждением → result_delete=True)

Не трогает модель до apply_to_model(). Если пользователь нажал
«Отмена» — модель не изменена.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)


class ReferencePropertiesDialog(QDialog):
    """Диалог свойств подложки."""

    def __init__(self, ref_model, parent=None):
        super().__init__(parent)

        self._ref = ref_model
        self.result_delete = False

        self.setWindowTitle("Свойства подложки")
        self.resize(420, 280)

        self._build_ui()
        self._load_from_model()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Подложка")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        # Масштаб
        self._ppm_spin = QDoubleSpinBox()
        self._ppm_spin.setRange(0.1, 10000.0)
        self._ppm_spin.setDecimals(2)
        self._ppm_spin.setSingleStep(1.0)
        self._ppm_spin.setSuffix(" px/м")
        form.addRow("Масштаб:", self._ppm_spin)

        # Прозрачность
        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.valueChanged.connect(
            self._on_opacity_changed
        )
        opacity_row.addWidget(self._opacity_slider, 1)

        self._opacity_label = QLabel("50%")
        self._opacity_label.setFixedWidth(40)
        self._opacity_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        opacity_row.addWidget(self._opacity_label)

        form.addRow("Прозрачность:", opacity_row)

        # Видимость
        self._visible_check = QCheckBox("Показывать")
        form.addRow("", self._visible_check)

        layout.addLayout(form)
        layout.addStretch()

        # Кнопка удаления (слева)
        del_btn = QPushButton("Удалить подложку")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background: #3A1F1F; color: #E5B5B5; "
            "border: 1px solid #5A2D2D; border-radius: 3px; "
            "padding: 6px 12px; font-size: 11px; }"
            "QPushButton:hover { background: #4A2525; }"
        )
        del_btn.clicked.connect(self._on_delete)

        # Кнопки диалога
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Сохранить"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Отмена"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        bottom = QHBoxLayout()
        bottom.addWidget(del_btn)
        bottom.addStretch()
        bottom.addWidget(buttons)

        layout.addLayout(bottom)

    # ------------------------------------------------------------

    def _load_from_model(self) -> None:
        self._ppm_spin.setValue(self._ref.pixels_per_meter)
        opacity_pct = int(round(self._ref.opacity * 100))
        self._opacity_slider.setValue(opacity_pct)
        self._opacity_label.setText(f"{opacity_pct}%")
        self._visible_check.setChecked(self._ref.visible)

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_label.setText(f"{value}%")

    def _on_delete(self) -> None:
        reply = QMessageBox.question(
            self,
            "Удалить подложку",
            "Удалить картинку-подложку?\n\n"
            "Само действие применится после «Сохранить» в "
            "главном окне.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.result_delete = True
        self.accept()

    # ------------------------------------------------------------

    def apply_to_model(self) -> None:
        """Записать значения полей обратно в ReferenceImage."""
        if self.result_delete:
            return
        self._ref.pixels_per_meter = self._ppm_spin.value()
        self._ref.opacity = self._opacity_slider.value() / 100.0
        self._ref.visible = self._visible_check.isChecked()
