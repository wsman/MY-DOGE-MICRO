"""Compatibility wrapper for the source eval runner used by legacy tests."""

from doge.eval.runner import main, run

__all__ = ["main", "run"]


if __name__ == "__main__":
    main()
