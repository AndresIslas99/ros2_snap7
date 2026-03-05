"""Unit tests for S7Client encode/decode functions."""

import struct

import pytest

from ros2_snap7.s7_client import (
    _decode,
    _encode_into,
    _resolve_area,
    _byte_size_for_type,
    value_to_string,
)


class TestDecode:
    """Tests for _decode function."""

    def test_decode_bool_true(self):
        data = bytearray([0b00000100])
        assert _decode(data, 'bool', bit_offset=2) is True

    def test_decode_bool_false(self):
        data = bytearray([0b11111011])
        assert _decode(data, 'bool', bit_offset=2) is False

    def test_decode_bool_bit0(self):
        data = bytearray([0b00000001])
        assert _decode(data, 'bool', bit_offset=0) is True

    def test_decode_bool_bit7(self):
        data = bytearray([0b10000000])
        assert _decode(data, 'bool', bit_offset=7) is True

    def test_decode_byte(self):
        data = bytearray([0xAB])
        assert _decode(data, 'byte') == 0xAB

    def test_decode_byte_zero(self):
        data = bytearray([0x00])
        assert _decode(data, 'byte') == 0

    def test_decode_int_positive(self):
        data = bytearray(struct.pack('>h', 1234))
        assert _decode(data, 'int') == 1234

    def test_decode_int_negative(self):
        data = bytearray(struct.pack('>h', -5678))
        assert _decode(data, 'int') == -5678

    def test_decode_word(self):
        data = bytearray(struct.pack('>H', 50000))
        assert _decode(data, 'word') == 50000

    def test_decode_dint_positive(self):
        data = bytearray(struct.pack('>i', 100000))
        assert _decode(data, 'dint') == 100000

    def test_decode_dint_negative(self):
        data = bytearray(struct.pack('>i', -100000))
        assert _decode(data, 'dint') == -100000

    def test_decode_dword(self):
        data = bytearray(struct.pack('>I', 3000000000))
        assert _decode(data, 'dword') == 3000000000

    def test_decode_real(self):
        data = bytearray(struct.pack('>f', 3.14))
        result = _decode(data, 'real')
        assert abs(result - 3.14) < 1e-5

    def test_decode_real_negative(self):
        data = bytearray(struct.pack('>f', -273.15))
        result = _decode(data, 'real')
        assert abs(result - (-273.15)) < 0.01

    def test_decode_string(self):
        # S7 string: max_len=254, actual_len=5, "Hello"
        data = bytearray(256)
        data[0] = 254
        data[1] = 5
        data[2:7] = b'Hello'
        assert _decode(data, 'string') == 'Hello'

    def test_decode_string_empty(self):
        data = bytearray(256)
        data[0] = 254
        data[1] = 0
        assert _decode(data, 'string') == ''

    def test_decode_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown data type"):
            _decode(bytearray(4), 'unknown')


class TestEncode:
    """Tests for _encode_into function."""

    def test_encode_bool_set(self):
        data = bytearray([0b00000000])
        _encode_into(data, True, 'bool', bit_offset=3)
        assert data[0] & (1 << 3) != 0

    def test_encode_bool_clear(self):
        data = bytearray([0b11111111])
        _encode_into(data, False, 'bool', bit_offset=3)
        assert data[0] & (1 << 3) == 0

    def test_encode_bool_preserves_other_bits(self):
        data = bytearray([0b10101010])
        _encode_into(data, True, 'bool', bit_offset=0)
        assert data[0] == 0b10101011  # bit 0 set, others unchanged

    def test_encode_bool_from_string_true(self):
        data = bytearray([0x00])
        _encode_into(data, 'true', 'bool', bit_offset=0)
        assert data[0] & 1 != 0

    def test_encode_int(self):
        data = bytearray(2)
        _encode_into(data, 1234, 'int')
        assert struct.unpack('>h', data)[0] == 1234

    def test_encode_int_negative(self):
        data = bytearray(2)
        _encode_into(data, -5678, 'int')
        assert struct.unpack('>h', data)[0] == -5678

    def test_encode_real(self):
        data = bytearray(4)
        _encode_into(data, 3.14, 'real')
        result = struct.unpack('>f', data)[0]
        assert abs(result - 3.14) < 1e-5

    def test_encode_dint(self):
        data = bytearray(4)
        _encode_into(data, 100000, 'dint')
        assert struct.unpack('>i', data)[0] == 100000

    def test_encode_dword(self):
        data = bytearray(4)
        _encode_into(data, 3000000000, 'dword')
        assert struct.unpack('>I', data)[0] == 3000000000

    def test_encode_byte(self):
        data = bytearray(1)
        _encode_into(data, 0xAB, 'byte')
        assert data[0] == 0xAB

    def test_encode_word(self):
        data = bytearray(2)
        _encode_into(data, 50000, 'word')
        assert struct.unpack('>H', data)[0] == 50000

    def test_encode_string(self):
        data = bytearray(256)
        _encode_into(data, 'Hello', 'string')
        assert data[0] == 254  # max length
        assert data[1] == 5   # actual length
        assert data[2:7] == b'Hello'

    def test_encode_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown data type"):
            _encode_into(bytearray(4), 0, 'unknown')


