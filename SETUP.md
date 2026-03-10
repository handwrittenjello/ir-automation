# Smart Home IR/RF Automation — Setup Guide

Complete ordered steps from hardware to a fully running system.

---

## Step 1 — Capture IR Signals on the Flipper Zero

You need **3 signals** (or 2 if your AC has a single sleep toggle):

| File name to save     | Remote button to press       |
|-----------------------|------------------------------|
| `ac_sleep_disable`    | AC: button that cancels sleep|
| `ac_sleep_enable`     | AC: button that sets sleep   |
| `tv_power`            | TV: power button             |

> **Single-toggle AC?** If your AC remote has one "Sleep" button that
> alternates between enable/disable, capture it once and save it under
> *both* names. The script sends it twice (cancel then restart).

**On the Flipper Zero:**
1. Main Menu → **Infrared** → **Learn New Remote**
2. Point the original remote at Flipper's IR port (top edge of device)
3. Press and hold the button until Flipper shows "Saved"
4. Rename the file to match the table above
5. Verify: **Infrared → Saved Remotes → [file] → Send** — confirm the device responds

Files land on the SD card at: `/ext/infrared/`

---

## Step 2 — Set Up Raspberry Pi

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv

# Grant serial port access (required for USB communication with Flipper Zero)
sudo usermod -aG dialout pi
sudo reboot
```

---

## Step 3 — Deploy Project Files

Copy this entire `ir_automation/` directory to the Pi:

```bash
# From your development machine:
scp -r ir_automation/ pi@raspberrypi.local:/home/pi/

# Or on the Pi directly:
mkdir -p /home/pi/ir_automation/logs
```

---

## Step 4 — Install Dependencies

```bash
cd /home/pi/ir_automation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Step 5 — Connect and Verify Flipper Zero

1. Plug Flipper Zero into the Raspberry Pi via USB
2. On Flipper: navigate to the main menu (do not enter any sub-app)

```bash
# Confirm serial port is visible
ls /dev/ttyACM*          # should print /dev/ttyACM0

# Quick connection test
python3 -c "
import serial, time
with serial.Serial('/dev/ttyACM0', 115200, timeout=3) as s:
    s.write(b'\r\n')
    time.sleep(0.3)
    print('Connected:', s.read_all())
"

# Test an actual IR transmission (point Flipper at your TV)
source venv/bin/activate
python3 -c "
from flipper_serial import send_ir_command
print(send_ir_command('/ext/infrared/tv_power.ir', '/dev/ttyACM0', 115200))
"
```

### Optional: stable port via udev rule

If the Flipper Zero ever reconnects, `/dev/ttyACM0` may shift. Pin it:

```bash
# Flipper Zero USB IDs: vendor 0483, product 5740
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", SYMLINK+="flipper"' \
  | sudo tee /etc/udev/rules.d/99-flipper.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Then change FLIPPER_PORT in config.py:
#   FLIPPER_PORT = '/dev/flipper'
```

---

## Step 6 — Configure config.py

Edit `/home/pi/ir_automation/config.py` and set:

| Variable      | What to put there                              |
|---------------|------------------------------------------------|
| `FLIPPER_PORT`| `/dev/ttyACM0` (or `/dev/flipper` after udev) |
| `ROKU_IP`     | Your Roku's local IP address (see below)       |

**Find your Roku's IP:**
- On Roku: **Settings → Network → About**
- Or scan your subnet:

```bash
python3 -c "
import requests
for i in range(1, 255):
    try:
        r = requests.get(f'http://192.168.1.{i}:8060/query/device-info', timeout=0.4)
        if r.status_code == 200:
            print('Roku found at 192.168.1.' + str(i))
    except: pass
"
```

**Verify Roku ECP is reachable:**
```bash
python3 -c "
import requests
r = requests.get('http://ROKU_IP:8060/query/device-info')
print(r.status_code, r.text[:200])
"
```

**Find the YouTubeTV app ID:**
```bash
python3 -c "
import requests
r = requests.get('http://ROKU_IP:8060/query/apps')
# Search the output for 'YouTube TV'
print(r.text)
" | grep -i youtube
# Expected: <app id="195316" ...>YouTube TV</app>
```

---

## Step 7 — Calibrate Roku Channel Sequences

The placeholder sequences in `config.py` must be replaced with your actual
button paths. Do this interactively on the Pi:

```bash
source /home/pi/ir_automation/venv/bin/activate
python3
```

```python
from roku_control import RokuController
roku = RokuController('YOUR_ROKU_IP')

# Reset to a known state
roku.keypress('Home')

# Step through navigation manually, one keypress at a time.
# Note each key you press and the delay needed.
roku.keypress('Right')   # → Live TV tab?
roku.keypress('Right')
roku.keypress('Select')
import time; time.sleep(3)   # wait for guide
roku.keypress('Down')        # → first channel row
roku.keypress('Select')      # → tune in
```

Once you have the working sequence, update `CHANNEL_1_SEQUENCE` and
`CHANNEL_2_SEQUENCE` in `config.py`.

---

## Step 8 — Test Each Script Manually

```bash
cd /home/pi/ir_automation
source venv/bin/activate

python3 tv_on.py
python3 ac_recycle.py
python3 roku_startup.py
python3 roku_channel_switch.py

# Check logs
tail -20 logs/tv_on.log
tail -20 logs/ac_recycle.log
tail -20 logs/roku_startup.log
```

---

## Step 9 — Set Up Cron

```bash
crontab -e
```

Paste the following (adjust times to match your actual schedule):

```cron
# ── Smart Home Automation ────────────────────────────────────────────────────

# TV power on at 10:00 PM
0 22 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/tv_on.py >> /home/pi/ir_automation/logs/cron.log 2>&1

# Roku startup 45 s after TV on (TV needs time to boot)
1 22 * * * sleep 44 && /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/roku_startup.py >> /home/pi/ir_automation/logs/cron.log 2>&1

# AC sleep timer recycle at 2:00 AM
0 2 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/ac_recycle.py >> /home/pi/ir_automation/logs/cron.log 2>&1

# Roku channel switch at 6:00 AM
0 6 * * * /home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/roku_channel_switch.py >> /home/pi/ir_automation/logs/cron.log 2>&1
```

Verify cron is running:
```bash
sudo systemctl enable cron
sudo systemctl status cron
```

---

## Step 10 — Log Rotation

Prevent logs from filling the SD card:

```bash
sudo tee /etc/logrotate.d/ir_automation << 'EOF'
/home/pi/ir_automation/logs/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```

---

## Step 11 — Final Verification

```bash
# Reboot and confirm cron fires at scheduled times.
sudo reboot

# After reboot, watch the combined cron log live:
tail -f /home/pi/ir_automation/logs/cron.log
```

Trigger a test run immediately (without waiting for the scheduled time):
```bash
# Simulate the 10 PM block right now:
/home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/tv_on.py
sleep 45
/home/pi/ir_automation/venv/bin/python /home/pi/ir_automation/roku_startup.py
```
