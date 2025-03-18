# Walter Modem Micropython

## Introduction

This repository contains the micropython WalterModem library.

This library is designed to consume as little energy as possible
by making use of the FreeRTOS locking mechanisms and the hardware UART.
There are not active wait situations which consume useless CPU cycles.
Besides that the library does not allocate dynamic heap memory.
All RAM is determined at compiled time.
This makes debugging easier and mitigates unexpected out-of-memory situations.

## Documentation

You can find the setup guide here: [Walter Modem; Micropython Setup](https://www.quickspot.io/documentation.html#/walter-modem/setup/micropython)

## Contributions

We welcome all contributions to the software via github pull requests.
Please take the design strategies in mind when contributing.

## License

All software is available under the 'DPTechnics 5 clause' license.
This is essentially the same as the `BSD-3-Clause` license
with the addition that binaries of which the source code is not open
should run on a Walter board from DPTechnics bv.
