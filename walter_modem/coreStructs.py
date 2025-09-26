import gc
from asyncio import Event

from .coreEnums import *
from .utils import *

class WalterModemRsp:
    CORE_ATTR = (
        ('result', WalterModemState.OK),
        ('type', WalterModemRspType.NO_DATA),
        ('op_state', None),
        ('cme_error', None),
        ('clock', None),
    )
    _classType = None

    def __new__(cls, *attributes):
        if cls._classType is not None:
            if __debug__: log('DEBUG', 'New ModemRsp instance created')
            return cls._classType()
        
        if __debug__:
            log('DEBUG', 'Creating ModemRsp classType with:\n' + 
            '\n'.join(str(item) for item in (cls.CORE_ATTR + attributes)))

        cls._classType = type('ModemRsp', (), dict(cls.CORE_ATTR + attributes))
        gc.collect()

class WalterModemCmd:
    def __init__(self):
        self.state = WalterModemCmdState.NEW
        self.type = WalterModemCmdType.TX_WAIT
        self.at_cmd = b''
        self.data = None
        self.at_rsp = None
        self.max_attempts = 0        
        self.attempt = 0
        self.attempt_start = 0
        self.rsp = None
        self.ring_return = None
        self.complete_handler = None
        self.complete_handler_arg = None
        self.event = Event()

class WalterModemATParserData:
    def __init__(self):
        self.state = WalterModemRspParserState.START_CR
        self.line = b''
        self.raw_chunk_size = 0

class WalterModemTaskQueueItem:
    def __init__(self):
        self.rsp = None 
        self.cmd = None
