# Macropad OS — user configuration
# Copy this file to the CIRCUITPY root alongside code.py.

# ---------------------------------------------------------------------------
# Screensaver / sleep settings
# ---------------------------------------------------------------------------

# Set to False to disable the screensaver entirely.
SLEEP_ENABLED = True

# Seconds of idle input before the screen sleeps.
SLEEP_TIMEOUT = 60

# Which screensaver to show when the display sleeps.
# Options:
#   "black"  — turn the display off completely (best for burn-in prevention)
#   "bounce" — a single pixel bounces around the screen
#   "stars"  — sparse pixels slowly flicker independently like distant stars
#   "lines"  — two horizontal lines drift downward at different speeds
#   "rain"   — sparse falling pixel drops (minimal matrix rain)
#   "random" — pick a random animated screensaver each time the screen sleeps
SCREENSAVER = "rain"

# ---------------------------------------------------------------------------
# Exit button
# ---------------------------------------------------------------------------

# Key index to use as a global "return to home screen" button on all macro
# apps, shown as a red LED with the label "Exit".
# Set to an integer (e.g. 0 for the top-left key) to enable globally.
# Individual apps can override this per-app via "exit_key" in their app dict.
# Set to None to disable (each app must opt in via "exit_key" in its dict).
EXIT_KEY = None

# ---------------------------------------------------------------------------
# App list
# ---------------------------------------------------------------------------

# List of app module names (without .py) to load, in the order they appear
# on the home screen. If omitted or set to None, all .py files in the apps/
# folder are loaded alphabetically.
APPS = [
    "media",
    "numpad",
    "pomodoro",
    "github",
    "graphite",
    "fidget",
    "web"
]
