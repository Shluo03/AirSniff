# File: offline/run_da3_pipeline.py

from __future__ import annotations

import argparse
import sys

from pipeline import run_da3_video_to_3d


def main() -> None:
    p = argparse.ArgumentParser(description="Run Depth Anything V3 on a video")
    p.add_argument("--video", required=True, help="Path to MP4 video")
    p.add_argument("--work_dir", default="logs/offline_da3", help="Working/output directory")
    p.add_argument("--stride", type=int, default=1, help="Use every Nth frame")
    p.add_argument("--max_frames", type=int, default=0, help="Cap number of frames (0 = all)")
    p.add_argument("--format", default="ply", choices=["ply", "glb", "npz", "mini_npz", "gs_ply", "gs_video"], help="Export format")
    args = p.parse_args()

    try:
        out = run_da3_video_to_3d(
            video_path=args.video,
            work_dir=args.work_dir,
            stride=args.stride,
            max_frames=args.max_frames,
            export_format=args.format,
        )
        print(f"Export written to: {out}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

