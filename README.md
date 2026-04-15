# Macropad OS

A clean, extensible operating system for the [Adafruit MacroPad RP2040](https://www.adafruit.com/product/5100), built on CircuitPython 10.

Apps are simple Python files — either a collection of hotkeys or a fully interactive mini-app. The home screen lets you navigate and launch them from the 12-key grid.

---

## Getting Started

### 1. Flash CircuitPython 10

Download [CircuitPython 10 for MacroPad RP2040](https://circuitpython.org/board/adafruit_macropad_rp2040/) and follow the [flashing guide](https://learn.adafruit.com/adafruit-macropad-rp2040/circuitpython).

### 2. Copy files to the device

Connect the MacroPad over USB. It will appear as a drive called `CIRCUITPY`. Copy the following from this repo to the device root:

```
code.py
apps/
lib/
```

The `lib/` folder already contains all required compiled libraries for CircuitPython 10 — no extra install steps needed.

> **Bongo Cat**: also copy the `bongo/` folder (containing `bongo.bmp`) to the device root if you want to use that app.

---

## Navigation

| Action | Result |
|--------|--------|
| **Press encoder knob** | Open home screen |
| **Turn encoder** (on home) | Cycle through pages of apps |
| **Press a key** (on home) | Launch that app |
| **Press encoder knob** (in a macro app) | Return to home |
| **Press encoder knob** (in a sub-app) | Return to home |

The home screen shows up to 12 apps per page in a 3×4 grid that matches the physical key layout. If you have more than 12 apps, turn the encoder to go to the next page.

---

## Creating Apps

All app files live in the `apps/` folder. Each file must define a module-level variable called `app`.

### Macro App (hotkeys)

Maps each key to an LED colour, a short label, and a sequence of actions. Copy `apps/sample_macro.py` as a starting point.

```python
from adafruit_hid.keycode import Keycode

app = {
    "name": "My Macros",
    "macros": [
        # (LED colour,   label,    [sequence])
        (0x004400,  "Copy",   [Keycode.CONTROL, Keycode.C]),
        (0x004400,  "Paste",  [Keycode.CONTROL, Keycode.V]),
        # ... up to 12 keys (plus an optional 13th for the encoder button)
    ],
}
```

**Sequence item types:**

| Type | Meaning | Example |
|------|---------|---------|
| Positive `int` | Press keycode | `Keycode.A` |
| Negative `int` | Release keycode | `-Keycode.SHIFT` |
| `float` | Delay (seconds) | `0.1` |
| `str` | Type text | `"hello\n"` |
| `list` | Consumer control codes | `[ConsumerControlCode.PLAY_PAUSE]` |
| `dict` with `"tone"` | Play a tone (Hz, 0 = stop) | `{"tone": 440}` |
| `dict` with `x/y/wheel/buttons` | Mouse action | `{"x": 10, "y": -5}` |

### Sub-app (interactive)

Takes full control of the display and keys. Define a `run(macropad)` function and return from it when the user should go home. Copy `apps/sample_app.py` as a starting point.

```python
import displayio, terminalio
from adafruit_display_text import label

# Module-level state persists between visits to the app
state = {"count": 0}

def run(macropad):
    # Set up display
    group = displayio.Group()
    lbl = label.Label(terminalio.FONT, text="0", color=0xFFFFFF,
                      anchored_position=(64, 32), anchor_point=(0.5, 0.5))
    group.append(lbl)
    macropad.display.root_group = group

    while True:
        # Always check the encoder — press = go home
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            return

        event = macropad.keys.events.get()
        if event and event.pressed:
            state["count"] += 1
            lbl.text = str(state["count"])
            macropad.display.refresh()

app = {
    "name": "Counter",
    "run": run,
}
```

**Rules for sub-apps:**
- Call `macropad.encoder_switch_debounced.update()` every loop iteration.
- `return` from `run()` to go back to the home screen.
- Module-level variables persist for the whole device session — use them for timers, counters, and any other state you want to survive navigation.

---

## Included Apps

| App | Type | Description |
|-----|------|-------------|
| `numpad.py` | Macro | Numpad keys |
| `media.py` | Macro | Media playback & brightness |
| `github.py` | Macro | Git keyboard shortcuts |
| `web.py` | Macro | Browser shortcuts |
| `tones.py` | Macro | Sound/tone demos |
| `win-adobe-photoshop.py` | Macro | Photoshop shortcuts (Windows) |
| `pomodoro.py` | Sub-app | Focus timer with work/break sessions |
| `bongo.py` | Sub-app | Bongo cat animation (requires `/bongo/bongo.bmp`) |

---

## Hardware

- [Adafruit MacroPad RP2040](https://www.adafruit.com/product/5100)
- CircuitPython 10.1.4+

---

## License

GNU GPL v3. See [LICENSE](LICENSE).
