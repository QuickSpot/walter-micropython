# Modem Passthrough Utility

This utility is an application that allows you to send AT commands
to the Walter Modem directly and see the output of the modem.

> [!NOTE]
> This utility program relies on mpremote being installed on your system and
> preferably available in your PATH.

## How to use

Simply run the modem_passthrough python:

```shell
python util/modem_passthrough/modem_passthrough.py
```

### Optional File Logging

You can optionally pass `--log` as an argument to log the commands
and results to a log file.
This file will be placed in `passthrough.log` next to the script's location.

```shell
python util/modem_passthrough/modem_passthrough.py --log
```
