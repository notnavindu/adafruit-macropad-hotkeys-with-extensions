# SPDX-FileCopyrightText: 2021 Emma Humphries for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys example: Universal Numpad

from adafruit_hid.keycode import Keycode  # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name': 'Numpad',  # Application name
    'macros': [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x202000, '7', [Keycode.KEYPAD_SEVEN]),
        (0x202000, '8', [Keycode.KEYPAD_EIGHT]),
        (0x202000, '9', [Keycode.KEYPAD_NINE]),
        # 2nd row ----------
        (0x202000, '4', [Keycode.KEYPAD_FOUR]),
        (0x202000, '5', [Keycode.KEYPAD_FIVE]),
        (0x202000, '6', [Keycode.KEYPAD_SIX]),
        # 3rd row ----------
        (0x202000, '1', [Keycode.KEYPAD_ONE]),
        (0x202000, '2', [Keycode.KEYPAD_TWO]),
        (0x202000, '3', [Keycode.KEYPAD_THREE]),
        # 4th row ----------
        (0x101010, '*', [Keycode.KEYPAD_ASTERISK]),
        (0x800000, '0', [Keycode.KEYPAD_ZERO]),
        (0x101010, 'L', [Keycode.KEYPAD_NUMLOCK]),
        # Encoder button ---
        (0x000000, '', [Keycode.BACKSPACE])
    ]
}
