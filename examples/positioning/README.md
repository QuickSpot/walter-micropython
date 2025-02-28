# Walter Position Example

## Purpose

Walter has a built-in GNSS receiver which makes use of the GPS and Galileo
constellations. This example effectively is a demo of a tracker device in which
position is transmitted to our demo [server](http://walterdemo.quickspot.io/).

Walter's GNSS subsystem is built to be very low power and works
with 'snapshot' technology. To limit power usage the same radio is used for LTE
and GNSS and thus they cannot work concurrently. Altough this lowers power
consumption, it also means that the minimum update interval is limited by how
fast a fix is found and an LTE connection is created. You can test these
parameters using this example.

## Required hardware

To run this example you will need the following items:

- Walter
- An LTE antenna
- A passive GNSS antenna
- A SIM card (For GNSS assistance)
- USB-C cable to flash Walter

## Installation

Follow the instructions in the main [README](../../README.md) to install the modem library.

### 1. Configuration

Copy `config.example.py`, rename it to `config.py`, and update the values as needed.
Then, copy it to the board alongside `boot.py`:

```shell
mpremote cp examples/positioning/config.py :config.py
```

### 2. Copy the Example Script

Copy the boot.py script onto the board:

```shell
mpremote cp examples/positioning/boot.py :boot.py
```

## Running the Example

1. Connect the LTE antenna to Walter.
2. **Do not run the example without an antenna connected**—this could damage the modem's radio frontend.
3. Insert the SIM card before starting the script.

Micropython automatically runs `boot.py` (unless the device is in safe-boot mode).