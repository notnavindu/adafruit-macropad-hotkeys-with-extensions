# Macropad OS — screensaver implementations
# CircuitPython 10 — Adafruit MacroPad RP2040

import random
import time
import displayio


# ---------------------------------------------------------------------------
# NeoPixel row-sweep helper (shared by all screensavers)
# ---------------------------------------------------------------------------

class _PixelSweep:
    """Smooth white line that sweeps down the 4 keypad rows with soft falloff.

    Uses a continuous float position so the glow interpolates between rows
    every frame rather than jumping. No circular wrapping — the sweep fades
    in from above row 0 and fades out below row 3, then pauses in darkness
    before repeating.
    """

    _PEAK_V     = 22    # brightest channel value (keep subtle)
    _SIGMA      = 1.2   # falloff width in rows; controls how wide the glow is
    _SPEED      = 9.0   # rows per second
    _POS_START  = -1.5  # start well before row 0 is visible
    _POS_END    =  4.5  # end well after row 3 fades out
    _PAUSE_S    =  2.0  # dark gap between sweeps

    def __init__(self):
        self._pos         = self._POS_START
        self._last_update = 0.0
        self._pausing     = False
        self._pause_until = 0.0

    def start(self, macropad):
        self._pos         = self._POS_START
        self._pausing     = False
        self._last_update = time.monotonic()
        macropad.pixels.fill(0)
        macropad.pixels.show()

    def tick(self, macropad):
        now = time.monotonic()
        dt  = now - self._last_update
        self._last_update = now

        if self._pausing:
            if now >= self._pause_until:
                self._pausing = False
                self._pos     = self._POS_START
            return

        self._pos += dt * self._SPEED

        if self._pos >= self._POS_END:
            self._pausing     = True
            self._pause_until = now + self._PAUSE_S
            macropad.pixels.fill(0)
            macropad.pixels.show()
            return

        self._render(macropad)

    def _render(self, macropad):
        for key in range(12):
            row  = key // 3
            dist = abs(row - self._pos)
            weight = max(0.0, 1.0 - dist / self._SIGMA)
            v = int(self._PEAK_V * weight)
            macropad.pixels[key] = (v, v, v)
        macropad.pixels.show()

    def stop(self, macropad):
        macropad.pixels.fill(0)
        macropad.pixels.show()


# ---------------------------------------------------------------------------
# BlackScreensaver
# ---------------------------------------------------------------------------

class BlackScreensaver:
    """Turn the display off completely — best burn-in prevention."""

    def start(self, macropad):
        macropad.display.brightness = 0
        self._sweep = _PixelSweep()
        self._sweep.start(macropad)

    def tick(self, macropad):
        self._sweep.tick(macropad)

    def stop(self, macropad):
        macropad.display.brightness = 1.0
        self._sweep.stop(macropad)


# ---------------------------------------------------------------------------
# Shared helper: a full-screen black bitmap for animated screensavers
# ---------------------------------------------------------------------------

def _make_canvas(macropad):
    """Return (group, bitmap, palette) covering the full display."""
    w = macropad.display.width
    h = macropad.display.height
    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = 0xFFFFFF
    bitmap = displayio.Bitmap(w, h, 2)
    tile = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tile)
    return group, bitmap, palette


# ---------------------------------------------------------------------------
# BounceScreensaver
# ---------------------------------------------------------------------------

class BounceScreensaver:
    """A single pixel bouncing around the screen.

    Starting position and direction are randomised each time. Diagonal speed
    combos (1,1), (1,2) and (2,1) give distinct path shapes so repeated
    sleeps feel different.
    """

    _TICK_S = 0.07  # seconds between animation frames (~14 fps)

    def start(self, macropad):
        w = macropad.display.width
        h = macropad.display.height
        self._group, self._bmp, _ = _make_canvas(macropad)
        self._w = w
        self._h = h

        self._x = random.randint(4, w - 5)
        self._y = random.randint(4, h - 5)

        combos = [(1, 1), (1, 2), (2, 1)]
        sx, sy = combos[random.randrange(len(combos))]
        self._dx = sx * random.choice([-1, 1])
        self._dy = sy * random.choice([-1, 1])

        self._bmp[self._x, self._y] = 1
        self._last_tick = time.monotonic()

        self._sweep = _PixelSweep()
        self._sweep.start(macropad)
        macropad.display.root_group = self._group

    def tick(self, macropad):
        self._sweep.tick(macropad)

        now = time.monotonic()
        if now - self._last_tick < self._TICK_S:
            return
        self._last_tick = now

        self._bmp[self._x, self._y] = 0

        self._x += self._dx
        self._y += self._dy

        if self._x <= 0:
            self._x = 0
            self._dx = abs(self._dx)
        elif self._x >= self._w - 1:
            self._x = self._w - 1
            self._dx = -abs(self._dx)

        if self._y <= 0:
            self._y = 0
            self._dy = abs(self._dy)
        elif self._y >= self._h - 1:
            self._y = self._h - 1
            self._dy = -abs(self._dy)

        self._bmp[self._x, self._y] = 1

    def stop(self, macropad):
        self._sweep.stop(macropad)


