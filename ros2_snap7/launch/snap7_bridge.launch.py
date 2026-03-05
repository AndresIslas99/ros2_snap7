"""Launch file for the snap7_bridge_node."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('ros2_snap7')
    default_config = os.path.join(pkg_share, 'config', 'plc_config.yaml')

    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=default_config,
        description='Path to the PLC configuration YAML file',
    )

    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Namespace for the snap7_bridge_node',
    )

    snap7_node = Node(
        package='ros2_snap7',
        executable='snap7_bridge_node',
        name='snap7_bridge_node',
        namespace=LaunchConfiguration('namespace'),
        parameters=[{
            'config_file': LaunchConfiguration('config_file'),
        }],
        output='screen',
    )

    return LaunchDescription([
        config_file_arg,
        namespace_arg,
        snap7_node,
    ])