class TestRoundTrip:
    """Parametrized round-trip encode/decode tests."""

    @pytest.mark.parametrize("data_type,value", [
        ('byte', 0),
        ('byte', 255),
        ('int', 0),
        ('int', 32767),
        ('int', -32768),
        ('word', 0),
        ('word', 65535),
        ('dint', 0),
        ('dint', 2147483647),
        ('dint', -2147483648),
        ('dword', 0),
        ('dword', 4294967295),
    ])
    def test_round_trip_integer_types(self, data_type, value):
        size = {'byte': 1, 'int': 2, 'word': 2, 'dint': 4, 'dword': 4}[data_type]
        data = bytearray(size)
        _encode_into(data, value, data_type)
        result = _decode(data, data_type)
        assert result == value

    @pytest.mark.parametrize("value", [0.0, 1.0, -1.0, 3.14, -273.15, 1e10])
    def test_round_trip_real(self, value):
        data = bytearray(4)
        _encode_into(data, value, 'real')
        result = _decode(data, 'real')
        assert abs(result - value) < abs(value) * 1e-6 + 1e-6

    @pytest.mark.parametrize("bit", range(8))
    def test_round_trip_bool(self, bit):
        for val in (True, False):
            data = bytearray(1)
            _encode_into(data, val, 'bool', bit_offset=bit)
            result = _decode(data, 'bool', bit_offset=bit)
            assert result == val


class TestResolveArea:
    """Tests for _resolve_area function."""

    def test_valid_areas(self):
        from snap7.types import Areas
        assert _resolve_area('DB') == Areas.DB
        assert _resolve_area('INPUT') == Areas.PE
        assert _resolve_area('OUTPUT') == Areas.PA
        assert _resolve_area('MERKER') == Areas.MK
        assert _resolve_area('COUNTER') == Areas.CT
        assert _resolve_area('TIMER') == Areas.TM

    def test_case_insensitive(self):
        from snap7.types import Areas
        assert _resolve_area('db') == Areas.DB
        assert _resolve_area('Db') == Areas.DB
        assert _resolve_area('input') == Areas.PE

    def test_unknown_area(self):
        with pytest.raises(ValueError, match="Unknown area"):
            _resolve_area('INVALID')


class TestByteSizeForType:
    """Tests for _byte_size_for_type function."""

    def test_all_types(self):
        assert _byte_size_for_type('bool') == 1
        assert _byte_size_for_type('byte') == 1
        assert _byte_size_for_type('int') == 2
        assert _byte_size_for_type('word') == 2
        assert _byte_size_for_type('dint') == 4
        assert _byte_size_for_type('dword') == 4
        assert _byte_size_for_type('real') == 4
        assert _byte_size_for_type('string') == 256

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown data type"):
            _byte_size_for_type('float64')


class TestValueToString:
    """Tests for value_to_string function."""

    def test_bool(self):
        assert value_to_string(True, 'bool') == 'true'
        assert value_to_string(False, 'bool') == 'false'

    def test_real(self):
        result = value_to_string(3.14, 'real')
        assert result.startswith('3.14')

    def test_int(self):
        assert value_to_string(42, 'int') == '42'

    def test_string(self):
        assert value_to_string('hello', 'string') == 'hello'
