"""
MountPointDialog - создание / редактирование одной MountPoint.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
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
        asset=None,
        parent=None,
    ):
        super().__init__(parent)

        self.result_mountpoint: MountPoint | None = None

        self._original = mountpoint
        self._is_edit = mountpoint is not None
        self._asset = asset

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
        self._form = form  # Step 5: для скрытия полей в group_bound

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

        # Step 4: привязка к семантической группе (границы распределения)
        self._group_combo = QComboBox()
        self._group_combo.addItem("— не привязано —", "")
        _asset = getattr(self, "_asset", None)
        if _asset is not None:
            groups = getattr(_asset, "semantic_groups", None) or {}
            for gid, g in sorted(
                groups.items(),
                key=lambda kv: (getattr(kv[1], "name", "") or "").lower(),
            ):
                gname = getattr(g, "name", "") or gid
                glabel = getattr(g, "label", "") or gname
                self._group_combo.addItem(
                    f"{glabel}  ({gname})", gid,
                )
        self._group_combo.currentIndexChanged.connect(
            self._on_group_changed
        )
        form.addRow("Группа:", self._group_combo)

        layout.addLayout(form)

        dist_title = QLabel("Размножение")
        dist_title.setStyleSheet(
            "font-weight: 600; font-size: 12px; padding-top: 8px;"
        )
        layout.addWidget(dist_title)

        dist_form = QFormLayout()
        dist_form.setSpacing(8)
        self._dist_form = dist_form  # Step 5

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

        self._margin_x_spin = QDoubleSpinBox()
        self._margin_x_spin.setRange(0.0, 100000.0)
        self._margin_x_spin.setDecimals(3)
        self._margin_x_spin.setSuffix(" м")
        dist_form.addRow("Отступ по X:", self._margin_x_spin)

        self._margin_y_spin = QDoubleSpinBox()
        self._margin_y_spin.setRange(0.0, 100000.0)
        self._margin_y_spin.setDecimals(3)
        self._margin_y_spin.setSuffix(" м")
        dist_form.addRow("Отступ по Y:", self._margin_y_spin)

        self._adaptive_x_check = QCheckBox("Адаптивно по X (count от размера)")
        self._adaptive_x_check.toggled.connect(
            self._on_adaptive_x_toggled
        )
        dist_form.addRow("", self._adaptive_x_check)

        self._adaptive_y_check = QCheckBox("Адаптивно по Y (count от размера)")
        self._adaptive_y_check.toggled.connect(
            self._on_adaptive_y_toggled
        )
        dist_form.addRow("", self._adaptive_y_check)

        # Step 5: понятные имена
        _lbl_x = dist_form.labelForField(self._spacing_x_spin)
        if _lbl_x is not None:
            _lbl_x.setText("Расстояние между точками по X:")
        _lbl_y = dist_form.labelForField(self._spacing_y_spin)
        if _lbl_y is not None:
            _lbl_y.setText("Расстояние между точками по Y:")
        _lbl_mx = dist_form.labelForField(self._margin_x_spin)
        if _lbl_mx is not None:
            _lbl_mx.setText("Отступ от края группы по X:")
        _lbl_my = dist_form.labelForField(self._margin_y_spin)
        if _lbl_my is not None:
            _lbl_my.setText("Отступ от края группы по Y:")

        self._symmetric_x_check = QCheckBox("Симметрично по X (в обе стороны)")
        dist_form.addRow("", self._symmetric_x_check)

        self._symmetric_y_check = QCheckBox("Симметрично по Y (в обе стороны)")
        dist_form.addRow("", self._symmetric_y_check)

        layout.addLayout(dist_form)

        hint = QLabel(
            "Шаг = 0 при count > 1 → auto-fill: точки "
            "разложатся равномерно от края до края стены. "
            "Шаг > 0 → фиксированный шаг в метрах."
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

    def _on_group_changed(self, idx: int) -> None:
        """Step 5: в group_bound режиме скрываем ненужные поля.

        Остаются: Роль, X/Y, Группа, Шаг X/Y, Отступ X/Y, Симметрично X/Y.
        """
        group_id = self._group_combo.currentData() or ""
        is_group = bool(group_id)

        # Скрываем в верхней форме
        for w in (
            self._anchor_combo,
            self._anchor_x_spin,
            self._anchor_y_spin,
        ):
            try:
                self._form.setRowVisible(w, not is_group)
            except Exception:
                w.setVisible(not is_group)

        # Скрываем в форме размножения
        for w in (
            self._count_x_spin,
            self._count_y_spin,
            self._adaptive_x_check,
            self._adaptive_y_check,
        ):
            try:
                self._dist_form.setRowVisible(w, not is_group)
            except Exception:
                w.setVisible(not is_group)

    def _on_adaptive_x_toggled(self, checked: bool) -> None:
        """B3: при adaptive_x — count_x вычисляется, поле серое."""
        self._count_x_spin.setEnabled(not checked)

    def _on_adaptive_y_toggled(self, checked: bool) -> None:
        self._count_y_spin.setEnabled(not checked)

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
        self._margin_x_spin.setValue(
            float(getattr(d, "margin_x", 0.0))
        )
        self._margin_y_spin.setValue(
            float(getattr(d, "margin_y", 0.0))
        )
        self._adaptive_x_check.setChecked(
            bool(getattr(d, "adaptive_x", False))
        )
        self._adaptive_y_check.setChecked(
            bool(getattr(d, "adaptive_y", False))
        )
        self._on_adaptive_x_toggled(
            self._adaptive_x_check.isChecked()
        )
        self._on_adaptive_y_toggled(
            self._adaptive_y_check.isChecked()
        )

        # Step 4: group_bound
        gid = getattr(mp, "semantic_group_id", None) or ""
        gi = self._group_combo.findData(gid)
        if gi >= 0:
            self._group_combo.setCurrentIndex(gi)
        else:
            self._group_combo.setCurrentIndex(0)

        # Step 4: symmetric
        self._symmetric_x_check.setChecked(
            bool(getattr(d, "symmetric_x", False))
        )
        self._symmetric_y_check.setChecked(
            bool(getattr(d, "symmetric_y", False))
        )

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
        self._on_group_changed(0)

    def _on_accept(self) -> None:
        role_str = self._role_combo.currentData() or ""
        role = parse_role(role_str) if role_str else None

        cx = self._count_x_spin.value()
        cy = self._count_y_spin.value()
        sx = self._spacing_x_spin.value()
        sy = self._spacing_y_spin.value()

        # B2: spacing=0 при count>1 — это auto-fill (равномерно от края
        # до края bbox). Валидация не нужна.

        dist = Distribution(
            count_x=cx,
            count_y=cy,
            spacing_x=sx,
            spacing_y=sy,
            margin_x=self._margin_x_spin.value(),
            margin_y=self._margin_y_spin.value(),
            adaptive_x=self._adaptive_x_check.isChecked(),
            adaptive_y=self._adaptive_y_check.isChecked(),
            symmetric_x=self._symmetric_x_check.isChecked(),
            symmetric_y=self._symmetric_y_check.isChecked(),
        )
        group_id = self._group_combo.currentData() or None

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
            self._original.semantic_group_id = group_id
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
                semantic_group_id=group_id,
            )

        self.accept()
