"""Shared detector registry for Praxis experiment harnesses."""

from .registry import DetectorSpec, detector_table, list_detector_specs, make_detector

__all__ = ["DetectorSpec", "detector_table", "list_detector_specs", "make_detector"]
