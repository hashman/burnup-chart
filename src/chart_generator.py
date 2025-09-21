"""Chart generation utilities for burn-up chart system."""

import datetime as dt
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List

import plotly.graph_objects as go


@dataclass
class PositionedAnnotation:
    """Represent an annotation with computed screen coordinates."""

    task: Dict
    y: float
    x_offset: float
    end_date: date
    group_id: int

    def to_dict(self) -> Dict:
        """Return dictionary representation compatible with Plotly usage."""

        return {
            "task": self.task,
            "y": self.y,
            "x_offset": self.x_offset,
            "end_date": self.end_date,
            "group_id": self.group_id,
        }


class ChartGenerator:
    """Handle chart generation and annotation positioning."""

    @staticmethod
    def wrap_text(text: str, max_length: int = 20) -> str:
        """Wrap text for annotations with intelligent line breaks.

        Args:
            text: Text to wrap
            max_length: Maximum line length

        Returns:
            Wrapped text with line breaks
        """
        if len(text) <= max_length:
            return text

        # Try to break at spaces first
        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_length:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Word too long, force break
                    while len(word) > max_length:
                        lines.append(word[:max_length])
                        word = word[max_length:]
                    current_line = word

        if current_line:
            lines.append(current_line)

        return "<br>".join(lines)

    @staticmethod
    def _group_annotations(task_annotations: List[Dict]) -> List[List[Dict]]:
        """Group annotations by end date proximity."""

        groups: List[List[Dict]] = []
        sorted_tasks = sorted(task_annotations, key=lambda item: item["end_date"])
        for task in sorted_tasks:
            for group in groups:
                if any(
                    abs((task["end_date"] - existing["end_date"]).days) <= 5
                    for existing in group
                ):
                    group.append(task)
                    break
            else:
                groups.append([task])
        return groups

    @staticmethod
    def _base_heights(group_size: int) -> List[int]:
        """Return baseline heights for a group of annotations."""

        if group_size == 1:
            return [80]
        if group_size == 2:
            return [90, 70]
        if group_size == 3:
            return [95, 80, 65]
        if group_size == 4:
            return [95, 83, 71, 59]
        step = 80 / group_size
        heights = [int(95 - index * step) for index in range(group_size)]
        return [max(height, 15) for height in heights]

    @staticmethod
    def _horizontal_offsets(group_size: int) -> List[float]:
        """Return horizontal offsets used to stagger annotations."""

        if group_size == 1:
            return [0]
        if group_size == 2:
            return [-1, 1]
        if group_size == 3:
            return [-2, 0, 2]
        if group_size == 4:
            return [-2, -0.7, 0.7, 2]
        span = 6
        return [
            span * (index / (group_size - 1)) - span / 2 for index in range(group_size)
        ]

    @classmethod
    def _assign_base_positions(
        cls, groups: List[List[Dict]]
    ) -> List[PositionedAnnotation]:
        """Assign base positions for each annotation group."""

        positions: List[PositionedAnnotation] = []
        for group_id, group in enumerate(groups):
            heights = cls._base_heights(len(group))
            offsets = cls._horizontal_offsets(len(group))
            for index, task in enumerate(group):
                positions.append(
                    PositionedAnnotation(
                        task=task,
                        y=heights[index],
                        x_offset=offsets[index],
                        end_date=task["end_date"],
                        group_id=group_id,
                    )
                )
        print("  Initial position assignment completed")
        return positions

    @staticmethod
    def _check_collision(
        pos1: PositionedAnnotation, pos2: PositionedAnnotation
    ) -> bool:
        """Return True when two annotations overlap visually."""

        h_dist = abs(
            (pos1.end_date - pos2.end_date).days + pos1.x_offset - pos2.x_offset
        )
        v_dist = abs(pos1.y - pos2.y)
        return bool(h_dist < 3 and v_dist < 30)

    @classmethod
    def _adjust_position(
        cls,
        position: PositionedAnnotation,
        existing_positions: List[PositionedAnnotation],
    ) -> bool:
        """Adjust an annotation vertically to avoid collisions."""

        original_y = position.y
        adjustments = [0, 15, -15, 30, -30, 45, -45]
        for adjustment in adjustments:
            test_y = original_y + adjustment
            if not 10 <= test_y <= 95:
                continue
            previous_y = position.y
            position.y = test_y
            has_collision = any(
                cls._check_collision(position, existing)
                for existing in existing_positions
            )
            if not has_collision:
                return True
            position.y = previous_y

        for y_value in range(95, 10, -5):
            previous_y = position.y
            position.y = y_value
            has_collision = any(
                cls._check_collision(position, existing)
                for existing in existing_positions
            )
            if not has_collision:
                return True
            position.y = previous_y

        position.y = original_y
        return False

    @classmethod
    def _resolve_collisions(
        cls, base_positions: List[PositionedAnnotation]
    ) -> List[PositionedAnnotation]:
        """Resolve collisions by adjusting annotation heights."""

        final_positions: List[PositionedAnnotation] = []
        for index, position in enumerate(base_positions):
            print(
                f"  Processing annotation {index + 1}: "
                f"{position.task['task_name'][:25]}..."
            )
            collision_count = sum(
                1
                for existing in final_positions
                if cls._check_collision(position, existing)
            )
            if collision_count > 0:
                print(f"    Found {collision_count} collisions, adjusting...")
                if cls._adjust_position(position, final_positions):
                    print(f"    ✓ Adjusted to Y={position.y:.0f}")
                else:
                    print(
                        f"    ⚠ Unable to avoid all collisions, using Y={position.y:.0f}"
                    )
            else:
                print(f"    ✓ No collisions, position Y={position.y:.0f}")
            final_positions.append(position)

        print(f"✅ Smart positioning completed: {len(final_positions)} annotations")
        return final_positions

    @staticmethod
    def _log_group_statistics(
        final_positions: List[PositionedAnnotation],
    ) -> None:
        """Print summary statistics for annotation placement."""

        groups_info: Dict[int, List[float]] = {}
        for position in final_positions:
            groups_info.setdefault(position.group_id, []).append(position.y)
        for group_id, heights in groups_info.items():
            print(
                f"  Group {group_id + 1}: {len(heights)} annotations, "
                f"height range {min(heights):.0f}-{max(heights):.0f}"
            )

    @classmethod
    def calculate_smart_annotation_positions(
        cls,
        task_annotations: List[Dict],
    ) -> List[Dict]:
        """Calculate smart annotation positions with collision avoidance."""

        if not task_annotations:
            return []

        print(f"🎯 Smart positioning for {len(task_annotations)} annotations...")
        groups = cls._group_annotations(task_annotations)
        print(f"  Grouped into {len(groups)} date groups")
        base_positions = cls._assign_base_positions(groups)
        final_positions = cls._resolve_collisions(base_positions)
        cls._log_group_statistics(final_positions)
        return [position.to_dict() for position in final_positions]

    @classmethod
    def create_burnup_chart(
        cls,
        project_name: str,
        dates: List,
        plan_progress: List[float],
        actual_dates: List,
        actual_progress: List[float],
        task_annotations: List[Dict],
        today: datetime,
    ) -> go.Figure:
        """Create burn-up chart with smart annotation positioning.

        Args:
            project_name: Name of the project
            dates: List of dates for plan progress
            plan_progress: List of plan progress values
            actual_dates: List of dates for actual progress
            actual_progress: List of actual progress values
            task_annotations: List of task annotation dictionaries
            today: Today's date

        Returns:
            Plotly Figure object
        """
        print(
            f"📊 Generating improved burn-up chart (with horizontal offset): {project_name}"
        )

        # Get annotation positions using smart algorithm
        positioned_annotations = cls.calculate_smart_annotation_positions(
            task_annotations
        )

        # Create chart
        fig = go.Figure()

        # Add plan line
        fig.add_trace(
            go.Scatter(
                x=[datetime.combine(x, datetime.min.time()) for x in dates],
                y=plan_progress,
                mode="lines",
                name="Planned Progress",
                line={"color": "lightblue", "width": 2},
            )
        )

        # Add actual line
        if actual_dates:
            fig.add_trace(
                go.Scatter(
                    x=[datetime.combine(x, datetime.min.time()) for x in actual_dates],
                    y=actual_progress,
                    mode="lines+markers",
                    name="Actual Progress",
                    line={"color": "orange", "width": 3},
                    marker={"size": 6},
                )
            )

        # Add today marker
        today_datetime = datetime.combine(today.date(), datetime.min.time())
        fig.add_shape(
            type="line",
            x0=today_datetime,
            x1=today_datetime,
            y0=0,
            y1=100,
            line={"color": "red", "width": 3, "dash": "dash"},
        )

        fig.add_annotation(
            x=today_datetime,
            y=92,
            text="TODAY",
            showarrow=True,
            arrowhead=4,
            arrowcolor="red",
            font={"color": "red", "size": 16},
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="red",
            borderwidth=2,
            borderpad=10,
        )

        # Add task annotations with horizontal offset support
        print(
            f"Adding {len(positioned_annotations)} task annotations (with horizontal offset)..."
        )

        for pos in positioned_annotations:
            # Calculate actual display position (original date + offset)
            display_date = pos["end_date"] + dt.timedelta(days=pos["x_offset"])
            display_datetime = datetime.combine(display_date, datetime.min.time())

            # Vertical line (still at original date)
            original_datetime = datetime.combine(pos["end_date"], datetime.min.time())
            fig.add_shape(
                type="line",
                x0=original_datetime,
                x1=original_datetime,
                y0=0,
                y1=100,
                line={"color": "purple", "width": 1, "dash": "dot"},
            )

            # Annotation text (at offset position)
            wrapped_label = cls.wrap_text(pos["task"]["label"])
            fig.add_annotation(
                x=display_datetime,
                y=pos["y"],
                text=f"{wrapped_label}<br>Due: {pos['end_date'].strftime('%m/%d')}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="purple",
                arrowwidth=1,
                font={"color": "purple", "size": 9},
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="purple",
                borderwidth=1,
                borderpad=4,
                align="center",
            )

        # Chart settings
        fig.update_layout(
            title={
                "text": f"Project status: {project_name}",
                "font": {"size": 18},
            },
            xaxis_title="Date",
            yaxis_title="Progress (%)",
            hovermode="x unified",
            template="plotly_white",
            height=700,
            showlegend=True,
            xaxis={
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": "lightgray",
                "type": "date",
            },
            yaxis={
                "range": [0, 100],
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": "lightgray",
            },
        )

        return fig
