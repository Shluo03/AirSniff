# File: da3test/da_v3_wrapper.py

from __future__ import annotations

"""
Depth Anything V3 wrapper using the official API.

Usage:
    from da_v3_wrapper import DepthAnythingV3
    da3 = DepthAnythingV3()
    da3.load()
    pred = da3.infer(images=["frame_000001.jpg", ...], export_dir="out", export_format="ply")

Dependencies (install on Jetson):
    - torch, torchvision (JetPack-matched wheels)
    - depth-anything-3
"""

from pathlib import Path
from typing import Any, List, Optional

try:
    import torch  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "PyTorch is required. Install Jetson-matched wheels for your JetPack."
    ) from e

try:
    from depth_anything_3.api import DepthAnything3  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "depth-anything-3 package is required. Install with: pip install depth-anything-3"
    ) from e


class DepthAnythingV3:
    def __init__(self, model_id: str = "depth-anything/da3-giant", device: Optional[str] = None) -> None:
        self.model_id = model_id
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model: Optional[DepthAnything3] = None

    def load(self) -> None:
        self.model = DepthAnything3.from_pretrained(self.model_id)
        self.model = self.model.to(device=self.device)  # type: ignore[assignment]

    def infer(
        self,
        images: List[Any],
        export_dir: str | Path,
        export_format: str = "ply",
    ) -> Any:
        if self.model is None:
            raise RuntimeError("DepthAnythingV3 model is not loaded. Call load() first.")
        export_dir = str(export_dir)
        prediction = self.model.inference(
            images,
            export_dir=export_dir,
            export_format=export_format,
        )
        return prediction

