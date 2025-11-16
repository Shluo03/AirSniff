#!/usr/bin/env python3
"""
Isaac Visual SLAM - Refactored for Monocular VIO.
Computes position from a single camera and IMU.

This is now a simple Visual-Inertial Odometry (VIO) implementation.
- The IMU provides the world orientation (Roll, Pitch, Yaw).
- The Camera provides the (unscaled) translation between frames.
- This fuses the two, preventing the rotational drift of the original.

*** IMPORTANT ***
This version STILL CANNOT determine absolute scale.
The (x, y, z) position is UN SCALED and will drift.
A full VIO system (e.g., EKF-based) would be needed
to fuse IMU acceleration data to properly scale the translation.
"""

import numpy as np
import cv2
from pymavlink import mavutil
import time
import threading
from queue import Queue, Empty

# Configuration
IMU_PORT = "/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00"
IMU_BAUD = 115200
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_SENSOR_ID = 0

# Camera calibration (approximate for IMX219 - you should calibrate yours!)
FOCAL_LENGTH = CAMERA_WIDTH * 0.8  # Approximate focal length in pixels
CX = CAMERA_WIDTH / 2
CY = CAMERA_HEIGHT / 2

def euler_to_rotation_matrix(roll, pitch, yaw):
    """
    Convert Euler angles (Roll, Pitch, Yaw) to a 3x3
    ZYX rotation matrix.
    """
    c_y = np.cos(yaw)
    s_y = np.sin(yaw)
    c_p = np.cos(pitch)
    s_p = np.sin(pitch)
    c_r = np.cos(roll)
    s_r = np.sin(roll)

    # Z (Yaw)
    Rz = np.array([
        [c_y, -s_y, 0],
        [s_y,  c_y, 0],
        [0,    0,   1]
    ])
    # Y (Pitch)
    Ry = np.array([
        [c_p, 0, s_p],
        [0,   1, 0],
        [-s_p, 0, c_p]
    ])
    # X (Roll)
    Rx = np.array([
        [1, 0,   0],
        [0, c_r, -s_r],
        [0, s_r,  c_r]
    ])

    # ZYX convention
    R = Rz @ Ry @ Rx
    return R


class IMUReader:
    """Read IMU data from flight controller via MAVLink."""
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.imu_queue = Queue(maxsize=100)
        self.running = False
        self.thread = None
        # Use a lock for thread-safe access to orientation
        self.orientation_lock = threading.Lock()
        self._orientation = np.array([0.0, 0.0, 0.0])  # roll, pitch, yaw

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _read_loop(self):
        try:
            master = mavutil.mavlink_connection(self.port, baud=self.baud)
            print("[IMU] Waiting for heartbeat...")
            master.wait_heartbeat()
            print(f"[IMU] Connected to system {master.target_system}")

            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
                50, 1
            )
            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
                10, 1
            )

            while self.running:
                msg = master.recv_match(type=["RAW_IMU", "ATTITUDE"], blocking=True, timeout=1)
                if msg is None:
                    continue

                if msg.get_type() == "RAW_IMU":
                    imu_data = {
                        'timestamp': time.time(),
                        'accel': np.array([msg.xacc, msg.yacc, msg.zacc]) * 0.00981,
                        'gyro': np.array([msg.xgyro, msg.ygyro, msg.zgyro]) * 0.001
                    }
                    if not self.imu_queue.full():
                        self.imu_queue.put(imu_data)

                elif msg.get_type() == "ATTITUDE":
                    with self.orientation_lock:
                        self._orientation = np.array([msg.roll, msg.pitch, msg.yaw])

        except Exception as e:
            print(f"[IMU] Error: {e}")
            self.running = False

    def get_latest_imu(self):
        try:
            return self.imu_queue.get_nowait()
        except Empty:
            return None

    def get_orientation(self):
        with self.orientation_lock:
            return self._orientation.copy()

class ThreadedCamera:
    """
    Efficient, threaded GStreamer camera reader.
    Fix: Captures at a known-good resolution (1280x720) and uses
    nvvidconv for efficient hardware scaling to the desired output size.
    """
    def __init__(self, sensor_id=0, width=640, height=480, fps=30):
        self.width = width   # Desired *output* width
        self.height = height # Desired *output* height
        self.fps = fps
        
        # Define a known-good capture resolution (from your functional script)
        CAPTURE_WIDTH = 1280
        CAPTURE_HEIGHT = 720
        
        # GStreamer pipeline for Jetson + CSI camera
        # This pipeline captures at a high resolution (1280x720) which is known to work,
        # then uses the hardware-accelerated 'nvvidconv' to scale it down
        # to the desired processing resolution (width x height).
        self.gst_pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width={CAPTURE_WIDTH}, height={CAPTURE_HEIGHT}, framerate={fps}/1 ! "
            f"nvvidconv ! "
            f"video/x-raw, width={self.width}, height={self.height}, format=BGRx ! "
            f"videoconvert ! appsink"
        )
        
        print("[CAM] Using pipeline:")
        print(self.gst_pipeline)

        self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            print("[CAM] ERROR: Failed to open GStreamer pipeline.")
            print("[CAM] Check that the camera is connected and no other process is using it.")
            print(f"[CAM] Also check if 'nvarguscamerasrc sensor-id={sensor_id}' is correct.")
            raise RuntimeError("Could not open camera with GStreamer pipeline")

        self.frame_queue = Queue(maxsize=2)
        self.running = False
        self.thread = None
        print(f"[CAM] Camera opened. Capturing at {CAPTURE_WIDTH}x{CAPTURE_HEIGHT}, scaling to {self.width}x{self.height} @ {fps}fps")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self):
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("[CAM] Frame grab failed, stopping.")
                self.running = False
                break
            
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                # Discard old frame and put new one
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
                self.frame_queue.put(frame)

    def read(self):
        """Get the latest frame from the queue (blocking)."""
        try:
            return self.frame_queue.get(timeout=1.0)
        except Empty:
            print("[CAM] Warning: Camera queue is empty.")
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("[CAM] Camera released.")

