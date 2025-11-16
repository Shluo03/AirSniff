# File: ros2_ws/src/slam_pycu_interface/pycu_slam_wrapper.py

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml

try:
    from nvidia_isaac_perceptor.vslam import vslam
except ImportError:
    vslam = None

try:
    from .imu_utils import IMUReader
except ImportError:
    IMUReader = None


class PycuVSLAMManager:
    """Encapsulates pycuVSLAM usage for monocular/stereo SLAM.

    Responsibilities:
    - Load configuration and camera intrinsics.
    - Initialize cuVSLAM system (GPU-backed) with provided parameters.
    - Accept frames with timestamps and feed them to the SLAM pipeline.
    - Provide accessors for the latest pose and (optionally) map points.
    """

    def __init__(self, config_path: str | Path) -> None:
        """Create the manager with a path to a slam_config.yaml file.

        Args:
            config_path: Path to YAML config containing camera and cuVSLAM params.
        """
        self.config_path = str(config_path)
        self._is_initialized: bool = False
        self._latest_pose: Optional[Dict[str, Any]] = None
        self._map_points: List[Tuple[float, float, float]] = []
        self._vslam_system: Optional[Any] = None
        self._frame_count: int = 0
        self._imu_reader: Optional[Any] = None
        
        # Load YAML configuration
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load YAML configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default SLAM configuration."""
        return {
            "camera": {
                "model": "pinhole",
                "width": 640,
                "height": 480,
                "fx": 400.0,
                "fy": 400.0,
                "cx": 320.0,
                "cy": 240.0,
                "distortion_model": "radtan",
                "distortion_coeffs": [0.0, 0.0, 0.0, 0.0],
                "frame_id": "camera_link",
            },
            "pycuVSLAM": {
                "use_stereo": True,
                "enable_loop_closure": True,
                "enable_relocalization": True,
                "max_features": 2000,
            },
        }

    def initialize_slam(self) -> None:
        """Initialize pycuVSLAM system and any required resources."""
        try:
            if vslam is None:
                print("Warning: nvidia_isaac_perceptor.vslam not available. Using mock SLAM.")
                self._vslam_system = None
            else:
                # Initialize Isaac VSLAM with configuration
                camera_cfg = self._config.get("camera", {})
                slam_cfg = self._config.get("pycuVSLAM", {})
                
                # Create camera intrinsics
                fx = camera_cfg.get("fx", 400.0)
                fy = camera_cfg.get("fy", 400.0)
                cx = camera_cfg.get("cx", 320.0)
                cy = camera_cfg.get("cy", 240.0)
                width = camera_cfg.get("width", 640)
                height = camera_cfg.get("height", 480)
                
                # Initialize VSLAM system
                # Note: Actual Isaac VSLAM API may vary; this is a template
                self._vslam_system = vslam.VSLAMSystem(
                    camera_matrix=np.array([
                        [fx, 0.0, cx],
                        [0.0, fy, cy],
                        [0.0, 0.0, 1.0]
                    ], dtype=np.float32),
                    image_width=width,
                    image_height=height,
                    enable_loop_closure=slam_cfg.get("enable_loop_closure", True),
                    enable_relocalization=slam_cfg.get("enable_relocalization", True),
                )
                print(f"Initialized Isaac VSLAM: {width}x{height}, fx={fx}, fy={fy}")
        except Exception as e:
            print(f"Warning: Could not initialize Isaac VSLAM: {e}. Using mock SLAM.")
            self._vslam_system = None
        
        self._is_initialized = True
        self._frame_count = 0

    def process_frame(self, image: Any, timestamp: float) -> Optional[bool]:
        """Feed a frame into cuVSLAM.

        Args:
            image: Image buffer as numpy array (uint8, single channel or BGR).
            timestamp: Wall or device time in seconds.

        Returns:
            Optional[bool]: True/False if processed; None if not initialized.
        """
        if not self._is_initialized:
            return None

        if image is None:
            return False

        try:
            # Ensure image is numpy array
            if not isinstance(image, np.ndarray):
                image = np.array(image, dtype=np.uint8)
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                # Convert BGR or RGB to grayscale
                image = np.dot(image[..., :3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
            
            if self._vslam_system is not None:
                try:
                    # Feed frame to Isaac VSLAM
                    self._vslam_system.add_frame(image, timestamp)
                    
                    # Try to get pose estimate
                    pose_data = self._vslam_system.get_pose()
                    if pose_data is not None:
                        self._update_pose_from_vslam(pose_data, timestamp)
                except Exception as e:
                    print(f"Error processing frame with VSLAM: {e}")
            else:
                # Mock SLAM: generate dummy pose that drifts slightly
                self._generate_mock_pose(timestamp)
            
            self._frame_count += 1
            return True
        except Exception as e:
            print(f"Error in process_frame: {e}")
            return False

    def _update_pose_from_vslam(self, pose_data: Any, timestamp: float) -> None:
        """Update internal pose from VSLAM output.
        
        Args:
            pose_data: Output from VSLAM system (format depends on Isaac API).
            timestamp: Current timestamp.
        """
        try:
            # Extract position and orientation from VSLAM output
            # This depends on the actual Isaac VSLAM API
            if hasattr(pose_data, 'position') and hasattr(pose_data, 'orientation'):
                position = pose_data.position
                orientation = pose_data.orientation
            elif isinstance(pose_data, dict):
                position = pose_data.get('position', (0.0, 0.0, 0.0))
                orientation = pose_data.get('orientation', (1.0, 0.0, 0.0, 0.0))
            elif isinstance(pose_data, (tuple, list)) and len(pose_data) >= 7:
                # Assume format: [x, y, z, qw, qx, qy, qz]
                position = tuple(pose_data[:3])
                orientation = tuple(pose_data[3:7])
            else:
                # Fallback to mock
                self._generate_mock_pose(timestamp)
                return
            
            self._latest_pose = {
                "timestamp": timestamp,
                "position": tuple(position),
                "orientation": tuple(orientation),
                "frame_count": self._frame_count,
            }
        except Exception as e:
            print(f"Error updating pose from VSLAM: {e}")
            self._generate_mock_pose(timestamp)

    def _generate_mock_pose(self, timestamp: float) -> None:
        """Generate a mock pose for testing (slowly drifting position)."""
        # Simple mock: position drifts based on frame count
        drift_scale = 0.01
        x = self._frame_count * drift_scale
        y = np.sin(self._frame_count * 0.05) * drift_scale * 10
        z = 0.5  # Hovering at 0.5m
        
        imu_data = None
        if self._imu_reader is not None and self._imu_reader.is_connected():
            imu_data = self._imu_reader.get_latest_imu()
        
        self._latest_pose = {
            "timestamp": timestamp,
            "position": (x, y, z),
            "orientation": (1.0, 0.0, 0.0, 0.0),  # Identity quaternion
            "frame_count": self._frame_count,
            "is_mock": True,
            "imu": imu_data,
        }

    def get_latest_pose(self) -> Optional[Dict[str, Any]]:
        """Return the latest pose estimate.

        Returns:
            Optional[Dict[str, Any]]: A dict with keys:
                {
                    "timestamp": float,
                    "position": (x, y, z),
                    "orientation": (w, x, y, z),  # quaternion
                    "frame_count": int,
                }
            or None if no estimate is available yet.
        """
        return self._latest_pose

    def get_map_points(self) -> List[Tuple[float, float, float]]:
        """Return a list of 3D map points.

        Returns:
            List[Tuple[float, float, float]]: XYZ tuples (may be empty).
        """
        if self._vslam_system is not None:
            try:
                map_points = self._vslam_system.get_map_points()
                if map_points is not None:
                    self._map_points = [tuple(pt[:3]) for pt in map_points]
            except Exception as e:
                print(f"Warning: Could not get map points: {e}")
        
        return list(self._map_points)

    def initialize_imu(self, port: str, baud: int = 115200) -> bool:
        """Initialize IMU reader.
        
        Args:
            port: Serial port for MAVLink connection.
            baud: Baud rate.
            
        Returns:
            bool: True if initialized successfully.
        """
        if IMUReader is None:
            print("Warning: IMUReader not available")
            return False
        
        try:
            self._imu_reader = IMUReader(port=port, baud=baud)
            self._imu_reader.start()
            return self._imu_reader.is_connected()
        except Exception as e:
            print(f"Warning: Could not initialize IMU: {e}")
            return False

    def shutdown(self) -> None:
        """Clean up resources."""
        if self._imu_reader is not None:
            self._imu_reader.stop()

