# File: offline/offline_reconstructor.py

from __future__ import annotations

"""
OfflineReconstructor (lightweight test implementation)

Purpose
- Provide a minimal, runnable offline pipeline to validate the flow of
  video -> frames -> synthetic poses/depth -> point cloud (PLY).
- This is a placeholder for the real pipeline using Depth Anything V3 and COLMAP.

What it does (currently)
- Reads frames from an MP4 using OpenCV.
- Generates synthetic per-frame poses (translate forward along Z).
- Generates a simple depth map proxy (per-pixel gradient scaled by frame index).
- Back-projects a sparse set of pixels per frame into 3D points.
- Colors points from the frame and writes an ASCII PLY point cloud.

TODO (future)
- Replace synthetic poses with COLMAP monocular SfM outputs.
- Replace synthetic depth with Depth Anything V3 inference.
- Add TSDF fusion for higher-quality meshes (e.g., via Open3D).
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


@dataclass
class CameraIntrinsics:
    fx: float = 600.0
    fy: float = 600.0
    cx: float = 640.0
    cy: float = 360.0


class OfflineReconstructor:
    def __init__(
        self,
        max_frames: int = 300,
        frame_stride: int = 1,
        sample_step: int = 8,
        depth_scale: float = 2.0,
        motion_step_m: float = 0.02,
        intrinsics: Optional[CameraIntrinsics] = None,
        output_dir: str | Path = "logs/offline",
    ) -> None:
        self.max_frames = int(max_frames)
        self.frame_stride = int(frame_stride)
        self.sample_step = int(sample_step)
        self.depth_scale = float(depth_scale)
        self.motion_step_m = float(motion_step_m)
        self.K = intrinsics or CameraIntrinsics()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, mp4_path: str | Path) -> Optional[str]:
        if cv2 is None:
            raise RuntimeError("OpenCV not available: install opencv-python to run offline reconstruction")

        mp4_path = str(mp4_path)
        cap = cv2.VideoCapture(mp4_path)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {mp4_path}")

        frames: List[np.ndarray] = []
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if (idx % self.frame_stride) == 0:
                frames.append(frame)
            idx += 1
            if len(frames) >= self.max_frames:
                break
        cap.release()

        if not frames:
            raise RuntimeError("No frames read from video")

        poses = self._generate_synthetic_poses(len(frames))
        points_xyz, colors = self._accumulate_point_cloud(frames, poses)

        out_ply = self._write_ply(points_xyz, colors)
        return out_ply

    def _generate_synthetic_poses(self, n: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Return a list of (R, t) camera-to-world poses.

        For testing, we keep R = I and translate along +Z per frame by motion_step_m.
        """
        poses: List[Tuple[np.ndarray, np.ndarray]] = []
        for i in range(n):
            R = np.eye(3, dtype=np.float32)
            t = np.array([0.0, 0.0, i * self.motion_step_m], dtype=np.float32)
            poses.append((R, t))
        return poses

    def _accumulate_point_cloud(
        self, frames: List[np.ndarray], poses: List[Tuple[np.ndarray, np.ndarray]]
    ) -> Tuple[np.ndarray, np.ndarray]:
        all_pts: List[np.ndarray] = []
        all_cols: List[np.ndarray] = []

        fx, fy, cx, cy = self.K.fx, self.K.fy, self.K.cx, self.K.cy

        for i, (frame, (R, t)) in enumerate(zip(frames, poses)):
            h, w = frame.shape[:2]
            # Synthetic depth: gradient plus frame index term to push points outward
            yy, xx = np.mgrid[0:h:self.sample_step, 0:w:self.sample_step]
            depth = self.depth_scale * (0.5 + 0.5 * (xx.astype(np.float32) / max(w - 1, 1)))
            depth += 0.1 * i  # drift outward over frames

            # Back-project to camera frame
            x_norm = (xx - cx) / fx
            y_norm = (yy - cy) / fy
            Z = depth
            X = x_norm * Z
            Y = y_norm * Z

            cam_pts = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)

            # Transform to world: Xw = R*Xc + t
            world_pts = (cam_pts @ R.T) + t[None, :]
            all_pts.append(world_pts)

            # Sample colors corresponding to the sampled pixels
            sampled = frame[yy, xx, :]  # BGR
            cols = sampled.reshape(-1, 3)[:, ::-1]  # to RGB
            all_cols.append(cols.astype(np.uint8))

        pts = np.concatenate(all_pts, axis=0) if all_pts else np.zeros((0, 3), dtype=np.float32)
        cols = np.concatenate(all_cols, axis=0) if all_cols else np.zeros((0, 3), dtype=np.uint8)
        return pts.astype(np.float32), cols

    def _write_ply(self, points_xyz: np.ndarray, colors_rgb: np.ndarray) -> str:
        ts = int(time.time())
        out_path = str(self.output_dir / f"pointcloud_{ts}.ply")

        n = points_xyz.shape[0]
        header = (
            "ply\n"
            "format ascii 1.0\n"
            f"element vertex {n}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "property uchar red\n"
            "property uchar green\n"
            "property uchar blue\n"
            "end_header\n"
        )

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header)
            for (x, y, z), (r, g, b) in zip(points_xyz, colors_rgb):
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)}\n")

        return out_path