class MonocularVIO:
    """Monocular Visual-Inertial Odometry."""

    def __init__(self, focal_length, cx, cy):
        self.focal_length = focal_length
        self.cx = cx
        self.cy = cy

        # VIO pose (World frame)
        # We only track translation 't'. Rotation comes from the IMU.
        self.t = np.zeros(3)  # Translation vector (camera in world)

        # Feature detector and matcher
        self.detector = cv2.ORB_create(nfeatures=2000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # Previous frame data
        self.prev_gray = None
        self.prev_kps = None
        self.prev_descriptors = None

        # Camera matrix
        self.K = np.array([
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1]
        ])

        print(f"[VIO] Initialized Monocular VIO")
        print(f"[VIO] Focal length: {focal_length:.1f}px")
        print("[VIO] WARNING: Output is unscaled. Position is not in meters.")

    def process_frame(self, frame, imu_orientation_rpy):
        """
        Process a single frame and estimate motion.
        imu_orientation_rpy is a (roll, pitch, yaw) array from the IMU.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kps, des = self.detector.detectAndCompute(gray, None)

        if des is None or len(kps) < 10:
            print("[VIO] Not enough features")
            return self.t.copy()

        if self.prev_gray is None:
            self.prev_gray = gray
            self.prev_kps = kps
            self.prev_descriptors = des
            return self.t.copy()

        matches = self.matcher.knnMatch(self.prev_descriptors, des, k=2)
        good_matches = []
        try:
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
        except ValueError:
            pass

        if len(good_matches) < 20:
            print(f"[VIO] Not enough good matches: {len(good_matches)}")
            return self.t.copy()

        prev_pts = np.float32([self.prev_kps[m.queryIdx].pt for m in good_matches])
        curr_pts = np.float32([kps[m.trainIdx].pt for m in good_matches])

        E, mask = cv2.findEssentialMat(curr_pts, prev_pts, self.K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None:
            print("[VIO] Could not find Essential Matrix")
            return self.t.copy()

        _, R_rel, t_rel, mask = cv2.recoverPose(E, curr_pts, prev_pts, self.K)
        if R_rel is None or t_rel is None:
            print("[VIO] Could not recover pose")
            return self.t.copy()

        # --- VIO POSE UPDATE ---
        # t_rel is the (unscaled) translation in the *camera* frame.
        # We get the world rotation from the IMU.
        
        # 1. Get current world orientation from IMU
        R_world = euler_to_rotation_matrix(*imu_orientation_rpy)

        # 2. Rotate the camera-frame translation (t_rel) into the world frame
        t_world = (R_world @ t_rel).flatten()

        # 3. Integrate the unscaled world translation
        self.t = self.t + t_world
        
        # NOTE: We completely DISCARD R_rel (relative rotation from VO).
        # We trust the IMU's orientation entirely. This prevents
        # the classic rotational drift of pure VO.

        self.prev_gray = gray
        self.prev_kps = kps
        self.prev_descriptors = des

        return self.t.copy()


def main():
    """Main execution loop."""
    print("=" * 60)
    print("Isaac Visual SLAM - Monocular VIO (1-Camera) Refactor")
    print("=" * 60)
    print("WARNING: This version uses Monocular VIO and is UN SCALED.")
    print("The (x, y, z) position is not in metric meters and will drift.")
    print("Rotation is now provided by the IMU.")
    print("-" * 60)
    print("Starting position: (0, 0, 0)")
    print("-" * 60)

    # Initialize components
    imu_reader = IMUReader(IMU_PORT, IMU_BAUD)
    camera = ThreadedCamera(
        sensor_id=CAMERA_SENSOR_ID,
        width=CAMERA_WIDTH,
        height=CAMERA_HEIGHT,
        fps=CAMERA_FPS
    )
    vo = MonocularVIO(FOCAL_LENGTH, CX, CY)

    # Start hardware readers
    imu_reader.start()
    camera.start()
    time.sleep(2)  # Wait for devices to stabilize

    try:
        frame_count = 0
        start_time = time.time()

        print("\n[VIO] Starting tracking...")
        print("=" * 60)

        while True:
            # Read from threaded queues
            frame = camera.read()
            if frame is None:
                print("[WARN] Failed to read frame")
                continue

            # Get latest orientation from IMU
            orientation = imu_reader.get_orientation()
            
            # (Optional: Get latest accel/gyro data if you want to use it)
            # imu_data = imu_reader.get_latest_imu() 

            # Process and get position
            position = vo.process_frame(frame, orientation)

            # Output position
            frame_count += 1
            if frame_count % 3 == 0:  # Print every 3 frames
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0

                print(f"Frame {frame_count:4d} | "
                      f"Pos (Unscaled): x={position[0]:7.3f} y={position[1]:7.3f} z={position[2]:7.3f} | "
                      f"Roll={np.rad2deg(orientation[0]):6.1f}° "
                      f"Pitch={np.rad2deg(orientation[1]):6.1f}° "
                      f"Yaw={np.rad2deg(orientation[2]):6.1f}° | "
                      f"FPS: {fps:.1f}")

    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
    finally:
        imu_reader.stop()
        camera.stop()
        print("[DONE] Cleanup complete")


if __name__ == "__main__":
    main()