# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys: Obsidian.md

from adafruit_hid.keycode import Keycode  # REQUIRED if using Keycode.* values

app = {                      # REQUIRED dict, must be named 'app'
    'name': 'Obsidian',  # Application name
    'exit_key': 11,
    'macros': [             # List of button macros...
        # COLOR       LABEL       KEY SEQUENCE
        # 1st row ----------
        (0x3A0070, 'base',      [Keycode.LEFT_GUI, Keycode.HOME, -Keycode.LEFT_GUI, -Keycode.HOME,
                                 Keycode.F7, -Keycode.F7,
                                 0.5,
                                 Keycode.UP_ARROW, -Keycode.UP_ARROW,
                                 Keycode.UP_ARROW, -Keycode.UP_ARROW,
                                 Keycode.ENTER]),
        (0x3A0070, 'scope',     [Keycode.F5]),
        (0x3A0070, 'app60',     ['[[60 /']),
        # 2nd row ----------
        (0x200050, 'stdio',     [Keycode.F6]),
        (0x200050, 'rsrc',      [Keycode.F7]),
        (0x200050, 'link',      [Keycode.F8]),
        # 3rd row ----------
        (0x150038, 'move',      [Keycode.F9]),
        (0x150038, 'reveal',    [Keycode.F12]),
        (0x000000, '',          []),
        # 4th row ----------
        (0x0A0025, '<<',        [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.LEFT_ARROW]),
        (0x0A0025, '>>',        [Keycode.LEFT_GUI, Keycode.LEFT_ALT, Keycode.RIGHT_ARROW]),
        # Encoder button ---
        (0x000000, '',          [])
    ]
}

