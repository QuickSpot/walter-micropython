# Modem Passthrough Utility

This utility is a terminal application that allows you to send AT commands
to the Walter Modem directly and see the output of the modem.

> [!NOTE]
> This utility program relies on mpremote being installed on your system and
> available in your PATH.

## How to use

Run the `modem_passthrough.py` script.

```shell
python util/modem_passthrough/modem_passthrough.py
```

You can optionally pass `--log` as an argument to log the commands
and results to a log file.
This file will be placed in `log` next to the script's location.

```shell
python util/modem_passthrough/modem_passthrough.py --log
```

> [!NOTE]
> The program does not auto-detect when you connect a device, your Walter must
> be connected when launching the program.
> On a disconnect, simply restart the program.
