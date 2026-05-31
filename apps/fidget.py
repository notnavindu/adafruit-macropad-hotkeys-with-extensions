# Macropad OS — Fidget DJ Pad
#
# Keys    → trigger animation from key position; presses stack
# Encoder → rotate: cycle presets
#           short press: return home
#           long press (≥ 0.4 s): cycle OLED display mode
#             D = Dot (1 pixel, default)   C = Circle (5-pixel +)   B = Block (4×4 tile)
#
# A distance lookup table (12 keys × 384 cells) is computed once at first
# import (~100-300 ms), eliminating math.sqrt from the per-frame render loop.

import array
import math
import time
import displayio
import terminalio
from adafruit_display_text import label


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _add_colors(c1, c2):
    return (
        min(255, c1[0] + c2[0]),
        min(255, c1[1] + c2[1]),
        min(255, c1[2] + c2[2]),
    )


# ---------------------------------------------------------------------------
# LED pixel geometry
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
# OLED logical grid constants
# ---------------------------------------------------------------------------
# 32×12 logical cells map to key-space (col 0..2, row 0..3), matching the LED
# coordinate system.

_OLED_W = 32
_OLED_H = 12
_OLED_N = _OLED_W * _OLED_H        # 384 cells total


def _build_tables():
    """Build per-frame lookup tables. Called once at the top of run().

    Returns a ctx tuple passed to _render_oled.  Keeping the tables as
    locals inside run() means they are freed as soon as the user exits
    the app — no permanent RAM cost while other apps are running.

    Uses array.append() throughout to avoid large intermediate Python lists,
    which would each cost ~4-6 KB of temporary heap on CircuitPython.
    """
    import gc
    gc.collect()  # free home-screen objects before allocating

    oled_col = [bx * 2.0 / (_OLED_W - 1) for bx in range(_OLED_W)]
    oled_row = [by * 3.0 / (_OLED_H - 1) for by in range(_OLED_H)]

    oled_cs = array.array('f')
    oled_rs = array.array('f')
    oled_cx = array.array('B')
    oled_cy = array.array('B')
    for i in range(_OLED_N):
        oled_cs.append(oled_col[i % _OLED_W])
        oled_rs.append(oled_row[i // _OLED_W])
        oled_cx.append((i % _OLED_W) * 4 + 2)
        oled_cy.append((i // _OLED_W) * 4 + 2)

    oled_dist = []
    for k in range(12):
        kc = _COL[k]
        kr = _ROW[k]
        row = array.array('f')
        for i in range(_OLED_N):
            dx = oled_col[i % _OLED_W] - kc
            dy = oled_row[i // _OLED_W] - kr
            row.append(math.sqrt(dx * dx + dy * dy))
        oled_dist.append(row)

    del oled_col, oled_row
    gc.collect()
    return oled_dist, oled_cs, oled_rs, oled_cx, oled_cy, bytearray(_OLED_N), bytes(_OLED_N)

# Circle-mode stamp: (dx, dy) offsets from cell centre
_DOT_CIRCLE = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))

# Shared 2-colour palette for both bitmaps (black bg, white pixels)
_BM_PAL = displayio.Palette(2)
_BM_PAL[0] = 0x000000
_BM_PAL[1] = 0xFFFFFF

# Preallocated LED pixel buffer — reused every frame to avoid heap churn
_BLACK      = (0, 0, 0)
_led_pixels = [_BLACK] * 12

# ---------------------------------------------------------------------------
# Display mode
# ---------------------------------------------------------------------------

MODE_DOT    = 0   # default: single pixel per cell
MODE_CIRCLE = 1   # 5-pixel plus per cell
MODE_BLOCK  = 2   # 4×4 solid tile per cell (via scale=4 bitmap)
_MODE_SUFFIX = (" D", " C", " B")
_LONG_PRESS  = 0.4   # seconds for long encoder press

# ---------------------------------------------------------------------------
# Animation types (integer IDs stored in PRESETS instead of function refs)
# ---------------------------------------------------------------------------

ANIM_RIPPLE  = 0
ANIM_BURST   = 1
ANIM_XHAIR   = 2
ANIM_CASCADE = 3
ANIM_WAVE    = 4
ANIM_FLASH   = 5
ANIM_DRIPPLE = 6

# Precomputed constants — replace divisions in the hot loop
DURATION  = 0.7
_IDR      = 1.0 / DURATION           # ≈ 1.4286
_IDURP8   = 1.0 / (DURATION * 0.8)   # ≈ 1.786   (burst)
_IDURP75  = 1.0 / (DURATION * 0.75)  # ≈ 1.905   (cascade)
_WAVE_K   = math.pi * 1.5 / DURATION  # ≈ 6.732   (wave sin frequency)
_SQTHR    = 0.388                     # sqrt(0.15) — threshold where fade²>0.15


# ---------------------------------------------------------------------------
# LED animation functions  (12-pixel output, function-call pattern unchanged)
# ---------------------------------------------------------------------------

def _anim_ripple(px, src, age, palette):
    d = _dist(px, src)
    diff = abs(d - age * 4.5)
    if diff > 0.9:
        return (0, 0, 0)
    brightness = (1.0 - diff * 1.111) * (1.0 - age * _IDR)
    c1, c2 = palette
    color = _lerp_color(c1, c2, (d / 2.5) % 1.0)
    return (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness))


def _anim_burst(px, src, age, palette):
    d = _dist(px, src)
    la = age - d * 0.06
    if la < 0:
        return (0, 0, 0)
    fade = max(0.0, 1.0 - la * _IDURP8)
    brightness = fade * fade
    c1, c2 = palette
    color = _lerp_color(c1, c2, min(1.0, d / 2.5))
    return (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness))


def _anim_crosshair(px, src, age, palette):
    same_col = _COL[px] == _COL[src]
    same_row = _ROW[px] == _ROW[src]
    if not (same_col or same_row):
        return (0, 0, 0)
    brightness = max(0.0, 1.0 - age * _IDR) ** 2
    c1, c2 = palette
    color = c1 if same_col and same_row else (c1 if same_col else c2)
    return (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness))


