"""Shared test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyberautopsy.dataset import Dataset  # noqa: E402

DATA_DIR = ROOT / "data"


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    return Dataset.load(DATA_DIR)
