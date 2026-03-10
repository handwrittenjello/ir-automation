#!/usr/bin/env python3
"""
roku_startup.py
---------------
Launch YouTubeTV on the Roku and navigate to the first channel.

Run this ~45 seconds after tv_on.py so the TV has time to boot fully.

Cron entry (example — 10:01 PM, with a 44-second built-in delay):
    1 22 * * * sleep 44 && /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/roku_startup.py >> /home/pi/ir_automation/logs/cron.log 2>&1

Calibrating CHANNEL_1_SEQUENCE:
    1. Launch YouTubeTV on your Roku manually.
    2. Note what screen appears immediately after launch (usually "Home" or
       the last thing you were watching).
    3. Count each D-pad press needed to reach the Live TV guide and then
       scroll to your desired channel.
    4. Update CHANNEL_1_SEQUENCE in config.py accordingly.
    5. Test interactively:
           from roku_control import RokuController
           roku = RokuController('YOUR_ROKU_IP')
           roku.send_sequence(['Home', 2, 'Right', 'Right', 'Select', 3, ...])
"""

import logging
import sys
import time

import config
from roku_control import RokuController

# ── Logging ───────────────────────────────────────────────────────────────────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(config.LOG_DIR / 'roku_startup.log'),
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info('=== Roku startup: launching YouTubeTV ===')

    roku = RokuController(config.ROKU_IP, config.ROKU_PORT)

    # Confirm the Roku is reachable before doing anything.
    if not roku.query_device_info():
        logger.error('Roku at %s:%s is not reachable — aborting', config.ROKU_IP, config.ROKU_PORT)
        sys.exit(1)

    # Launch YouTubeTV.
    logger.info('Launching YouTubeTV (app ID %s)', config.YOUTUBE_TV_APP_ID)
    if not roku.launch_app(config.YOUTUBE_TV_APP_ID):
        logger.error('FAILED to launch YouTubeTV')
        sys.exit(1)

    # Give the app time to fully load before sending navigation keys.
    logger.info('Waiting %ds for YouTubeTV to load...', config.ROKU_APP_LAUNCH_WAIT)
    time.sleep(config.ROKU_APP_LAUNCH_WAIT)

    # Navigate to channel 1.
    logger.info('Sending CHANNEL_1_SEQUENCE: %s', config.CHANNEL_1_SEQUENCE)
    roku.send_sequence(config.CHANNEL_1_SEQUENCE, default_delay=config.ROKU_KEYPRESS_DELAY)

    logger.info('Roku startup complete')


if __name__ == '__main__':
    main()
