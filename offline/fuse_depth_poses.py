# File: offline/fuse_depth_poses.py

"""
Fuse per-frame depth maps with camera poses to produce a point cloud or mesh.

Approach (skeleton):
- Load intrinsics (fx, fy, cx, cy) from YAML.
- For each frame: back-project depth map to 3D in camera frame; transform by pose to world.
- Accumulate into a point cloud; optionally run TSDF fusion (Open3D) - TODO.
- Save PLY/OBJ and per-frame pose JSON.

This module includes only interfaces and TODO stubs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def fuse_depth_and_poses(
    depths_dir: str | Path,
    poses_path: str | Path,
    intrinsics_path: str | Path,
    output_ply: str | Path,
) -> Optional[str]:
    """Fuse depth maps and poses to a point cloud (stub).

    Returns path to output file or None.
    """
    # TODO: implement fusion logic (possibly using Open3D TSDF)
    return None

