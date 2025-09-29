"""Tests for the check_quality utility script."""

from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from src import check_quality


class CheckQualityTests(TestCase):
    """Ensure code-quality helper behaves as expected."""

    def test_run_command_success(self) -> None:
        """Successful subprocess runs should return True."""

        completed = SimpleNamespace(stdout="ok")
        with patch("subprocess.run", return_value=completed):
            self.assertTrue(check_quality.run_command(["echo"], "echo"))

    def test_run_command_failure(self) -> None:
        """Failed subprocess execution should be reported as False."""

        with patch(
            "subprocess.run",
            side_effect=check_quality.subprocess.CalledProcessError(
                1, "cmd", "bad", "worse"
            ),
        ):
            self.assertFalse(check_quality.run_command(["false"], "failure"))

    def test_main_handles_failures(self) -> None:
        """Main should aggregate command results and return appropriate codes."""

        with patch.object(Path, "glob", return_value=[Path("foo.py")]), patch.object(
            check_quality, "run_command", side_effect=[True, False, False, True]
        ):
            exit_code = check_quality.main()

        self.assertEqual(exit_code, 1)

    def test_main_all_pass(self) -> None:
        """Successful execution of all checks should return zero."""

        with patch.object(Path, "glob", return_value=[Path("foo.py")]), patch.object(
            check_quality, "run_command", return_value=True
        ):
            exit_code = check_quality.main()

        self.assertEqual(exit_code, 0)
