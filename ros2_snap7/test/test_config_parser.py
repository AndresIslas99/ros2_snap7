"""Unit tests for the configuration parser."""

import os
import tempfile

import pytest

from ros2_snap7.config_parser import parse_config


def _write_temp_yaml(content: str) -> str:
    """Write content to a temporary YAML file and return its path."""
    fd, path = tempfile.mkstemp(suffix='.yaml')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


class TestParseConfig:
    """Tests for parse_config function."""

    def test_minimal_config(self):
        path = _write_temp_yaml("""
connection:
  ip: "10.0.0.1"
  rack: 0
  slot: 2
""")
        try:
            config = parse_config(path)
            assert config.connection.ip == '10.0.0.1'
            assert config.connection.rack == 0
            assert config.connection.slot == 2
            assert config.read_groups == []
            assert config.write_groups == []
        finally:
            os.unlink(path)

    def test_defaults(self):
        path = _write_temp_yaml("connection: {}")
        try:
            config = parse_config(path)
            assert config.connection.ip == '192.168.0.1'
            assert config.connection.rack == 0
            assert config.connection.slot == 1
        finally:
            os.unlink(path)

    def test_read_groups(self):
        path = _write_temp_yaml("""
connection:
  ip: "192.168.1.10"
read_groups:
  - name: sensors
    poll_rate_hz: 10.0
    variables:
      - name: temp
        area: DB
        db_number: 1
        byte_offset: 0
        data_type: real
      - name: pressure
        area: DB
        db_number: 1
        byte_offset: 4
        data_type: real
""")
        try:
            config = parse_config(path)
            assert len(config.read_groups) == 1
            rg = config.read_groups[0]
            assert rg.name == 'sensors'
            assert rg.poll_rate_hz == 10.0
            assert len(rg.variables) == 2
            assert rg.variables[0].name == 'temp'
            assert rg.variables[0].data_type == 'real'
            assert rg.variables[1].name == 'pressure'
        finally:
            os.unlink(path)

    def test_write_groups(self):
        path = _write_temp_yaml("""
connection:
  ip: "192.168.1.10"
write_groups:
  - name: commands
    variables:
      - name: setpoint
        area: DB
        db_number: 3
        byte_offset: 0
        data_type: real
""")
        try:
            config = parse_config(path)
            assert len(config.write_groups) == 1
            wg = config.write_groups[0]
            assert wg.name == 'commands'
            assert len(wg.variables) == 1
            assert wg.variables[0].name == 'setpoint'
        finally:
            os.unlink(path)

    def test_variable_defaults(self):
        path = _write_temp_yaml("""
connection: {}
read_groups:
  - name: test
    variables:
      - name: myvar
""")
        try:
            config = parse_config(path)
            var = config.read_groups[0].variables[0]
            assert var.area == 'DB'
            assert var.db_number == 0
            assert var.byte_offset == 0
            assert var.bit_offset == 0
            assert var.data_type == 'int'
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_config('/nonexistent/path/config.yaml')

    def test_empty_yaml(self):
        path = _write_temp_yaml("")
        try:
            with pytest.raises(ValueError, match="empty or invalid"):
                parse_config(path)
        finally:
            os.unlink(path)

    def test_invalid_yaml_structure(self):
        path = _write_temp_yaml("- just\n- a\n- list")
        try:
            with pytest.raises(ValueError, match="must contain a YAML mapping"):
                parse_config(path)
        finally:
            os.unlink(path)

    def test_read_group_missing_name(self):
        path = _write_temp_yaml("""
connection: {}
read_groups:
  - poll_rate_hz: 1.0
    variables: []
""")
        try:
            with pytest.raises(ValueError, match="must have a 'name'"):
                parse_config(path)
        finally:
            os.unlink(path)

    def test_write_group_missing_name(self):
        path = _write_temp_yaml("""
connection: {}
write_groups:
  - variables: []
""")
        try:
            with pytest.raises(ValueError, match="must have a 'name'"):
                parse_config(path)
        finally:
            os.unlink(path)

    def test_variable_missing_name(self):
        path = _write_temp_yaml("""
connection: {}
read_groups:
  - name: test
    variables:
      - area: DB
        db_number: 1
""")
        try:
            with pytest.raises(ValueError, match="must include 'name'"):
                parse_config(path)
        finally:
            os.unlink(path)
