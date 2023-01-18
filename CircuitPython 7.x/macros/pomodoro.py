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
    "boot_at": None,
    "start_time": None,
    "paused_at": 0,
    "offset": 0,  # used for pausing and resuming
    "session_count": 0,
    "session_ended": False,
    "total_focused": 0,
    "total_sessions": 0,
}

# constants
WORK_SESSION = {
    "duration": 25 * 60,
    "title": "FOCUS",
    "focus": True,  # Required to calculate "Total sessions" and "total focused"
}
SHORT_BREAK = {"duration": 5 * 60, "title": "SHORT BREAK", "focus": False}
LONG_BREAK = {"duration": 15 * 60, "title": "LONG BREAK", "focus": False}

sequence = [
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    SHORT_BREAK,
    WORK_SESSION,
    LONG_BREAK,
]


def seconds_to_hours_minutes(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return (hours, minutes)


def lightPulse(macropad):
    for i in range(0, 8):
        macropad.pixels.fill((0, 0, 0))
        macropad.pixels.show()

        rowId = (i % 4) * 3
        macropad.pixels[rowId] = (255, 255, 255)
        macropad.pixels[rowId + 1] = (255, 255, 255)
        macropad.pixels[rowId + 2] = (255, 255, 255)
        macropad.pixels.show()
        time.sleep(0.1)

    # reset to original colors
    macropad.pixels.fill((0, 0, 0))
    macropad.pixels[0] = (27, 148, 0)
    macropad.pixels[1] = (252, 186, 3)
    macropad.pixels[2] = (255, 0, 0)
    macropad.pixels.show()


def Pomodoro(macropad, encoder_position):
    # Save boot time to later calculate the "slacking" time
    if data["boot_at"] is None:
        data["boot_at"] = time.time()
    # Set neopixel colors
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
            line_spacing=0.8,
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

                    # prolly need a cleaner way to do this
                    group[2].scale = 2
                if key_number == 1:
                    if data["paused_at"] > 0:
                        data["offset"] = data["offset"] + (
                            data["paused_at"] - data["start_time"]
                        )
                        data["start_time"] = time.time()
                        data["paused_at"] = 0
                    else:
                        data["paused_at"] = time.time()
                if key_number == 2:
                    data["session_ended"] = True
                    diff = 0
                    data["session_count"] = data["session_count"] + 1
                    lightPulse(macropad)

        # exit -------------------------------------
        pos = macropad.encoder

        if not pos == encoder_position:
            return

        # Calculate time difference ---------------
        if not data["start_time"] is None:
            idx = data["session_count"] % len(sequence)

            if data["session_ended"]:
                _h, _m = seconds_to_hours_minutes(data["total_focused"])

                slacking_dur = time.time() - \
                    data["boot_at"] - data["total_focused"]
                slack_h, slack_m = seconds_to_hours_minutes(slacking_dur)

                stat_text = f"{_h}h {_m}m focused ({data['total_sessions']})"
                stat_text = stat_text + f"\n {slack_h}h {slack_m}m slacking"

                group[2].text = stat_text

                group[2].scale = 1

                group[3].text = f"Next: {sequence[idx]['title']}"
                macropad.display.refresh()
                continue

            if data["paused_at"] > 0:
                diff = data["paused_at"] - data["start_time"] + data["offset"]
            else:
                diff = time.time() - data["start_time"] + data["offset"]

            diff = sequence[idx]["duration"] - diff

            # this means the timer has ended
            if diff <= 0:
                macropad.play_tone(255, 1)
                macropad.play_tone(255, 1)

                data["session_ended"] = True
                data["session_count"] = data["session_count"] + 1

                if sequence[idx]["focus"]:
                    data["total_focused"] = (
                        data["total_focused"] + WORK_SESSION["duration"]
                    )
                    data["total_sessions"] = data["total_sessions"] + 1

                diff = 0

                # Do a little visual indication
                lightPulse(macropad)
                lightPulse(macropad)

            minutes = diff // 60
            seconds = diff % 60

            formatted_minutes = "{:02d}".format(minutes)
            formatted_seconds = "{:02d}".format(seconds)

            group[3].text = sequence[idx]["title"]
            group[2].text = "{0}:{1}".format(
                formatted_minutes, formatted_seconds)

            macropad.display.refresh()


app = {"name": "Pomodoro",
       "macros": [],
       "custom_func": Pomodoro,
       "custom_data": data
       }
