MVP: Offline 3D (Depth Anything V3) + Wi‑Fi RSSI (Jetson)

Goal
- MVP for a drone-based system that records camera video (MP4) and Wi‑Fi RSSI during flight, then offline reconstructs a 3D model using Depth Anything V3 (depth) and monocular SfM (poses), and fuses pose + RSSI for heatmap generation.

Packages
- video_recorder: subscribes to camera images, writes MP4 + frame timestamps.
- wifi_monitor: polls Wi‑Fi RSSI and publishes readings (JSON on /wifi/rssi).
- (offline) scripts: depth (Depth Anything V3), SfM (COLMAP), fusion utilities.

Data Flow (text diagram)
- Online (capture):
  - Camera -> video_recorder -> MP4 + timestamps JSONL
  - Wi‑Fi iface (wlan0) -> wifi_monitor -> publishes /wifi/rssi (String/JSON) and writes CSV under logs/wifi
- Offline (reconstruction):
  - MP4 + timestamps -> extract frames
  - Frames -> COLMAP -> per-frame poses (scale ambiguous)
  - Frames -> Depth Anything V3 -> per-frame depth maps (relative depth)
  - Poses + depth + intrinsics -> fuse -> point cloud/mesh
  - Wi‑Fi CSV + poses -> fused CSV for heatmap

Structure
- config/
  - video_recorder.yaml      # recorder params
  - wifi_config.yaml         # Wi‑Fi interface + targets
- ros2_ws/
  - src/
    - video_recorder/
    - wifi_monitor/
- launch/
  - mvp_system.launch.py
- scripts/                   # helper scripts (TODO)
- logs/                      # output CSV logs
- offline/
  - da_v3_wrapper.py         # depth model wrapper (TODO)
  - colmap_runner.py         # COLMAP invocation (TODO)
  - fuse_depth_poses.py      # back-projection and fusion (TODO)
  - pipeline.py              # orchestrator (TODO)
  - fuse_wifi_posthoc.py     # post-hoc Wi‑Fi fusion (TODO)
  - offline_reconstructor.py # lightweight test reconstructor (runs without ML)
  - run_offline_reconstruction.py # CLI to generate a test PLY from video
  - run_da3_pipeline.py      # CLI to run Depth Anything V3 on video -> 3D export

Setup (high-level, TODO details)
- Install ROS 2 (Humble/Irons) and dependencies (`cv_bridge`, OpenCV codecs).
- Create a ROS 2 workspace and place these packages under ros2_ws/src.
- Build with colcon and source the setup file.
- Configure camera driver and topic names to publish images (e.g., /camera/image_raw).
- Configure `config/video_recorder.yaml` and `config/wifi_config.yaml` parameters.
- Launch capture: `ros2 launch mvp_system.launch.py`.
  - Output: MP4 + JSONL in `logs/video/`, Wi‑Fi CSV in `logs/wifi/`.
- Offline steps (TODO scripts):
  - Install COLMAP CLI and PyTorch; install Depth Anything V3 per its repo.
  - Run `offline/pipeline.py` to reconstruct poses and depth; fuse to a 3D model.
  - Run `offline/fuse_wifi_posthoc.py` to produce fused CSV.

Offline test (no Wi‑Fi, no ML)
- You can dry-run the offline pipeline to validate the end-to-end flow and outputs without Depth Anything V3 or COLMAP:
  - `python3 offline/run_offline_reconstruction.py --video logs/video/capture_<ts>.mp4`
  - Output: `logs/offline/pointcloud_<ts>.ply` (synthetic 3D point cloud)
  - Notes: This uses synthetic poses/depths and sparse back-projection to produce a quick test point cloud.

Full offline pipeline (Depth Anything V3)
- Install PyTorch (Jetson wheel matching your JetPack) and `depth-anything-3`.
- Run DA‑V3 directly on extracted frames from your video:
  - `python3 offline/run_da3_pipeline.py --video logs/video/capture_<ts>.mp4 --work_dir logs/offline_da3 --stride 2 --format ply`
  - Exports 3D assets under `logs/offline_da3/da3_output/` (e.g., PLY or GLB), along with depth/conf/intrinsics/extrinsics in the model’s output format.
  - Notes: Increase `--stride` or cap `--max_frames` to reduce processing time on Jetson.

Notes
- Online capture is lightweight; reconstruction is offline.
- Depth Anything V3 and COLMAP integrations are stubbed in offline/ with TODOs.
- Wi‑Fi polling is stubbed with TODOs.
- This repository is a starting skeleton, not a complete solution.
