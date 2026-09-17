from PySide6.QtCore import QObject, QTimer

from .arrow_router import ArrowRouter


class ArrowFollowManager(QObject):
    """
    Отдельный менеджер для обновления положения стрелок
    и расчёта маршрутов вокруг карточек.

    Логика вынесена из BaseCard и других карточек специально,
    чтобы не изменять существующие классы.
    """

    def __init__(self, scene, parent=None):
        super().__init__(parent)

        self.scene = scene

        self.router = ArrowRouter()

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update_arrows)

        self.timer.start()

    def update_arrows(self):
        if self.scene is None:
            return

        try:
            items = self.scene.items()
        except RuntimeError:
            return
        except Exception:
            return

        processed = set()

        for item in items:
            try:
                arrows = getattr(item, "arrows", None)

                if not arrows:
                    continue

                for arrow in list(arrows):
                    if arrow is None:
                        continue

                    arrow_id = id(arrow)

                    if arrow_id in processed:
                        continue

                    processed.add(arrow_id)

                    try:
                        self._update_arrow(arrow)
                    except RuntimeError:
                        continue
                    except Exception:
                        continue

            except RuntimeError:
                continue
            except Exception:
                continue

    def _update_arrow(self, arrow):
        """
        Обновляет существующую стрелку и рассчитывает
        новый безопасный маршрут между карточками.

        Сам ArrowItem здесь не изменяется.
        """

        source_item = getattr(
            arrow,
            "source_item",
            None,
        )

        target_item = getattr(
            arrow,
            "target_item",
            None,
        )

        if source_item is None or target_item is None:
            if hasattr(arrow, "update_position"):
                arrow.update_position()

            return

        try:
            route = self.router.route(
                source_item,
                target_item,
                obstacles=None,
            )
        except RuntimeError:
            return
        except Exception:
            route = None

        if route:
            try:
                arrow._calculated_route = route
            except RuntimeError:
                return
            except Exception:
                pass

        try:
            if hasattr(arrow, "update_position"):
                arrow.update_position()
        except RuntimeError:
            return
        except Exception:
            return

    def stop(self):
        if self.timer.isActive():
            self.timer.stop()

    def start(self):
        if not self.timer.isActive():
            self.timer.start()