"""Thread-safe wrapper around the Snap7 client for S7 PLC communication."""

import struct
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

import snap7
from snap7.types import Areas


@dataclass
class S7ClientStats:
    """Counters for S7 client operations."""
    read_count: int = 0
    write_count: int = 0
    error_count: int = 0
    last_error: str = ''


# Mapping from string area names to snap7 Areas enum
_AREA_MAP = {
    'DB': Areas.DB,
    'INPUT': Areas.PE,
    'OUTPUT': Areas.PA,
    'MERKER': Areas.MK,
    'COUNTER': Areas.CT,
    'TIMER': Areas.TM,
}


def _resolve_area(area_str: str) -> Areas:
    """Resolve a string area name to a snap7 Areas enum value."""
    area_upper = area_str.upper()
    if area_upper not in _AREA_MAP:
        raise ValueError(f"Unknown area '{area_str}'. Valid: {list(_AREA_MAP.keys())}")
    return _AREA_MAP[area_upper]


def _byte_size_for_type(data_type: str) -> int:
    """Return the number of bytes to read for a given data type."""
    sizes = {
        'bool': 1,
        'byte': 1,
        'int': 2,
        'word': 2,
        'dint': 4,
        'dword': 4,
        'real': 4,
        'string': 256,
    }
    dt = data_type.lower()
    if dt not in sizes:
        raise ValueError(f"Unknown data type '{data_type}'. Valid: {list(sizes.keys())}")
    return sizes[dt]


def _decode(data: bytearray, data_type: str, bit_offset: int = 0) -> Any:
    """Decode raw bytes from the PLC into a Python value."""
    dt = data_type.lower()
    if dt == 'bool':
        return bool(data[0] & (1 << bit_offset))
    elif dt == 'byte':
        return data[0]
    elif dt == 'int':
        return struct.unpack('>h', data[:2])[0]
    elif dt == 'word':
        return struct.unpack('>H', data[:2])[0]
    elif dt == 'dint':
        return struct.unpack('>i', data[:4])[0]
    elif dt == 'dword':
        return struct.unpack('>I', data[:4])[0]
    elif dt == 'real':
        return struct.unpack('>f', data[:4])[0]
    elif dt == 'string':
        # S7 string: byte 0 = max length, byte 1 = actual length, then chars
        if len(data) < 2:
            return ''
        actual_len = data[1]
        return data[2:2 + actual_len].decode('ascii', errors='replace')
    else:
        raise ValueError(f"Unknown data type '{data_type}'")


def _encode_into(data: bytearray, value: Any, data_type: str, bit_offset: int = 0) -> bytearray:
    """Encode a Python value into a bytearray for writing to the PLC.

    For bool type, performs read-modify-write on the provided data to preserve other bits.
    """
    dt = data_type.lower()
    if dt == 'bool':
        val = bool(value) if not isinstance(value, bool) else value
        if isinstance(value, str):
            val = value.lower() in ('true', '1', 'yes')
        if val:
            data[0] |= (1 << bit_offset)
        else:
            data[0] &= ~(1 << bit_offset)
    elif dt == 'byte':
        data[0] = int(value) & 0xFF
    elif dt == 'int':
        struct.pack_into('>h', data, 0, int(value))
    elif dt == 'word':
        struct.pack_into('>H', data, 0, int(value))
    elif dt == 'dint':
        struct.pack_into('>i', data, 0, int(value))
    elif dt == 'dword':
        struct.pack_into('>I', data, 0, int(value))
    elif dt == 'real':
        struct.pack_into('>f', data, 0, float(value))
    elif dt == 'string':
        s = str(value)
        max_len = min(len(s), 254)
        data[0] = 254  # max length
        data[1] = max_len  # actual length
        for i in range(max_len):
            data[2 + i] = ord(s[i])
    else:
        raise ValueError(f"Unknown data type '{data_type}'")
    return data


def value_to_string(value: Any, data_type: str) -> str:
    """Convert a decoded PLC value to its string representation."""
    dt = data_type.lower()
    if dt == 'bool':
        return str(bool(value)).lower()
    elif dt == 'real':
        return f"{float(value):.6f}"
    else:
        return str(value)


