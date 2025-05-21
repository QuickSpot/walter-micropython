import gc

from .core import ModemCore
from .utils import (
    log
)

class Modem:
    _instance = None

    def __new__(cls,
        *mixins,
        load_default_pdp_mixin=True,
        load_default_sim_network_mixin=True,
        load_default_sleep_mixin=True
    ):
        if cls._instance is not None:
            if __debug__: log('DEBUG', 'Returning exisiting Modem instance')
            return cls._instance
        
        for mixin in mixins:
            if not issubclass(mixin, ModemCore):
                raise TypeError(f'{mixin.__name__} is not a valid ModemMixin')
        
        # Default Mixins
        # Technically not needed for the library to function
        # Practically often wanted by the end-user

        if load_default_pdp_mixin:
            from .mixins._default_pdp import _ModemPDP
            mixins = (mixins + (_ModemPDP,))
        
        if load_default_sim_network_mixin:
            from .mixins._default_sim_network import _ModemSimNetwork
            mixins = (mixins + (_ModemSimNetwork,))
        
        if load_default_sleep_mixin:
            from .mixins._default_sleep import _ModemSleep
            mixins = (mixins + (_ModemSleep,))
        
        if not (
            load_default_pdp_mixin or
            load_default_sim_network_mixin or
            load_default_sleep_mixin
        ):
            mixins = (mixins + (ModemCore,))
        
        # ---

        ModemClass = type('Modem', mixins, {})

        if __debug__:
            log('DEBUG', 'Creating Modem with: '
            + ', '.join(b.__name__ for b in ModemClass.__bases__))

        cls._instance = ModemClass()
        gc.collect()
        return cls._instance