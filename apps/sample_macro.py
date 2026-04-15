# Macropad OS — Macro App Template
#
# A macro app maps each of the 12 physical keys to a colour, a short label,
# and a key sequence. Copy this file, rename it, and fill in your own macros.
#
# Sequence items (each key's third element is a list):
#   Positive int  — press that keycode      e.g. Keycode.A
#   Negative int  — release that keycode    e.g. -Keycode.SHIFT
#   Float         — delay in seconds        e.g. 0.1
#   String        — type the text           e.g. "hello\n"
#   List of ints  — consumer control codes  e.g. [ConsumerControlCode.PLAY_PAUSE]
#   Dict          — mouse / tone / play     e.g. {"tone": 440}  {"x": 10, "y": -5}

from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control_code import ConsumerControlCode

app = {
    "name": "My Macros",   # shown on the home screen (keep it short)
    "macros": [
        # ---- Row 1 (keys 0-2) ----
        # (LED colour,  label,   [sequence])
        (0x004400,  "Copy",   [Keycode.CONTROL, Keycode.C]),
        (0x004400,  "Cut",    [Keycode.CONTROL, Keycode.X]),
        (0x004400,  "Paste",  [Keycode.CONTROL, Keycode.V]),
        # ---- Row 2 (keys 3-5) ----
        (0x000044,  "Undo",   [Keycode.CONTROL, Keycode.Z]),
        (0x000044,  "Redo",   [Keycode.CONTROL, Keycode.Y]),
        (0x000044,  "Save",   [Keycode.CONTROL, Keycode.S]),
        # ---- Row 3 (keys 6-8) ----
        (0x440000,  "Key 7",  [Keycode.F7]),
        (0x440000,  "Key 8",  [Keycode.F8]),
        (0x440000,  "Key 9",  [Keycode.F9]),
        # ---- Row 4 (keys 9-11) ----
        (0x222222,  "Key10",  [Keycode.F10]),
        (0x222222,  "Key11",  [Keycode.F11]),
        (0x222222,  "Key12",  [Keycode.F12]),
    ],
}
