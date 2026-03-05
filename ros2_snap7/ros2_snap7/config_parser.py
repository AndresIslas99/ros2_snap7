"""YAML configuration parser for the ros2_snap7 driver."""

from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class VariableConfig:
    """Configuration for a single PLC variable."""
    name: str
    area: str
    db_number: int = 0
    byte_offset: int = 0
    bit_offset: int = 0
    data_type: str = 'int'


@dataclass
class ReadGroupConfig:
    """Configuration for a read polling group."""
    name: str
    poll_rate_hz: float = 1.0
    variables: List[VariableConfig] = field(default_factory=list)


@dataclass
class WriteGroupConfig:
    """Configuration for a write subscription group."""
    name: str
    variables: List[VariableConfig] = field(default_factory=list)


@dataclass
class ConnectionConfig:
    """PLC connection parameters."""
    ip: str = '192.168.0.1'
    rack: int = 0
    slot: int = 1
    port: int = 102


@dataclass
class PlcConfig:
    """Top-level PLC configuration."""
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    read_groups: List[ReadGroupConfig] = field(default_factory=list)
    write_groups: List[WriteGroupConfig] = field(default_factory=list)


def _parse_variable(var_dict: dict) -> VariableConfig:
    """Parse a single variable config dict into a VariableConfig."""
    if 'name' not in var_dict:
        raise ValueError("Variable config must include 'name'")
    return VariableConfig(
        name=var_dict['name'],
        area=var_dict.get('area', 'DB'),
        db_number=var_dict.get('db_number', 0),
        byte_offset=var_dict.get('byte_offset', 0),
        bit_offset=var_dict.get('bit_offset', 0),
        data_type=var_dict.get('data_type', 'int'),
    )


def parse_config(config_path: str) -> PlcConfig:
    """Parse a YAML configuration file into a PlcConfig.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        PlcConfig with all parsed settings.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the YAML is invalid or missing required fields.
    """
    with open(config_path, 'r') as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Config file '{config_path}' is empty or invalid YAML")

    if not isinstance(raw, dict):
        raise ValueError(f"Config file '{config_path}' must contain a YAML mapping")

    # Parse connection
    conn_dict = raw.get('connection', {})
    connection = ConnectionConfig(
        ip=conn_dict.get('ip', '192.168.0.1'),
        rack=conn_dict.get('rack', 0),
        slot=conn_dict.get('slot', 1),
        port=conn_dict.get('port', 102),
    )

    # Parse read groups
    read_groups = []
    for rg in raw.get('read_groups', []):
        if 'name' not in rg:
            raise ValueError("Each read_group must have a 'name'")
        variables = [_parse_variable(v) for v in rg.get('variables', [])]
        read_groups.append(ReadGroupConfig(
            name=rg['name'],
            poll_rate_hz=rg.get('poll_rate_hz', 1.0),
            variables=variables,
        ))

    # Parse write groups
    write_groups = []
    for wg in raw.get('write_groups', []):
        if 'name' not in wg:
            raise ValueError("Each write_group must have a 'name'")
        variables = [_parse_variable(v) for v in wg.get('variables', [])]
        write_groups.append(WriteGroupConfig(
            name=wg['name'],
            variables=variables,
        ))

    return PlcConfig(
        connection=connection,
        read_groups=read_groups,
        write_groups=write_groups,
    )
