#!/usr/bin/env python3
"""Launch the desktop game, or the original prototype with --text."""

import sys


if __name__ == "__main__":
    if "--text" in sys.argv:
        from text_game import main
    else:
        from dungeon.app import main
    main()
