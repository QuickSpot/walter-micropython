# Auto Reconnect Utility

This is a simple convenience script that will keep trying to reconnect if
the connection to your Micropython Device fails. You can stop it by pressing
`ctrl` + `c`.

> [!TIP]
> Should you enter or end up in the REPL, you can exit by
> pressing `ctrl` + `x` *(exit REPL)* & `ctrl` + `c` *(exit this script)*
> in rapid succession.

The purpose of this utility is when testing deepsleep or working on code that
introduces disconnects for which you don't manually want to keep re-connecting.

This utility script uses
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).

## How to use

> [!NOTE]
> This convenience script currently has no version for Windows.

- Run `auto-reconnect.sh` when on Linux

You can optionally pass the device name along,
in that case that you have multiple devices connected.
*(eg. `./util/install_walter_modem.sh ttyACM0` or
`.\util\install_walter_modem.ps1 COM3`)*
