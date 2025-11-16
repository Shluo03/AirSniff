from setuptools import setup

package_name = 'wifi_monitor'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='ROS2 node to poll Wi‑Fi RSSI and publish readings (MVP)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wifi_monitor_node = wifi_monitor.wifi_monitor_node:main',
        ],
    },
)

