#!/usr/bin/env python3
import time
import config
from roku_control import RokuController

roku = RokuController(config.ROKU_IP, config.ROKU_PORT)

roku.launch_app(config.YOUTUBE_TV_APP_ID)
time.sleep(15)
roku.keypress('Select')
time.sleep(10)
roku.keypress('Right')
time.sleep(3)
roku.keypress('Down')
time.sleep(3)
roku.keypress('Down')
time.sleep(3)
roku.keypress('Select')
