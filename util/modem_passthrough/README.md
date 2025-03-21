# Modem Passthrough Utility

This utility is a terminal application that allows you to send AT commands
to the Walter Modem directly and see the output of the modem.

> [!NOTE]
> This utility program relies on mpremote being installed on your system and
> available in your PATH.

## How to use

There are two versions available:

- **TUI (Terminal User Interface)**
- **GUI (Graphical User Interface)**

> [!WARNING]
> The program does not auto-detect when you connect a device, your Walter must
> be connected when launching the program.
> On a disconnect, simply restart the program.

### Windows

The **GUI** version (`modem_passthrough_gui.py`) is recommended for Windows.

> [!NOTE]
> Curses, the library used for the TUI, is not available by default on Windows.\
> You can install it using the following command: `pip install windows-curses`

### Linux

Both the **TUI** and **GUI** work out of the box
*(granted you have python3 & mpremote installed on your system)*.

### Running the Scripts

Simply run one of the 2 modem_passthrough python scripts:

```shell
python util/modem_passthrough/modem_passthrough.py  # For GUI
```

or

```shell
python util/modem_passthrough/modem_passthrough_tui.py  # For TUI
```

### Optional File Logging

You can optionally pass `--log` as an argument to log the commands
and results to a log file.
This file will be placed in `log` next to the script's location.

```shell
python util/modem_passthrough/modem_passthrough_gui.py --log
```

```shell
python util/modem_passthrough/modem_passthrough_tui.py --log
```


