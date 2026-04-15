# Macropad OS — Fidget DJ Pad
#
# Press any key to trigger a satisfying animation from that key's position.
# Turn the encoder to cycle through presets (animation type + colour palette).
# Press the encoder knob to return to the home screen.
#
# Multiple key presses stack — animations overlap and blend.

import math
import time
import displayio
import terminalio
from adafruit_display_text import label


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _lerp_color(c1, c2, t):
    """Linearly interpolate between two (r,g,b) colours."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _add_colors(c1, c2):
    """Additive colour blend, capped at 255 per channel."""
    return (
        min(255, c1[0] + c2[0]),
        min(255, c1[1] + c2[1]),
        min(255, c1[2] + c2[2]),
    )


# ---------------------------------------------------------------------------
# LED pixel geometry helpers
# ---------------------------------------------------------------------------
# Grid layout (col, row):
#   0(0,0)  1(1,0)  2(2,0)
#   3(0,1)  4(1,1)  5(2,1)
#   6(0,2)  7(1,2)  8(2,2)
#   9(0,3) 10(1,3) 11(2,3)

_COL = [i % 3 for i in range(12)]
_ROW = [i // 3 for i in range(12)]


def _dist(key_a, key_b):
    dx = _COL[key_a] - _COL[key_b]
    dy = _ROW[key_a] - _ROW[key_b]
    return math.sqrt(dx * dx + dy * dy)


# ---------------------------------------------------------------------------
# OLED bitmap coordinate system
# ---------------------------------------------------------------------------
# The animation canvas is a Bitmap rendered at scale=4, giving 32x12 "macro-
# pixels" that fill the 128×48 px area below the header labels. Each macro-
# pixel maps to the same continuous key-space (col 0..2, row 0..3) used by
# the LED animations, so all animation math runs identically on both outputs.

_OLED_W = 32   # bitmap columns  (×4 scale → 128 screen px)
_OLED_H = 12   # bitmap rows     (×4 scale →  48 screen px)

# Precomputed key-space position for each bitmap column / row
_OLED_COL = [bx * 2.0 / (_OLED_W - 1) for bx in range(_OLED_W)]
_OLED_ROW = [by * 3.0 / (_OLED_H - 1) for by in range(_OLED_H)]


def _oled_dist(bx, by, src):
    """Distance from bitmap cell (bx, by) to source key, in key-space units."""
    dx = _OLED_COL[bx] - _COL[src]
    dy = _OLED_ROW[by] - _ROW[src]
    return math.sqrt(dx * dx + dy * dy)


# ---------------------------------------------------------------------------
# LED animation functions
# Each receives (pixel_index, src_key, age, palette) and returns (r,g,b).
# age = seconds since key was pressed.  duration = total life of event.
# ---------------------------------------------------------------------------

DURATION = 0.7


def _anim_ripple(px, src, age, palette):
    """Expanding ring of colour from the source key."""
    d = _dist(px, src)
    ring_pos = age * 4.5
    ring_width = 0.9
    diff = abs(d - ring_pos)
    if diff > ring_width:
        return (0, 0, 0)
    fade = 1.0 - (age / DURATION)
    brightness = (1.0 - diff / ring_width) * fade
    c1, c2 = palette
    t = (d / 2.5) % 1.0
    color = _lerp_color(c1, c2, t)
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def _anim_burst(px, src, age, palette):
    """Instantaneous bright flash that fades faster the farther from source."""
    d = _dist(px, src)
    delay = d * 0.06
    local_age = age - delay
    if local_age < 0:
        return (0, 0, 0)
    fade = max(0.0, 1.0 - local_age / (DURATION * 0.8))
    brightness = fade * fade
    c1, c2 = palette
    frac = min(1.0, d / 2.5)
    color = _lerp_color(c1, c2, frac)
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def _anim_crosshair(px, src, age, palette):
    """Row and column of the source key flash and fade."""
    same_col = _COL[px] == _COL[src]
    same_row = _ROW[px] == _ROW[src]
    if not (same_col or same_row):
        return (0, 0, 0)
    fade = max(0.0, 1.0 - age / DURATION)
    brightness = fade * fade
    c1, c2 = palette
    color = c1 if same_col and same_row else (c1 if same_col else c2)
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def _anim_cascade(px, src, age, palette):
    """Light cascades downward from the source key's row."""
    src_row = _ROW[src]
    px_row  = _ROW[px]
    if px_row < src_row:
        return (0, 0, 0)
    row_delay = (px_row - src_row) * 0.12
    local_age = age - row_delay
    if local_age < 0:
        return (0, 0, 0)
    fade = max(0.0, 1.0 - local_age / (DURATION * 0.75))
    brightness = fade
    c1, c2 = palette
    frac = (px_row - src_row) / 3.0
    color = _lerp_color(c1, c2, min(1.0, frac))
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def _anim_wave(px, src, age, palette):
    """Horizontal wave sweeps left-to-right from the source key's column."""
    src_col = _COL[src]
    px_col  = _COL[px]
    col_delay = abs(px_col - src_col) * 0.10
    local_age = age - col_delay
    if local_age < 0:
        return (0, 0, 0)
    phase = math.sin(local_age * math.pi / DURATION * 1.5)
    brightness = max(0.0, phase) * max(0.0, 1.0 - age / DURATION)
    c1, c2 = palette
    frac = abs(px_col - src_col) / 2.0
    color = _lerp_color(c1, c2, frac)
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def _anim_flash_all(px, src, age, palette):
    """All keys flash white together on any press."""
    fade = max(0.0, 1.0 - age / DURATION)
    brightness = fade * fade
    c1, _ = palette
    return (
        int(c1[0] * brightness),
        int(c1[1] * brightness),
        int(c1[2] * brightness),
    )


