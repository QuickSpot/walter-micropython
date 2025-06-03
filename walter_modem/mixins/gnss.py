import asyncio
import gc

from micropython import const # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemGNSSAssistanceType,
    WalterModemGNSSAction,
    WalterModemState,
    WalterModemRspType
)
from ..structs import (
    ModemRsp,
    ModemGNSSFix,
    ModemGnssFixWaiter,
    ModemGNSSAssistance,
    ModemGNSSSat
)
from ..utils import (
    parse_gnss_time,
    log
)

_UNICODE_0 = const(0)
_UNICODE_1 = const(1)
_UNICODE_2 = const(2)
_UNICODE_COMMA = const(44)
_UNICODE_BRACKET_OPEN = const(40)
_UNICODE_BRACKET_CLOSE = const(41)

class GNSSMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self.__gnss_fix_lock = asyncio.Lock()
        self.__gnss_fix_waiters = []

        self.__queue_rsp_rsp_handlers = (
            self.__queue_rsp_rsp_handlers + (
                (b'+LPGNSSFIXREADY: ', self.__handle_lp_gnss_fix_ready),
                (b'+LPGNSSASSISTANCE: ', self.__handle_lp_gnss_assistance),
            )
        )

        self.__mirror_state_reset_callables = (
            self.__mirror_state_reset_callables + (self._gnss_mirror_state_reset,)
        )

        self.__initialised_mixins.append(GNSSMixin)
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
        log('INFO', 'GNSS mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)
    
#region PublicMethods

    # Deprecated aliases, to bre removed in a later release

    async def config_gnss(self, *args, **kwargs):
        return await self.gnss_config(*args, **kwargs)
    
    async def get_gnss_assistance_status(self, *args, **kwargs):
        return await self.gnss_assistance_get_status(*args, **kwargs)
    
    async def update_gnss_assistance(self, *args, **kwargs):
        return await self.gnss_assistance_update(*args, **kwargs)
    
    async def perform_gnss_action(self, *args, **kwargs):
        return await self.gnss_perform_action(*args, **kwargs)
    
    async def wait_for_gnss_fix(self):
        return await self.gnss_wait_for_fix()

    # ---

    async def gnss_config(self,
        sens_mode: int = WalterModemGNSSSensMode.HIGH,
        acq_mode: int = WalterModemGNSSAcqMode.COLD_WARM_START,
        loc_mode: int = WalterModemGNSSLocMode.ON_DEVICE_LOCATION,
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSCFG={loc_mode},{sens_mode},2,,1,{acq_mode}',
            at_rsp=b'OK'
        )

    async def gnss_assistance_get_status(self,
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+LPGNSSASSISTANCE?',
            at_rsp=b'OK'
        )
    
    async def gnss_assistance_update(self,
        type: int = WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS, 
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSASSISTANCE={type}',
            at_rsp=b'+LPGNSSASSISTANCE:'
        )
    
    async def gnss_perform_action(self,
        action: int = WalterModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp = None
    ) -> bool:
        if action == WalterModemGNSSAction.GET_SINGLE_FIX:
            action_str = 'single'
        elif action == WalterModemGNSSAction.CANCEL:
            action_str = 'stop'
        else:
            action_str = ''

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSFIXPROG="{action_str}"',
            at_rsp=b'OK'
        )

    async def gnss_wait_for_fix(self) -> ModemGNSSFix:
        gnss_fix_waiter = ModemGnssFixWaiter()

        async with self.__gnss_fix_lock:
            self.__gnss_fix_waiters.append(gnss_fix_waiter)

        await gnss_fix_waiter.event.wait()

        return gnss_fix_waiter.gnss_fix

#endregion

#region PrivateMethods

    def _gnss_mirror_state_reset(self):
        self.__gnss_fix_lock = asyncio.Lock()
        self.__gnss_fix_waiters = []

#endregion

