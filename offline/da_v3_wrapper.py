# File: offline/da_v3_wrapper.py

"""
Depth Anything V3 wrapper using the official API.

Responsibilities:
- Load DA‑V3 model and weights via Hugging Face.
- Run inference on a list of images (paths / numpy / PIL) and optionally export 3D.
- Provide a simple interface for the offline pipeline.

Notes:
- Ensure PyTorch for Jetson is installed (JetPack-matched wheel) and CUDA is available.
- Install: `pip install depth-anything-3` (plus its dependencies) on the target.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from depth_anything_3.api import DepthAnything3


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
