#!/usr/bin/env python3
"""
debug_flipper.py
----------------
Interactive serial diagnostic for the Flipper Zero CLI.
Run this directly and watch what the Flipper actually responds.

Usage:
    python debug_flipper.py
    python debug_flipper.py COM4          # override port
    python debug_flipper.py COM3 /ext/infrared/Westinghouse.ir
"""

import sys
import time
import serial

try:
    import config
    _default_port = config.FLIPPER_PORT
except ImportError:
    import platform
    _default_port = 'COM3' if platform.system() == 'Windows' else '/dev/ttyACM0'

PORT = sys.argv[1] if len(sys.argv) > 1 else _default_port
BAUD = 115200
IR_FILE = sys.argv[2] if len(sys.argv) > 2 else '/ext/infrared/Westinghouse.ir'


def read_until_quiet(ser, timeout: float = 2.0) -> str:
    """Read until no new bytes arrive for `timeout` seconds."""
    buf = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            deadline = time.time() + timeout  # reset on new data
    return buf.decode('utf-8', errors='replace')


print(f'Opening {PORT} at {BAUD} baud...')
with serial.Serial(PORT, BAUD, timeout=5) as ser:
    time.sleep(0.5)
    ser.reset_input_buffer()

    # ── Step 1: Wake the CLI ──────────────────────────────────────────────────
    print('\n[1] Sending bare newline to wake CLI...')
    ser.write(b'\r\n')
    response = read_until_quiet(ser, timeout=1.5)
    print(f'    Flipper says: {repr(response)}')

    # ── Step 2: Send the IR transmit command ──────────────────────────────────
    cmd = f'ir tx {IR_FILE}\r\n'
    print(f'\n[2] Sending command: {cmd.strip()!r}')
    ser.write(cmd.encode('utf-8'))
    response = read_until_quiet(ser, timeout=3.0)
    print(f'    Flipper says: {repr(response)}')

    # ── Step 3: Read the IR file content ─────────────────────────────────────
    read_cmd = f'storage read {IR_FILE}\r\n'
    print(f'\n[3] Reading IR file contents...')
    print(f'    Sending: {read_cmd.strip()!r}')
    ser.write(read_cmd.encode('utf-8'))
    response = read_until_quiet(ser, timeout=3.0)
    print(f'    Flipper says:\n{response}')

print('\nDone.')