def _anim_cascade(px, src, age, palette):
    src_row = _ROW[src]
    px_row  = _ROW[px]
    if px_row < src_row:
        return (0, 0, 0)
    la = age - (px_row - src_row) * 0.12
    if la < 0:
        return (0, 0, 0)
    fade = max(0.0, 1.0 - la * _IDURP75)
    c1, c2 = palette
    color = _lerp_color(c1, c2, min(1.0, (px_row - src_row) / 3.0))
    return (int(color[0] * fade), int(color[1] * fade), int(color[2] * fade))


def _anim_wave(px, src, age, palette):
    la = age - abs(_COL[px] - _COL[src]) * 0.10
    if la < 0:
        return (0, 0, 0)
    brightness = max(0.0, math.sin(la * _WAVE_K)) * max(0.0, 1.0 - age * _IDR)
    c1, c2 = palette
    color = _lerp_color(c1, c2, abs(_COL[px] - _COL[src]) / 2.0)
    return (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness))


def _anim_flash_all(px, src, age, palette):
    brightness = max(0.0, 1.0 - age * _IDR) ** 2
    c1, _ = palette
    return (int(c1[0] * brightness), int(c1[1] * brightness), int(c1[2] * brightness))


def _anim_double_ripple(px, src, age, palette):
    d = _dist(px, src)
    fade = max(0.0, 1.0 - age * _IDR)
    c1, c2 = palette
    result = (0, 0, 0)
    for ring_i, color in enumerate((c1, c2)):
        rp = age * 4.0 - ring_i * 0.7
        diff = abs(d - rp)
        if diff < 0.8:
            brightness = (1.0 - diff * 1.25) * fade
            result = _add_colors(result, (
                int(color[0] * brightness),
                int(color[1] * brightness),
                int(color[2] * brightness),
            ))
    return result


# ---------------------------------------------------------------------------
# Presets: (name, led_anim_fn, oled_anim_type, palette, press_color)
# ---------------------------------------------------------------------------

