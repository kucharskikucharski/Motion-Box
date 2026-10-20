#!/usr/bin/env python3
"""Motion Box - start here:  python3 motion_box.py   (add --quick to skip splash and start window)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mb_app import App  # noqa: E402


def main():
    App(quick="--quick" in sys.argv).run()


if __name__ == "__main__":
    main()
