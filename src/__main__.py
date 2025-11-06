"""Allow running the package as a module: python -m src"""
from src.main import main
import asyncio
import sys

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
