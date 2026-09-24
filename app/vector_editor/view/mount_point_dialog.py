"""
MountPointDialog - создание / редактирование одной MountPoint.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from ..model.mounting import (
    MountPoint, MountRole, Distribution, parse_role,
)


# Храним СТРОКИ, потому что PySide конвертирует StrEnum в str
# при QComboBox.addItem(label, data) — .currentData() вернёт строку.
ROLE_LABELS = [
    ("", "— без роли —"),
    ("window", "Окно"),
    ("door", "Дверь"),
    ("foundation", "Фундамент"),
    ("cornice", "Карниз"),
    ("decor", "Декор"),
]


class MountPointDialog(QDialog):
    """Диалог одной MountPoint."""

    def __init__(
        self,
        mountpoint: MountPoint | None = None,
        default_position: tuple[float, float] = (0.0, 0.0),
        parent=None,
    ):
        super().__init__(parent)

        self.result_mountpoint: MountPoint | None = None

        self._original = mountpoint
        self._is_edit = mountpoint is not None

        self.setWindowTitle(
            "Редактировать точку" if self._is_edit
            else "Новая точка крепления"
        )
        self.resize(440, 360)

        self._build_ui()

        if self._is_edit:
            self._load_from(mountpoint)
        else:
            self._x_spin.setValue(float(default_position[0]))
            self._y_spin.setValue(float(default_position[1]))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(
            "Редактировать точку крепления" if self._is_edit
            else "Новая точка крепления"
        )
        title.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self._role_combo = QComboBox()
        for role, label in ROLE_LABELS:
            self._role_combo.addItem(label, role)
        form.addRow("Роль:", self._role_combo)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(-100000.0, 100000.0)
        self._x_spin.setDecimals(3)
        self._x_spin.setSuffix(" м")
        form.addRow("X:", self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(-100000.0, 100000.0)
        self._y_spin.setDecimals(3)
        self._y_spin.setSuffix(" м")
        form.addRow("Y:", self._y_spin)

        # V22: режим привязки
        self._anchor_combo = QComboBox()
        self._anchor_combo.addItem("Абсолютный (не едет)", "absolute")
        self._anchor_combo.addItem("Относительный (% bbox)", "relative_xy")
        self._anchor_combo.currentIndexChanged.connect(
            self._on_anchor_mode_changed
        )
        form.addRow("Привязка:", self._anchor_combo)

        self._anchor_x_spin = QDoubleSpinBox()
        self._anchor_x_spin.setRange(0.0, 1.0)
        self._anchor_x_spin.setDecimals(3)
        self._anchor_x_spin.setSingleStep(0.05)
        form.addRow("Anchor X (0-1):", self._anchor_x_spin)

        self._anchor_y_spin = QDoubleSpinBox()
        self._anchor_y_spin.setRange(0.0, 1.0)
        self._anchor_y_spin.setDecimals(3)
        self._anchor_y_spin.setSingleStep(0.05)
        form.addRow("Anchor Y (0-1):", self._anchor_y_spin)

        layout.addLayout(form)

        dist_title = QLabel("Размножение")
        dist_title.setStyleSheet(
            "font-weight: 600; font-size: 12px; padding-top: 8px;"
        )
        layout.addWidget(dist_title)

        dist_form = QFormLayout()
        dist_form.setSpacing(8)

        self._count_x_spin = QSpinBox()
        self._count_x_spin.setRange(1, 500)
        dist_form.addRow("Количество по X:", self._count_x_spin)

        self._count_y_spin = QSpinBox()
        self._count_y_spin.setRange(1, 500)
        dist_form.addRow("Количество по Y:", self._count_y_spin)

        self._spacing_x_spin = QDoubleSpinBox()
        self._spacing_x_spin.setRange(0.0, 100000.0)
        self._spacing_x_spin.setDecimals(3)
        self._spacing_x_spin.setSuffix(" м")
        dist_form.addRow("Шаг по X:", self._spacing_x_spin)

        self._spacing_y_spin = QDoubleSpinBox()
        self._spacing_y_spin.setRange(0.0, 100000.0)
        self._spacing_y_spin.setDecimals(3)
        self._spacing_y_spin.setSuffix(" м")
        dist_form.addRow("Шаг по Y:", self._spacing_y_spin)

        layout.addLayout(dist_form)

        hint = QLabel(
            "position — первая точка. count_x=3 создаёт 3 точки: "
            "исходная + 2 копии с шагом spacing."
        )
        hint.setStyleSheet(
            "color: #858B93; font-size: 10px; padding-top: 4px;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText("Сохранить")
        buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_anchor_mode_changed(self, idx: int) -> None:
        mode = self._anchor_combo.currentData() or "absolute"
        enabled = (mode == "relative_xy")
        self._anchor_x_spin.setEnabled(enabled)
        self._anchor_y_spin.setEnabled(enabled)
        # В absolute — X/Y спинбоксы активны
        self._x_spin.setEnabled(not enabled)
        self._y_spin.setEnabled(not enabled)

    def _load_from(self, mp: MountPoint) -> None:
        # Приводим role к строке (может быть enum или str)
        role_str = ""
        if mp.role is not None:
            role_str = getattr(mp.role, "value", str(mp.role))
        idx = self._role_combo.findData(role_str)
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)
        else:
            self._role_combo.setCurrentIndex(0)

        self._x_spin.setValue(mp.position[0])
        self._y_spin.setValue(mp.position[1])

        d = mp.distribution
        self._count_x_spin.setValue(d.count_x)
        self._count_y_spin.setValue(d.count_y)
        self._spacing_x_spin.setValue(d.spacing_x)
        self._spacing_y_spin.setValue(d.spacing_y)

        # V22: anchor
        mode = getattr(mp, "anchor_mode", "absolute") or "absolute"
        mi = self._anchor_combo.findData(mode)
        if mi >= 0:
            self._anchor_combo.setCurrentIndex(mi)
        self._anchor_x_spin.setValue(
            float(getattr(mp, "anchor_x", 0.5))
        )
        self._anchor_y_spin.setValue(
            float(getattr(mp, "anchor_y", 0.5))
        )
        self._on_anchor_mode_changed(0)

    def _on_accept(self) -> None:
        role_str = self._role_combo.currentData() or ""
        role = parse_role(role_str) if role_str else None

        dist = Distribution(
            count_x=self._count_x_spin.value(),
            count_y=self._count_y_spin.value(),
            spacing_x=self._spacing_x_spin.value(),
            spacing_y=self._spacing_y_spin.value(),
        )

        anchor_mode = self._anchor_combo.currentData() or "absolute"
        anchor_x = self._anchor_x_spin.value()
        anchor_y = self._anchor_y_spin.value()

        if self._is_edit:
            self._original.role = role
            self._original.position = (
                self._x_spin.value(),
                self._y_spin.value(),
            )
            self._original.distribution = dist
            self._original.anchor_mode = anchor_mode
            self._original.anchor_x = anchor_x
            self._original.anchor_y = anchor_y
            self.result_mountpoint = self._original
        else:
            self.result_mountpoint = MountPoint(
                role=role,
                position=(
                    self._x_spin.value(),
                    self._y_spin.value(),
                ),
                distribution=dist,
                anchor_mode=anchor_mode,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
            )

        self.accept()