def _anim_double_ripple(px, src, age, palette):
    """Two concentric ripple rings, different colours."""
    d = _dist(px, src)
    speed = 4.0
    fade = max(0.0, 1.0 - age / DURATION)
    c1, c2 = palette
    result = (0, 0, 0)
    for ring_i, color in enumerate((c1, c2)):
        ring_pos = age * speed - ring_i * 0.7
        ring_width = 0.8
        diff = abs(d - ring_pos)
        if diff < ring_width:
            brightness = (1.0 - diff / ring_width) * fade
            contrib = (
                int(color[0] * brightness),
                int(color[1] * brightness),
                int(color[2] * brightness),
            )
            result = _add_colors(result, contrib)
    return result


# ---------------------------------------------------------------------------
# OLED animation functions
# Each receives (bx, by, src_key, age) and returns a brightness float 0..1.
# The math mirrors the LED functions but operates on continuous key-space
# coordinates so shapes expand smoothly across the full bitmap canvas.
# ---------------------------------------------------------------------------

def _oled_ripple(bx, by, src, age):
    d = _oled_dist(bx, by, src)
    ring_pos = age * 4.5
    ring_width = 0.9
    diff = abs(d - ring_pos)
    if diff > ring_width:
        return 0.0
    fade = 1.0 - (age / DURATION)
    return (1.0 - diff / ring_width) * fade


def _oled_burst(bx, by, src, age):
    d = _oled_dist(bx, by, src)
    delay = d * 0.06
    local_age = age - delay
    if local_age < 0:
        return 0.0
    fade = max(0.0, 1.0 - local_age / (DURATION * 0.8))
    return fade * fade


def _oled_crosshair(bx, by, src, age):
    cx = _OLED_COL[bx]
    cy = _OLED_ROW[by]
    # Thresholds tuned so the lines are ~2-3 macro-pixels wide on screen
    same_col = abs(cx - _COL[src]) < 0.2
    same_row = abs(cy - _ROW[src]) < 0.4
    if not (same_col or same_row):
        return 0.0
    fade = max(0.0, 1.0 - age / DURATION)
    return fade * fade


