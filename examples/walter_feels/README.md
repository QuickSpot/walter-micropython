# Walter Feels Example

## Purpose

Walter Feels is an open-source carrier board reference design
for the Walter module.

This example periodically reads internal power management data
and sensor values, then transmits them to [Blynk](https://blynk.cloud).

## Required Hardware

To run this example, you will need the following:

- Walter
- Walter Feels
- An LTE antenna
- A SIM card
- A USB-C cable (for flashing Walter)
- A power supply or battery (to power Walter Feels)

> [!WARNING]
> **Never connect both the power supply and the USB-C cable at the same time.**\
> This could cause damage by connecting two power sources simultaneously.
>
> *For development, power Walter Feels via the USB-C port on Walter
> or use a USB-C cable with the +5V lead cut.*

## Installation

Follow the instructions in the main [README](../../README.md)
to install the modem library.

### 1. Install Dependencies

This example requires drivers for various sensors.

#### HDC1080

For the HDC1080, we use
[mcauser's micropython-hdc1080 MIP package](https://github.com/mcauser/micropython-hdc1080).
Install it using
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):

```shell
mpremote mip install github:mcauser/micropython-hdc1080
```

If multiple devices are connected, specify the device:

```shell
mpremote connect <device> mip install github:mcauser/micropython-hdc1080
```

> [!NOTE]
> If `mpremote` is not in your system's PATH,
> you can run it using `python -m mpremote` instead.

#### LPS22HB & LTC4015

Minimal drivers for the LPS22HB and LTC4015 are included in this example.
Place them in the `lib` folder on Walter
under their respective directories as `__init__.py`.

Use `mpremote` to copy them
*(if multiple devices are connected, use `connect` as shown above)*:

```shell
mpremote mkdir :lib/lps22hb
mpremote mkdir :lib/ltc4015
mpremote cp examples/walter_feels/lps22hb.py :lib/lps22hb/__init__.py
mpremote cp examples/walter_feels/ltc4015.py :lib/ltc4015/__init__.py
```

### 2. Configuration

Copy `config.example.py`, rename it to `config.py`,
and update the values as needed.
Then, copy it to the board alongside `boot.py`:

```shell
mpremote cp examples/walter_feels/config.py :config.py
```

### 3. Copy the Example Script

Copy the boot.py script onto the board:

```shell
mpremote cp examples/walter_feels/boot.py :boot.py
```

## Running the Example

1. Connect the LTE antenna to Walter.
2. **Do not run the example without an antenna connected**,
   this could damage the modem's radio frontend.
3. Insert the SIM card before starting the script.

Micropython automatically runs `boot.py`
*(unless the device is in safe-boot mode)*.

> [!NOTE]
> If it looks like it's doing nothing, it may be waiting for network registration.\
> Give it some time, if it fails on any step it will log/print that.
