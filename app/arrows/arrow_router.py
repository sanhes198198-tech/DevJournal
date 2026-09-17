import math

from PySide6.QtCore import QPointF, QRectF


class ArrowRouter:

    GRID_SIZE = 20.0
    OBSTACLE_MARGIN = 20.0

    TURN_COST = 8.0
    STEP_COST = 1.0

    MAX_SEARCH_NODES = 15000

    DIRECTIONS = (
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
    )

    @classmethod
    def find_path(
        cls,
        start,
        end,
        obstacles=None,
    ):
        """
        Строит ортогональный маршрут между двумя точками.

        Возвращает список QPointF.
        """

        if obstacles is None:
            obstacles = []

        start = QPointF(start)
        end = QPointF(end)

        if cls._points_are_close(start, end):
            return [
                start,
                end,
            ]

        prepared_obstacles = cls._prepare_obstacles(
            obstacles
        )

        bounds = cls._calculate_bounds(
            start,
            end,
            prepared_obstacles,
        )

        start_cell = cls._point_to_cell(
            start,
            bounds,
        )

        end_cell = cls._point_to_cell(
            end,
            bounds,
        )

        blocked = cls._build_blocked_cells(
            prepared_obstacles,
            bounds,
        )

        blocked.discard(
            start_cell
        )

        blocked.discard(
            end_cell
        )

        path_cells = cls._a_star(
            start_cell,
            end_cell,
            blocked,
        )

        if not path_cells:
            return [
                start,
                end,
            ]

        points = []

        for cell in path_cells:
            points.append(
                cls._cell_to_point(
                    cell,
                    bounds,
                )
            )

        points[0] = start
        points[-1] = end

        points = cls._simplify_path(
            points
        )

        return points

    @classmethod
    def _prepare_obstacles(
        cls,
        obstacles,
    ):
        result = []

        for obstacle in obstacles:

            if obstacle is None:
                continue

            try:
                rect = QRectF(
                    obstacle
                )
            except Exception:
                continue

            if not rect.isValid():
                continue

            rect = rect.normalized()

            rect.adjust(
                -cls.OBSTACLE_MARGIN,
                -cls.OBSTACLE_MARGIN,
                cls.OBSTACLE_MARGIN,
                cls.OBSTACLE_MARGIN,
            )

            result.append(
                rect
            )

        return result

    @classmethod
    def _calculate_bounds(
        cls,
        start,
        end,
        obstacles,
    ):
        left = min(
            start.x(),
            end.x(),
        )

        right = max(
            start.x(),
            end.x(),
        )

        top = min(
            start.y(),
            end.y(),
        )

        bottom = max(
            start.y(),
            end.y(),
        )

        for rect in obstacles:

            left = min(
                left,
                rect.left(),
            )

            right = max(
                right,
                rect.right(),
            )

            top = min(
                top,
                rect.top(),
            )

            bottom = max(
                bottom,
                rect.bottom(),
            )

        padding = (
            cls.GRID_SIZE
            *
            6.0
        )

        left -= padding
        right += padding
        top -= padding
        bottom += padding

        width = max(
            right - left,
            cls.GRID_SIZE * 4,
        )

        height = max(
            bottom - top,
            cls.GRID_SIZE * 4,
        )

        return QRectF(
            left,
            top,
            width,
            height,
        )

    @classmethod
    def _point_to_cell(
        cls,
        point,
        bounds,
    ):
        gx = math.floor(
            (
                point.x()
                -
                bounds.left()
            )
            /
            cls.GRID_SIZE
        )

        gy = math.floor(
            (
                point.y()
                -
                bounds.top()
            )
            /
            cls.GRID_SIZE
        )

        return (
            gx,
            gy,
        )

    @classmethod
    def _cell_to_point(
        cls,
        cell,
        bounds,
    ):
        gx, gy = cell

        return QPointF(
            bounds.left()
            +
            (
                gx
                +
                0.5
            )
            *
            cls.GRID_SIZE,

            bounds.top()
            +
            (
                gy
                +
                0.5
            )
            *
            cls.GRID_SIZE,
        )

    @classmethod
    def _build_blocked_cells(
        cls,
        obstacles,
        bounds,
    ):
        blocked = set()

        if not obstacles:
            return blocked

        max_x = int(
            math.ceil(
                bounds.width()
                /
                cls.GRID_SIZE
            )
        )

        max_y = int(
            math.ceil(
                bounds.height()
                /
                cls.GRID_SIZE
            )
        )

        for gy in range(
            0,
            max_y,
        ):

            for gx in range(
                0,
                max_x,
            ):

                cell = (
                    gx,
                    gy,
                )

                point = cls._cell_to_point(
                    cell,
                    bounds,
                )

                for obstacle in obstacles:

                    if obstacle.contains(
                        point
                    ):
                        blocked.add(
                            cell
                        )
                        break

        return blocked

    @classmethod
    def _a_star(
        cls,
        start,
        goal,
        blocked,
    ):
        import heapq

        open_heap = []

        counter = 0

        start_state = (
            start,
            None,
        )

        heapq.heappush(
            open_heap,
            (
                0.0,
                counter,
                start,
                None,
            ),
        )

        came_from = {}

        g_score = {
            start_state: 0.0
        }

        visited = 0

        while open_heap:

            (
                current_f,
                _,
                current,
                previous_direction,
            ) = heapq.heappop(
                open_heap
            )

            current_state = (
                current,
                previous_direction,
            )

            visited += 1

            if visited > cls.MAX_SEARCH_NODES:
                return None

            if current == goal:
                return cls._reconstruct_path(
                    came_from,
                    current_state,
                )

            for direction in cls.DIRECTIONS:

                dx, dy = direction

                neighbor = (
                    current[0] + dx,
                    current[1] + dy,
                )

                if neighbor in blocked:
                    continue

                movement_cost = (
                    cls.STEP_COST
                )

                if (
                    previous_direction is not None
                    and
                    previous_direction != direction
                ):
                    movement_cost += (
                        cls.TURN_COST
                    )

                tentative_g = (
                    g_score[current_state]
                    +
                    movement_cost
                )

                neighbor_state = (
                    neighbor,
                    direction,
                )

                old_g = g_score.get(
                    neighbor_state,
                    float("inf"),
                )

                if tentative_g >= old_g:
                    continue

                came_from[
                    neighbor_state
                ] = current_state

                g_score[
                    neighbor_state
                ] = tentative_g

                heuristic = (
                    abs(
                        neighbor[0]
                        -
                        goal[0]
                    )
                    +
                    abs(
                        neighbor[1]
                        -
                        goal[1]
                    )
                )

                counter += 1

                heapq.heappush(
                    open_heap,
                    (
                        tentative_g
                        +
                        heuristic,
                        counter,
                        neighbor,
                        direction,
                    )
                )

        return None

    @classmethod
    def _reconstruct_path(
        cls,
        came_from,
        state,
    ):
        path = [
            state[0]
        ]

        current = state

        while current in came_from:

            current = came_from[
                current
            ]

            path.append(
                current[0]
            )

        path.reverse()

        return path

    @classmethod
    def _simplify_path(
        cls,
        points,
    ):
        if len(points) <= 2:
            return points

        result = [
            points[0]
        ]

        previous_direction = None

        for index in range(
            1,
            len(points),
        ):

            previous = result[-1]
            current = points[index]

            direction = cls._direction(
                previous,
                current,
            )

            if previous_direction is None:

                result.append(
                    current
                )

            elif direction == previous_direction:

                result[-1] = current

            else:

                result.append(
                    current
                )

            previous_direction = direction

        if not cls._points_are_close(
            result[-1],
            points[-1],
        ):
            result.append(
                points[-1]
            )

        return cls._remove_duplicate_points(
            result
        )

    @staticmethod
    def _direction(
        a,
        b,
    ):
        dx = (
            b.x()
            -
            a.x()
        )

        dy = (
            b.y()
            -
            a.y()
        )

        if abs(dx) >= abs(dy):

            if dx >= 0:
                return "right"

            return "left"

        if dy >= 0:
            return "down"

        return "up"

    @staticmethod
    def _remove_duplicate_points(
        points,
    ):
        result = []

        for point in points:

            if not result:

                result.append(
                    point
                )

                continue

            previous = result[-1]

            if (
                abs(
                    point.x()
                    -
                    previous.x()
                ) < 0.01
                and
                abs(
                    point.y()
                    -
                    previous.y()
                ) < 0.01
            ):
                continue

            result.append(
                point
            )

        return result

    @staticmethod
    def _points_are_close(
        a,
        b,
        tolerance=0.01,
    ):
        return (
            abs(
                a.x()
                -
                b.x()
            )
            <= tolerance
            and
            abs(
                a.y()
                -
                b.y()
            )
            <= tolerance
        )