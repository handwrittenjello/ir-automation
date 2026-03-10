#!/usr/bin/env python3
"""
roku_remote.py
--------------
Interactive terminal Roku remote control.

Keyboard shortcuts
  Arrow keys     Up / Down / Left / Right
  Enter          Select / OK
  h              Home
  Backspace/Esc  Back
  p              Play / Pause
  r              Rewind
  f              Fast Forward
  + or =         Volume Up
  -              Volume Down
  m              Mute
  i              Info / Options
  s              Search
  *              Instant Replay
  q / Ctrl-C     Quit

Usage:
  python roku_remote.py
  python roku_remote.py 192.168.1.100   # override IP
"""

import re
import sys
import threading
import time
from collections import deque

import requests
from prompt_toolkit import Application
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

# ── Config ────────────────────────────────────────────────────────────────────
try:
    import config
    ROKU_URL = f'http://{config.ROKU_IP}:{config.ROKU_PORT}'
except ImportError:
    ip = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.100'
    ROKU_URL = f'http://{ip}:8060'

LOG_MAX = 6
FLASH_S = 0.25

# ── ANSI helpers ──────────────────────────────────────────────────────────────
R  = '\033[0m'    # reset
BD = '\033[1m'    # bold
DM = '\033[2m'    # dim
CY = '\033[96m'   # cyan
GR = '\033[92m'   # green
YL = '\033[93m'   # yellow
WH = '\033[97m'   # white
BG = '\033[42m'   # bg green  (active button)
BK = '\033[40m'   # bg black  (normal button)

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def vis(s: str) -> int:
    """Visible length of a string (strips ANSI codes)."""
    return len(_ANSI_RE.sub('', s))

def pad(s: str, width: int) -> str:
    """Right-pad s to `width` visible characters."""
    return s + ' ' * max(0, width - vis(s))

def btn(label: str, active: bool) -> str:
    if active:
        return f'{BG}{BD}{WH}[{label}]{R}'
    return f'{BK}{CY}[{WH}{label}{CY}]{R}'

# ── Remote art ────────────────────────────────────────────────────────────────

def render(active: str | None) -> str:
    """Build the full remote display as an ANSI string."""

    def b(name: str, label: str) -> str:
        return btn(label, active == name)

    # Border chars
    T  = f'{CY}╔{"═"*38}╗{R}'   # top
    M  = f'{CY}╠{"═"*38}╣{R}'   # mid divider
    Bo = f'{CY}╚{"═"*38}╝{R}'   # bottom
    LB = f'{CY}║{R}'             # left border
    RB = f'{CY}║{R}'             # right border

    def row(*parts, fill: int = 38) -> str:
        """Build a bordered row. `parts` are pre-formatted strings joined by spaces."""
        inner = '  '.join(parts)
        return f'{LB}  {pad(inner, fill - 2)}{RB}'

    def blank() -> str:
        return f'{LB}{" " * 38}{RB}'

    lines = [
        T,
        f'{LB}{BD}{CY}{"ROKU  REMOTE":^38}{R}{RB}',
        f'{LB}{DM}{CY}{"arrows=nav  Enter=ok  h=home  q=quit":^38}{R}{RB}',
        M,
        blank(),
        row(b('Home', ' HOME '), ' ' * 10, b('Back', ' BACK ')),
        row(f'{DM}{CY}(h){R}', ' ' * 16, f'{DM}{CY}(⌫ Bksp/Esc){R}'),
        blank(),
        M,
        blank(),
        row(b('Rev', ' ◄◄ '), ' ', b('Play', ' ▶/⏸ '), ' ', b('Fwd', ' ▶▶ ')),
        row(f'{DM}{CY}(r){R}', '     ', f'{DM}{CY}(p){R}', '      ', f'{DM}{CY}(f){R}'),
        blank(),
        M,
        blank(),
        f'{LB}{"":>17}{b("Up", "  ▲  ")}{"":>15}{RB}',
        f'{LB}{"":>18}{DM}{CY}( ↑ ){R}{"":>16}{RB}',
        f'{LB}  {b("Left", " ◄ ")}{"":>8}{b("Select", "  OK  ")}{"":>7}{b("Right", " ► ")}  {RB}',
        f'{LB}  {DM}{CY}(←){R}{"":>11}{DM}{CY}(Enter){R}{"":>8}{DM}{CY}(→){R}   {RB}',
        f'{LB}{"":>17}{b("Down", "  ▼  ")}{"":>15}{RB}',
        f'{LB}{"":>18}{DM}{CY}( ↓ ){R}{"":>16}{RB}',
        blank(),
        M,
        blank(),
        row(b('InstantReplay', ' ⊛ '), '  ', b('Search', ' SRCH '), '  ', b('Info', ' INFO ')),
        row(f'{DM}{CY}(*){R}', '       ', f'{DM}{CY}(s){R}', '        ', f'{DM}{CY}(i){R}'),
        blank(),
        M,
        blank(),
        row(b('VolumeUp', ' VOL+ '), '  ', b('VolumeMute', ' MUTE '), '  ', b('VolumeDown', ' VOL- ')),
        row(f'{DM}{CY}(+/=){R}', '     ', f'{DM}{CY}(m){R}', '        ', f'{DM}{CY}(-){R}'),
        blank(),
        Bo,
    ]
    return '\n'.join(lines)


