def Loop(macropad, encoder_position):
    text_lines = macropad.display_text(title="Hotkeys extension")

    while True:
        # Your logic
        key_event = macropad.keys.events.get()

        if key_event and key_event.pressed:
            text_lines[0].text = "Key {} pressed!".format(key_event.key_number)

        text_lines[1].text = "Rotary encoder {}".format(macropad.encoder)
        text_lines[2].text = "Encoder switch: {}".format(
            macropad.encoder_switch)
        text_lines.show()

        # [IMPORTANT]
        # This will break the main loop and return back to the
        # Hotkeys loop when the rotary encoder changes position
        # This can also be done when a certain key is pressed.
        pos = macropad.encoder

        if not pos == encoder_position:
            return

        macropad.display.refresh()


app = {
    'name': 'Sample',
    'macros': [],
    'custom_func': Loop,
}
