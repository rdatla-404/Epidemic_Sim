"""
tests/conftest.py

Makes sure the project root (the folder containing src/) is on
sys.path, so `from src.compartmental_model import ...` works regardless
of how pytest was invoked.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
