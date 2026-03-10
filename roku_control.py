"""
roku_control.py
---------------
Thin wrapper around the Roku External Control Protocol (ECP).

ECP is a simple HTTP REST API that every Roku device exposes on port 8060
of its local IP address. No authentication required.

Reference: https://developer.roku.com/docs/developer-program/debugging/external-control-api.md
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

# Per-request HTTP timeout (seconds).
_HTTP_TIMEOUT = 5


class RokuController:
    """Send ECP commands to a Roku device on the local network."""

    def __init__(self, ip: str, port: int = 8060) -> None:
        self.base = f'http://{ip}:{port}'

    # ── Low-level ECP calls ────────────────────────────────────────────────

    def keypress(self, key: str) -> bool:
        """
        Simulate pressing a single remote-control button.

        Common keys: Home, Back, Up, Down, Left, Right, Select,
                     Play, Rev, Fwd, Info, Search, InstantReplay,
                     VolumeUp, VolumeDown, VolumeMute
        """
        try:
            r = requests.post(
                f'{self.base}/keypress/{key}',
                timeout=_HTTP_TIMEOUT,
            )
            ok = r.status_code == 200
            logger.info('keypress %-14s %s', key, 'OK' if ok else f'HTTP {r.status_code}')
            return ok
        except requests.RequestException as exc:
            logger.error('keypress %s failed: %s', key, exc)
            return False

    def launch_app(self, app_id: str) -> bool:
        """
        Launch a Roku channel by its numeric app ID.
        The app must already be installed on the Roku.

        Useful IDs:
            195316  YouTubeTV
            tvinput.hdmi1  HDMI 1 input
        """
        try:
            r = requests.post(
                f'{self.base}/launch/{app_id}',
                timeout=_HTTP_TIMEOUT * 2,  # launching can be slower
            )
            ok = r.status_code == 200
            logger.info('launch %s: %s', app_id, 'OK' if ok else f'HTTP {r.status_code}')
            return ok
        except requests.RequestException as exc:
            logger.error('launch %s failed: %s', app_id, exc)
            return False

    def query_device_info(self) -> bool:
        """Ping the Roku to confirm it's reachable. Returns True if reachable."""
        try:
            r = requests.get(f'{self.base}/query/device-info', timeout=_HTTP_TIMEOUT)
            return r.status_code == 200
        except requests.RequestException:
            return False

    # ── Higher-level helpers ───────────────────────────────────────────────

    def send_sequence(
        self,
        sequence: list,
        default_delay: float = 1.2,
    ) -> None:
        """
        Execute a list of keypresses with inter-key delays.

        Each element of *sequence* is either:
        - str   → sent as a keypress
        - int / float → interpreted as a sleep duration in seconds

        Example:
            roku.send_sequence(['Home', 2, 'Right', 'Right', 'Select', 3, 'Down', 'Select'])
        """
        for item in sequence:
            if isinstance(item, (int, float)):
                logger.debug('Sleeping %.1fs', item)
                time.sleep(item)
            else:
                self.keypress(item)
                time.sleep(default_delay)
