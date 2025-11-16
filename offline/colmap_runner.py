# File: offline/colmap_runner.py

"""
COLMAP runner (skeleton) to estimate camera poses from extracted frames.

Steps (typical):
- colmap feature_extractor
- colmap exhaustive_matcher or sequential_matcher
- colmap mapper (SfM) -> sparse reconstruction
- colmap image_undistorter (optional)

Outputs:
- Per-frame camera poses (R,t) and intrinsics (JSON/CSV) for later fusion.

This module only includes interfaces and TODO stubs; it does not run COLMAP yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


def run_colmap_sfm(frames_dir: str | Path, work_dir: str | Path) -> Optional[Dict]:
    """Run COLMAP on frames to get poses (stub).

    Args:
        frames_dir: Path to a directory of frames (e.g., extracted from MP4).
        work_dir: Path to a directory for COLMAP databases and outputs.

    Returns:
        Optional[Dict]: placeholder dict containing pose paths or None.
    """
    # TODO: implement subprocess calls to COLMAP CLI and parse outputs
    return None

