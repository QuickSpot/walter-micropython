from ..core import ModemCore
from ..enums import (
    WalterModemCmdType,
    WalterModemState
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    modem_string,
    log
)

class ModemTLSCerts(ModemCore):
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
        if profile_id > ModemCore.MAX_TLS_PROFILES or profile_id <= 0:
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
            cmd += f'{client_certificate_id}'
        
        cmd += ','
        if client_private_key is not None:
            cmd += f'{client_private_key}'

        cmd += ',"","",0,0,0'
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK',
        )
    
    async def tls_write_credential(self,
        is_private_key: bool,
        slot_idx: int,
        credential,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Upload key or certificate to modem NVRAM.

        It is recommended to save credentials in index 10-19 to avoid overwriting preinstalled
        certificates and (if applicable) BlueCherry cloud platform credentials.

        :param is_private_key: True if it's a private key, False if it's a certificate
        :param slot_idx: Slot index within the modem NVRAM keystore
        :param credential: NULL-terminated string containing the PEM key/cert data
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        key_type = 'privatekey' if is_private_key else 'certificate'
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSNVW={modem_string(key_type)},{slot_idx},{len(credential)}',
            at_rsp=b'OK',
            data=credential,
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )

    async def tls_provision_keys(self,
        walter_certificate,
        walter_private_key,
        ca_certificate,
        rsp: ModemRsp = None
        ) -> bool:
        """
        DEPRECATED: This method will be removed in future releases.
        It is still present for backwards compatibility.
        Use tls_write_credential() instead.
        """
        if walter_certificate:
            if not await self.tls_write_credential(False, 5, walter_certificate, rsp):
                if self.debug_log: log('DEBUG'
                    'Failed to upload client certificate.')
                return False
            if self.debug_log: log('DEBUG',
                'Certificate stored in NVRAM slot 5.')

        if walter_private_key:
            if not await self.tls_write_credential(True, 0, walter_private_key, rsp):
                if self.debug_log: log('DEBUG',
                    'Failed to upload private key.')
                return False
            if self.debug_log: log('DEBUG',
                'Private key stored in NVRAM slot 0.')

        if ca_certificate:
            if not await self.tls_write_credential(False, 6, ca_certificate, rsp):
                if self.debug_log: log('DEBUG',
                    'Failed to upload CA certificate.')
                return False
            if self.debug_log: log('DEBUG',
                'CA certificate stored in NVRAM slot 6.')

        return True