# ── State & HTTP sender ───────────────────────────────────────────────────────

class State:
    def __init__(self):
        self.active:      str | None = None
        self.flash_until: float      = 0.0
        self.status:      str        = f'  {CY}●{R}  {WH}{ROKU_URL}{R}  —  ready'
        self.log:         deque      = deque(maxlen=LOG_MAX)
        self._lock = threading.Lock()

    def press(self, name: str) -> None:
        with self._lock:
            self.active      = name
            self.flash_until = time.monotonic() + FLASH_S
            self.status      = f'  {YL}▶{R}  Sending: {WH}{name}{R}'
        threading.Thread(target=self._post, args=(name,), daemon=True).start()

    def _post(self, name: str) -> None:
        try:
            r = requests.post(f'{ROKU_URL}/keypress/{name}', timeout=3)
            ok     = r.status_code == 200
            result = f'{GR}OK{R}' if ok else f'{YL}HTTP {r.status_code}{R}'
        except requests.RequestException as exc:
            result = f'{YL}ERR  {exc}{R}'
        ts = time.strftime('%H:%M:%S')
        entry = f'  {DM}{CY}{ts}{R}   {WH}{name:<20}{R}  {result}'
        with self._lock:
            self.log.appendleft(entry)
            self.status = f'  {CY}●{R}  Last: {WH}{name}{R}  →  {result}'

    def tick(self) -> bool:
        with self._lock:
            if self.active and time.monotonic() >= self.flash_until:
                self.active = None
                return True
        return False

    def get_text(self) -> str:
        with self._lock:
            remote  = render(self.active)
            divider = f'\n{DM}{CY}{"─" * 42}{R}\n'
            log_hdr = f'  {BD}{CY}Activity log{R}\n'
            log_out = '\n'.join(self.log) if self.log else f'  {DM}No activity yet{R}'
            return f'{remote}\n{self.status}\n{divider}{log_hdr}{log_out}\n'


# ── App ───────────────────────────────────────────────────────────────────────

def build_app(state: State) -> Application:
    kb = KeyBindings()

    def on(key: str, name: str):
        @kb.add(key)
        def _(event):
            state.press(name)
            event.app.invalidate()

    on('up',        'Up')
    on('down',      'Down')
    on('left',      'Left')
    on('right',     'Right')
    on('enter',     'Select')
    on('h',         'Home')
    on('backspace', 'Back')
    on('escape',    'Back')
    on('p',         'Play')
    on('r',         'Rev')
    on('f',         'Fwd')
    on('+',         'VolumeUp')
    on('=',         'VolumeUp')
    on('-',         'VolumeDown')
    on('m',         'VolumeMute')
    on('i',         'Info')
    on('s',         'Search')
    on('*',         'InstantReplay')

    @kb.add('q')
    @kb.add('c-c')
    def _quit(event):
        event.app.exit()

    control = FormattedTextControl(lambda: ANSI(state.get_text()), focusable=True)
    layout  = Layout(HSplit([Window(content=control)]))
    app     = Application(layout=layout, key_bindings=kb, full_screen=True, mouse_support=False)

    def _ticker():
        while True:
            time.sleep(0.04)
            if state.tick():
                try:
                    app.invalidate()
                except Exception:
                    pass
    threading.Thread(target=_ticker, daemon=True).start()

    return app


def main() -> None:
    build_app(State()).run()


if __name__ == '__main__':
    main()
