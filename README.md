# Macropad Hotkeys With Extension Support

This is a modified version of the OG [Hotkeys](https://learn.adafruit.com/macropad-hotkeys) script from Adafruit. This script allows you to define custom functions to override the main loop to create your own functionalities. Currently, this repo includes a Pomodoro timer and a Bongo Cat thingy as extentions.

## Included Extensions

### Pomodoro Timer ([?](https://todoist.com/productivity-methods/pomodoro-technique))

![screenshot of pomodoro](screenshots/pomodoro.jpg)

`/macros/pomodoro.py`

#### Buttons

- **Green** - Start a pomodoro session
- **Yellow** - Pause/resume a session
- **Red** - Doesn't do anything yet

#### Configuring Pomodoro Sessions

You can customize the sessions duration, short break duration, long break duration and the sequence in which they occur by changing the constant variables defined in `/macros/pomodoro.py`

### Bongo Cat

![bonogo](screenshots/bongo.jpg)

`/macros/bongo.py`

Bongo cat that taps when you tap. Based off of [this repo](https://github.com/christanaka/circuitpython-bongo).

## Creating your own extensions

You can use the template given in `/macros/sample.py` to create your own extensions.

## Roadmap

- [x] Base structure
- [x] Pomodoro Timer
- [x] Bongo Cat
- [ ] Save Pomodoro session times in a file
- [ ] Refactor Pomodoro timer to use classes
