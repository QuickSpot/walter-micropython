from ..core import ModemCore
from ..enums import (
    WalterModemSQNMONIReportsType,
    WalterModemNetworkSelMode,
    WalterModemOperatorFormat,
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    modem_string
)

class ModemSimNetwork(ModemCore):
    async def get_op_state(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the modem's current operational state.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CFUN?',
            at_rsp=b'OK'
        )
    
    async def set_op_state(self, op_state: int, rsp: ModemRsp = None) -> bool:
        """
        Sets the operational state of the modem.

        :param op_state: The new operational state of the modem.
        :type op_state: WalterModemOpState
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CFUN={op_state}',
            at_rsp=b'OK'
        )

    def get_network_reg_state(self) -> int:
        """
        Get the network registration state.
        This is buffered by the library and thus instantly available.

        :return int: The current modem registration state
        """
        return self._reg_state
    
    async def get_rssi(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the RSSI information.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CSQ',
            at_rsp=b'OK'
        )
    
    async def get_signal_quality(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves information about the serving and neighbouring cells,
        including operator, cell ID, RSSI, and RSRP.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CESQ',
            at_rsp=b'OK'
        )
    
    async def get_cell_information(self,
        reports_type: int = WalterModemSQNMONIReportsType.SERVING_CELL,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the modem's identity details, including IMEI, IMEISV, and SVN.

        :param reports_type: The type of cell information to retreive,
        defaults to the cell which is currently serving the connection.
        :type reports_type: WalterModemSQNMONIReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMONI={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_rat(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the Radio Access Technology (RAT) for the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNMODEACTIVE?',
            at_rsp=b'OK'
        )
    
    async def set_rat(self, rat: int, rsp: ModemRsp = None) -> bool:
        """
        Sets the Radio Access Technology (RAT) for the modem.

        :param rat: The new RAT
        :type rat: WalterModemRat
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        rat_cmd_result = await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMODEACTIVE={rat}',
            at_rsp=b'OK'
        )
        
        return rat_cmd_result and await self.soft_reset()
        

    async def get_radio_bands(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the radio bands the modem is configured to use for network connection.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNBANDSEL?',
            at_rsp=b'OK'
        )
    
    async def get_sim_state(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the state of the SIM card.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CPIN?',
            at_rsp=b'OK'
        )

    async def unlock_sim(self, pin: str = None, rsp: ModemRsp = None) -> bool:
        """
        Sets the SIM card's PIN code.
        The modem must be in FULL or NO_RF operational state.

        :param pin: The PIN code of the SIM card or NULL for no pin.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
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
        """
        Sets the network selection mode for Walter.
        This command is only available when the modem is in the fully operational state.

        :param mode: The network selection mode.
        :type mode: WalterModemNetworkSelMode
        :param operator_name: The network operator name in case manual selection has been chosen.
        :param operator_format: The format in which the network operator name is passed.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

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