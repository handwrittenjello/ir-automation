import platform
from pathlib import Path

# ── Paths (cross-platform) ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR  = BASE_DIR / 'logs'

# ── Hardware ──────────────────────────────────────────────────────────────────
# Windows:     'COM3' (check Device Manager after plugging in Flipper Zero)
# Raspberry Pi: '/dev/ttyACM0'  (or '/dev/flipper' after setting up udev rule)
FLIPPER_PORT = 'COM3' if platform.system() == 'Windows' else '/dev/ttyACM0'
FLIPPER_BAUD = 115200

# ── Roku ──────────────────────────────────────────────────────────────────────
ROKU_IP   = '192.168.1.100'
ROKU_PORT = 8060

# ── IR file paths on Flipper Zero SD card ─────────────────────────────────────
# Captured via: Flipper Zero → Infrared → Learn New Remote
IR_AC_SLEEP_DISABLE = '/ext/infrared/ac_sleep_disable.ir'
IR_AC_SLEEP_ENABLE  = '/ext/infrared/ac_sleep_enable.ir'
IR_TV_POWER         = '/ext/infrared/Westinghouse.ir'

# ── Roku app IDs ──────────────────────────────────────────────────────────────
# Verify with: requests.get('http://ROKU_IP:8060/query/apps').text
YOUTUBE_TV_APP_ID = '195316'

# ── Timing ────────────────────────────────────────────────────────────────────
IR_INTER_COMMAND_DELAY = 2.0   # seconds between back-to-back IR sends
ROKU_KEYPRESS_DELAY    = 1.2   # seconds between ECP keypresses
ROKU_APP_LAUNCH_WAIT   = 12    # seconds to wait for YouTubeTV to fully load

# ── Channel navigation sequences ──────────────────────────────────────────────
# Each element is either a key name (str) or a sleep duration (int/float seconds).
# Valid key names: Home, Back, Up, Down, Left, Right, Select,
#                  Rev, Fwd, Play, Info, Search, InstantReplay
#
# TODO: Replace placeholder sequences with your actual button paths.
# Calibration tip — run interactively on the Pi:
#   from roku_control import RokuController
#   roku = RokuController('ROKU_IP')
#   roku.keypress('Home')    # reset, then step through manually
#
CHANNEL_1_SEQUENCE = [
    'Home', 2,                        # go home, wait 2s
    'Right', 'Right', 'Select',       # navigate to Live TV tab
    3,                                # wait for guide to load
    'Down', 'Down', 'Select',         # select channel row  ← ADJUST
]

CHANNEL_2_SEQUENCE = [
    'Home', 2,
    'Right', 'Right', 'Select',
    3,
    'Down', 'Down', 'Down', 'Select', # ← ADJUST
]
