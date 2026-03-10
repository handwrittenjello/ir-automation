#!/usr/bin/env python3
import time
import config
from flipper_serial import send_ir_command

send_ir_command(config.IR_TV_POWER, config.FLIPPER_PORT, config.FLIPPER_BAUD)
time.sleep(2)
send_ir_command(config.IR_TV_POWER, config.FLIPPER_PORT, config.FLIPPER_BAUD)
