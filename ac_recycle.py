#!/usr/bin/env python3
"""
ac_recycle.py
-------------
Recycle the AC sleep timer so the unit keeps running overnight.

Cron entry (example — 2:00 AM every night):
    0 2 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/ac_recycle.py >> /home/pi/ir_automation/logs/cron.log 2>&1

Logic:
    1. Send the IR command that disables / cancels the current sleep timer.
    2. Wait briefly, then send the IR command that re-enables the sleep timer.
    The timer now starts a fresh countdown from its configured duration.

    If your AC remote has a single "Sleep" toggle (one button does both),
    capture it once and point both IR_AC_SLEEP_DISABLE and IR_AC_SLEEP_ENABLE
    at the same .ir file. Sending it twice will cancel then restart.
"""

import logging
import sys
import time

import config
from flipper_serial import send_ir_command

# ── Logging ───────────────────────────────────────────────────────────────────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(config.LOG_DIR / 'ac_recycle.log'),
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info('=== AC sleep timer recycle started ===')

    # Step 1: Cancel existing sleep timer.
    logger.info('Sending AC sleep DISABLE → %s', config.IR_AC_SLEEP_DISABLE)
    if not send_ir_command(config.IR_AC_SLEEP_DISABLE, config.FLIPPER_PORT, config.FLIPPER_BAUD):
        logger.error('FAILED to send AC sleep disable — aborting')
        sys.exit(1)
    logger.info('AC sleep disabled')

    time.sleep(config.IR_INTER_COMMAND_DELAY)

    # Step 2: Re-enable sleep timer (fresh countdown begins).
    logger.info('Sending AC sleep ENABLE → %s', config.IR_AC_SLEEP_ENABLE)
    if not send_ir_command(config.IR_AC_SLEEP_ENABLE, config.FLIPPER_PORT, config.FLIPPER_BAUD):
        logger.error('FAILED to send AC sleep enable')
        sys.exit(1)

    logger.info('AC sleep timer recycled successfully')


if __name__ == '__main__':
    main()
