from setuptools import setup
import os
from glob import glob

package_name = 'wifi_scanner_node'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='your@email.com',
    description='WiFi RSSI scanner for RF heatmap generation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wifi_scanner = wifi_scanner_node.wifi_scanner:main',
        ],
    },
)

