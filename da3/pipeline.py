# File: da3test/pipeline.py

from __future__ import annotations

"""
Depth Anything V3: Video -> 3D export (self-contained).

Copy this folder (da3test/) to your Jetson and run:
    python3 pipeline.py --video /path/to/video.mp4 --work_dir ./out --stride 2 --format ply

Requirements on Jetson:
    - Python 3
    - opencv-python
    - torch + torchvision (JetPack-matched wheels)
    - depth-anything-3
"""

import argparse
from pathlib import Path
from typing import List

try:
    import cv2  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError("OpenCV (opencv-python) is required to extract frames") from e

from da_v3_wrapper import DepthAnythingV3


def extract_frames(
    mp4_path: str | Path,
    out_dir: str | Path,
    stride: int = 1,
    max_frames: int = 0,
) -> List[str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(mp4_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {mp4_path}")
    frames: List[str] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % max(1, stride) == 0:
            name = f"frame_{idx:06d}.jpg"
            path = str(out_dir / name)
            cv2.imwrite(path, frame)
            frames.append(path)
            if max_frames and len(frames) >= max_frames:
                break
        idx += 1
    cap.release()
    if not frames:
        raise RuntimeError("No frames extracted from video")
    return frames


def run_da3_video_to_3d(
    video_path: str | Path,
    work_dir: str | Path,
    stride: int = 1,
    max_frames: int = 0,
    export_format: str = "ply",
) -> str:
    work_dir = Path(work_dir)
    frames_dir = work_dir / "frames"
    export_dir = work_dir / "da3_output"
    export_dir.mkdir(parents=True, exist_ok=True)

    images = extract_frames(video_path, frames_dir, stride=stride, max_frames=max_frames)

    da3 = DepthAnythingV3()
    da3.load()
    _pred = da3.infer(images=images, export_dir=export_dir, export_format=export_format)
    return str(export_dir)


def main() -> None:
    p = argparse.ArgumentParser(description="Depth Anything V3: video -> 3D export")
    p.add_argument("--video", required=True, help="Path to MP4 video")
    p.add_argument("--work_dir", default="./out_da3", help="Working/output directory")
    p.add_argument("--stride", type=int, default=1, help="Use every Nth frame")
    p.add_argument("--max_frames", type=int, default=0, help="Cap number of frames (0 = all)")
    p.add_argument(
        "--format",
        default="ply",
        choices=["ply", "glb", "npz", "mini_npz", "gs_ply", "gs_video"],
        help="Export format",
    )
    args = p.parse_args()

    out = run_da3_video_to_3d(
        video_path=args.video,
        work_dir=args.work_dir,
        stride=args.stride,
        max_frames=args.max_frames,
        export_format=args.format,
    )
    print(f"Depth Anything V3 export written to: {out}")


if __name__ == "__main__":
    main()

