<!-- POSTING INSTRUCTIONS
Post to: https://discourse.ros.org/c/ros-projects/16
Title:   [RFC] ros2_snap7 -- ROS 2 Driver for Siemens S7 PLCs (Snap7/PUT-GET)
Tags:    ros2, driver, industrial, snap7, plc
Copy everything below this comment block as the post body.
-->

# RFC: ros2_snap7 -- ROS 2 Driver for Siemens S7 PLCs

## Summary

`ros2_snap7` is a ROS 2 package that provides a driver for Siemens S7 PLCs (S7-300, S7-1200, S7-1500) using the open-source [Snap7](http://snap7.sourceforge.net/) library via the PUT/GET communication protocol.

## Motivation

Many industrial automation and robotics applications require communication with Siemens PLCs. Currently, there is no well-maintained, open-source ROS 2 driver for this purpose. Existing solutions are often ad-hoc, tightly coupled to specific projects, or rely on proprietary protocols.

This package aims to provide a reusable, configurable, and production-ready ROS 2 driver for Siemens S7 PLCs.

## Design

### Architecture

The package consists of two ROS 2 packages:

1. **`ros2_snap7_interfaces`** -- Custom message and service definitions
2. **`ros2_snap7`** -- Python node with a thread-safe Snap7 wrapper

### Key Features

- **YAML-based configuration** for PLC connection and variable mapping
- **Configurable read groups** with independent polling rates
- **Write groups** with variable-name validation
- **Auto-reconnection** on connection loss
- **Thread-safe** S7 client with `ReentrantCallbackGroup` and `MultiThreadedExecutor`
- **Diagnostics** integration via `diagnostic_updater`
- **Service interface** for on-demand reads/writes

### Supported Data Types

Bool, Byte, Int (16-bit signed), Word (16-bit unsigned), DInt (32-bit signed), DWord (32-bit unsigned), Real (32-bit float), String (S7 format, 254 chars max).

### PLC Compatibility

- S7-300: Full support
- S7-1200: Requires PUT/GET enabled in TIA Portal
- S7-1500: Requires PUT/GET enabled in TIA Portal

## Limitations

- Uses PUT/GET protocol (not OPC UA or PROFINET)
- Single PLC connection per node instance (run multiple nodes for multiple PLCs)
- Python-based (not real-time; suitable for supervisory/monitoring use cases)
- String type limited to 254 characters (S7 string format)

## Questions for the Community

1. Would OPC UA support be preferred over PUT/GET for newer PLCs?
2. Interest in a C++ implementation for real-time use cases?
3. Should we support S7-400 or S7-200 (via different Snap7 connection types)?
4. Are there naming conventions or topic structures preferred by the ROS industrial community?

## References

- [Snap7 Library](http://snap7.sourceforge.net/)
- [python-snap7](https://github.com/gijzelaerr/python-snap7)
- [ROS 2 Humble Documentation](https://docs.ros.org/en/humble/)

## Feedback

Please share your thoughts, suggestions, and use cases. All feedback is welcome!
