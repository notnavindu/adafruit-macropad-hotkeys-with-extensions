# Macropad OS — Bongo Cat
# Animated bongo cat on the display. Tap any key to make it bop.
# Sprite sheet must be at /bongo/bongo.bmp on the device.
#
# Press the encoder knob to return to the home screen.
#
# Credit: https://github.com/christanaka/circuitpython-bongo

import random
import time
import displayio
import adafruit_imageload
from adafruit_display_shapes.line import Line


class BongoCat:
    SPRITE_SHEET_PATH = "/bongo/bongo.bmp"
    TILE_WIDTH        = 57
    TILE_HEIGHT       = 35
    BOUNCE_FRAMES     = 5
    TAP_FRAME_START   = 5
    TAP_FRAME_END     = 7

    def __init__(self, bounce_time=0.125, tap_time=0.125):
        self.bounce_time = bounce_time
        self.tap_time    = tap_time
        self._frame      = 0
        self._before     = -1
        self._pause_time = 1.0

        self._group = displayio.Group()
        self._line  = Line(-10, 30, self.TILE_WIDTH + 6, 13, color=0xFFFFFF)
        self._group.append(self._line)

        sprite_sheet, palette = adafruit_imageload.load(
            self.SPRITE_SHEET_PATH,
            bitmap=displayio.Bitmap,
            palette=displayio.Palette,
        )
        self._sprite = displayio.TileGrid(
            sprite_sheet,
            pixel_shader=palette,
            width=1, height=1,
            tile_width=self.TILE_WIDTH,
            tile_height=self.TILE_HEIGHT,
        )
        self._group.append(self._sprite)

    @property
    def group(self):
        return self._group

    @property
    def x(self):
        return self._group.x

    @x.setter
    def x(self, value):
        self._group.x = value

    @property
    def y(self):
        return self._group.y

    @y.setter
    def y(self, value):
        self._group.y = value

    def update(self, key_event):
        now = time.monotonic()

        if key_event and key_event.pressed:
            self._before   = now
            self._sprite[0] = random.randint(self.TAP_FRAME_START, self.TAP_FRAME_END)

        elif self._sprite[0] == 0:
            if now >= self._before + self._pause_time:
                self._before     = now
                self._pause_time = random.uniform(0.5, 1.0)
                self._frame      = 1
                self._sprite[0]  = self._frame % self.BOUNCE_FRAMES

        elif self._sprite[0] < self.BOUNCE_FRAMES:
            if now >= self._before + self.bounce_time:
                self._before    = now
                self._frame    += 1
                self._sprite[0] = self._frame % self.BOUNCE_FRAMES

        else:
            if now >= self._before + self.tap_time:
                self._before    = now
                self._sprite[0] = 0


# ---------------------------------------------------------------------------
# Entry point called by Macropad OS
# ---------------------------------------------------------------------------

def run(macropad):
    cat = BongoCat()
    cat.x = 40
    cat.y = 15

    group = displayio.Group()
    group.append(cat.group)

    macropad.pixels.fill((0, 0, 0))
    macropad.pixels.show()
    macropad.display.root_group = group

    while True:
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            return

        key_event = macropad.keys.events.get()
        cat.update(key_event)
        macropad.display.refresh()


app = {
    "name": "Bongo Cat",
    "run":  run,
}
