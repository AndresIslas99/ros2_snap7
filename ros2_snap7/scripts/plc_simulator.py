#!/usr/bin/env python3
"""Virtual PLC simulator using Snap7 server.

Registers three data blocks matching the default plc_config.yaml:
  DB1 (sensors)  - 16 bytes: temperature(real), pressure(real), flow_rate(real), level(int), valve(bool)
  DB2 (status)   - 12 bytes: system_running(bool), error_code(dint), operating_mode(byte), production_counter(dword)
  DB3 (commands) - 12 bytes: setpoint_temp(real), setpoint_pressure(real), start/stop(bool), recipe_id(int)

Sensor values drift periodically to simulate a live process.

Usage:
    python3 plc_simulator.py [--port 1102]
"""

import argparse
import math
import signal
import struct
import sys
import time

import snap7.server
from snap7.types import srvAreaDB, WordLen, wordlen_to_ctypes


def create_buffer(size):
    """Create a ctypes buffer compatible with snap7 server register_area."""
    return (wordlen_to_ctypes[WordLen.Byte.value] * size)()


def pack_real(buf, offset, value):
    """Write a 32-bit float (big-endian) into buffer at offset."""
    struct.pack_into('>f', buf, offset, value)


def pack_int16(buf, offset, value):
    """Write a 16-bit signed int (big-endian) into buffer at offset."""
    struct.pack_into('>h', buf, offset, value)


def pack_dint(buf, offset, value):
    """Write a 32-bit signed int (big-endian) into buffer at offset."""
    struct.pack_into('>i', buf, offset, value)


def pack_dword(buf, offset, value):
    """Write a 32-bit unsigned int (big-endian) into buffer at offset."""
    struct.pack_into('>I', buf, offset, value)


def pack_byte(buf, offset, value):
    """Write a single byte into buffer at offset."""
    buf[offset] = value & 0xFF


def pack_bool(buf, offset, bit, value):
    """Set or clear a single bit in buffer."""
    if value:
        buf[offset] = buf[offset] | (1 << bit)
    else:
        buf[offset] = buf[offset] & ~(1 << bit)


def populate_initial_values(db1, db2, db3):
    """Set realistic initial values in all data blocks."""
    # DB1 - Sensors
    pack_real(db1, 0, 25.5)      # temperature_reactor_1 (C)
    pack_real(db1, 4, 1.013)     # pressure_reactor_1 (bar)
    pack_real(db1, 8, 42.0)      # flow_rate_inlet (L/min)
    pack_int16(db1, 12, 750)     # level_tank_1 (mm)
    pack_bool(db1, 14, 0, True)  # valve_open_sensor

    # DB2 - Status
    pack_bool(db2, 0, 0, True)   # system_running
    pack_dint(db2, 2, 0)         # error_code (no error)
    pack_byte(db2, 6, 1)         # operating_mode (1=auto)
    pack_dword(db2, 8, 1000)     # production_counter

    # DB3 - Commands (initial setpoints)
    pack_real(db3, 0, 25.0)      # setpoint_temperature
    pack_real(db3, 4, 1.0)       # setpoint_pressure
    pack_bool(db3, 8, 0, False)  # start_command
    pack_bool(db3, 8, 1, False)  # stop_command
    pack_int16(db3, 10, 1)       # recipe_id


def update_sensor_values(db1, db2, tick):
    """Simulate sensor drift based on tick counter."""
    t = tick * 0.5  # 0.5s per tick

    # Temperature: 25.5 +/- 2 degrees sinusoidal
    temperature = 25.5 + 2.0 * math.sin(t * 0.1)
    pack_real(db1, 0, temperature)

    # Pressure: 1.013 +/- 0.05 bar
    pressure = 1.013 + 0.05 * math.sin(t * 0.15 + 1.0)
    pack_real(db1, 4, pressure)

    # Flow rate: 42.0 +/- 5 L/min
    flow = 42.0 + 5.0 * math.sin(t * 0.08 + 2.0)
    pack_real(db1, 8, flow)

    # Level: 750 +/- 50 mm
    level = int(750 + 50 * math.sin(t * 0.05 + 0.5))
    pack_int16(db1, 12, level)

    # Production counter increments
    current_counter = struct.unpack_from('>I', db2, 8)[0]
    pack_dword(db2, 8, current_counter + 1)


def main():
    parser = argparse.ArgumentParser(description='ros2_snap7 PLC Simulator')
    parser.add_argument('--port', type=int, default=1102,
                        help='TCP port to listen on (default: 1102)')
    args = parser.parse_args()

    server = snap7.server.Server(log=False)

    # Create data block buffers matching plc_config.yaml
    db1 = create_buffer(16)   # sensors
    db2 = create_buffer(12)   # status
    db3 = create_buffer(12)   # commands

    # Set initial values
    populate_initial_values(db1, db2, db3)

    # Register areas
    server.register_area(srvAreaDB, 1, db1)
    server.register_area(srvAreaDB, 2, db2)
    server.register_area(srvAreaDB, 3, db3)

    # Start server
    server.start(tcpport=args.port)
    print(f"Server started on port {args.port}")
    print(f"  DB1 (sensors):  16 bytes - temperature, pressure, flow, level, valve")
    print(f"  DB2 (status):   12 bytes - running, error_code, mode, counter")
    print(f"  DB3 (commands): 12 bytes - setpoint_temp, setpoint_pressure, start/stop, recipe")
    print(f"Press Ctrl+C to stop.")

    # Handle SIGINT/SIGTERM for clean shutdown
    shutdown = False

    def signal_handler(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    tick = 0
    try:
        while not shutdown:
            time.sleep(0.5)
            tick += 1
            update_sensor_values(db1, db2, tick)

            # Print status every 10 ticks (5 seconds)
            if tick % 10 == 0:
                temp = struct.unpack_from('>f', db1, 0)[0]
                pres = struct.unpack_from('>f', db1, 4)[0]
                flow = struct.unpack_from('>f', db1, 8)[0]
                level = struct.unpack_from('>h', db1, 12)[0]
                counter = struct.unpack_from('>I', db2, 8)[0]
                print(f"  [tick {tick}] temp={temp:.1f}C  pres={pres:.3f}bar  "
                      f"flow={flow:.1f}L/min  level={level}mm  counter={counter}")

            # Check for events
            while True:
                event = server.pick_event()
                if event is None:
                    break
                text = server.event_text(event)
                print(f"  Event: {text}")
    finally:
        print("\nStopping server...")
        server.stop()
        server.destroy()
        print("Server stopped.")


if __name__ == '__main__':
    main()
