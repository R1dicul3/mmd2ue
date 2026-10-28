"""Unit test for PMM entry placeholder (AC-M1-8)."""

from __future__ import annotations

import pytest

from mmd2ue.core.parsers import pmm


def test_pmm_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        pmm.parse(b"")
    with pytest.raises(NotImplementedError):
        pmm.parse_file("whatever.pmm")
