from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00',
            description='Serial port path to the flight controller'
        ),
        DeclareLaunchArgument(
            'baud',
            default_value='115200',
            description='Serial baud rate'
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='imu_link',
            description='Frame ID for the IMU messages'
        ),
        DeclareLaunchArgument(
            'publish_rate',
            default_value='200.0',
            description='ROS 2 publish rate in Hz'
        ),
        DeclareLaunchArgument(
            'data_stream_rate',
            default_value='50',
            description='MAVLink data stream rate in Hz'
        ),
        Node(
            package='fc_imu_node',
            executable='fc_imu_node',
            name='fc_imu_node',
            parameters=[{
                'port': LaunchConfiguration('port'),
                'baud': LaunchConfiguration('baud'),
                'frame_id': LaunchConfiguration('frame_id'),
                'publish_rate': LaunchConfiguration('publish_rate'),
                'data_stream_rate': LaunchConfiguration('data_stream_rate'),
            }],
            output='screen'
        )
    ])

