"""Compatibility wrapper for the source eval runner used by legacy tests."""

from doge.eval.runner import main, run, run_suite

__all__ = ["main", "run", "run_suite"]


if __name__ == "__main__":
    main()
