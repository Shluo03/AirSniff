"""Simple IMU data reader using MAVLink protocol."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

from pymavlink import mavutil


class IMUReader:
    """Reads IMU data from MAVLink-connected autopilot."""

    def __init__(
        self,
        port: str = "/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00",
        baud: int = 115200,
    ) -> None:
        """Initialize IMU reader.
        
        Args:
            port: Serial port path for MAVLink connection.
            baud: Baud rate for serial connection.
        """
        self.port = port
        self.baud = baud
        self._master: Optional[mavutil.mavlink_connection] = None
        self._is_running: bool = False
        self._reader_thread: Optional[threading.Thread] = None
        self._latest_imu: Dict[str, Tuple[float, float, float]] = {
            "accel": (0.0, 0.0, 0.0),
            "gyro": (0.0, 0.0, 0.0),
        }
        self._lock = threading.Lock()
        self._is_connected: bool = False

    def connect(self) -> bool:
        """Establish connection to MAVLink device."""
        try:
            self._master = mavutil.mavlink_connection(self.port, baud=self.baud)
            print(f"[IMU] Waiting for heartbeat on {self.port}...")
            self._master.wait_heartbeat(timeout=5)
            print(f"[IMU] Connected to system {self._master.target_system}")

            # Request raw sensor data stream at 50 Hz
            self._master.mav.request_data_stream_send(
                self._master.target_system,
                self._master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
                50,
                1,
            )
            print("[IMU] Requested RAW_SENSORS data stream")
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[IMU] Failed to connect: {e}")
            self._is_connected = False
            return False

    def start(self) -> None:
        """Start the IMU reader thread."""
        if self._is_running:
            return

        if not self._is_connected:
            if not self.connect():
                return

        self._is_running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        print("[IMU] Reader thread started")

    def stop(self) -> None:
        """Stop the IMU reader thread."""
        self._is_running = False
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2.0)
        if self._master is not None:
            self._master.close()

    def _read_loop(self) -> None:
        """Main read loop for IMU data."""
        while self._is_running:
            try:
                msg = self._master.recv_match(
                    type="RAW_IMU", blocking=True, timeout=1
                )
                if msg is None:
                    continue

                ax, ay, az = msg.xacc, msg.yacc, msg.zacc
                gx, gy, gz = msg.xgyro, msg.ygyro, msg.zgyro

                with self._lock:
                    self._latest_imu = {
                        "accel": (ax, ay, az),
                        "gyro": (gx, gy, gz),
                    }

            except Exception as e:
                print(f"[IMU] Error in read loop: {e}")
                time.sleep(0.5)

    def get_latest_imu(self) -> Dict[str, Tuple[float, float, float]]:
        """Get latest IMU data (thread-safe)."""
        with self._lock:
            return {
                "accel": self._latest_imu["accel"],
                "gyro": self._latest_imu["gyro"],
            }

    def is_connected(self) -> bool:
        """Check if IMU reader is connected and running."""
        return self._is_connected and self._is_running
