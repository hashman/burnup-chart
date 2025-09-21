#!/usr/bin/env python3
"""
Script to run code quality checks on the burn-up chart system.

This script runs isort, black, pylint, and mypy to ensure code quality.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n🔧 Running {description}...")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"✅ {description} passed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main() -> int:
    """Run all code quality checks."""
    print("🚀 Running code quality checks for burn-up chart system")

    # Get all Python files
    python_files = list(Path(".").glob("*.py"))
    python_file_names = [str(f) for f in python_files]

    print(f"📁 Found {len(python_files)} Python files: {', '.join(python_file_names)}")

    checks = [
        (
            ["isort", "--check-only", "--diff"] + python_file_names,
            "isort (import sorting)",
        ),
        (["black", "--check", "--diff"] + python_file_names, "black (code formatting)"),
        (["pylint"] + python_file_names, "pylint (code linting)"),
        (["mypy"] + python_file_names, "mypy (type checking)"),
    ]

    failed_checks = []

    for command, description in checks:
        if not run_command(command, description):
            failed_checks.append(description)

    print("\n📊 Summary:")
    if failed_checks:
        print(f"❌ {len(failed_checks)} checks failed:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\n💡 To fix issues automatically, run:")
        print("  isort .")
        print("  black .")
        return 1

    print("✅ All code quality checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
