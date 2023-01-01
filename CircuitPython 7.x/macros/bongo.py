# bongo.py
# A cute bongo cat for your display

import random
import time
import displayio
import adafruit_imageload
from adafruit_display_shapes.line import Line


class Bongo(object):
    SPRITE_SHEET_PATH = "/bongo/bongo.bmp"
    TILE_WIDTH = 57
    TILE_HEIGHT = 35
    BOUNCE_FRAME_COUNT = 5
    TAP_FRAME_START = 5
    TAP_FRAME_END = 7

    def __init__(self, bounce_time=0.125, tap_time=0.125):
        self.bounce_time = bounce_time
        self.tap_time = tap_time
        self._frame = 0
        self._before = -1
        self._pause_time = 1.0
        self._group = displayio.Group()

        # Init table line and it to group
        self._line = Line(-10, 30, self.TILE_WIDTH + 6, 13, color=0xFFFFFF)
        self._group.append(self._line)

        # Init sprite and add it to group
        sprite_sheet, palette = adafruit_imageload.load(
            self.SPRITE_SHEET_PATH, bitmap=displayio.Bitmap, palette=displayio.Palette
        )
        self._sprite = displayio.TileGrid(
            sprite_sheet,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=self.TILE_WIDTH,
            tile_height=self.TILE_HEIGHT,
        )
        self._group.append(self._sprite)

    # Group bongo is rendered to
    @property
    def group(self):
        return self._group

    # Bongo x position
    @property
    def x(self):
        return self._group.x

    @x.setter
    def x(self, value):
        self._group.x = value

    # Bongo y position
    @property
    def y(self):
        return self._group.y

    @y.setter
    def y(self, value):
        self._group.y = value

    # Bongo scale
    @property
    def scale(self):
        return self._group.scale

    @scale.setter
    def scale(self, value):
        self._group.scale = value

    # Update method
    # Should be called in main loop
    def update(self, key_event):
        now = time.monotonic()

        # Tap on key press
        if key_event and key_event.pressed:
            self._before = now
            self._sprite[0] = random.randint(
                self.TAP_FRAME_START, self.TAP_FRAME_END)
        # Pause animation reset
        if self._sprite[0] == 0:
            if now >= self._before + self._pause_time:
                self._before = now
                self._pause_time = random.uniform(0.5, 1)
                self._frame = 1
                self._sprite[0] = self._frame % self.BOUNCE_FRAME_COUNT
        # Bounce animation progression
        elif self._sprite[0] < self.BOUNCE_FRAME_COUNT:
            if now >= self._before + self.bounce_time:
                self._before = now
                self._frame += 1
                self._sprite[0] = self._frame % self.BOUNCE_FRAME_COUNT
        # Tap animation reset
        else:
            if now >= self._before + self.tap_time:
                self._before = now
                self._sprite[0] = 0


def Loop(_data, macropad, encoder_position):
    bongo = Bongo()

    bongo.x = 40
    bongo.y = 15

    group = displayio.Group()
    group.append(bongo.group)

    macropad.display.show(group)

    macropad.pixels.fill((0, 0, 0))
    macropad.pixels.show()

    while True:
        key_event = macropad.keys.events.get()
        bongo.update(key_event)
        macropad.display.refresh()

        pos = macropad.encoder

        if not pos == encoder_position:
            return _data


app = {
    'name': 'Pomodoro',
    'macros': [],
    'custom_func': Loop,
    'custom_data': {}
}
