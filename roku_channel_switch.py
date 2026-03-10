#!/usr/bin/env python3
"""
roku_channel_switch.py
----------------------
Switch the Roku / YouTubeTV to the second channel at 6:00 AM.

Assumes YouTubeTV is already running from the overnight startup sequence.
The script navigates from whatever state the app is currently in — hence
CHANNEL_2_SEQUENCE should start from a known anchor (e.g., pressing 'Home'
inside the YouTubeTV app to reset to the main menu first).

Cron entry:
    0 6 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/roku_channel_switch.py >> /home/pi/ir_automation/logs/cron.log 2>&1
"""

import logging
import sys

import config
from roku_control import RokuController

# ── Logging ───────────────────────────────────────────────────────────────────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(config.LOG_DIR / 'roku_channel_switch.log'),
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info('=== Roku 6AM channel switch ===')

    roku = RokuController(config.ROKU_IP, config.ROKU_PORT)

    if not roku.query_device_info():
        logger.error('Roku at %s:%s is not reachable — aborting', config.ROKU_IP, config.ROKU_PORT)
        sys.exit(1)

    logger.info('Sending CHANNEL_2_SEQUENCE: %s', config.CHANNEL_2_SEQUENCE)
    roku.send_sequence(config.CHANNEL_2_SEQUENCE, default_delay=config.ROKU_KEYPRESS_DELAY)

    logger.info('Channel switch complete')


if __name__ == '__main__':
    main()
