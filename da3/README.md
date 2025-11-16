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
  - `python3 pipeline.py --video IMG_0612.mp4 --work_dir ./out --stride 10 --format glb`
- Output: exported 3D assets under `./out/da3_output/` (e.g., PLY/GLB) and extracted frames under `./out/frames/`.

Notes
- Increase `--stride` or set `--max_frames` to reduce compute on Jetson.
- The model chooses CUDA if available; ensure `torch.cuda.is_available()` returns True.

mkdir -p /da3test /out
docker cp ~/da3test/. dee5d6f54c7a:/da3test
docker run -it --rm dustynv/l4t-pytorch:r36.4.0
docker run -it dustynv/l4t-pytorch:r36.4.0
https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl

wget raw.githubusercontent.com/pytorch/pytorch/5c6af2b583709f6176898c017424dc9981023c28/.ci/docker/common/install_cusparselt.sh 
export CUDA_VERSION=12.1
bash ./install_cusparselt.sh