def _oled_cascade(bx, by, src, age):
    cy = _OLED_ROW[by]
    src_row = _ROW[src]
    if cy < src_row:
        return 0.0
    row_delay = (cy - src_row) * 0.12
    local_age = age - row_delay
    if local_age < 0:
        return 0.0
    fade = max(0.0, 1.0 - local_age / (DURATION * 0.75))
    return fade


def _oled_wave(bx, by, src, age):
    cx = _OLED_COL[bx]
    src_col = _COL[src]
    col_delay = abs(cx - src_col) * 0.10
    local_age = age - col_delay
    if local_age < 0:
        return 0.0
    phase = math.sin(local_age * math.pi / DURATION * 1.5)
    return max(0.0, phase) * max(0.0, 1.0 - age / DURATION)


def _oled_flash_all(bx, by, src, age):
    fade = max(0.0, 1.0 - age / DURATION)
    return fade * fade


def _oled_double_ripple(bx, by, src, age):
    d = _oled_dist(bx, by, src)
    speed = 4.0
    fade = max(0.0, 1.0 - age / DURATION)
    result = 0.0
    for ring_i in range(2):
        ring_pos = age * speed - ring_i * 0.7
        ring_width = 0.8
        diff = abs(d - ring_pos)
        if diff < ring_width:
            result = min(1.0, result + (1.0 - diff / ring_width) * fade)
    return result


# ---------------------------------------------------------------------------
# Presets: (name, led_anim_fn, oled_anim_fn, palette, press_color)
# palette      — two (r,g,b) colours used by the LED animation.
# press_color  — colour to force on a held-down source key, or None.
# ---------------------------------------------------------------------------

_RED = (255, 0, 0)

