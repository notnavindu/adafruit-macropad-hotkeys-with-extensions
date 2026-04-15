# Macropad OS — Sub-app Template
#
# A sub-app takes full control of the display and keys while it is running.
# It runs its own loop and returns when the user presses the encoder knob.
#
# Module-level variables (like `state` below) are created once at import time
# and persist for the entire device session — even when the user navigates
# away to another app and comes back. Use them for timers, counters, etc.

import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label

# ---------------------------------------------------------------------------
# Persistent state — survives navigating away and back
# ---------------------------------------------------------------------------

state = {
    "counter": 0,
}

# ---------------------------------------------------------------------------
# Entry point — called by Macropad OS every time the app is opened
# ---------------------------------------------------------------------------

def run(macropad):
    # --- Set up the display ---
    group = displayio.Group()
    group.append(Rect(0, 0, macropad.display.width, 12, fill=0xFFFFFF))
    group.append(
        label.Label(terminalio.FONT, text="My App", color=0x000000,
                    anchored_position=(macropad.display.width // 2, -2),
                    anchor_point=(0.5, 0.0))
    )
    counter_label = label.Label(
        terminalio.FONT, text=str(state["counter"]), color=0xFFFFFF,
        anchored_position=(macropad.display.width // 2, macropad.display.height // 2),
        anchor_point=(0.5, 0.5), scale=2,
    )
    group.append(counter_label)
    macropad.display.root_group = group

    # --- Set up LEDs (optional) ---
    macropad.pixels.fill((0, 0, 0))
    macropad.pixels[0] = (0, 80, 0)   # green: increment
    macropad.pixels[1] = (80, 0, 0)   # red:   decrement
    macropad.pixels.show()

    # --- Main loop ---
    while True:
        # Always check encoder first — press = go home
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            return  # hand control back to Macropad OS

        event = macropad.keys.events.get()
        if event and event.pressed:
            if event.key_number == 0:
                state["counter"] += 1
            elif event.key_number == 1:
                state["counter"] -= 1

            counter_label.text = str(state["counter"])
            macropad.display.refresh()


app = {
    "name": "My App",   # shown on the home screen (keep it short)
    "run":  run,
}
