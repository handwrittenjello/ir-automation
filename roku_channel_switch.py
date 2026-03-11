#!/usr/bin/env python3
import time
import config
from roku_control import RokuController

roku = RokuController(config.ROKU_IP, config.ROKU_PORT)

roku.keypress('Back')
time.sleep(3)
roku.keypress('Down')
time.sleep(3)
roku.keypress('Select')
