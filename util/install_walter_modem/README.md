# Install WalterModem Utility

This is a simple convencience script that will install / copy
the WalterModem Library to the correct place on the board, using
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).

The purpose of this utility is for convenience during development
of the modem library itself or should there be any issues with
[MIP](https://docs.micropython.org/en/latest/reference/packages.html)

## How to use

- Run `install_walter_modem.ps1` when on Windows
- Run `install_walter_modem.sh` when on Linux

You can optionally pass the device name along,
in that case that you have multiple devices connected.
_(eg. `./util/install_walter_modem.sh ttyACM0` or
`.\util\install_walter_modem.ps1 COM3`)_
