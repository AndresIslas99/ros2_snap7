"""Main ROS 2 node for the Snap7 PLC bridge."""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from diagnostic_updater import Updater, DiagnosticStatusWrapper

from ros2_snap7_interfaces.msg import PlcData, PlcVariable, PlcState
from ros2_snap7_interfaces.srv import ReadVar, WriteVar, GetCpuInfo

from ros2_snap7.s7_client import S7Client, value_to_string
from ros2_snap7.config_parser import parse_config, ReadGroupConfig, WriteGroupConfig


class Snap7BridgeNode(Node):
    """ROS 2 node that bridges Snap7 PLC communication."""

    def __init__(self):
        super().__init__('snap7_bridge_node')

        # Declare parameters
        self.declare_parameter('config_file', '')
        self.declare_parameter('reconnect_interval_s', 5.0)
        self.declare_parameter('state_publish_rate_hz', 1.0)

        config_path = self.get_parameter('config_file').get_parameter_value().string_value
        if not config_path:
            self.get_logger().fatal('Parameter "config_file" is required')
            raise SystemExit('Missing config_file parameter')

        self._reconnect_interval = (
            self.get_parameter('reconnect_interval_s').get_parameter_value().double_value
        )
        state_rate = (
            self.get_parameter('state_publish_rate_hz').get_parameter_value().double_value
        )

        # Parse config
        self.get_logger().info(f'Loading config from: {config_path}')
        self._config = parse_config(config_path)

        # Create S7 client
        self._client = S7Client()

        # Callback group for all callbacks (reentrant for multi-threaded executor)
        self._cb_group = ReentrantCallbackGroup()

        # State publisher
        self._state_pub = self.create_publisher(PlcState, '~/state', 10)
        self._state_timer = self.create_timer(
            1.0 / state_rate, self._publish_state, callback_group=self._cb_group
        )

        # Read group publishers and timers
        self._read_publishers = {}
        for rg in self._config.read_groups:
            pub = self.create_publisher(PlcData, f'~/read/{rg.name}', 10)
            self._read_publishers[rg.name] = pub
            period = 1.0 / rg.poll_rate_hz
            self.create_timer(
                period,
                lambda rg=rg: self._read_group_callback(rg),
                callback_group=self._cb_group,
            )
            self.get_logger().info(
                f'Read group "{rg.name}": {len(rg.variables)} vars @ {rg.poll_rate_hz} Hz'
            )

        # Write group subscribers
        self._write_group_vars = {}
        for wg in self._config.write_groups:
            self._write_group_vars[wg.name] = {v.name for v in wg.variables}
            self.create_subscription(
                PlcData,
                f'~/write/{wg.name}',
                lambda msg, wg=wg: self._write_group_callback(msg, wg),
                10,
                callback_group=self._cb_group,
            )
            self.get_logger().info(
                f'Write group "{wg.name}": {len(wg.variables)} vars'
            )

        # Services
        self.create_service(
            ReadVar, '~/read_var', self._read_var_callback,
            callback_group=self._cb_group,
        )
        self.create_service(
            WriteVar, '~/write_var', self._write_var_callback,
            callback_group=self._cb_group,
        )
        self.create_service(
            GetCpuInfo, '~/get_cpu_info', self._get_cpu_info_callback,
            callback_group=self._cb_group,
        )

        # Diagnostics
        self._diag_updater = Updater(self)
        self._diag_updater.setHardwareID(
            f"S7 PLC @ {self._config.connection.ip}:{self._config.connection.port}"
        )
        self._diag_updater.add('PLC Connection', self._diagnostics_callback)

        # Reconnection timer
        self._reconnect_timer = self.create_timer(
            self._reconnect_interval,
            self._reconnect_callback,
            callback_group=self._cb_group,
        )

        # Initial connection attempt
        self._try_connect()

    def _try_connect(self) -> None:
        """Attempt initial connection to the PLC."""
        conn = self._config.connection
        try:
            self._client.connect(conn.ip, conn.rack, conn.slot, port=conn.port)
            self.get_logger().info(
                f'Connected to PLC at {conn.ip}:{conn.port} (rack={conn.rack}, slot={conn.slot})'
            )
        except Exception as e:
            self.get_logger().warn(
                f'Failed to connect to PLC at {conn.ip}: {e}. Will retry...'
            )

    def _reconnect_callback(self) -> None:
        """Periodically attempt reconnection if disconnected."""
        if self._client.connected:
            return
        try:
            self._client.reconnect()
            self.get_logger().info('Reconnected to PLC')
        except Exception as e:
            self.get_logger().debug(f'Reconnect attempt failed: {e}')

    def _publish_state(self) -> None:
        """Publish the current PLC state."""
        msg = PlcState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.connected = self._client.connected
        msg.plc_ip = self._config.connection.ip
        try:
            if self._client.connected:
                msg.cpu_state = self._client.get_cpu_state()
            else:
                msg.cpu_state = 'Disconnected'
        except Exception:
            msg.cpu_state = 'Unknown'
        msg.last_error = self._client.stats.last_error
        msg.read_count = self._client.stats.read_count
        msg.write_count = self._client.stats.write_count
        msg.error_count = self._client.stats.error_count
        self._state_pub.publish(msg)

    def _read_group_callback(self, read_group: ReadGroupConfig) -> None:
        """Timer callback to poll a read group."""
        if not self._client.connected:
            return

        msg = PlcData()
        msg.header.stamp = self.get_clock().now().to_msg()

        for var_cfg in read_group.variables:
            try:
                value = self._client.read_variable(
                    var_cfg.area, var_cfg.db_number,
                    var_cfg.byte_offset, var_cfg.bit_offset,
                    var_cfg.data_type,
                )
                plc_var = PlcVariable()
                plc_var.name = var_cfg.name
                plc_var.area = var_cfg.area
                plc_var.db_number = var_cfg.db_number
                plc_var.byte_offset = var_cfg.byte_offset
                plc_var.bit_offset = var_cfg.bit_offset
                plc_var.data_type = var_cfg.data_type
                plc_var.value_string = value_to_string(value, var_cfg.data_type)
                msg.variables.append(plc_var)
            except Exception as e:
                self.get_logger().warn(
                    f'Read error for "{var_cfg.name}": {e}'
                )
                return  # Stop reading this group on error

        pub = self._read_publishers.get(read_group.name)
        if pub:
            pub.publish(msg)

    def _write_group_callback(self, msg: PlcData, write_group: WriteGroupConfig) -> None:
        """Subscription callback to write variables to the PLC."""
        if not self._client.connected:
            self.get_logger().warn('Cannot write: not connected to PLC')
            return

        allowed_names = self._write_group_vars.get(write_group.name, set())
        var_lookup = {v.name: v for v in write_group.variables}

        for plc_var in msg.variables:
            if plc_var.name not in allowed_names:
                self.get_logger().warn(
                    f'Write rejected: "{plc_var.name}" not in group "{write_group.name}"'
                )
                continue

            var_cfg = var_lookup[plc_var.name]
            try:
                self._client.write_variable(
                    var_cfg.area, var_cfg.db_number,
                    var_cfg.byte_offset, var_cfg.bit_offset,
                    var_cfg.data_type, plc_var.value_string,
                )
            except Exception as e:
                self.get_logger().error(
                    f'Write error for "{plc_var.name}": {e}'
                )

    def _read_var_callback(self, request: ReadVar.Request,
                           response: ReadVar.Response) -> ReadVar.Response:
        """Service callback to read a single variable."""
        try:
            value = self._client.read_variable(
                request.area, request.db_number,
                request.byte_offset, request.bit_offset,
                request.data_type,
            )
            response.success = True
            response.value_string = value_to_string(value, request.data_type)
            response.message = ''
        except Exception as e:
            response.success = False
            response.value_string = ''
            response.message = str(e)
        return response

    def _write_var_callback(self, request: WriteVar.Request,
                            response: WriteVar.Response) -> WriteVar.Response:
        """Service callback to write a single variable."""
        try:
            self._client.write_variable(
                request.area, request.db_number,
                request.byte_offset, request.bit_offset,
                request.data_type, request.value_string,
            )
            response.success = True
            response.message = ''
        except Exception as e:
            response.success = False
            response.message = str(e)
        return response

    def _get_cpu_info_callback(self, request: GetCpuInfo.Request,
                               response: GetCpuInfo.Response) -> GetCpuInfo.Response:
        """Service callback to get CPU info."""
        try:
            info = self._client.get_cpu_info()
            response.success = True
            response.module_type = info['module_type']
            response.serial_number = info['serial_number']
            response.as_name = info['as_name']
            response.copyright = info['copyright']
            response.module_name = info['module_name']
            response.message = ''
        except Exception as e:
            response.success = False
            response.message = str(e)
        return response

    def _diagnostics_callback(self, stat: DiagnosticStatusWrapper):
        """Diagnostic updater callback."""
        stat.add('Connected', str(self._client.connected))
        stat.add('PLC IP', self._config.connection.ip)
        stat.add('Read Count', str(self._client.stats.read_count))
        stat.add('Write Count', str(self._client.stats.write_count))
        stat.add('Error Count', str(self._client.stats.error_count))
        stat.add('Last Error', self._client.stats.last_error or 'None')

        if self._client.connected:
            stat.summary(DiagnosticStatusWrapper.OK, 'Connected')
        else:
            stat.summary(DiagnosticStatusWrapper.ERROR, 'Disconnected')
        return stat

    def destroy_node(self):
        """Graceful shutdown: disconnect from PLC."""
        self.get_logger().info('Shutting down, disconnecting from PLC...')
        self._client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Snap7BridgeNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
