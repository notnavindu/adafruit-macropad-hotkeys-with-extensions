# Macropad OS
# CircuitPython 10 — Adafruit MacroPad RP2040

import os
import time
import displayio
import terminalio
import traceback
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from screensaver import get_screensaver

try:
    import config
except ImportError:
    class config:  # sensible defaults when config.py is absent
        SLEEP_ENABLED = True
        SLEEP_TIMEOUT = 60
        SCREENSAVER = "bounce"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APPS_FOLDER = "/apps"
APPS_PER_PAGE = 12          # matches the 12 physical keys
MAX_LABEL_CHARS = 6         # characters visible per home-screen slot
HEADER_HEIGHT = 12          # pixels reserved for the top title bar

# ---------------------------------------------------------------------------
# App wrappers
# ---------------------------------------------------------------------------

class MacroApp:
    """Wraps an app dict that drives hotkeys via a 'macros' list."""

    def __init__(self, appdata):
        self.name = appdata["name"]
        self.macros = appdata["macros"]
        self.auto_return = appdata.get("auto_return", False)

    def activate(self, macropad):
        """Show key labels and LED colours for this macro set."""
        for i in range(12):
            if i < len(self.macros):
                macropad.pixels[i] = self.macros[i][0]
                _home_group[i].text = self.macros[i][1]
            else:
                macropad.pixels[i] = 0
                _home_group[i].text = ""
        _home_group[13].text = self.name
        macropad.pixels.show()
        macropad.display.root_group = _home_group
        macropad.display.refresh()


class SubApp:
    """Wraps an app dict that exposes a blocking 'run(macropad)' function."""

    def __init__(self, appdata):
        self.name = appdata["name"]
        self._run = appdata["run"]

    def activate(self, macropad):
        """Hand control to the sub-app; returns when the user exits."""
        self._run(macropad)


# ---------------------------------------------------------------------------
# Home screen
# ---------------------------------------------------------------------------

