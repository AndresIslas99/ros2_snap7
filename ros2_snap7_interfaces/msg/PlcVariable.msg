# A single PLC variable read or write value

# Variable name (from config, e.g., "temperature_sensor_1")
string name

# S7 area: DB, INPUT, OUTPUT, MERKER, COUNTER, TIMER
string area

# Data block number (only relevant for area=DB)
uint16 db_number

# Byte offset within the area
uint32 byte_offset

# Bit offset within the byte (0-7, relevant for Bool type)
uint8 bit_offset

# Data type: bool, byte, int, word, dint, dword, real, string
string data_type

# Value as a string representation
string value_string