# ---------------------------------------------------------------------------
# StarsScreensaver
# ---------------------------------------------------------------------------

class StarsScreensaver:
    """Sparse pixels that slowly flicker on and off like distant stars.

    Stars are placed at random positions; each has an independent, randomised
    flicker interval so they don't all change at once.
    """

    _NUM_STARS = 7
    _MIN_INTERVAL = 0.4
    _MAX_INTERVAL = 2.0

    def start(self, macropad):
        self._group, self._bmp, _ = _make_canvas(macropad)
        w = macropad.display.width
        h = macropad.display.height

        now = time.monotonic()
        self._stars = []
        for _ in range(self._NUM_STARS):
            x = random.randrange(w)
            y = random.randrange(h)
            on = random.choice([True, False])
            interval = self._MIN_INTERVAL + random.random() * (self._MAX_INTERVAL - self._MIN_INTERVAL)
            next_flip = now + interval
            self._stars.append([x, y, on, interval, next_flip])
            self._bmp[x, y] = 1 if on else 0

        self._sweep = _PixelSweep()
        self._sweep.start(macropad)
        macropad.display.root_group = self._group

    def tick(self, macropad):
        self._sweep.tick(macropad)

        now = time.monotonic()
        for star in self._stars:
            if now >= star[4]:
                star[2] = not star[2]
                self._bmp[star[0], star[1]] = 1 if star[2] else 0
                interval = self._MIN_INTERVAL + random.random() * (self._MAX_INTERVAL - self._MIN_INTERVAL)
                star[3] = interval
                star[4] = now + interval

    def stop(self, macropad):
        self._sweep.stop(macropad)


# ---------------------------------------------------------------------------
# LinesScreensaver
# ---------------------------------------------------------------------------

class LinesScreensaver:
    """Two thin horizontal lines drifting slowly downward at different speeds.

    The lines wrap at the bottom of the screen. Each session starts with
    random y positions so the motion looks different every time.
    """

    _TICK_S = 0.12

    def start(self, macropad):
        self._group, self._bmp, _ = _make_canvas(macropad)
        w = macropad.display.width
        h = macropad.display.height
        self._w = w
        self._h = h

        # [y_pos, ticks_per_step, tick_counter]
        self._lines = [
            [random.randrange(h), 2, 0],
            [random.randrange(h), 5, 0],
        ]

        self._draw_all()
        self._last_tick = time.monotonic()

        self._sweep = _PixelSweep()
        self._sweep.start(macropad)
        macropad.display.root_group = self._group

    def _draw_all(self):
        self._bmp.fill(0)
        for line in self._lines:
            y = line[0]
            for x in range(self._w):
                self._bmp[x, y] = 1

    def tick(self, macropad):
        self._sweep.tick(macropad)

        now = time.monotonic()
        if now - self._last_tick < self._TICK_S:
            return
        self._last_tick = now

        moved = False
        for line in self._lines:
            line[2] += 1
            if line[2] >= line[1]:
                line[2] = 0
                line[0] = (line[0] + 1) % self._h
                moved = True

        if moved:
            self._draw_all()

    def stop(self, macropad):
        self._sweep.stop(macropad)


# ---------------------------------------------------------------------------
# RainScreensaver
# ---------------------------------------------------------------------------

class RainScreensaver:
    """Sparse falling pixel drops, like a minimal matrix rain.

    A small number of bright "drops" fall down random columns. Each drop
    has a short tail that erases behind it, giving a clean streak effect.
    Drops reset to the top of a new random column when they leave the screen.
    """

    _NUM_DROPS = 5
    _TAIL = 4
    _TICK_S = 0.06

    def start(self, macropad):
        self._group, self._bmp, _ = _make_canvas(macropad)
        w = macropad.display.width
        h = macropad.display.height
        self._w = w
        self._h = h

        self._drops = []
        used = set()
        for _ in range(self._NUM_DROPS):
            col = random.randrange(w)
            while col in used and len(used) < w:
                col = random.randrange(w)
            used.add(col)
            y = random.randrange(-h, 0)
            self._drops.append([col, y])

        self._last_tick = time.monotonic()

        self._sweep = _PixelSweep()
        self._sweep.start(macropad)
        macropad.display.root_group = self._group

    def tick(self, macropad):
        self._sweep.tick(macropad)

        now = time.monotonic()
        if now - self._last_tick < self._TICK_S:
            return
        self._last_tick = now

        for drop in self._drops:
            col, y = drop[0], drop[1]

            erase_y = y - self._TAIL
            if 0 <= erase_y < self._h:
                self._bmp[col, erase_y] = 0

            if 0 <= y < self._h:
                self._bmp[col, y] = 1

            drop[1] = y + 1

            if y - self._TAIL >= self._h:
                drop[0] = random.randrange(self._w)
                drop[1] = -self._TAIL

    def stop(self, macropad):
        self._sweep.stop(macropad)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ANIMATED = [BounceScreensaver, StarsScreensaver, LinesScreensaver, RainScreensaver]


