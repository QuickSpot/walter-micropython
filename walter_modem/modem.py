import time
from machine import Pin

from .core import ModemCore
import walter_modem.mixins as mixins
from .enums import (
    WalterModemCmdType,
    WalterModemCMEErrorReportsType,
    WalterModemCEREGReportsType,
    WalterModemSQNMONIReportsType,
    WalterModemNetworkSelMode,
    WalterModemOperatorFormat,
    WalterModemState
)
from .structs import (
    ModemRsp,
)
from .utils import (
    modem_string,
    log
)

class Modem(
    mixins.ModemGNSS,
    mixins.ModemHTTP,
    mixins.ModemPDP,
    mixins.ModemSocket,
    mixins.ModemMQTT
):
    def __init__(self):
        ModemCore.__init__(self)
    
    def get_network_reg_state(self) -> int:
        """
        Get the network registration state.
        This is buffered by the library and thus instantly available.

        :return int: The current modem registration state
        """
        return self._reg_state
    
    async def reset(self, rsp: ModemRsp = None) -> bool:
        """
        Physically reset the modem and wait for it to start.
        All connections will be lost when this function is called.
        The function will fail when the modem doesn't start after the reset.

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        reset_pin = Pin(ModemCore.WALTER_MODEM_PIN_RESET, Pin.OUT)
        reset_pin.off()
        time.sleep(0.1)
        reset_pin.on()

        # Also reset internal "modem mirror" state
        super().__init__()

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='',
            at_rsp=b'+SYSSTART',
            cmd_type=WalterModemCmdType.WAIT
        )
    
    async def check_comm(self, rsp: ModemRsp = None) -> bool:
        """
        Sends the 'AT' command to check if the modem responds with 'OK',
        verifying communication between the ESP32 and the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT',
            at_rsp=b'OK'
        )
    
    async def get_clock(self, rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the current time and date from the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CCLK?',
            at_rsp=b'OK'
        )

    
    async def config_cme_error_reports(self,
        reports_type: int = WalterModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CME error report type.
        By default, errors are enabled and numeric.
        Changing this may affect error reporting.

        :param reports_type: The CME error report type.
        :type reports_type: WalterModemCMEErrorReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CMEE={reports_type}',
            at_rsp=b'OK'
        )
    
    async def config_cereg_reports(self,
        reports_type: int = WalterModemCEREGReportsType.ENABLED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CEREG status report type.
        By default, reports are enabled with minimal operational info.
        Changing this may affect library functionality.

        :param reports_type: The CEREG status reports type.
        :type reports_type: WalterModemCEREGReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CEREG={reports_type}',
            at_rsp=b'OK'
        )
    
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
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMODEACTIVE={rat}',
            at_rsp=b'OK'
        )

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
        self._sim_PIN = pin
        if self._sim_PIN is None:
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
        self._network_sel_mode = mode
        self._operator.format = operator_format
        self._operator.name = operator_name

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
                    self._network_sel_mode, self._operator.format,
                    modem_string(self._operator.name)
                ),
                at_rsp=b'OK'
            )

    async def tls_config_profile(self,
        profile_id: int,
        tls_version: int,
        tls_validation: int,
        ca_certificate_id: int = None,
        client_certificate_id: int = None,
        client_private_key: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures TLS profiles in the modem,
        including optional client authentication certificates, validation levels, and TLS version. 
        This should be done in an initializer sketch, 
        allowing later HTTP, MQTT, CoAP, or socket sessions to use the preconfigured profile IDs.

        :param profile_id: Security profile id (1-6)
        :param tls_version: TLS version
        :type tls_version: WalterModemTlsVersion
        :param tls_validation: TLS validation level: nothing, URL, CA+period or all
        :type tls_validation: WalterModemTlsValidation
        :param ca_certificate_id: CA certificate for certificate validation (0-19)
        :param client_certificate_id: Client TLS certificate index (0-19)
        :param client_private_key: Client TLS private key index (0-19)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id > ModemCore.WALTER_MODEM_MAX_TLS_PROFILES or profile_id <= 0:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        cmd = 'AT+SQNSPCFG={},{},"",{}'.format(
                profile_id, tls_version, tls_validation, 
        )

        cmd += ','
        if ca_certificate_id is not None:
            cmd += f'{ca_certificate_id}'

        cmd += ','
        if client_certificate_id is not None:
            cmd += f',{client_certificate_id}'
        
        cmd += ','
        if client_private_key is not None:
            cmd += f',{client_private_key}'

        cmd += ',"","",0'
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK',
        )
    
    async def _tls_upload_key(self,
        is_private_key: bool,
        slot_idx: int,
        key,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to store a certificate or a key in the NVRAM of the modem
        """
        key_type = 'privatekey' if is_private_key else 'certificate'
        return self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSNVW={modem_string(key_type)},{slot_idx},{len(key)}',
            at_rsp=b'OK',
            data=key,
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )

    # TODO: update docstring to match style of others
    async def tls_provision_keys(self,
        walter_certificate,
        walter_private_key,
        ca_certificate,
        rsp: ModemRsp = None
        ) -> bool:
        """
        Coroutine to store certificates and/or keys in the NVRAM of the modem.
        This is a wrapper for _tls_upload_key, which does the actual uploading.
        Basically a copy of the Arduino example, including the slot numbers of the
        NVRAM, which seem arbitrary.
        """
        if walter_certificate:
            if not await self._tls_upload_key(False, 5, walter_certificate, rsp):
                if self.debug_log: log('DEBUG'
                    'Failed to upload client certificate.')
                return False
            if self.debug_log: log('DEBUG',
                'Certificate stored in NVRAM slot 5.')

        if walter_private_key:
            if not await self._tls_upload_key(True, 0, walter_private_key, rsp):
                if self.debug_log: log('DEBUG',
                    'Failed to upload private key.')
                return False
            if self.debug_log: log('DEBUG',
                'Private key stored in NVRAM slot 0.')

        if ca_certificate:
            if not await self._tls_upload_key(False, 6, ca_certificate, rsp):
                if self.debug_log: log('DEBUG',
                    'Failed to upload CA certificate.')
                return False
            if self.debug_log: log('DEBUG',
                'CA certificate stored in NVRAM slot 6.')

        return True