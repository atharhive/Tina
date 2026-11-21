"""`python -m colony` is the same entry point as `python -m colony.cli`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
