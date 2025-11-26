#!/usr/bin/env python3
"""
VIO Node - Visual-Inertial Odometry ROS2 Node
Publishes pose (position + orientation) to /vio/pose topic
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import numpy as np
import cv2
from pymavlink import mavutil
import time
import threading
from queue import Queue, Empty


def euler_to_quaternion(roll, pitch, yaw):
    """Convert Euler angles to quaternion."""
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)
    
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    
    return np.array([x, y, z, w])


def euler_to_rotation_matrix(roll, pitch, yaw):
    """Convert Euler angles to rotation matrix."""
    c_y = np.cos(yaw)
    s_y = np.sin(yaw)
    c_p = np.cos(pitch)
    s_p = np.sin(pitch)
    c_r = np.cos(roll)
    s_r = np.sin(roll)
    
    Rz = np.array([[c_y, -s_y, 0], [s_y, c_y, 0], [0, 0, 1]])
    Ry = np.array([[c_p, 0, s_p], [0, 1, 0], [-s_p, 0, c_p]])
    Rx = np.array([[1, 0, 0], [0, c_r, -s_r], [0, s_r, c_r]])
    
    return Rz @ Ry @ Rx


class IMUReader:
    """Read IMU data from flight controller via MAVLink."""
    def __init__(self, node, port, baud):
        self.node = node
        self.port = port
        self.baud = baud
        self.imu_queue = Queue(maxsize=100)
        self.running = False
        self.thread = None
        self.orientation_lock = threading.Lock()
        self._orientation = np.array([0.0, 0.0, 0.0])
    
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
            self.node.get_logger().info('[IMU] Waiting for heartbeat...')
            master.wait_heartbeat()
            self.node.get_logger().info(f'[IMU] Connected to system {master.target_system}')
            
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
            self.node.get_logger().error(f'[IMU] Error: {e}')
            self.running = False
    
    def get_orientation(self):
        with self.orientation_lock:
            return self._orientation.copy()


class ThreadedCamera:
    """Efficient, threaded GStreamer camera reader."""
    def __init__(self, node, sensor_id=0, width=640, height=480, fps=30):
        self.node = node
        self.width = width
        self.height = height
        self.fps = fps
        
        CAPTURE_WIDTH = 1280
        CAPTURE_HEIGHT = 720
        
        self.gst_pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width={CAPTURE_WIDTH}, height={CAPTURE_HEIGHT}, framerate={fps}/1 ! "
            f"nvvidconv ! "
            f"video/x-raw, width={self.width}, height={self.height}, format=BGRx ! "
            f"videoconvert ! appsink"
        )
        
        self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera with GStreamer pipeline")
        
        self.frame_queue = Queue(maxsize=2)
        self.running = False
        self.thread = None
        self.node.get_logger().info(f'[CAM] Camera opened at {self.width}x{self.height} @ {fps}fps')
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
    
    def _read_loop(self):
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                self.node.get_logger().error('[CAM] Frame grab failed')
                self.running = False
                break
            
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
                self.frame_queue.put(frame)
    
    def read(self):
        try:
            return self.frame_queue.get(timeout=1.0)
        except Empty:
            return None
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()


class MonocularVIO:
    """Monocular Visual-Inertial Odometry."""
    def __init__(self, node, focal_length, cx, cy):
        self.node = node
        self.focal_length = focal_length
        self.cx = cx
        self.cy = cy
        
        self.t = np.zeros(3)
        
        self.detector = cv2.ORB_create(nfeatures=2000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        
        self.prev_gray = None
        self.prev_kps = None
        self.prev_descriptors = None
        
        self.K = np.array([
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1]
        ])
        
        self.node.get_logger().info(f'[VIO] Initialized with focal length: {focal_length:.1f}px')
        self.node.get_logger().warn('[VIO] Output is unscaled - position not in meters')
    
    def process_frame(self, frame, imu_orientation_rpy):
        """Process frame and estimate motion."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kps, des = self.detector.detectAndCompute(gray, None)
        
        if des is None or len(kps) < 10:
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
            return self.t.copy()
        
        prev_pts = np.float32([self.prev_kps[m.queryIdx].pt for m in good_matches])
        curr_pts = np.float32([kps[m.trainIdx].pt for m in good_matches])
        
        E, mask = cv2.findEssentialMat(curr_pts, prev_pts, self.K, 
                                       method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None:
            return self.t.copy()
        
        _, R_rel, t_rel, mask = cv2.recoverPose(E, curr_pts, prev_pts, self.K)
        if R_rel is None or t_rel is None:
            return self.t.copy()
        
        # VIO pose update
        R_world = euler_to_rotation_matrix(*imu_orientation_rpy)
        t_world = (R_world @ t_rel).flatten()
        self.t = self.t + t_world
        
        self.prev_gray = gray
        self.prev_kps = kps
        self.prev_descriptors = des
        
        return self.t.copy()


class VIONode(Node):
    def __init__(self):
        super().__init__('vio_node')
        
        # Declare parameters
        self.declare_parameter('imu_port', '/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00')
        self.declare_parameter('imu_baud', 115200)
        self.declare_parameter('camera_sensor_id', 0)
        self.declare_parameter('camera_width', 640)
        self.declare_parameter('camera_height', 480)
        self.declare_parameter('camera_fps', 30)
        self.declare_parameter('focal_length', 512.0)
        
        # Get parameters
        imu_port = self.get_parameter('imu_port').value
        imu_baud = self.get_parameter('imu_baud').value
        sensor_id = self.get_parameter('camera_sensor_id').value
        width = self.get_parameter('camera_width').value
        height = self.get_parameter('camera_height').value
        fps = self.get_parameter('camera_fps').value
        focal_length = self.get_parameter('focal_length').value
        
        cx = width / 2
        cy = height / 2
        
        # Create publisher
        self.publisher_ = self.create_publisher(PoseStamped, '/vio/pose', 10)
        
        # Initialize VIO components
        self.imu_reader = IMUReader(self, imu_port, imu_baud)
        self.camera = ThreadedCamera(self, sensor_id, width, height, fps)
        self.vio = MonocularVIO(self, focal_length, cx, cy)
        
        # Start hardware
        self.get_logger().info('Starting IMU and Camera...')
        self.imu_reader.start()
        self.camera.start()
        time.sleep(2)
        
        # Create timer for VIO processing
        self.timer = self.create_timer(0.033, self.vio_callback)  # ~30Hz
        
        self.frame_count = 0
        self.get_logger().info('VIO Node Started')
    
    def vio_callback(self):
        """Timer callback for VIO processing."""
        frame = self.camera.read()
        if frame is None:
            return
        
        orientation = self.imu_reader.get_orientation()
        position = self.vio.process_frame(frame, orientation)
        
        # Create and publish pose message
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'world'
        
        msg.pose.position.x = float(position[0])
        msg.pose.position.y = float(position[1])
        msg.pose.position.z = float(position[2])
        
        quat = euler_to_quaternion(orientation[0], orientation[1], orientation[2])
        msg.pose.orientation.x = float(quat[0])
        msg.pose.orientation.y = float(quat[1])
        msg.pose.orientation.z = float(quat[2])
        msg.pose.orientation.w = float(quat[3])
        
        self.publisher_.publish(msg)
        
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            self.get_logger().info(
                f'Frame {self.frame_count} | '
                f'Pos: x={position[0]:.3f} y={position[1]:.3f} z={position[2]:.3f}'
            )
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        self.get_logger().info('Shutting down VIO Node...')
        self.imu_reader.stop()
        self.camera.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = VIONode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