PRESETS = [
    ("Neon Ripple",    _anim_ripple,        _oled_ripple,        ((0, 255, 255), (255, 0, 255)),    None),
    ("Fire Ripple",    _anim_ripple,        _oled_ripple,        ((255, 80,  0), (255, 200, 0)),    None),
    ("Ocean Ripple",   _anim_ripple,        _oled_ripple,        ((0,  80, 255), (0,  220, 200)),   None),
    ("White Ripple",   _anim_ripple,        _oled_ripple,        ((255, 255, 255), (200, 200, 255)), _RED),
    ("Neon Burst",     _anim_burst,         _oled_burst,         ((0, 255, 255), (255, 255, 255)),  None),
    ("Fire Burst",     _anim_burst,         _oled_burst,         ((255, 60,  0), (255, 220,  0)),   None),
    ("White Flash",    _anim_flash_all,     _oled_flash_all,     ((255, 255, 255), (200, 200, 255)), _RED),
    ("Purple Cross",   _anim_crosshair,     _oled_crosshair,     ((180,  0, 255), (255,  0, 180)),  None),
    ("Ice Cascade",    _anim_cascade,       _oled_cascade,       ((0, 180, 255), (150, 240, 255)),  None),
    ("Acid Wave",      _anim_wave,          _oled_wave,          ((0, 255,  60), (180, 255,   0)),  None),
    ("Lava Burst",     _anim_burst,         _oled_burst,         ((255,  0,   0), (180,  0,  50)),  None),
    ("Double Ripple",  _anim_double_ripple, _oled_double_ripple, ((255,  0, 100), (0,  200, 255)),  None),
    ("Sunset Cross",   _anim_crosshair,     _oled_crosshair,     ((255, 100,  0), (255, 200,  50)), None),
]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _build_display(macropad, preset_name, preset_index):
    w = macropad.display.width

    group = displayio.Group()

    # Preset name — top-left, white on black
    name_lbl = label.Label(
        terminalio.FONT,
        text=preset_name,
        color=0xFFFFFF,
        anchored_position=(2, 1),
        anchor_point=(0.0, 0.0),
    )
    group.append(name_lbl)  # index 0

    # Counter — top-right, white on black
    num_lbl = label.Label(
        terminalio.FONT,
        text=f"{preset_index + 1}/{len(PRESETS)}",
        color=0xFFFFFF,
        anchored_position=(w - 2, 1),
        anchor_point=(1.0, 0.0),
    )
    group.append(num_lbl)  # index 1

    # Animation canvas — 32×12 Bitmap rendered at 4× scale → 128×48 px
    bitmap = displayio.Bitmap(_OLED_W, _OLED_H, 2)
    bm_palette = displayio.Palette(2)
    bm_palette[0] = 0x000000  # off (black bg)
    bm_palette[1] = 0xFFFFFF  # on  (white pixel)
    tg = displayio.TileGrid(bitmap, pixel_shader=bm_palette)
    anim_group = displayio.Group(scale=4)
    anim_group.append(tg)
    anim_group.x = 0
    anim_group.y = 13  # leaves ~1 px gap below the label row
    group.append(anim_group)  # index 2

    return group, name_lbl, num_lbl, bitmap


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(macropad):
    preset_index = 0
    last_encoder = macropad.encoder

    # active_events: list of [src_key, start_time]
    active_events = []
    # keys currently held down
    held_keys = set()
    # track whether the OLED had content last frame (for efficient clearing)
    oled_was_active = False

    group, name_lbl, num_lbl, bitmap = _build_display(
        macropad, PRESETS[preset_index][0], preset_index
    )
    macropad.display.root_group = group
    macropad.pixels.fill(0)
    macropad.pixels.show()
    macropad.display.refresh()

    while True:
        now = time.monotonic()

        # --- Encoder press → exit ---
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            macropad.pixels.fill(0)
            macropad.pixels.show()
            return

        # --- Encoder rotate → change preset ---
        enc = macropad.encoder
        if enc != last_encoder:
            delta = 1 if enc > last_encoder else -1
            preset_index = (preset_index + delta) % len(PRESETS)
            last_encoder = enc
            active_events.clear()
            held_keys.clear()
            macropad.pixels.fill(0)
            macropad.pixels.show()
            name_lbl.text = PRESETS[preset_index][0]
            num_lbl.text  = f"{preset_index + 1}/{len(PRESETS)}"
            for by in range(_OLED_H):
                for bx in range(_OLED_W):
                    bitmap[bx, by] = 0
            oled_was_active = False
            macropad.display.refresh()

        # --- Key events → spawn animation, track held state ---
        event = macropad.keys.events.get()
        if event:
            if event.pressed:
                active_events.append([event.key_number, now])
                held_keys.add(event.key_number)
            else:
                held_keys.discard(event.key_number)

        # --- Prune expired events ---
        active_events = [e for e in active_events if now - e[1] < DURATION]

        # --- Render LED frame ---
        _, anim_fn, oled_fn, palette, press_color = PRESETS[preset_index]

        if active_events:
            pixels = [(0, 0, 0)] * 12

            for src_key, start in active_events:
                age = now - start
                for px in range(12):
                    contrib = anim_fn(px, src_key, age, palette)
                    pixels[px] = _add_colors(pixels[px], contrib)

            if press_color is not None:
                for src_key, _ in active_events:
                    if src_key in held_keys:
                        pixels[src_key] = press_color

            for i in range(12):
                macropad.pixels[i] = pixels[i]
        else:
            macropad.pixels.fill(0)

        macropad.pixels.show()

        # --- Render OLED bitmap ---
        if active_events:
            oled_was_active = True
            for by in range(_OLED_H):
                for bx in range(_OLED_W):
                    total = 0.0
                    for src_key, start in active_events:
                        age = now - start
                        total += oled_fn(bx, by, src_key, age)
                    bitmap[bx, by] = 1 if total > 0.15 else 0
            macropad.display.refresh()
        elif oled_was_active:
            # Animation just ended — clear canvas once
            oled_was_active = False
            for by in range(_OLED_H):
                for bx in range(_OLED_W):
                    bitmap[bx, by] = 0
            macropad.display.refresh()


app = {
    "name": "Fidget",
    "run":  run,
}
