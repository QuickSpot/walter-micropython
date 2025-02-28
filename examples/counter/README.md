# Counter Example

## Purpose

This example will make Walter count and send the counter value to our demo
[server](http://walterdemo.quickspot.io/) every 10 seconds. It allows you to
test connectivity without creating a motherboard to plug Walter in.

## Required hardware

To run this example you will need the following items:

- Walter
- An LTE antenna
- A SIM card
- USB-C cable to flash Walter

## Installation Running the Example

Follow the instructions in the main [README](../../README.md) to install the modem library.

## Running the Example

Since this is a small example script, you can run this example without copying it onto the board,
using [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):\
*As long as the computer is attached / the command is not interrupted it will keep running*

```shell
mpremote run examples/counter/boot.py
```

If you prefer to copy the example script onto the board, you can copy it like so:

```shell
mpremote cp examples/counter/boot.py :boot.py
```
