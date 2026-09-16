"""Standalone launcher: handle frozen multiprocessing before importing the CLI."""

import sys
from multiprocessing import freeze_support

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    freeze_support()
    from ai_dev_doctor.cli import main

    raise SystemExit(main())
