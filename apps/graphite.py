from adafruit_hid.keycode import Keycode

app = {
    'name': 'gt',
    'auto_return': True,
    'exit_key': 11,
    'macros': [
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x003838, 'ls',    ['gt ls\n']),
        (0x003838, 'log',   ['gt log short\n']),
        (0x003838, 'submit', ['gt submit\n']),
        # 2nd row ----------
        (0x002850, 'up',    ['gt up\n']),
        (0x002850, 'down',  ['gt down\n']),
        (0x002850, 'rstck',  ['gt restack\n']),
        # 3rd row ----------
        (0x280050, 'new',   ['gt create -m ']),
        (0x280050, 'mod',   ['gt modify\n']),
        (0x280050, 'sync',  ['gt sync\n']),
        # 4th row ----------
        (0x500028, 'top',   ['gt top\n']),
        (0x500028, 'btm',   ['gt bottom\n']),
        (0x500028, '', []),
        # Encoder button ---
        (0x000000, '', []),
    ]
}
