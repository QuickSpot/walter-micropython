import gc

from micropython import const # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemSQNMONIReportsType,
    WalterModemNetworkSelMode,
    WalterModemOperatorFormat,
    WalterModemRspType,
    WalterModemState,
    WalterModemRat,
    WalterModemSimState
)
from ..structs import (
    ModemRsp,
    ModemSignalQuality,
    ModemBandSelection,
    ModemCellInformation
)
from ..utils import (
    modem_string,
    log
)

_OPERATOR_MAX_SIZE = const(16)
"""The maximum number of characters of an operator name"""

class SimNetworkMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self.__queue_rsp_rsp_handlers = (
            self.__queue_rsp_rsp_handlers + (
                (b'+SQNMODEACTIVE: ', self.__handle_mode_active),
                (b'+CESQ: ', self.__handle_cesq),
                (b'+CSQ: ', self.__handle_csq),
                (b'+SQNMONI', self.__handle_sqnmoni),
                (b'+SQNBANDSEL: ', self.__handle_band_sel),
                (b'+CPIN: ', self.__handle_cpin),
            )
        )

        self.__initialised_mixins.append(SimNetworkMixin)
        if len(self.__initialised_mixins) == len(self.__class__.__bases__):
            del self.__initialised_mixins
            next_base = None
        else:
            next_base: callable
            for base in self.__class__.__bases__:
                if base not in self.__initialised_mixins:
                    next_base = base
                    break

        gc.collect()
        log('INFO', '(default) SIM & Network mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)

#region PublicMethods

    async def get_rssi(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CSQ',
            at_rsp=b'OK'
        )
    
    async def get_signal_quality(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CESQ',
            at_rsp=b'OK'
        )
    
    async def get_cell_information(self,
        reports_type: int = WalterModemSQNMONIReportsType.SERVING_CELL,
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMONI={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_rat(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNMODEACTIVE?',
            at_rsp=b'OK'
        )
    
    async def set_rat(self, rat: int, rsp: ModemRsp = None) -> bool:
        rat_cmd_result = await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMODEACTIVE={rat}',
            at_rsp=b'OK'
        )
        
        return rat_cmd_result and await self.soft_reset()
        

    async def get_radio_bands(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNBANDSEL?',
            at_rsp=b'OK'
        )
    
    async def get_sim_state(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CPIN?',
            at_rsp=b'OK'
        )

    async def unlock_sim(self, pin: str = None, rsp: ModemRsp = None) -> bool:
        if pin is None:
            return await self.get_sim_state()

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CPIN={pin}',
            at_rsp=b'OK'
        )

    async def set_network_selection_mode(self,
        mode: int = WalterModemNetworkSelMode.AUTOMATIC,
        operator_name: str = '',
        operator_format: int = WalterModemOperatorFormat.LONG_ALPHANUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        if mode == WalterModemNetworkSelMode.AUTOMATIC:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd=f'AT+COPS={mode}',
                at_rsp=b'OK'
            )
        else:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd='AT+COPS={},{},{}'.format(
                    mode, operator_format,
                    modem_string(operator_name)
                ),
                at_rsp=b'OK'
            )

#endregion

