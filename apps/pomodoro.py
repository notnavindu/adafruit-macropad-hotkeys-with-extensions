# Macropad OS — Pomodoro Timer
# A focus timer that tracks work sessions and breaks.
#
# Keys (when running):
#   Key 0 (green)  — Start / restart current session
#   Key 1 (yellow) — Pause / resume
#   Key 2 (red)    — Skip to next session
#
# Press the encoder knob at any time to return to the home screen.
# State persists between visits (timer keeps its session count, etc.).

import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from screensaver import SleepManager
try:
    import config as _cfg
except ImportError:
    class _cfg:
        SLEEP_ENABLED = True
        SLEEP_TIMEOUT = 60
        SCREENSAVER   = "bounce"

# ---------------------------------------------------------------------------
# Session sequence (edit durations in seconds)
# ---------------------------------------------------------------------------

WORK_SESSION  = {"duration": 25 * 60, "title": "FOCUS",       "focus": True}
SHORT_BREAK   = {"duration":  5 * 60, "title": "SHORT BREAK",  "focus": False}
LONG_BREAK    = {"duration": 15 * 60, "title": "LONG BREAK",   "focus": False}

SEQUENCE = [
    WORK_SESSION, SHORT_BREAK,
    WORK_SESSION, SHORT_BREAK,
    WORK_SESSION, SHORT_BREAK,
    WORK_SESSION, LONG_BREAK,
]

# ---------------------------------------------------------------------------
# Persistent state — survives navigating away and back
# ---------------------------------------------------------------------------

state = {
    "boot_at":        None,
    "start_time":     None,
    "paused_at":      0,
    "offset":         0,
    "session_count":  0,
    "session_ended":  False,
    "total_focused":  0,
    "total_sessions": 0,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_hm(seconds):
    m, _ = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return h, m


def _light_pulse(macropad):
    for i in range(8):
        macropad.pixels.fill((0, 0, 0))
        row = (i % 4) * 3
        macropad.pixels[row]     = (255, 255, 255)
        macropad.pixels[row + 1] = (255, 255, 255)
        macropad.pixels[row + 2] = (255, 255, 255)
        macropad.pixels.show()
        time.sleep(0.1)
    macropad.pixels.fill((0, 0, 0))
    macropad.pixels[0] = (27, 148, 0)
    macropad.pixels[1] = (252, 186, 3)
    macropad.pixels[2] = (255, 0, 0)
    macropad.pixels.show()


def _build_display(macropad):
    group = displayio.Group()
    group.append(Rect(0, 0, macropad.display.width, 12, fill=0xFFFFFF))
    group.append(
        label.Label(terminalio.FONT, text="Pomodoro", color=0x000000,
                    anchored_position=(macropad.display.width // 2, -2),
                    anchor_point=(0.5, 0.0))
    )
    # Timer / stat text (large)
    group.append(
        label.Label(terminalio.FONT, text="Press 1 to start", color=0xFFFFFF,
                    line_spacing=0.8,
                    anchored_position=(macropad.display.width / 2,
                                       macropad.display.height / 2),
                    anchor_point=(0.5, 0.5), scale=1)
    )
    # Sub-label (session name or next-session hint)
    group.append(
        label.Label(terminalio.FONT, text="", color=0xAAAAAA,
                    anchored_position=(macropad.display.width / 2,
                                       macropad.display.height - 4),
                    anchor_point=(0.5, 1.0))
    )
    return group  # group[2] = main text, group[3] = sub text

# ---------------------------------------------------------------------------
# Entry point called by Macropad OS
# ---------------------------------------------------------------------------

def _set_pixels(macropad):
    macropad.pixels.fill((0, 0, 0))
    macropad.pixels[0] = (27, 148, 0)
    macropad.pixels[1] = (252, 186, 3)
    macropad.pixels[2] = (255, 0, 0)
    macropad.pixels.show()


def run(macropad):
    if state["boot_at"] is None:
        state["boot_at"] = time.time()

    _set_pixels(macropad)

    group = _build_display(macropad)
    macropad.display.root_group = group
    macropad.display.refresh()

    sleep = SleepManager(_cfg)

    while True:
        # Sleep/wake tick — returns True on the frame the screen wakes up.
        woke = sleep.tick(macropad)
        if woke:
            macropad.display.root_group = group
            macropad.display.refresh()
            _set_pixels(macropad)
            continue  # skip input handling on the wake frame
        if sleep.sleeping:
            continue

        # Encoder press → exit to home
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            sleep.force_stop(macropad)
            return

        # Key handling
        event = macropad.keys.events.get()
        if event and event.pressed:
            sleep.notify_input()
            k = event.key_number

            if k == 0:  # Start / restart
                state["start_time"]    = time.time()
                state["paused_at"]     = 0
                state["offset"]        = 0
                state["session_ended"] = False
                group[2].scale = 2

            elif k == 1:  # Pause / resume
                if state["paused_at"] > 0:
                    state["offset"]    += state["paused_at"] - state["start_time"]
                    state["start_time"] = time.time()
                    state["paused_at"]  = 0
                else:
                    state["paused_at"] = time.time()

            elif k == 2:  # Skip session
                state["session_ended"]  = True
                state["session_count"] += 1
                _light_pulse(macropad)

        if state["start_time"] is None:
            continue

        idx = state["session_count"] % len(SEQUENCE)

        # Show summary after session ends
        if state["session_ended"]:
            fh, fm = _fmt_hm(state["total_focused"])
            elapsed = time.time() - state["boot_at"] - state["total_focused"]
            sh, sm = _fmt_hm(elapsed)
            group[2].scale = 1
            group[2].text  = f"{fh}h{fm}m focus ({state['total_sessions']})"
            group[3].text  = f"slack {sh}h{sm}m | next: {SEQUENCE[idx]['title'][:5]}"
            macropad.display.refresh()
            continue

        # Running / paused countdown
        if state["paused_at"] > 0:
            diff = state["paused_at"] - state["start_time"] + state["offset"]
        else:
            diff = time.time() - state["start_time"] + state["offset"]

        diff = SEQUENCE[idx]["duration"] - diff

        if diff <= 0:
            macropad.play_tone(440, 0.3)
            macropad.play_tone(550, 0.3)
            state["session_ended"]  = True
            state["session_count"] += 1
            if SEQUENCE[idx]["focus"]:
                state["total_focused"]  += WORK_SESSION["duration"]
                state["total_sessions"] += 1
            _light_pulse(macropad)
            _light_pulse(macropad)
            diff = 0

        mins = int(diff) // 60
        secs = int(diff) % 60
        group[2].scale = 2
        group[2].text  = f"{mins:02d}:{secs:02d}"
        group[3].text  = SEQUENCE[idx]["title"]
        macropad.display.refresh()


app = {
    "name": "Pomodoro",
    "run":  run,
}
