import asyncio

LPS22HB_ADDRESS = 0x5C
LPS22HB_WHO_AM_I_REG = 0x0F
LPS22HB_CTRL2_REG = 0x11
LPS22HB_STATUS_REG = 0x27
LPS22HB_PRESS_OUT_XL_REG = 0x28
LPS22HB_PRESS_OUT_L_REG = 0x29
LPS22HB_PRESS_OUT_H_REG = 0x2A
LPS22HB_TEMP_OUT_L_REG = 0x2B
LPS22HB_TEMP_OUT_H_REG = 0x2C

MILLIBAR = 0
PSI = 1
PA = 2

class LPS22HB:
    def __init__(self, i2c):
        self._i2c = i2c
        self._initialized = False

    def begin(self):
        if self.i2c_read(LPS22HB_WHO_AM_I_REG) != 0xB1:
            self.end()
            return False
        self._initialized = True
        return True

    def end(self):
        self._initialized = False

    def read_pressure(self, units=MILLIBAR):
        if not self._initialized:
            return 0
        # Trigger one shot
        self.i2c_write(LPS22HB_CTRL2_REG, 0x01)
        
        # Wait for ONE_SHOT bit to be cleared by the hardware
        while self.i2c_read(LPS22HB_CTRL2_REG) & 0x01 != 0:
            asyncio.sleep(0.01)  # Short delay to avoid busy loop

        # Read pressure value
        reading = (self.i2c_read(LPS22HB_PRESS_OUT_XL_REG) |
                   (self.i2c_read(LPS22HB_PRESS_OUT_L_REG) << 8) |
                   (self.i2c_read(LPS22HB_PRESS_OUT_H_REG) << 16)) / 40960.0

        if units == MILLIBAR:
            return reading * 10
        elif units == PSI:
            return reading * 0.145038
        else:
            return reading

    def read_temperature(self):
        # Read temperature value
        reading = (self.i2c_read(LPS22HB_TEMP_OUT_L_REG) |
                   (self.i2c_read(LPS22HB_TEMP_OUT_H_REG) << 8))
        return reading / 100

    def i2c_read(self, reg):
        self._i2c.writeto(LPS22HB_ADDRESS, bytes([reg]))
        data = self._i2c.readfrom(LPS22HB_ADDRESS, 1)
        if data:
            return data[0]
        return -1

    def i2c_write(self, reg, val):
        self._i2c.writeto(LPS22HB_ADDRESS, bytes([reg, val]))
        return 1