def get_screensaver(name):
    """Return a new screensaver instance. Reseeds random each call."""
    random.seed(int(time.monotonic() * 1000) % 65536)

    if name == "black":
        return BlackScreensaver()
    if name == "bounce":
        return BounceScreensaver()
    if name == "stars":
        return StarsScreensaver()
    if name == "lines":
        return LinesScreensaver()
    if name == "rain":
        return RainScreensaver()
    if name == "random":
        cls = _ANIMATED[random.randrange(len(_ANIMATED))]
        return cls()
    return BounceScreensaver()


# ---------------------------------------------------------------------------
# SleepManager — for use inside SubApp run() loops
# ---------------------------------------------------------------------------

class SleepManager:
    """Handles sleep/wake inside a SubApp's own run() loop.

    Usage pattern in a SubApp's run(macropad) function:

        from screensaver import SleepManager
        import config as _cfg

        def run(macropad):
            sleep = SleepManager(_cfg)
            while True:
                woke = sleep.tick(macropad)
                if woke:
                    redraw_my_ui()
                    continue          # skip input handling on the wake frame
                if sleep.sleeping:
                    continue

                # --- normal input handling ---
                event = macropad.keys.events.get()
                if event and event.pressed:
                    sleep.notify_input()
                    handle(event)

    Any key press, encoder turn, or encoder press wakes the screen.
    The waking input is consumed so it doesn't trigger an unintended action.
    After waking, the caller is responsible for redrawing its own UI.
    The SleepManager only restores pixel state; display redraws are up to you.
    """

    def __init__(self, cfg):
        self._cfg          = cfg
        self._last_input   = time.monotonic()
        self._screensaver  = None
        self._sleeping     = False
        self._last_enc_pos = None

    @property
    def sleeping(self):
        return self._sleeping

    def notify_input(self):
        """Reset the idle timer. Call whenever the user provides input."""
        self._last_input = time.monotonic()

    def tick(self, macropad):
        """Call once per loop iteration.

        While awake:  checks the timeout and initiates sleep if needed.
        While asleep: ticks the screensaver animation and checks for wake.

        Returns True on the frame the screen wakes up — caller should redraw
        its UI and then `continue` to skip input handling for that iteration.
        Returns False in all other cases.
        """
        now = time.monotonic()

        # Lazily capture encoder position the first time tick() is called.
        if self._last_enc_pos is None:
            self._last_enc_pos = macropad.encoder

        # --- Trigger sleep ---
        if not self._sleeping and self._cfg.SLEEP_ENABLED:
            if now - self._last_input > self._cfg.SLEEP_TIMEOUT:
                self._sleeping     = True
                self._last_enc_pos = macropad.encoder
                self._screensaver  = get_screensaver(self._cfg.SCREENSAVER)
                self._screensaver.start(macropad)

        if not self._sleeping:
            return False

        # --- Sleeping: tick animation, then check for wake ---
        self._screensaver.tick(macropad)
        macropad.display.refresh()

        macropad.encoder_switch_debounced.update()
        enc_pos  = macropad.encoder
        wake_key = macropad.keys.events.get()
        wake_enc = enc_pos != self._last_enc_pos
        wake_sw  = macropad.encoder_switch_debounced.pressed

        if wake_key or wake_enc or wake_sw:
            self._screensaver.stop(macropad)
            self._screensaver  = None
            self._sleeping     = False
            self._last_input   = time.monotonic()
            self._last_enc_pos = macropad.encoder
            # Drain remaining key events so the wake input isn't acted on.
            while macropad.keys.events.get():
                pass
            return True  # caller should redraw its UI and continue

        return False

    def force_stop(self, macropad):
        """Stop any active screensaver immediately (call before returning from run())."""
        if self._sleeping and self._screensaver:
            self._screensaver.stop(macropad)
            self._screensaver = None
            self._sleeping    = False
