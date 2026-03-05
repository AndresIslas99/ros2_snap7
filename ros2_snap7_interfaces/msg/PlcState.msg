# PLC connection state and diagnostics

std_msgs/Header header

# Whether the driver is currently connected to the PLC
bool connected

# PLC IP address
string plc_ip

# CPU state (e.g., "Run", "Stop", "Unknown")
string cpu_state

# Last error message (empty if no error)
string last_error

# Cumulative read operation count
uint64 read_count

# Cumulative write operation count
uint64 write_count

# Cumulative error count
uint64 error_count
