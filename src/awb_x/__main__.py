# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Command-line entry point: `awb-x` or `python -m awb_x`."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from awb_x.ui.app import run

    return run(sys.argv if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
