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
