#!/usr/bin/env python3
"""Generate demo screenshots for the README using Chrome headless."""

import os
import subprocess
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(REPO_DIR, 'docs', 'images')

CSS = """
body {
    margin: 0;
    padding: 40px;
    background: #1a1a2e;
    font-family: 'Ubuntu Mono', 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.5;
}
.terminal {
    background: #0d1117;
    border-radius: 10px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    overflow: hidden;
    max-width: 720px;
}
.titlebar {
    background: #161b22;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.dot { width: 12px; height: 12px; border-radius: 50%; }
.dot-red { background: #ff5f57; }
.dot-yellow { background: #febc2e; }
.dot-green { background: #28c840; }
.title {
    color: #7d8590;
    font-size: 13px;
    margin-left: 8px;
    font-family: 'Ubuntu Mono', monospace;
}
.content {
    padding: 16px 20px;
    color: #c9d1d9;
    white-space: pre;
}
.prompt { color: #58a6ff; }
.info { color: #3fb950; }
.warn { color: #d29922; }
.cyan { color: #79c0ff; }
.dim { color: #7d8590; }
.bold { font-weight: bold; }
"""

TEMPLATES = {
    'demo_simulator.png': {
        'title': 'PLC Simulator',
        'width': 780,
        'height': 470,
        'content': (
            '<span class="prompt">$</span> python3 scripts/plc_simulator.py\n'
            '<span class="info">[PLC Simulator]</span> Starting Snap7 server on 0.0.0.0:1102\n'
            '<span class="info">[PLC Simulator]</span> Server started on port 1102\n'
            '<span class="dim">  DB1 (sensors):  16 bytes - temperature, pressure, flow, level, valve</span>\n'
            '<span class="dim">  DB2 (status):   12 bytes - running, error_code, mode, counter</span>\n'
            '<span class="dim">  DB3 (commands): 12 bytes - setpoint_temp, setpoint_pressure, start/stop, recipe</span>\n'
            '<span class="dim">  Press Ctrl+C to stop.</span>\n'
            '\n'
            '<span class="cyan">  [tick 10]</span> temp=<span class="bold">23.4</span>C  pres=<span class="bold">1.013</span>bar  flow=<span class="bold">42.7</span>L/min  level=<span class="bold">850</span>mm  counter=<span class="bold">10</span>\n'
            '<span class="cyan">  [tick 20]</span> temp=<span class="bold">24.1</span>C  pres=<span class="bold">1.027</span>bar  flow=<span class="bold">43.2</span>L/min  level=<span class="bold">852</span>mm  counter=<span class="bold">20</span>\n'
            '<span class="cyan">  [tick 30]</span> temp=<span class="bold">23.8</span>C  pres=<span class="bold">1.005</span>bar  flow=<span class="bold">41.9</span>L/min  level=<span class="bold">848</span>mm  counter=<span class="bold">30</span>\n'
            '<span class="cyan">  [tick 40]</span> temp=<span class="bold">24.5</span>C  pres=<span class="bold">1.031</span>bar  flow=<span class="bold">44.1</span>L/min  level=<span class="bold">855</span>mm  counter=<span class="bold">40</span>'
        ),
    },
    'demo_node.png': {
        'title': 'ROS 2 Bridge Node',
        'width': 780,
        'height': 400,
        'content': (
            '<span class="prompt">$</span> ros2 launch ros2_snap7 snap7_bridge.launch.py\n'
            '<span class="dim">[INFO] [launch]: All log files can be found below /tmp/.ros/log</span>\n'
            '<span class="dim">[INFO] [launch]: Default logging verbosity is set to INFO</span>\n'
            '<span class="info">[snap7_bridge_node]</span> Loading config from: /ros2_ws/src/ros2_snap7/config/plc_config.yaml\n'
            '<span class="info">[snap7_bridge_node]</span> Read group "<span class="cyan">sensors</span>": <span class="bold">5</span> vars @ <span class="bold">2.0</span> Hz\n'
            '<span class="info">[snap7_bridge_node]</span> Read group "<span class="cyan">status</span>": <span class="bold">4</span> vars @ <span class="bold">1.0</span> Hz\n'
            '<span class="info">[snap7_bridge_node]</span> Write group "<span class="cyan">commands</span>": <span class="bold">4</span> vars\n'
            '<span class="info">[snap7_bridge_node]</span> Connected to PLC at <span class="cyan">127.0.0.1:1102</span> (rack=0, slot=1)\n'
            '\n'
            '<span class="dim">[INFO] [snap7_bridge_node]: Diagnostics: PLC Connection - OK</span>'
        ),
    },
    'demo_topic_echo.png': {
        'title': 'Topic Monitor',
        'width': 780,
        'height': 680,
        'content': (
            '<span class="prompt">$</span> ros2 topic echo /snap7_bridge_node/read/sensors\n'
            '<span class="dim">---</span>\n'
            'header:\n'
            '  stamp:\n'
            '    sec: <span class="cyan">1709654321</span>\n'
            '    nanosec: <span class="cyan">456789012</span>\n'
            '  frame_id: <span class="dim">\'\'</span>\n'
            'variables:\n'
            '  - name: <span class="cyan">temperature</span>\n'
            '    area: <span class="dim">DB</span>\n'
            '    db_number: <span class="cyan">1</span>\n'
            '    byte_offset: <span class="cyan">0</span>\n'
            '    bit_offset: <span class="cyan">0</span>\n'
            '    data_type: <span class="dim">real</span>\n'
            '    value_string: <span class="info">\'23.4\'</span>\n'
            '  - name: <span class="cyan">pressure</span>\n'
            '    area: <span class="dim">DB</span>\n'
            '    db_number: <span class="cyan">1</span>\n'
            '    byte_offset: <span class="cyan">4</span>\n'
            '    bit_offset: <span class="cyan">0</span>\n'
            '    data_type: <span class="dim">real</span>\n'
            '    value_string: <span class="info">\'1.013\'</span>\n'
            '<span class="dim">---</span>'
        ),
    },
    'demo_service_call.png': {
        'title': 'Service Calls',
        'width': 780,
        'height': 630,
        'content': (
            '<span class="dim"># Write a setpoint to the PLC</span>\n'
            '<span class="prompt">$</span> ros2 service call /snap7_bridge_node/write_var ros2_snap7_interfaces/srv/WriteVar \\\n'
            '    <span class="dim">"{area: DB, db_number: 3, byte_offset: 0, bit_offset: 0, data_type: real, value_string: \'75.0\'}"</span>\n'
            '\n'
            'requester: making request: ros2_snap7_interfaces.srv.WriteVar_Request(...)\n'
            '\n'
            'response:\n'
            'ros2_snap7_interfaces.srv.WriteVar_Response(\n'
            '    success=<span class="info">True</span>,\n'
            '    message=<span class="dim">\'\'</span>)\n'
            '\n'
            '<span class="dim"># Read it back</span>\n'
            '<span class="prompt">$</span> ros2 service call /snap7_bridge_node/read_var ros2_snap7_interfaces/srv/ReadVar \\\n'
            '    <span class="dim">"{area: DB, db_number: 3, byte_offset: 0, bit_offset: 0, data_type: real}"</span>\n'
            '\n'
            'response:\n'
            'ros2_snap7_interfaces.srv.ReadVar_Response(\n'
            '    success=<span class="info">True</span>,\n'
            '    value_string=<span class="cyan">\'75.0\'</span>,\n'
            '    message=<span class="dim">\'\'</span>)'
        ),
    },
}


def generate_html(title, content):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="terminal">
  <div class="titlebar">
    <div class="dot dot-red"></div>
    <div class="dot dot-yellow"></div>
    <div class="dot dot-green"></div>
    <span class="title">{title}</span>
  </div>
  <div class="content">{content}</div>
</div>
</body></html>"""


def render_screenshot(html_content, output_path, width, height):
    with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False) as f:
        f.write(html_content)
        tmp_path = f.name

    try:
        cmd = [
            'google-chrome-stable',
            '--headless=new',
            f'--screenshot={output_path}',
            f'--window-size={width},{height}',
            '--hide-scrollbars',
            '--disable-gpu',
            '--no-sandbox',
            f'file://{tmp_path}',
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    finally:
        os.unlink(tmp_path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename, spec in TEMPLATES.items():
        output_path = os.path.join(OUTPUT_DIR, filename)
        html = generate_html(spec['title'], spec['content'])
        render_screenshot(html, output_path, spec['width'], spec['height'])
        size = os.path.getsize(output_path)
        print(f"  {filename}: {size:,} bytes")

    print(f"\nAll screenshots saved to {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
