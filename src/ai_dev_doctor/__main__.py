from multiprocessing import freeze_support

from ai_dev_doctor.cli import main

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
