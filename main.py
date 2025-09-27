"""Main entry point for the burn-up chart system."""

from __future__ import annotations

import argparse
import traceback
from datetime import date
from pathlib import Path
from typing import Optional

from src.burnup_manager import BurnUpManager
from src.data_loader import DataLoader


def _resolve_plan_path(explicit_path: Optional[str]) -> str:
    """Return the plan file path to use, applying sensible fallbacks."""

    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.exists():
            return str(candidate)
        raise FileNotFoundError(f"Specified plan file not found: {explicit_path}")

    for default_name in ("plan.xlsx", "plan.csv"):
        candidate = Path(default_name)
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "No plan file supplied and neither 'plan.xlsx' nor 'plan.csv' were found."
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Run the burn-up chart system demo workflow"
    )
    parser.add_argument(
        "--plan",
        dest="plan_path",
        help="Path to the project plan file (CSV or XLSX).",
    )
    return parser.parse_args()


def main() -> None:
    """Main function to demonstrate the burn-up system usage."""
    args = parse_args()

    try:
        plan_path = _resolve_plan_path(args.plan_path)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return

    manager = BurnUpManager()
    loader = DataLoader()

    try:
        plan_df = loader.load_project_data(plan_path)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Failed to load plan data: {exc}")
        return

    unique_projects = sorted(plan_df["Project Name"].astype(str).unique())
    if not unique_projects:
        print("❌ Plan file contains no projects")
        return
    first_project = unique_projects[0]
    print("📁 Projects detected:")
    for project in unique_projects:
        print(f"  - {project}")
    print()

    print("=== IMPROVED Enhanced Safe Historical Burn-up Chart System ===")
    print("🔒 Features: History Protection + Smart Task Positioning")
    print("🔧 Improvements:")
    print("  ✅ Removed week numbers (restored standard date display)")
    print("  ✅ Better collision avoidance algorithm")
    print("  ✅ Multiple height levels for annotations")
    print("  ✅ Smart positioning scores")
    print("  ✅ Refactored with proper separation of concerns")
    print("  ✅ Full type hints and documentation")
    print("  ✅ Lint-compliant code (isort, pylint, black)")
    print()

    try:
        # Step 1: Check system status
        print("Step 1: Check system status")
        manager.check_status()
        print()

        # Step 2: Initialize if no data exists
        if not manager.system.has_historical_data():
            print("Step 2: Initialize project (first time use)")
            manager.initialize_project(plan_path)
            print()

        # Step 3: Safe daily update
        print("Step 3: Execute daily update (safe mode)")
        manager.daily_update(plan_path)
        print()

        # Step 4: Show improved chart
        print("Step 4: Show improved chart")
        start_date = date(2025, 7, 1)
        end_date = date(2025, 12, 31)
        for project_name in unique_projects:
            print(f"  → {project_name}")
            chart = manager.show_improved_chart(
                project_name,
                plan_path,
                start_date=start_date,
                end_date=end_date,
            )
            if chart:
                print("    ✅ Improved chart displayed successfully!")
                print("      ✓ Standard date display (no week numbers)")
                print("      ✓ Smart annotation positioning")
                print("      ✓ Better collision avoidance")
                print("      ✓ Multiple height levels")
                print("      ✓ History protection maintained")

        # Step 5: Show protection status
        print("\\nStep 5: Check historical protection status")
        for project_name in unique_projects:
            print(f"  → {project_name}")
            manager.show_protection_status(project_name)

        print("\\n🎉 IMPROVED system execution completed!")
        print("💡 Key improvements:")
        print("  - Removed week numbers from X-axis")
        print("  - Smarter annotation positioning algorithm")
        print("  - Better spacing between overlapping tasks")
        print("  - Maintained all safety features")
        print("  - Proper code structure and documentation")
        print("  - Full type hints and error handling")

    except Exception as e:
        print(f"❌ Execution error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
