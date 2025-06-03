import gc

from micropython import const # type: ignore

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

_TLS_MIN_CTX_ID = const(1)
_TLS_MAX_CTX_ID = const(6)

class TLSCertsMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self.__initialised_mixins.append(TLSCertsMixin)
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
        log('INFO', 'TLS & Certs mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)

#region PublicMethods

    async def tls_config_profile(self,
        profile_id: int,
        tls_version: int,
        tls_validation: int,
        ca_certificate_id: int = None,
        client_certificate_id: int = None,
        client_private_key: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        if profile_id > _TLS_MAX_CTX_ID or profile_id <= 0:
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
        key_type = 'privatekey' if is_private_key else 'certificate'
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSNVW={modem_string(key_type)},{slot_idx},{len(credential)}',
            at_rsp=b'OK',
            data=credential,
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )

#endregion
