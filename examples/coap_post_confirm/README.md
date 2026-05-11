# CoAP POST + Confirmation Example

## Purpose

This example demonstrates a complete CoAP POST flow in MicroPython:

- connect to the LTE network,
- create a CoAP context for a server,
- POST a payload to a configured path,
- wait for and verify the confirmation response.

## Required hardware

To run this example you need:

- Walter
- LTE antenna
- SIM card
- USB-C cable

## Configuration

Edit constants at the top of [main.py](main.py):

- `COAP_SERVER_ADDRESS`
- `COAP_SERVER_PORT`
- `COAP_PATH`
- `COAP_PAYLOAD`
- `CELL_APN` (and APN auth fields if needed)
- `SIM_PIN` (only if your SIM requires it)

Default endpoint uses `coap.me` and path `test`.

## Run with mpremote

```shell
mpremote run examples/coap_post_confirm/main.py
```

Or copy it to the board first:

```shell
mpremote cp examples/coap_post_confirm/main.py :main.py
```
