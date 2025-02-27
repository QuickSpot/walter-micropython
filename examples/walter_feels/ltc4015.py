from machine import I2C

# Register definitions
QCOUNT = 0x13 # Coulomb counter value 0x8000 

CONFIG_BITS = 0x14 # Configuration Settings  

ICHARGE_TARGET = 0x1A # Maximum charge current target = (ICHARGE_TARGET + 1)x1mV/RSNSB
VCHARGE_SETTING = 0x1B # Charge voltage target
CHEM_CELLS = 0x43 # Readout of CHEM and CELLS pin settings 
VBAT = 0x3A # Two's complement ADC measurement result for the BATSENS pin
    # VBATSENS/cellcount = [VBAT] x 192.2uV for lithium chemistries
    # VBATSENS/cellcount = [VBAT] x 128.176uV for lead-acid
VIN = 0x3B # Two's complement ADC measurement result for VIN
    # VIN = [VIN] x 1.648mV
VSYS = 0x3C # Two's complement ADC measurement result for VSYS
    # VSYS = [VSYS] x 1.648mV)
IBAT = 0x3D # Two's complement ADC measurement result for (VCSP -VCSN)
    # Charge current (into the battery) is represented as a positive number
    # Battery current = [IBAT] x 1.46487uV/Rsnsb
IIN = 0x3E # Two's complement ADC measurement result for (VCLP -VCLN)
    # Input current = [IIN] x 1.46487uV/Rsnsi
DIE_TEMP = 0x3F # Two's complement ADC measurement result for die temperature
    # Temperature = (DIE_TEMP -12010)/45.6 °C

# Config bits
SUSPEND_CHARGER = (1 << 8) # suspend battery charger operation
FORCE_MEAS_SYS_ON = (1 << 4) # force measurement system to operate
MPPT_EN_I2C = (1 << 3) # enable maximum power point tracking
EN_QCOUNT = (1 << 2) # enable coulomb counter

# Battery chemistry constants
LI_ION = 0
LIFEPO4 = 1
LEAD_ACID = 2
INVALID = 3

CHEM_SHIFT = 4  # Upper 4 bits of CHEM_CELLS hold the chemistry

class LTC4015:
    def __init__(self, i2c: I2C, rsnsi: int, rsnsb: int, address: int = 0xD0):
        self.i2c = i2c
        self.Rsnsi = rsnsi
        self.Rsnsb = rsnsb
        self.address = address >> 1  
        self.is_programmable = False
        self.cell_count = 0
        self.chemistry = INVALID
        self.vcharge = 0

    def write_word(self, sub_address: int, word: int):
        data = bytearray([sub_address, word & 0xFF, (word >> 8) & 0xFF])
        self.i2c.writeto(self.address, data)

    def read_word(self, sub_address: int) -> int:
        self.i2c.writeto(self.address, bytearray([sub_address]))
        data = self.i2c.readfrom(self.address, 2)
        return data[0] | (data[1] << 8)

    def _set_bit(self, sub_address: int, bitmask: int):
        old = self.read_word(sub_address)
        new_val = old | bitmask
        self.write_word(sub_address, new_val)

    def _clr_bit(self, sub_address: int, bitmask: int):
        old = self.read_word(sub_address)
        new_val = old & ~bitmask
        self.write_word(sub_address, new_val)

    def initialize(self):
        self.suspend_charging()
        self.get_battery_info()

        print("Battery: ", self.get_battery_string())
        print("Cells: ", self.cell_count)

    def get_qcount(self) -> int:
        return self.read_word(QCOUNT)

    def suspend_charging(self):
        self._set_bit(CONFIG_BITS, SUSPEND_CHARGER)

    def start_charging(self):
        self._clr_bit(CONFIG_BITS, SUSPEND_CHARGER)

    def enable_mppt(self):
        self._set_bit(CONFIG_BITS, MPPT_EN_I2C)

    def disable_mppt(self):
        self._clr_bit(CONFIG_BITS, MPPT_EN_I2C)

    def enable_force_telemetry(self):
        self._set_bit(CONFIG_BITS, FORCE_MEAS_SYS_ON)

    def disable_force_telemetry(self):
        self._clr_bit(CONFIG_BITS, FORCE_MEAS_SYS_ON)

    def enable_coulomb_counter(self):
        self._set_bit(CONFIG_BITS, EN_QCOUNT)

    def disable_coulomb_counter(self):
        self._clr_bit(CONFIG_BITS, EN_QCOUNT)

    def config(self, setting: int):
        self.write_word(CONFIG_BITS, setting)

    def set_input_current_max(self, current: float):
        iin = int((2 * current * self.Rsnsi) - 1)
        if iin > 63:
            return
        self.write_word(ICHARGE_TARGET, iin)

    def set_charge_current(self, current: float):
        icharge = int((current * self.Rsnsb) - 1)
        if icharge > 31:
            return
        self.write_word(ICHARGE_TARGET, icharge)

    def set_charge_voltage(self, voltage: float):
        if self.cell_count == 0:
            return
        v_cell = voltage / self.cell_count
        if self.chemistry == LI_ION:
            v_cell -= 3.8125
            self.vcharge = int(v_cell * 80)
            if self.vcharge > 31:
                return
        elif self.chemistry == LIFEPO4:
            v_cell -= 3.4125
            self.vcharge = int(v_cell * 80)
            if self.vcharge > 31:
                return
        elif self.chemistry == LEAD_ACID:
            v_cell -= 2.0
            self.vcharge = int(v_cell * 105.0)
            if self.vcharge > 63:
                return
        self.write_word(VCHARGE_SETTING, self.vcharge)

    def get_battery_info(self):
        tmp = self.read_word(CHEM_CELLS)
        t_chem = (tmp >> CHEM_SHIFT) & 0x0F
        self.cell_count = tmp & 0x0F

        if t_chem < 4:
            self.chemistry = LI_ION
        elif t_chem < 7:
            self.chemistry = LIFEPO4
        elif t_chem < 9:
            self.chemistry = LEAD_ACID
        else:
            self.chemistry = INVALID
        if t_chem in (0, 4, 8):
            self.is_programmable = True

    def get_input_voltage(self) -> float:
        return float(self.read_word(VIN)) * 0.001648

    def get_input_current(self) -> float:
        return float(self.read_word(IIN)) * 0.00146487 / self.Rsnsi

    def get_system_voltage(self) -> float:
        return float(self.read_word(VSYS)) * 0.001648

    def get_battery_voltage(self) -> float:
        v_bat_cell = self.read_word(VBAT)
        v_bat = 0.0
        if self.chemistry == LEAD_ACID:
            v_bat = v_bat_cell * 0.000128176
        elif self.chemistry != INVALID:
            v_bat = v_bat_cell * 0.0001922
        return v_bat * self.cell_count

    def get_charge_current(self) -> float:
        return float(self.read_word(IBAT)) * 0.00146487 / self.Rsnsb

    def get_die_temp(self) -> float:
        rawdie = self.read_word(DIE_TEMP)
        return (rawdie - 12010) / 45.6

    def get_battery_string(self) -> str:
        if self.chemistry == LI_ION:
            return "Li Ion"
        elif self.chemistry == LIFEPO4:
            return "LiFePO4"
        elif self.chemistry == LEAD_ACID:
            return "Lead Acid"
        else:
            return "Invalid"
