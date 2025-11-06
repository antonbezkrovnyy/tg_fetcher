"""Allow running the package as a module: python -m src."""

import asyncio
import sys

from src.main import main

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
