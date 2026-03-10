"""
flipper_serial.py
-----------------
Sends IR signals via a Flipper Zero connected over USB serial.

The Flipper Zero CLI does NOT support 'ir tx <filepath>'. Instead we must:
  1. Read the .ir file content from the Flipper SD card via 'storage read'
  2. Parse the signal data (parsed protocol or raw timing)
  3. Build and send the correct 'ir tx' CLI command

Supported .ir file signal types:
  - type: parsed  → ir tx <Protocol> <Address> <Command>
  - type: raw     → ir tx RAW F:<freq> DC:<duty_cycle%> <sample0> <sample1>...
"""

import logging
import time
from typing import Optional

import serial

logger = logging.getLogger(__name__)

_WAKE_DELAY   = 1.0   # seconds after sending bare newline
_READ_TIMEOUT = 2.0   # seconds of silence before stop reading
_TX_WAIT      = 1.0   # seconds to wait after sending ir tx command


# ── Serial I/O helpers ────────────────────────────────────────────────────────

def _read_until_quiet(ser: serial.Serial, timeout: float = _READ_TIMEOUT) -> str:
    """Read until no new bytes arrive for `timeout` seconds."""
    buf = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            deadline = time.time() + timeout
    return buf.decode('utf-8', errors='replace')


def _wake_cli(ser: serial.Serial) -> None:
    """Send a bare newline to ensure the Flipper CLI is responsive."""
    ser.reset_input_buffer()
    ser.write(b'\r\n')
    time.sleep(_WAKE_DELAY)
    ser.reset_input_buffer()


def _send_cmd(ser: serial.Serial, cmd: str, wait: float = _READ_TIMEOUT) -> str:
    """Send a CLI command and return the response text."""
    ser.write(f'{cmd}\r\n'.encode('utf-8'))
    return _read_until_quiet(ser, timeout=wait)


# ── .ir file parsing ──────────────────────────────────────────────────────────

def _parse_ir_file(content: str, signal_name: Optional[str]) -> dict:
    """
    Parse the first matching signal from .ir file text content.

    Args:
        content:     Raw text of the .ir file.
        signal_name: If provided, find the signal with this name.
                     If None, use the first signal in the file.

    Returns a dict with at minimum {'type': 'parsed'|'raw'} plus the
    fields needed to build the ir tx command.

    Raises ValueError if no matching signal is found.
    """
    # Split file into per-signal blocks (each starts with 'name:').
    # Everything before the first 'name:' line (Size:, Filetype:, Version:,
    # the storage-read echo, etc.) is preamble and must be ignored.
    blocks = []
    current = None  # type: Optional[dict]
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if key == 'name':
                if current is not None:
                    blocks.append(current)
                current = {'name': value}
            elif current is not None:
                # Only collect fields once we're inside a signal block.
                current[key] = value
            # else: pre-signal header line (Size, Filetype, Version, etc.) — skip
    if current is not None:
        blocks.append(current)

    if not blocks:
        raise ValueError('No signals found in .ir file')

    if signal_name is None:
        signal = blocks[0]
        logger.debug('Using first signal: %r', signal.get('name'))
    else:
        matches = [b for b in blocks if b.get('name', '').lower() == signal_name.lower()]
        if not matches:
            available = [b.get('name', '?') for b in blocks]
            raise ValueError(
                f'Signal {signal_name!r} not found in file. '
                f'Available: {available}'
            )
        signal = matches[0]

    sig_type = signal.get('type', '').lower()
    if sig_type not in ('parsed', 'raw'):
        raise ValueError(f'Unknown signal type: {sig_type!r}')

    logger.debug('Parsed signal: %s', signal)
    return signal


def _build_tx_command(signal: dict) -> str:
    """
    Build the Flipper CLI 'ir tx ...' command string from a parsed signal dict.
    """
    sig_type = signal['type'].lower()

    if sig_type == 'parsed':
        protocol = signal['protocol']
        # Address/command are stored as space-separated bytes e.g. "04 00 00 00".
        # The CLI wants the first byte as a hex value, e.g. "04".
        address  = signal['address'].split()[0]
        command  = signal['command'].split()[0]
        return f'ir tx {protocol} {address} {command}'

    if sig_type == 'raw':
        frequency  = signal['frequency']
        duty_float = float(signal.get('duty_cycle', '0.33'))
        duty_pct   = max(1, min(100, round(duty_float * 100)))
        data       = signal['data']
        # CLI limit: max 512 samples
        samples    = data.split()
        if len(samples) > 512:
            logger.warning(
                'Raw signal has %d samples; truncating to 512 (CLI limit)',
                len(samples),
            )
            data = ' '.join(samples[:512])
        return f'ir tx RAW F:{frequency} DC:{duty_pct} {data}'

    raise ValueError(f'Unhandled signal type: {sig_type!r}')


# ── Public API ────────────────────────────────────────────────────────────────

def send_ir_command(
    ir_file_path: str,
    port: str,
    baud: int,
    signal_name: Optional[str] = None,
) -> bool:
    """
    Transmit an IR signal stored in a .ir file on the Flipper Zero SD card.

    Args:
        ir_file_path: Absolute SD-card path, e.g. '/ext/infrared/tv_power.ir'
        port:         Serial port ('COM3' on Windows, '/dev/ttyACM0' on Linux)
        baud:         Baud rate (Flipper default: 115200)
        signal_name:  Name of the signal within the file to send.
                      Pass None to use the first signal in the file.

    Returns True on success, False if any step fails.
    """
    try:
        with serial.Serial(port, baud, timeout=10) as ser:
            _wake_cli(ser)

            # Step 1: Read the .ir file from the Flipper SD card.
            logger.debug('Reading IR file: %s', ir_file_path)
            raw = _send_cmd(ser, f'storage read {ir_file_path}', wait=2.0)
            logger.debug('File content:\n%s', raw)

            if 'storage_file_open failed' in raw or 'Error' in raw:
                logger.error('Flipper could not read %s: %r', ir_file_path, raw)
                return False

            # Step 2: Parse the signal.
            try:
                signal = _parse_ir_file(raw, signal_name)
            except ValueError as exc:
                logger.error('Failed to parse IR file %s: %s', ir_file_path, exc)
                return False

            # Step 3: Build and send the ir tx command.
            cmd = _build_tx_command(signal)
            logger.info('Sending IR command: %s', cmd)
            response = _send_cmd(ser, cmd, wait=_TX_WAIT)
            logger.info('Flipper response: %r', response)

            if 'Wrong arguments' in response or 'Error' in response:
                logger.error('Flipper rejected command %r: %r', cmd, response)
                return False

        return True

    except serial.SerialException as exc:
        logger.error('Flipper serial error on %s: %s', port, exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error('Unexpected error: %s', exc)
        return False