#region QueueResponseHandlers

    async def __handle_lp_gnss_fix_ready(self, tx_stream, cmd, at_rsp):
        data = at_rsp[len(b'+LPGNSSFIXREADY: '):]

        parenthesis_open = False
        part_no = 0
        start_pos = 0
        part = ''
        gnss_fix = ModemGNSSFix()

        for character_pos in range(len(data)):
            character = data[character_pos]
            part_complete = False

            if character == _UNICODE_COMMA and not parenthesis_open:
                part = data[start_pos:character_pos]
                part_complete = True
            elif character == _UNICODE_BRACKET_OPEN:
                parenthesis_open = True
            elif character == _UNICODE_BRACKET_CLOSE:
                parenthesis_open = False
            elif character_pos + 1 == len(data):
                part = data[start_pos:character_pos + 1]
                part_complete = True

            if part_complete:
                if part_no == 0:
                    gnss_fix.fix_id = int(part)
                elif part_no == 1:
                    part = part[1:-1]
                    gnss_fix.timestamp = parse_gnss_time(part)
                elif part_no == 2:
                    gnss_fix.time_to_fix = int(part)
                elif part_no == 3:
                    part = part[1:-1]
                    gnss_fix.estimated_confidence = float(part)
                elif part_no == 4:
                    part = part[1:-1]
                    gnss_fix.latitude = float(part)
                elif part_no == 5:
                    part = part[1:-1]
                    gnss_fix.longitude = float(part)
                elif part_no == 6:
                    part = part[1:-1]
                    gnss_fix.height = float(part)
                elif part_no == 7:
                    part = part[1:-1]
                    gnss_fix.north_speed = float(part)
                elif part_no == 8:
                    part = part[1:-1]
                    gnss_fix.east_speed = float(part)
                elif part_no == 9:
                    part = part[1:-1]
                    gnss_fix.down_speed = float(part)
                elif part_no == 10:
                     # Raw satellite signal sample is ignored
                    pass
                else:
                    satellite_data = part.decode().split(',')

                    # Iterate through the satellite_data list, taking every two elements as pairs
                    for i in range(0, len(satellite_data), 2):
                        sat_no_str = satellite_data[i]
                        sat_sig_str = satellite_data[i + 1]

                        gnss_fix.sats.append(ModemGNSSSat(int(sat_no_str[1:]), int(sat_sig_str[:-1])))

                # +1 for the comma
                part_no += 1
                start_pos = character_pos + 1
                part = ''

        # notify every coroutine that is waiting for a fix
        async with self.__gnss_fix_lock:
            for gnss_fix_waiter in self.__gnss_fix_waiters:
                gnss_fix_waiter.gnss_fix = gnss_fix
                gnss_fix_waiter.event.set()

            self.__gnss_fix_waiters = []
        
        return WalterModemState.OK

    async def __handle_lp_gnss_assistance(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return

        if cmd.rsp.type != WalterModemRspType.GNSS_ASSISTANCE_DATA:
            cmd.rsp.type = WalterModemRspType.GNSS_ASSISTANCE_DATA
            cmd.rsp.gnss_assistance = ModemGNSSAssistance()

        data = at_rsp[len("+LPGNSSASSISTANCE: "):]
        part_no = 0
        start_pos = 0
        part = ''
        gnss_details = None

        for character_pos in range(len(data)):
            character = data[character_pos]
            part_complete = False

            if character == _UNICODE_COMMA:
                part = data[start_pos:character_pos]
                part_complete = True
            elif character_pos + 1 == len(data):
                part = data[start_pos:character_pos + 1]
                part_complete = True

            if part_complete:
                if part_no == 0:
                    if part[0] == _UNICODE_0:
                        gnss_details = cmd.rsp.gnss_assistance.almanac
                    elif part[0] == _UNICODE_1:
                        gnss_details = cmd.rsp.gnss_assistance.realtime_ephemeris
                    elif part[0] == _UNICODE_2:
                        gnss_details = cmd.rsp.gnss_assistance.predicted_ephemeris
                elif part_no == 1:
                    if gnss_details:
                        gnss_details.available = int(part) == 1
                elif part_no == 2:
                    if gnss_details:
                        gnss_details.last_update = int(part)
                elif part_no == 3:
                    if gnss_details:
                        gnss_details.time_to_update = int(part)
                elif part_no == 4 and gnss_details:
                        gnss_details.time_to_expire = int(part)

                # +1 for the comma
                part_no += 1
                start_pos = character_pos + 1
                part = ''

        return WalterModemState.OK

#endregion