_RED = (255, 0, 0)

PRESETS = [
    ("Neon Ripple",    _anim_ripple,        ANIM_RIPPLE,  ((0, 255, 255), (255, 0, 255)),    None),
    ("Fire Ripple",    _anim_ripple,        ANIM_RIPPLE,  ((255, 80,  0), (255, 200, 0)),    None),
    ("Ocean Ripple",   _anim_ripple,        ANIM_RIPPLE,  ((0,  80, 255), (0,  220, 200)),   None),
    ("White Ripple",   _anim_ripple,        ANIM_RIPPLE,  ((255, 255, 255), (200, 200, 255)), _RED),
    ("Neon Burst",     _anim_burst,         ANIM_BURST,   ((0, 255, 255), (255, 255, 255)),  None),
    ("Fire Burst",     _anim_burst,         ANIM_BURST,   ((255, 60,  0), (255, 220,  0)),   None),
    ("White Flash",    _anim_flash_all,     ANIM_FLASH,   ((255, 255, 255), (200, 200, 255)), _RED),
    ("Purple Cross",   _anim_crosshair,     ANIM_XHAIR,   ((180,  0, 255), (255,  0, 180)),  None),
    ("Ice Cascade",    _anim_cascade,       ANIM_CASCADE, ((0, 180, 255), (150, 240, 255)),  None),
    ("Acid Wave",      _anim_wave,          ANIM_WAVE,    ((0, 255,  60), (180, 255,   0)),  None),
    ("Lava Burst",     _anim_burst,         ANIM_BURST,   ((255,  0,   0), (180,  0,  50)),  None),
    ("Double Ripple",  _anim_double_ripple, ANIM_DRIPPLE, ((255,  0, 100), (0,  200, 255)),  None),
    ("Sunset Cross",   _anim_crosshair,     ANIM_XHAIR,   ((255, 100,  0), (255, 200,  50)), None),
]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _build_display(macropad, preset_name, preset_index, dot_mode):
    w = macropad.display.width
    group = displayio.Group()

    name_lbl = label.Label(
        terminalio.FONT, text=preset_name, color=0xFFFFFF,
        anchored_position=(2, 1), anchor_point=(0.0, 0.0),
    )
    group.append(name_lbl)   # index 0

    num_lbl = label.Label(
        terminalio.FONT,
        text=f"{preset_index + 1}/{len(PRESETS)}{_MODE_SUFFIX[dot_mode]}",
        color=0xFFFFFF,
        anchored_position=(w - 2, 1), anchor_point=(1.0, 0.0),
    )
    group.append(num_lbl)    # index 1

    # Block bitmap: 32×12 at scale=4 → 128×48 px
    # Both TileGrids share _BM_PAL — no need for two Palette objects.
    block_bm = displayio.Bitmap(_OLED_W, _OLED_H, 2)
    block_grp = displayio.Group(scale=4)
    block_grp.append(displayio.TileGrid(block_bm, pixel_shader=_BM_PAL))
    block_grp.x = 0
    block_grp.y = 13

    # Dot / circle bitmap: 128×48 px, no scale
    dot_bm = displayio.Bitmap(128, 48, 2)
    dot_grp = displayio.Group()
    dot_grp.append(displayio.TileGrid(dot_bm, pixel_shader=_BM_PAL))
    dot_grp.x = 0
    dot_grp.y = 13

    group.append(dot_grp if dot_mode != MODE_BLOCK else block_grp)   # index 2

    return group, name_lbl, num_lbl, block_bm, dot_bm, block_grp, dot_grp


# ---------------------------------------------------------------------------
# OLED render — optimised flat loop, no function calls, no sqrt
# ---------------------------------------------------------------------------
# Strategy:
#   • Event-outer / cell-inner loops: per-event constants (ring_pos, fade, …)
#     are computed once before the 384-cell inner loop.
#   • Animation math is inlined — no Python function calls inside the loop.
#   • _OLED_DIST[key] holds precomputed distances, so no sqrt at render time.
#   • _oled_flags[:] = _ZERO_FLAGS is a C-speed memset of the flag buffer.

