from __future__ import annotations

from custom_components.haier_atw_ew11.coordinator import _build_contiguous_ranges, _split_range


def test_build_contiguous_ranges_groups_consecutive_addresses() -> None:
    addresses = [0, 1, 2, 5, 9, 10]
    assert _build_contiguous_ranges(addresses) == [(0, 2), (5, 5), (9, 10)]


def test_split_range_respects_chunk_size() -> None:
    assert _split_range(100, 110, chunk_size=4) == [(100, 103), (104, 107), (108, 110)]


def test_split_range_handles_invalid_chunk_size() -> None:
    assert _split_range(7, 9, chunk_size=0) == [(7, 7), (8, 8), (9, 9)]
