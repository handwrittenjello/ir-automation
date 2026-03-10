#!/usr/bin/env python3
"""
tv_on.py
--------
Power on the TV via IR command through the Flipper Zero.

Cron entry (example — 10:00 PM every night):
    0 22 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/tv_on.py >> /home/pi/ir_automation/logs/cron.log 2>&1

Note: Most TV remotes only have a power *toggle*, not a dedicated ON button.
If the TV is already off at the scheduled time this is safe. If it could be
on and you don't want it toggled off, consider using CEC over HDMI or a
smart plug that tracks power state.
"""

import logging
import sys

import config
from flipper_serial import send_ir_command

# ── Logging ───────────────────────────────────────────────────────────────────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(config.LOG_DIR / 'tv_on.log'),
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info('=== TV power on ===')
    logger.info('Sending TV power → %s', config.IR_TV_POWER)

    if not send_ir_command(config.IR_TV_POWER, config.FLIPPER_PORT, config.FLIPPER_BAUD):
        logger.error('FAILED to send TV power command')
        sys.exit(1)

    logger.info('TV power command sent successfully')


if __name__ == '__main__':
    main()
