"""Chart generation utilities for burn-up chart system."""

import datetime as dt
from datetime import datetime
from typing import Dict, List

import plotly.graph_objects as go


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
    def calculate_smart_annotation_positions(
        task_annotations: List[Dict],
    ) -> List[Dict]:
        """Calculate smart annotation positions with collision avoidance.

        Args:
            task_annotations: List of task annotation dictionaries

        Returns:
            List of positioned annotation dictionaries
        """
        if not task_annotations:
            return []

        print(f"🎯 Smart positioning for {len(task_annotations)} annotations...")

        # Step 1: Group annotations by date proximity (within 5 days)
        groups: List[List[Dict]] = []
        sorted_tasks = sorted(task_annotations, key=lambda x: x["end_date"])

        for task in sorted_tasks:
            # Find if there's a nearby group (±5 days)
            found_group = False
            for group in groups:
                if any(
                    abs((task["end_date"] - existing["end_date"]).days) <= 5
                    for existing in group
                ):
                    group.append(task)
                    found_group = True
                    break

            if not found_group:
                groups.append([task])

        print(f"  Grouped into {len(groups)} date groups")

        # Step 2: Assign base positions for each group
        base_positions = []

        for i, group in enumerate(groups):
            # Determine vertical distribution range based on group size
            group_size = len(group)
            if group_size == 1:
                base_heights = [80]
            elif group_size == 2:
                base_heights = [90, 70]
            elif group_size == 3:
                base_heights = [95, 80, 65]
            elif group_size == 4:
                base_heights = [95, 83, 71, 59]
            else:  # 5+ annotations
                # Dynamically generate heights
                step = 80 / group_size
                base_heights = [int(95 - i * step) for i in range(group_size)]
                # Ensure not below 15
                base_heights = [max(h, 15) for h in base_heights]

            # Horizontal offset range based on group size
            h_offsets: List[float]
            if group_size == 1:
                h_offsets = [0]
            elif group_size == 2:
                h_offsets = [-1, 1]
            elif group_size == 3:
                h_offsets = [-2, 0, 2]
            elif group_size == 4:
                h_offsets = [-2, -0.7, 0.7, 2]
            else:
                # Distribute evenly within ±3 days
                span = 6  # ±3 days
                h_offsets = [
                    span * (i / (group_size - 1)) - span / 2 for i in range(group_size)
                ]

            # Assign positions to each task in the group
            for j, task in enumerate(group):
                base_positions.append(
                    {
                        "task": task,
                        "y": base_heights[j],
                        "x_offset": h_offsets[j],  # Offset in days
                        "end_date": task["end_date"],
                        "group_id": i,
                    }
                )

        print("  Initial position assignment completed")

        # Step 3: Collision detection and adjustment
        def check_collision(pos1: Dict, pos2: Dict) -> bool:
            """Check if two positions collide."""
            # Horizontal distance (considering offset)
            h_dist = abs(
                (pos1["end_date"] - pos2["end_date"]).days
                + pos1["x_offset"]
                - pos2["x_offset"]
            )

            # Vertical distance
            v_dist = abs(pos1["y"] - pos2["y"])

            # Collision condition: within 3 days horizontally and 30 pixels vertically
            return bool(h_dist < 3 and v_dist < 30)

        def adjust_position(pos: Dict, existing_positions: List[Dict]) -> bool:
            """Adjust position to avoid collisions."""
            original_y = pos["y"]

            # Try different adjustment strategies
            adjustments = [
                0,
                15,
                -15,
                30,
                -30,
                45,
                -45,
            ]  # Original, then incremental adjustments

            for adj in adjustments:
                test_y = original_y + adj

                # Ensure within reasonable range
                if test_y < 10 or test_y > 95:
                    continue

                # Test if this position collides with existing positions
                test_pos = pos.copy()
                test_pos["y"] = test_y

                has_collision = any(
                    check_collision(test_pos, existing)
                    for existing in existing_positions
                )

                if not has_collision:
                    pos["y"] = test_y
                    return True

            # If all adjustments fail, find an empty area
            for y in range(95, 10, -5):
                test_pos = pos.copy()
                test_pos["y"] = y

                has_collision = any(
                    check_collision(test_pos, existing)
                    for existing in existing_positions
                )

                if not has_collision:
                    pos["y"] = y
                    return True

            return False

        # Step 4: Process positions one by one, resolving collisions
        final_positions = []

        for i, pos in enumerate(base_positions):
            print(f"  Processing annotation {i+1}: {pos['task']['task_name'][:25]}...")

            # Check for collisions with already placed annotations
            collision_count = sum(
                1 for existing in final_positions if check_collision(pos, existing)
            )

            if collision_count > 0:
                print(f"    Found {collision_count} collisions, adjusting...")
                success = adjust_position(pos, final_positions)
                if success:
                    print(f"    ✓ Adjusted to Y={pos['y']:.0f}")
                else:
                    print(
                        f"    ⚠ Unable to avoid all collisions, using Y={pos['y']:.0f}"
                    )
            else:
                print(f"    ✓ No collisions, position Y={pos['y']:.0f}")

            final_positions.append(pos)

        print(f"✅ Smart positioning completed: {len(final_positions)} annotations")

        # Step 5: Statistics
        groups_info = {}
        for pos in final_positions:
            gid = pos["group_id"]
            if gid not in groups_info:
                groups_info[gid] = []
            groups_info[gid].append(pos["y"])

        for gid, heights in groups_info.items():
            print(
                f"  Group {gid+1}: {len(heights)} annotations, "
                f"height range {min(heights):.0f}-{max(heights):.0f}"
            )

        return final_positions

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
                line=dict(color="lightblue", width=2),
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
                    line=dict(color="orange", width=3),
                    marker=dict(size=6),
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
            line=dict(color="red", width=3, dash="dash"),
        )

        fig.add_annotation(
            x=today_datetime,
            y=92,
            text="TODAY",
            showarrow=True,
            arrowhead=4,
            arrowcolor="red",
            font=dict(color="red", size=16),
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
                line=dict(color="purple", width=1, dash="dot"),
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
                font=dict(color="purple", size=9),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="purple",
                borderwidth=1,
                borderpad=4,
                align="center",
            )

        # Chart settings
        fig.update_layout(
            title=dict(
                text=f"Project status: {project_name}",
                font=dict(size=18),
            ),
            xaxis_title="Date",
            yaxis_title="Progress (%)",
            hovermode="x unified",
            template="plotly_white",
            height=700,
            showlegend=True,
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor="lightgray", type="date"),
            yaxis=dict(
                range=[0, 100], showgrid=True, gridwidth=1, gridcolor="lightgray"
            ),
        )

        return fig
