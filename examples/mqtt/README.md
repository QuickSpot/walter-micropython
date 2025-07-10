# Counter Example

## Purpose

This example will make an MQTT connection, publish a message on it, and then subscribe,
listening to any future messages on that topic. It allows you to test MQTT functionality.

## Required hardware

To run this example you will need the following items:

- Walter
- An LTE antenna
- A SIM card
- USB-C cable to flash Walter

## Installation

> [!TIP]
> If you have not installed the modem library yet,
> you can find the documentation
> [here](https://www.quickspot.io/documentation.html#/walter-modem/micropython/setup).

### 1. Configuration

Copy `config.example.py`, rename it to `config.py`,
and update the values as needed.
Then, copy it to the board:

```shell
mpremote cp examples/positioning/config.py :config.py
```

> [!NOTE]
> If `mpremote` is not in your system's PATH,
> you can run it using `python -m mpremote` instead.

## Running the Example

Since this is a small example script,
you can run this example without copying it onto the board, using
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):\
*The script will continue running as long as the computer remains connected
and the command is not interrupted.*

```shell
mpremote run examples/counter/main.py
```

If you prefer to copy the example script onto the board,
you can copy it like so:

```shell
mpremote cp examples/counter/main.py :main.py
```
