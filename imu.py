from pymavlink import mavutil

PORT = "/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00"
BAUD = 115200

master = mavutil.mavlink_connection(PORT, baud=BAUD)

print("Waiting for heartbeat...")
master.wait_heartbeat()
print(f"Heartbeat from system {master.target_system}, component {master.target_component}")

# Ask FC to send raw sensor data (includes RAW_IMU on ArduPilot)
master.mav.request_data_stream_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,  # raw sensors group
    50,    # rate in Hz
    1      # start
)

print("Reading RAW_IMU...")

while True:
    msg = master.recv_match(type="RAW_IMU", blocking=True, timeout=2)
    if msg is None:
        print("No RAW_IMU received (timeout).")
        continue

    # Raw accelerometer (milli-g or sensor units, see ArduPilot docs)
    ax, ay, az = msg.xacc, msg.yacc, msg.zacc
    # Raw gyro
    gx, gy, gz = msg.xgyro, msg.ygyro, msg.zgyro

    print(f"acc=({ax}, {ay}, {az}), gyro=({gx}, {gy}, {gz})")
