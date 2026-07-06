from .executor import main

from settings import DRY_RUN

if __name__ == "__main__":
    main(dry_run=DRY_RUN)
