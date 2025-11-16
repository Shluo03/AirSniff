from setuptools import setup
import os
from glob import glob

package_name = 'fc_imu_node'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='ROS 2 node for reading IMU data from flight controller via MAVLink',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fc_imu_node = fc_imu_node.fc_imu_node:main',
        ],
    },
)
