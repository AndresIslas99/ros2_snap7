# Contributing to ros2_snap7

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository into a ROS 2 workspace:
   ```bash
   mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
   git clone https://github.com/your-username/ros2_snap7.git .
   ```

2. Install dependencies:
   ```bash
   pip install "python-snap7>=1.2,<2.0" pyyaml
   sudo apt install ros-humble-diagnostic-updater
   ```

3. Build:
   ```bash
   cd ~/ros2_ws
   colcon build --symlink-install
   source install/setup.bash
   ```

## Running Tests

```bash
colcon test --packages-select ros2_snap7
colcon test-result --verbose
```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code
- Use type hints where practical
- Keep lines under 100 characters

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes with descriptive messages
4. Push to your fork and open a Pull Request
5. Ensure all tests pass

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- ROS 2 distribution and OS version
- PLC model and firmware version
- Steps to reproduce the issue
- Relevant log output

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
