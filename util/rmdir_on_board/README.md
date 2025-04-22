# Remove Dir On Board Utility

This is a convencience script that will remove
the specified folder / directory with it's content from the (specified) board,
using
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html)

The purpose of this utility is to avoid manually issuing multiple commands.
As of making this utility,
[`mpremote fs rmdir`](https://docs.micropython.org/en/latest/reference/mpremote.html#mpremote-command-fs) does currently not support deletion of directories with content inside.

> [!NOTE]
> This convenience script does not replace
> [`mpremote fs rmdir`](https://docs.micropython.org/en/latest/reference/mpremotehtml#mpremote-command-fs),
> it is meant only for when you are sure to delete
> an entire directory _(with content)_ from your board.

## How to use

- Run `rmdir_on_board.ps1 <dirname>` when on Windows
- Run `rmdir_on_board.sh <dirname>` when on Linux

You can optionally pass the device name along,
in that case that you have multiple devices connected.
_(eg. `./util/rmdir_on_board.sh lib ttyACM0` or
`.\util\install_walter_modem.ps1 lib COM3`)_