class HomeScreen:
    """Renders a paginated 3×4 grid of app names on the OLED.

    Each grid slot corresponds to the matching physical key (0–11).
    Turning the encoder cycles pages; pressing a key launches that app.
    """

    def __init__(self, macropad):
        self._macropad = macropad
        self._group = self._build_group()

    def _build_group(self):
        mp = self._macropad
        group = displayio.Group()

        # Header bar background + title
        group.append(Rect(0, 0, mp.display.width, HEADER_HEIGHT, fill=0xFFFFFF))
        group.append(
            label.Label(
                terminalio.FONT,
                text="Macropad OS",
                color=0x000000,
                anchored_position=(mp.display.width // 2, -2),
                anchor_point=(0.5, 0.0),
            )
        )

        # 12 key-label slots in a 3-column × 4-row grid
        row_height = (mp.display.height - HEADER_HEIGHT) // 4
        for key_index in range(12):
            col = key_index % 3
            row = key_index // 3
            x = int((mp.display.width - 1) * col / 2)
            y = HEADER_HEIGHT + row_height // 2 + row * row_height
            group.append(
                label.Label(
                    terminalio.FONT,
                    text="",
                    color=0xFFFFFF,
                    anchored_position=(x, y),
                    anchor_point=(col / 2, 0.5),
                )
            )

        # Page indicator (slot index 14 = group index 2+12 = 14)
        group.append(
            label.Label(
                terminalio.FONT,
                text="",
                color=0x000000,
                anchored_position=(mp.display.width - 2, -2),
                anchor_point=(1.0, 0.0),
            )
        )

        return group

    def draw(self, apps, page):
        """Update the display for the given page of apps."""
        mp = self._macropad
        total_pages = max(1, (len(apps) + APPS_PER_PAGE - 1) // APPS_PER_PAGE)
        start = page * APPS_PER_PAGE

        for slot in range(12):
            app_index = start + slot
            # group[0] = rect, group[1] = title, group[2..13] = key labels
            lbl = self._group[2 + slot]
            if app_index < len(apps):
                name = apps[app_index].name
                lbl.text = name[:MAX_LABEL_CHARS]
            else:
                lbl.text = ""

        # Page indicator in header
        self._group[14].text = f"{page + 1}/{total_pages}"

        # Pixels off on home screen
        mp.pixels.fill(0)
        mp.pixels.show()

        mp.display.root_group = self._group
        mp.display.refresh()

    def app_index_for_key(self, key_number, page):
        """Convert a physical key press to an absolute app index."""
        return page * APPS_PER_PAGE + key_number


# ---------------------------------------------------------------------------
# The shared display group used by MacroApp (key labels + title bar)
# ---------------------------------------------------------------------------

def _build_macro_group(macropad):
    group = displayio.Group()
    for key_index in range(12):
        col = key_index % 3
        row = key_index // 3
        group.append(
            label.Label(
                terminalio.FONT,
                text="",
                color=0xFFFFFF,
                anchored_position=(
                    (macropad.display.width - 1) * col / 2,
                    macropad.display.height - 1 - (3 - row) * 12,
                ),
                anchor_point=(col / 2, 1.0),
            )
        )
    group.append(Rect(0, 0, macropad.display.width, HEADER_HEIGHT, fill=0xFFFFFF))
    group.append(
        label.Label(
            terminalio.FONT,
            text="",
            color=0x000000,
            anchored_position=(macropad.display.width // 2, -2),
            anchor_point=(0.5, 0.0),
        )
    )
    # Encoder-press hint
    group.append(
        label.Label(
            terminalio.FONT,
            text="[knob] home",
            color=0x444444,
            anchored_position=(macropad.display.width - 2, macropad.display.height - 2),
            anchor_point=(1.0, 1.0),
        )
    )
    return group


# ---------------------------------------------------------------------------
# App loading
# ---------------------------------------------------------------------------

def load_apps(folder):
    apps = []
    try:
        files = sorted(os.listdir(folder))
    except OSError:
        return apps

    for filename in files:
        if not filename.endswith(".py") or filename.startswith(("._", "_")):
            continue
        module_path = folder + "/" + filename[:-3]
        try:
            module = __import__(module_path)
            appdata = module.app
            if "run" in appdata:
                apps.append(SubApp(appdata))
            elif "macros" in appdata:
                apps.append(MacroApp(appdata))
        except Exception as err:
            print("ERROR loading", filename)
            traceback.print_exception(err, err, err.__traceback__)

    return apps


# ---------------------------------------------------------------------------
# Sequence execution (for MacroApp keys)
# ---------------------------------------------------------------------------

def _execute_sequence(macropad, sequence, pressed):
    if pressed:
        for item in sequence:
            if isinstance(item, int):
                if item >= 0:
                    macropad.keyboard.press(item)
                else:
                    macropad.keyboard.release(-item)
            elif isinstance(item, float):
                time.sleep(item)
            elif isinstance(item, str):
                macropad.keyboard_layout.write(item)
            elif isinstance(item, list):
                for code in item:
                    if isinstance(code, int):
                        macropad.consumer_control.release()
                        macropad.consumer_control.press(code)
                    elif isinstance(code, float):
                        time.sleep(code)
            elif isinstance(item, dict):
                if "buttons" in item:
                    if item["buttons"] >= 0:
                        macropad.mouse.press(item["buttons"])
                    else:
                        macropad.mouse.release(-item["buttons"])
                macropad.mouse.move(
                    item.get("x", 0),
                    item.get("y", 0),
                    item.get("wheel", 0),
                )
                if "tone" in item:
                    if item["tone"] > 0:
                        macropad.stop_tone()
                        macropad.start_tone(item["tone"])
                    else:
                        macropad.stop_tone()
                elif "play" in item:
                    macropad.play_file(item["play"])
    else:
        for item in sequence:
            if isinstance(item, int):
                if item >= 0:
                    macropad.keyboard.release(item)
            elif isinstance(item, dict):
                if "buttons" in item:
                    if item["buttons"] >= 0:
                        macropad.mouse.release(item["buttons"])
                elif "tone" in item:
                    macropad.stop_tone()
        macropad.consumer_control.release()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

macropad = MacroPad()
macropad.display.auto_refresh = False
macropad.pixels.auto_write = False

_home_group = _build_macro_group(macropad)

apps = load_apps(APPS_FOLDER)

if not apps:
    err_group = displayio.Group()
    err_group.append(
        label.Label(terminalio.FONT, text="No apps found\nin /apps", color=0xFF0000,
                    anchored_position=(macropad.display.width // 2, macropad.display.height // 2),
                    anchor_point=(0.5, 0.5))
    )
    macropad.display.root_group = err_group
    macropad.display.refresh()
    while True:
        pass

home = HomeScreen(macropad)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

STATE_HOME = "home"
STATE_APP = "app"
STATE_SLEEPING = "sleeping"

state = STATE_HOME
current_page = 0
current_app_index = 0
last_encoder_pos = macropad.encoder
last_encoder_switch = macropad.encoder_switch_debounced.pressed
last_input_time = time.monotonic()
_screensaver = None

home.draw(apps, current_page)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

while True:
    now = time.monotonic()

    # --- SLEEP TIMER --------------------------------------------------------
    if state != STATE_SLEEPING and config.SLEEP_ENABLED:
        if now - last_input_time > config.SLEEP_TIMEOUT:
            state = STATE_SLEEPING
            _screensaver = get_screensaver(config.SCREENSAVER)
            _screensaver.start(macropad)

    # --- SLEEPING STATE -----------------------------------------------------
    if state == STATE_SLEEPING:
        macropad.encoder_switch_debounced.update()
        _wake_key = macropad.keys.events.get()
        _wake_enc = macropad.encoder != last_encoder_pos
        _wake_sw = macropad.encoder_switch_debounced.pressed
        if _wake_key or _wake_enc or _wake_sw:
            _screensaver.stop(macropad)
            _screensaver = None
            state = STATE_HOME
            last_input_time = time.monotonic()
            last_encoder_pos = macropad.encoder
            last_encoder_switch = macropad.encoder_switch_debounced.pressed
            while macropad.keys.events.get():  # drain — don't fire HID on wake
                pass
            home.draw(apps, current_page)
        else:
            _screensaver.tick(macropad)
            macropad.display.refresh()
        continue

    macropad.encoder_switch_debounced.update()
    encoder_switch = macropad.encoder_switch_debounced.pressed
    encoder_pos = macropad.encoder

    # --- HOME STATE ---------------------------------------------------------
    if state == STATE_HOME:

        # Encoder turn → paginate
        if encoder_pos != last_encoder_pos:
            total_pages = max(1, (len(apps) + APPS_PER_PAGE - 1) // APPS_PER_PAGE)
            delta = 1 if encoder_pos > last_encoder_pos else -1
            current_page = (current_page + delta) % total_pages
            last_encoder_pos = encoder_pos
            last_input_time = now
            home.draw(apps, current_page)

        # Encoder press → re-enter last used app (if any)
        elif encoder_switch and encoder_switch != last_encoder_switch:
            last_encoder_switch = encoder_switch
            last_input_time = now
            app = apps[current_app_index]
            if isinstance(app, SubApp):
                app.activate(macropad)
                # sub-app returned; go back to home
                home.draw(apps, current_page)
            else:
                app.activate(macropad)
                state = STATE_APP
                while macropad.keys.events.get():
                    pass
            last_encoder_pos = macropad.encoder

        # Key press → launch that app
        else:
            event = macropad.keys.events.get()
            if event and event.pressed:
                last_input_time = now
                slot = event.key_number
                app_index = home.app_index_for_key(slot, current_page)
                if app_index < len(apps):
                    current_app_index = app_index
                    app = apps[current_app_index]
                    if isinstance(app, SubApp):
                        app.activate(macropad)
                        home.draw(apps, current_page)
                    else:
                        app.activate(macropad)
                        state = STATE_APP
                        while macropad.keys.events.get():
                            pass
                    last_encoder_pos = macropad.encoder

        last_encoder_switch = encoder_switch

    # --- APP STATE ----------------------------------------------------------
    elif state == STATE_APP:
        app = apps[current_app_index]

        # Encoder press → go home
        if encoder_switch and encoder_switch != last_encoder_switch:
            last_encoder_switch = encoder_switch
            last_input_time = now
            macropad.keyboard.release_all()
            macropad.consumer_control.release()
            macropad.mouse.release_all()
            macropad.stop_tone()
            state = STATE_HOME
            last_encoder_pos = macropad.encoder
            home.draw(apps, current_page)
            continue

        last_encoder_switch = encoder_switch

        # Key events → execute macro sequence
        event = macropad.keys.events.get()
        if not event:
            continue

        key_number = event.key_number
        pressed = event.pressed

        if key_number >= len(app.macros):
            continue

        sequence = app.macros[key_number][2]

        if pressed and key_number < 12:
            last_input_time = now
            macropad.pixels[key_number] = 0xFFFFFF
            macropad.pixels.show()

        _execute_sequence(macropad, sequence, pressed)

        if pressed and key_number < 12 and app.auto_return:
            macropad.keyboard.release_all()
            macropad.consumer_control.release()
            macropad.mouse.release_all()
            macropad.stop_tone()
            while macropad.keys.events.get():
                pass
            state = STATE_HOME
            last_encoder_pos = macropad.encoder
            home.draw(apps, current_page)
            continue

        if not pressed and key_number < 12:
            macropad.pixels[key_number] = app.macros[key_number][0]
            macropad.pixels.show()
