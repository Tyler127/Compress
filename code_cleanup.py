#!/usr/bin/env python3
"""
Code cleanup script that runs all formatting checks and fixes from lint.yml.

This script will:
1. Format code with Black (or check formatting with --check flag)
2. Sort imports with isort (or check imports with --check flag)
3. Run flake8 for linting checks
4. Run pylint for additional linting
5. Run mypy for type checking

Usage:
    python code_cleanup.py         # Format and fix code
    python code_cleanup.py --check # Check only (like CI does)
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
    """
    Run a command and return the exit code, stdout, and stderr.

    Args:
        cmd: Command to run as a list of strings
        check: If True, raise exception on non-zero exit code

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"


def check_dependencies() -> bool:
    """Check if all required tools are installed."""
    print_header("Checking Dependencies")

    required_tools = ["black", "isort", "flake8", "pylint", "mypy"]
    missing_tools = []

    for tool in required_tools:
        returncode, _, _ = run_command([tool, "--version"])
        if returncode == 0:
            print_success(f"{tool} is installed")
        else:
            print_error(f"{tool} is not installed")
            missing_tools.append(tool)

    if missing_tools:
        print_error("\nMissing tools. Install them with:")
        print(f"  pip install {' '.join(missing_tools)}")
        return False

    return True


def format_with_black(check_only: bool = False) -> bool:
    """Format code with Black."""
    action = "Checking" if check_only else "Formatting"
    print_header(f"Running Black (Code Formatter) - {action}")

    cmd = ["black", "compressy", "tests"]
    if check_only:
        cmd.extend(["--check", "--diff"])

    returncode, stdout, stderr = run_command(cmd)

    if returncode == 0:
        msg = (
            "Black check passed"
            if check_only
            else "Black formatting completed"
        )
        print_success(msg)
        if stdout:
            print(stdout)
        return True
    else:
        msg = "Black check failed" if check_only else "Black formatting failed"
        print_error(msg)
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        return False


def sort_imports_with_isort(check_only: bool = False) -> bool:
    """Sort imports with isort."""
    action = "Checking" if check_only else "Sorting"
    print_header(f"Running isort (Import Sorter) - {action}")

    cmd = ["isort", "compressy", "tests"]
    if check_only:
        cmd.extend(["--check-only", "--diff"])

    returncode, stdout, stderr = run_command(cmd)

    if returncode == 0:
        msg = (
            "isort check passed"
            if check_only
            else "Import sorting completed"
        )
        print_success(msg)
        if stdout:
            print(stdout)
        return True
    else:
        msg = "isort check failed" if check_only else "Import sorting failed"
        print_error(msg)
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        return False


def lint_with_flake8() -> bool:
    """Run flake8 linting checks."""
    print_header("Running flake8 (Linter)")

    # First pass: critical errors
    print(f"{Colors.OKCYAN}Running critical error checks...{Colors.ENDC}")
    returncode1, stdout1, stderr1 = run_command(
        [
            "flake8",
            "compressy",
            "tests",
            "--count",
            "--select=E9,F63,F7,F82",
            "--show-source",
            "--statistics",
        ]
    )

    if stdout1:
        print(stdout1)
    if stderr1:
        print(stderr1)

    # Second pass: all checks with warnings
    print(f"\n{Colors.OKCYAN}Running full checks...{Colors.ENDC}")
    returncode2, stdout2, stderr2 = run_command(
        [
            "flake8",
            "compressy",
            "tests",
            "--count",
            "--exit-zero",
            "--max-complexity=10",
            "--max-line-length=120",
            "--statistics",
        ]
    )

    if stdout2:
        print(stdout2)
    if stderr2:
        print(stderr2)

    if returncode1 == 0:
        print_success("flake8 checks passed")
        return True
    else:
        print_warning("flake8 found issues (see output above)")
        return False


def lint_with_pylint() -> str:
    """Run pylint checks."""
    print_header("Running pylint (Linter)")

    returncode, stdout, stderr = run_command(
        [
            "pylint",
            "compressy",
            "--disable=all",
            "--enable=E,F,unused-import,undefined-variable",
            "--max-line-length=120",
        ]
    )

    if stdout:
        print(stdout)
    if stderr:
        print(stderr)

    # pylint returns non-zero for warnings, so we just show results
    # (non-blocking)
    print_success("pylint check completed (informational only)")
    return "completed"


def type_check_with_mypy() -> str:
    """Run mypy type checking."""
    print_header("Running mypy (Type Checker)")

    returncode, stdout, stderr = run_command(
        [
            "mypy",
            "compressy",
            "--ignore-missing-imports",
            "--no-strict-optional",
        ]
    )

    if stdout:
        print(stdout)
    if stderr:
        print(stderr)

    # mypy returns non-zero for type errors, so we just show results
    # (non-blocking)
    print_success("mypy check completed (informational only)")
    return "completed"


def main() -> int:
    """Main function to run all checks."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run code formatting and quality checks"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode only (like CI) - don't modify files",
    )
    args = parser.parse_args()

    mode = "CHECK MODE (like CI)" if args.check else "FIX MODE"
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           Code Cleanup and Quality Checks                  ║")
    print(f"║                    {mode:^30}                  ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.ENDC)

    # Check if we're in the right directory
    if not Path("compressy").exists():
        print_error("Error: 'compressy' directory not found!")
        print("Please run this script from the project root directory.")
        return 1

    # Check dependencies
    if not check_dependencies():
        return 1

    # Track results
    results = {}

    # Run all checks and fixes
    results["Black formatting"] = format_with_black(check_only=args.check)
    results["isort import sorting"] = sort_imports_with_isort(
        check_only=args.check
    )
    results["flake8 linting"] = lint_with_flake8()
    results["pylint linting"] = lint_with_pylint()
    results["mypy type checking"] = type_check_with_mypy()

    # Print summary
    print_header("Summary")

    all_passed = True
    for check, status in results.items():
        if status == "completed":
            info_msg = f"ℹ {check}: COMPLETED (informational)"
            print(f"{Colors.OKCYAN}{info_msg}{Colors.ENDC}")
        elif status:
            print_success(f"{check}: PASSED")
        else:
            print_error(f"{check}: FAILED")
            all_passed = False

    print(f"\n{Colors.BOLD}", end="")
    if all_passed:
        success_msg = "All checks completed successfully!"
        print(f"{Colors.OKGREEN}{success_msg}{Colors.ENDC}")
        return 0
    else:
        warning_msg = "Some checks found issues. Please review the output."
        print(f"{Colors.WARNING}{warning_msg}{Colors.ENDC}")
        # In check mode, return non-zero exit code (like CI does)
        # In fix mode, return 0 since this is a cleanup script
        return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
