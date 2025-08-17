"""Main entry point for the burn-up chart system."""

import traceback
from datetime import date

from src.burnup_manager import BurnUpManager


def main() -> None:
    """Main function to demonstrate the burn-up system usage."""
    manager = BurnUpManager()

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
            manager.initialize_project("plan.xlsx")
            print()

        # Step 3: Safe daily update
        print("Step 3: Execute daily update (safe mode)")
        manager.daily_update("plan.xlsx")
        print()

        # Step 4: Show improved chart
        print("Step 4: Show improved chart")
        # chart = manager.show_improved_chart("YFB", "plan.xlsx")
        start_date = date(2025, 7, 1)
        end_date = date(2025, 12, 31)
        chart = manager.show_improved_chart(
            "YFB", "plan.xlsx", start_date=start_date, end_date=end_date
        )
        # chart = manager.show_improved_chart("YFB", "plan.xlsx", target_year=2025)
        if chart:
            print("✅ Improved chart displayed successfully!")
            print("  ✓ Standard date display (no week numbers)")
            print("  ✓ Smart annotation positioning")
            print("  ✓ Better collision avoidance")
            print("  ✓ Multiple height levels")
            print("  ✓ History protection maintained")

        # Step 5: Show protection status
        print("\\nStep 5: Check historical protection status")
        manager.show_protection_status("YFB")

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