def _render_oled(oled_type, active_events, now, dot_mode, block_bm, dot_bm, ctx):
    # ctx = (oled_dist, oled_cs, oled_rs, oled_cx, oled_cy, oled_flags, zero_flags)
    oled_dist, oled_cs, oled_rs, oled_cx, oled_cy, oled_flags, zero_flags = ctx
    oled_flags[:] = zero_flags   # fast C memset

    if oled_type == ANIM_RIPPLE:
        for src_key, start in active_events:
            age = now - start
            fd  = 1.0 - age * _IDR
            if fd > 0.15:
                rp   = age * 4.5
                rl   = rp - 0.9
                rh   = rp + 0.9
                drow = oled_dist[src_key]
                for i in range(_OLED_N):
                    d = drow[i]
                    if rl <= d <= rh:
                        oled_flags[i] = 1

    elif oled_type == ANIM_BURST:
        for src_key, start in active_events:
            age  = now - start
            drow = oled_dist[src_key]
            for i in range(_OLED_N):
                la = age - drow[i] * 0.06
                if la > 0 and 1.0 - la * _IDURP8 > _SQTHR:
                    oled_flags[i] = 1

    elif oled_type == ANIM_XHAIR:
        for src_key, start in active_events:
            age = now - start
            fd  = 1.0 - age * _IDR
            if fd * fd > 0.15:
                sc = _COL[src_key]
                sr = _ROW[src_key]
                for i in range(_OLED_N):
                    if abs(oled_cs[i] - sc) < 0.2 or abs(oled_rs[i] - sr) < 0.4:
                        oled_flags[i] = 1

    elif oled_type == ANIM_CASCADE:
        for src_key, start in active_events:
            age = now - start
            sr  = _ROW[src_key]
            for i in range(_OLED_N):
                rs = oled_rs[i]
                if rs >= sr:
                    la = age - (rs - sr) * 0.12
                    if la > 0 and 1.0 - la * _IDURP75 > 0.15:
                        oled_flags[i] = 1

    elif oled_type == ANIM_WAVE:
        for src_key, start in active_events:
            age  = now - start
            sc   = _COL[src_key]
            fd_o = 1.0 - age * _IDR
            if fd_o > 0:
                for i in range(_OLED_N):
                    la = age - abs(oled_cs[i] - sc) * 0.10
                    if la > 0:
                        pv = math.sin(la * _WAVE_K)
                        if pv > 0 and pv * fd_o > 0.15:
                            oled_flags[i] = 1

    elif oled_type == ANIM_FLASH:
        for src_key, start in active_events:
            age = now - start
            fd  = 1.0 - age * _IDR
            if fd * fd > 0.15:
                for i in range(_OLED_N):
                    oled_flags[i] = 1
                break   # all cells lit — no need to process more events

    elif oled_type == ANIM_DRIPPLE:
        for src_key, start in active_events:
            age  = now - start
            fd   = 1.0 - age * _IDR
            if fd > 0.15:
                sp4  = age * 4.0
                drow = oled_dist[src_key]
                for ring_i in range(2):
                    rp = sp4 - ring_i * 0.7
                    rl = rp - 0.8
                    rh = rp + 0.8
                    if rh >= 0:
                        for i in range(_OLED_N):
                            d = drow[i]
                            if rl <= d <= rh:
                                diff = d - rp
                                if diff < 0:
                                    diff = -diff
                                if (1.0 - diff * 1.25) * fd > 0.15:
                                    oled_flags[i] = 1

    # Write flags → bitmap
    if dot_mode == MODE_BLOCK:
        block_bm.fill(0)
        for i in range(_OLED_N):
            if oled_flags[i]:
                block_bm[i & 31, i >> 5] = 1   # i % _OLED_W, i // _OLED_W
    elif dot_mode == MODE_DOT:
        dot_bm.fill(0)
        for i in range(_OLED_N):
            if oled_flags[i]:
                dot_bm[oled_cx[i], oled_cy[i]] = 1
    else:   # MODE_CIRCLE
        dot_bm.fill(0)
        for i in range(_OLED_N):
            if oled_flags[i]:
                cx = oled_cx[i]
                cy = oled_cy[i]
                for ddx, ddy in _DOT_CIRCLE:
                    dot_bm[cx + ddx, cy + ddy] = 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(macropad):
    _ctx = _build_tables()
    preset_index = 0
    last_encoder = macropad.encoder
    dot_mode     = MODE_DOT     # user-preferred default

    active_events   = []
    held_keys       = set()
    oled_was_active = False
    enc_press_time  = None

    group, name_lbl, num_lbl, block_bm, dot_bm, block_grp, dot_grp = (
        _build_display(macropad, PRESETS[preset_index][0], preset_index, dot_mode)
    )
    macropad.display.root_group = group
    macropad.pixels.fill(0)
    macropad.pixels.show()
    macropad.display.refresh()

    while True:
        now = time.monotonic()

        # --- Encoder button: short press = exit, long press = cycle OLED mode ---
        macropad.encoder_switch_debounced.update()

        if macropad.encoder_switch_debounced.pressed:
            enc_press_time = now

        if macropad.encoder_switch_debounced.released:
            if enc_press_time is not None:
                held_for = now - enc_press_time
                enc_press_time = None
                if held_for < _LONG_PRESS:
                    macropad.pixels.fill(0)
                    macropad.pixels.show()
                    return
                # Long press → cycle mode
                old_mode = dot_mode
                dot_mode = (dot_mode + 1) % 3
                num_lbl.text = (
                    f"{preset_index + 1}/{len(PRESETS)}{_MODE_SUFFIX[dot_mode]}"
                )
                # Only swap group[2] when crossing the dot/circle ↔ block boundary.
                # Re-inserting an already-mounted group crashes CircuitPython.
                if (old_mode == MODE_BLOCK) != (dot_mode == MODE_BLOCK):
                    group[2] = block_grp if dot_mode == MODE_BLOCK else dot_grp
                block_bm.fill(0)
                dot_bm.fill(0)
                oled_was_active = False
                macropad.display.refresh()

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
            num_lbl.text  = (
                f"{preset_index + 1}/{len(PRESETS)}{_MODE_SUFFIX[dot_mode]}"
            )
            block_bm.fill(0)
            dot_bm.fill(0)
            oled_was_active = False
            macropad.display.refresh()

        # --- Key events ---
        event = macropad.keys.events.get()
        if event:
            if event.pressed:
                active_events.append((event.key_number, now))  # tuple: immutable, smaller
                held_keys.add(event.key_number)
            else:
                held_keys.discard(event.key_number)

        # --- Prune expired events (in-place, front-to-back — no new list) ---
        # Events are appended in timestamp order so expired ones are always at the front.
        _cutoff = now - DURATION
        _ei = 0
        while _ei < len(active_events) and active_events[_ei][1] < _cutoff:
            _ei += 1
        if _ei:
            del active_events[:_ei]

        # --- LED render ---
        _, anim_fn, oled_type, palette, press_color = PRESETS[preset_index]

        if active_events:
            for _pi in range(12):             # reset preallocated buffer in-place
                _led_pixels[_pi] = _BLACK
            for src_key, start in active_events:
                age = now - start
                for px in range(12):
                    _led_pixels[px] = _add_colors(
                        _led_pixels[px], anim_fn(px, src_key, age, palette)
                    )
            if press_color is not None:
                for src_key, _ in active_events:
                    if src_key in held_keys:
                        _led_pixels[src_key] = press_color
            for i in range(12):
                macropad.pixels[i] = _led_pixels[i]
        else:
            macropad.pixels.fill(0)

        macropad.pixels.show()

        # --- OLED render ---
        if active_events:
            oled_was_active = True
            _render_oled(oled_type, active_events, now, dot_mode, block_bm, dot_bm, _ctx)
            macropad.display.refresh()
        elif oled_was_active:
            oled_was_active = False
            block_bm.fill(0)
            dot_bm.fill(0)
            macropad.display.refresh()


app = {
    "name": "Fidget",
    "run":  run,
}
