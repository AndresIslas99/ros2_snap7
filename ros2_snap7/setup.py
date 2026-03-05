from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ros2_snap7'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'scripts'),
            glob(os.path.join('scripts', '*.py'))),
    ],
    install_requires=[
        'setuptools',
        'python-snap7>=1.2,<2.0',
        'pyyaml',
    ],
    zip_safe=True,
    maintainer='Andres',
    maintainer_email='andresislas2107@gmail.com',
    description='ROS 2 driver for Siemens S7 PLCs using the Snap7 library',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'snap7_bridge_node = ros2_snap7.snap7_bridge_node:main',
        ],
    },
)
