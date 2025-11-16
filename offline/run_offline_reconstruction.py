# File: offline/run_offline_reconstruction.py

from __future__ import annotations

import argparse
import sys

from offline_reconstructor import OfflineReconstructor


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run lightweight offline 3D reconstruction test")
    p.add_argument("--video", required=True, help="Path to MP4 video file")
    p.add_argument("--out", default="logs/offline", help="Output directory for PLY")
    p.add_argument("--max_frames", type=int, default=300, help="Max frames to process")
    p.add_argument("--stride", type=int, default=1, help="Frame stride (subsample)")
    p.add_argument("--sample_step", type=int, default=8, help="Pixel sampling step for back-projection")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    recon = OfflineReconstructor(
        max_frames=args.max_frames,
        frame_stride=args.stride,
        sample_step=args.sample_step,
        output_dir=args.out,
    )
    ply = recon.run(args.video)
    print(f"Wrote point cloud: {ply}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

