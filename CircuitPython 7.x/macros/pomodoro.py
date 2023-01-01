# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys: Pomodoro


import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label

# initializing data
data = {
    "start_time": None,
    "paused_at": 0,
    "offset": 0,  # used for pausing and resuming
    "session_count": 0,
    "session_ended": False
}

# constants
WORK_SESSION = {
    "duration": 25 * 60,
    "title": "FOCUS"
}
SHORT_BREAK = {
    "duration": 5 * 60,
    "title": "SHORT BREAK"
}
LONG_BREAK = {
    "duration": 15 * 60,
    "title": "LONG BREAK"
}

sequence = [
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    LONG_BREAK
]


def Pomodoro(macropad, encoder_position):
    macropad.pixels.fill((0, 0, 0))

    macropad.pixels[0] = (27, 148, 0)
    macropad.pixels[1] = (252, 186, 3)
    macropad.pixels[2] = (255, 0, 0)
    macropad.pixels.show()

    group = displayio.Group()

    group.append(Rect(0, 0, macropad.display.width, 12, fill=0xFFFFFF))

    group.append(
        label.Label(
            terminalio.FONT,
            text="Pomodoro",
            color=0x000000,
            anchored_position=(macropad.display.width // 2, -2),
            anchor_point=(0.5, 0.0),
        )
    )

    group.append(
        label.Label(
            terminalio.FONT,
            text="",
            color=0xFFFFFF,
            anchored_position=(
                macropad.display.width / 2,
                macropad.display.height / 2,
            ),
            anchor_point=(1 / 2, 0.5),
            scale=2,
        )
    )

    group.append(
        label.Label(
            terminalio.FONT,
            text="",
            color=0xFFFFFF,
            anchored_position=(
                macropad.display.width / 2,
                macropad.display.height - 12,
            ),
            anchor_point=(0.5, 0.5),
            scale=1,
        )
    )

    macropad.display.show(group)
    macropad.display.refresh()

    while True:
        # Check key presses ------------------
        event = macropad.keys.events.get()

        if event:
            key_number = event.key_number
            pressed = event.pressed

            if pressed:
                if key_number == 0:
                    data["start_time"] = time.time()
                    data["paused_at"] = 0
                    data["offset"] = 0
                    data["session_ended"] = False
                if key_number == 1:
                    if data["paused_at"] > 0:
                        data["offset"] = data["offset"] + \
                            (data["paused_at"] - data["start_time"])
                        data["start_time"] = time.time()
                        data["paused_at"] = 0
                    else:
                        data["paused_at"] = time.time()

        # exit -------------------------------------
        pos = macropad.encoder

        if not pos == encoder_position:
            return

        # Calculate time difference ---------------
        if not data["start_time"] == None:
            if data["session_ended"]:
                group[2].text = "00:00"
                continue

            if data["paused_at"] > 0:
                diff = data["paused_at"] - data["start_time"] + data["offset"]
            else:
                diff = time.time() - data["start_time"] + data["offset"]

            idx = data["session_count"] % len(sequence)

            diff = sequence[idx]["duration"] - diff

            if(diff <= 0):
                macropad.play_tone(262, 0.5)
                data["session_ended"] = True
                data["session_count"] = data["session_count"] + 1
                diff = 0

            minutes = diff // 60
            seconds = diff % 60

            formatted_minutes = "{:02d}".format(minutes)
            formatted_seconds = "{:02d}".format(seconds)

            group[3].text = sequence[idx]["title"]
            group[2].text = "{0}:{1}".format(
                formatted_minutes, formatted_seconds)

            macropad.display.refresh()


app = {
    'name': 'Pomodoro',
    'macros': [],
    'custom_func': Pomodoro,
    'custom_data': data
}
