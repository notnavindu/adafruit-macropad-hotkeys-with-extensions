# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys example: Microsoft Edge web browser for Windows

from adafruit_hid.keycode import Keycode  # REQUIRED if using Keycode.* values

app = {                      # REQUIRED dict, must be named 'app'
    'name': 'GitHub',  # Application name
    'macros': [             # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x000050, 'init', ['git init\n']),
        (0x000050, 'AC', [
         'git add . & git commit -m ""', Keycode.LEFT_ARROW]),
        (0x000050, 'Remote', ['git remote add origin']),
        # 2nd row ----------
        (0x05003F, 'Pull', ['git pull\n']),
        (0x05003F, 'POM', ['git pull origin main\n']),
        (0x05003F, 'Push', 'git push\n'),
        # 3rd row ----------
        (0x0A003F, 'Main.B', ['git checkout main\n']),
        (0x0A003F, 'New.B', ['git checkout -b ']),
        (0x0A003F, 'Rnme.B', ['git branch -M ']),
        # 4th row ----------
        (0x0D001F, 'G.Hub', [Keycode.CONTROL,
                             'n', -Keycode.COMMAND, 'github.com\n']),
        (0x0D001F, '', []),
        (0x0D001F, '', []),  # Hack-a-Day in new win
        # Encoder button ---
        (0x000000, '', ['git status'])  # Open both FE and backend
    ]
}