class S7Client:
    """Thread-safe Snap7 client wrapper for S7 PLC communication."""

    def __init__(self):
        self._client = snap7.client.Client()
        self._lock = threading.Lock()
        self._connected = False
        self._ip: Optional[str] = None
        self._rack: int = 0
        self._slot: int = 0
        self._port: int = 102
        self.stats = S7ClientStats()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def ip(self) -> Optional[str]:
        return self._ip

    def connect(self, ip: str, rack: int = 0, slot: int = 1, port: int = 102) -> None:
        """Connect to the PLC. Stores params for reconnection."""
        with self._lock:
            self._ip = ip
            self._rack = rack
            self._slot = slot
            self._port = port
            try:
                self._client.connect(ip, rack, slot, tcpport=port)
                self._connected = True
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise

    def reconnect(self) -> None:
        """Reconnect using stored connection parameters."""
        if self._ip is None:
            raise RuntimeError("No previous connection parameters stored")
        with self._lock:
            try:
                self._client.disconnect()
            except Exception:
                pass
            try:
                self._client.connect(self._ip, self._rack, self._slot, tcpport=self._port)
                self._connected = True
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise

    def disconnect(self) -> None:
        """Disconnect from the PLC."""
        with self._lock:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._connected = False

    def check_connection(self) -> bool:
        """Check if the PLC connection is alive."""
        with self._lock:
            try:
                state = self._client.get_cpu_state()
                self._connected = True
                return True
            except Exception:
                self._connected = False
                return False

    def read_variable(self, area: str, db_number: int, byte_offset: int,
                      bit_offset: int, data_type: str) -> Any:
        """Read a single variable from the PLC."""
        with self._lock:
            try:
                s7_area = _resolve_area(area)
                size = _byte_size_for_type(data_type)
                raw = self._client.read_area(s7_area, db_number, byte_offset, size)
                value = _decode(bytearray(raw), data_type, bit_offset)
                self.stats.read_count += 1
                return value
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise

    def write_variable(self, area: str, db_number: int, byte_offset: int,
                       bit_offset: int, data_type: str, value: Any) -> None:
        """Write a single variable to the PLC.

        For bool type, performs read-modify-write to preserve other bits in the byte.
        """
        with self._lock:
            try:
                s7_area = _resolve_area(area)
                size = _byte_size_for_type(data_type)

                # For bool: read current byte first to preserve other bits
                if data_type.lower() == 'bool':
                    raw = bytearray(self._client.read_area(s7_area, db_number, byte_offset, 1))
                else:
                    raw = bytearray(size)

                _encode_into(raw, value, data_type, bit_offset)
                self._client.write_area(s7_area, db_number, byte_offset, raw)
                self.stats.write_count += 1
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise

    def get_cpu_info(self) -> dict:
        """Get CPU information from the PLC."""
        with self._lock:
            try:
                info = self._client.get_cpu_info()
                return {
                    'module_type': info.ModuleTypeName.decode('ascii', errors='replace').strip(),
                    'serial_number': info.SerialNumber.decode('ascii', errors='replace').strip(),
                    'as_name': info.ASName.decode('ascii', errors='replace').strip(),
                    'copyright': info.Copyright.decode('ascii', errors='replace').strip(),
                    'module_name': info.ModuleName.decode('ascii', errors='replace').strip(),
                }
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise

    def get_cpu_state(self) -> str:
        """Get the current CPU state as a string."""
        with self._lock:
            try:
                state = self._client.get_cpu_state()
                if isinstance(state, str):
                    # python-snap7 >=1.4 returns strings like 'S7CpuStatusRun'
                    str_map = {
                        'S7CpuStatusUnknown': 'Unknown',
                        'S7CpuStatusStop': 'Stop',
                        'S7CpuStatusRun': 'Run',
                    }
                    return str_map.get(state, state)
                # Older versions return integers
                int_map = {0: 'Unknown', 4: 'Stop', 8: 'Run'}
                return int_map.get(state, f'Unknown({state})')
            except Exception as e:
                self._connected = False
                self.stats.error_count += 1
                self.stats.last_error = str(e)
                raise
