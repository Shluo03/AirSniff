# DA3 Test (Self-contained)

Video -> 3D export using Depth Anything V3.

Usage on Jetson
- Copy the entire `da3test/` folder to your Jetson.
- Install dependencies (Jetson-compatible):
  - PyTorch + torchvision (match your JetPack)
  - depth-anything-3
  - opencv-python
- Run:
  - `cd da3test`
  - `python3 pipeline.py --video /path/to/video.mp4 --work_dir ./out --stride 2 --format ply`
- Output: exported 3D assets under `./out/da3_output/` (e.g., PLY/GLB) and extracted frames under `./out/frames/`.

Notes
- Increase `--stride` or set `--max_frames` to reduce compute on Jetson.
- The model chooses CUDA if available; ensure `torch.cuda.is_available()` returns True.

pip3 install -r da3test/requirements.txt
Install torch/torchvision using NVIDIA’s Jetson wheels matched to your JetPack.

for 
docker cp /home/jetson/da3test 2d244da866f5:/workspace/da3test
docker cp /home/jetson/da3test/. 2d244da866f5:/da3test
docker cp ~/depth-anything-3 2d244da866f5:/root/depth-anything-3