#region QueueResponseHandlers

    async def __handle_mode_active(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return None
        
        cmd.rsp.type = WalterModemRspType.RAT
        cmd.rsp.rat = int(at_rsp.decode().split(':')[1])

        return WalterModemState.OK

    async def __handle_cesq(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.SIGNAL_QUALITY

        parts = at_rsp.decode().split(',')
        cmd.rsp.signal_quality = ModemSignalQuality()
        cmd.rsp.signal_quality.rsrq = -195 + (int(parts[4]) * 5)
        cmd.rsp.signal_quality.rsrp = -140 + int(parts[5])

        return WalterModemState.OK

    async def __handle_csq(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        parts = at_rsp.decode().split(',')
        raw_rssi = int(parts[0][len('+CSQ: '):])

        cmd.rsp.type = WalterModemRspType.RSSI
        cmd.rsp.rssi = -113 + (raw_rssi * 2)

        return WalterModemState.OK

    async def __handle_sqnmoni(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return

        cmd.rsp.type = WalterModemRspType.CELL_INFO

        data_str = at_rsp[len(b"+SQNMONI: "):].decode()

        cmd.rsp.cell_information = ModemCellInformation()
        first_key_parsed = False

        for part in data_str.split(' '):
            if ':' not in part:
                continue
                
            pattern, value = part.split(':', 1)
            pattern = pattern.strip()
            value = value.strip()

            if not first_key_parsed and len(pattern) > 2:
                operator_name = pattern[:-2]
                cmd.rsp.cell_information.net_name = operator_name[:_OPERATOR_MAX_SIZE]
                pattern = pattern[-2:]
                first_key_parsed = True

            if pattern == "Cc":
                cmd.rsp.cell_information.cc = int(value, 10)
            elif pattern == "Nc":
                cmd.rsp.cell_information.nc = int(value, 10)
            elif pattern == "RSRP":
                cmd.rsp.cell_information.rsrp = float(value)
            elif pattern == "CINR":
                cmd.rsp.cell_information.cinr = float(value)
            elif pattern == "RSRQ":
                cmd.rsp.cell_information.rsrq = float(value)
            elif pattern == "TAC":
                cmd.rsp.cell_information.tac = int(value, 10)
            elif pattern == "Id":
                cmd.rsp.cell_information.pci = int(value, 10)
            elif pattern == "EARFCN":
                cmd.rsp.cell_information.earfcn = int(value, 10)
            elif pattern == "PWR":
                cmd.rsp.cell_information.rssi = float(value)
            elif pattern == "PAGING":
                cmd.rsp.cell_information.paging = int(value, 10)
            elif pattern == "CID":
                cmd.rsp.cell_information.cid = int(value, 16)
            elif pattern == "BAND":
                cmd.rsp.cell_information.band = int(value, 10)
            elif pattern == "BW":
                cmd.rsp.cell_information.bw = int(value, 10)
            elif pattern == "CE":
                cmd.rsp.cell_information.ce_level = int(value, 10)

        return WalterModemState.OK

    async def __handle_band_sel(self, tx_stream, cmd, at_rsp):
        data = at_rsp[len(b'+SQNBANDSEL: '):]

        # create the array and response type upon reception of the
        # first band selection
        if cmd.rsp.type != WalterModemRspType.BANDSET_CFG_SET:
            cmd.rsp.type = WalterModemRspType.BANDSET_CFG_SET
            cmd.rsp.band_sel_cfg_list = []

        bsel = ModemBandSelection()

        if data[0] == ord('0'):
            bsel.rat = WalterModemRat.LTEM
        else:
            bsel.rat = WalterModemRat.NBIOT

        # Parse operator name
        bsel.net_operator.format = WalterModemOperatorFormat.LONG_ALPHANUMERIC
        bsel_parts = data[2:].decode().split(',')
        bsel.net_operator.name = bsel_parts[0]

        # Parse configured bands
        bands_list = bsel_parts[1:]
        if len(bands_list) > 1:
            bands_list[0] = bands_list[0][1:]
            bands_list[-1] = bands_list[-1][:-1]
            bsel.bands = [ int(x) for x in bands_list ]
        elif bands_list[0] != '""':
            bsel.bands = [ int(bands_list[0][1:-1]) ]
        else:
            bsel.bands = []

        cmd.rsp.band_sel_cfg_list.append(bsel)
        return WalterModemState.OK

    async def __handle_cpin(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return None

        cmd.rsp.type = WalterModemRspType.SIM_STATE
        if at_rsp[len('+CPIN: '):] == b'READY':
            cmd.rsp.sim_state = WalterModemSimState.READY
        elif at_rsp[len('+CPIN: '):] == b"SIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PUK":
            cmd.rsp.sim_state = WalterModemSimState.PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_SIM_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_FIRST_SIM_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PUK":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_FIRST_SIM_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PIN2":
            cmd.rsp.sim_state = WalterModemSimState.PIN2_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PUK2":
            cmd.rsp.sim_state = WalterModemSimState.PUK2_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NET PIN":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NET PUK":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PIN":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_SUBSET_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PUK":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_SUBSET_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SP PIN":
            cmd.rsp.sim_state = WalterModemSimState.SERVICE_PROVIDER_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SP PUK":
            cmd.rsp.sim_state = WalterModemSimState.SERVICE_PROVIDER_PUK_REQUIRED 
        elif at_rsp[len('+CPIN: '):] == b"PH-CORP PIN":
            cmd.rsp.sim_state = WalterModemSimState.CORPORATE_SIM_REQUIRED 
        elif at_rsp[len('+CPIN: '):] == b"PH-CORP PUK":
            cmd.rsp.sim_state = WalterModemSimState.CORPORATE_PUK_REQUIRED 
        else:
            cmd.rsp.type = WalterModemRspType.NO_DATA

        return WalterModemState.OK

#endregion
