"""Convenience launcher for the Streamlit application."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    """Run the scanner through Streamlit using the active Python interpreter."""
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app/main.py"], check=False)


if __name__ == "__main__":
    main()