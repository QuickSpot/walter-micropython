import gc

from .core import ModemCore
from .coreStructs import WalterModemRsp
from .utils import log

class Modem:
    _instance = None

    def __new__(cls,
        *mixins,
        load_default_pdp_mixin=True,
        load_default_sim_network_mixin=True,
        load_default_power_saving_mixin=True
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
            from .mixins.default_pdp import PDPMixin
            mixins = (mixins + (PDPMixin,))

        if load_default_sim_network_mixin:
            from .mixins.default_sim_network import SimNetworkMixin
            mixins = (mixins + (SimNetworkMixin,))

        if load_default_power_saving_mixin:
            from .mixins.default_power_saving import PowerSavingMixin
            mixins = (mixins + (PowerSavingMixin,))

        if not (
            load_default_pdp_mixin or
            load_default_sim_network_mixin or
            load_default_power_saving_mixin
        ):
            mixins = (mixins + (ModemCore,))

        # ---

        ModemClass = type('Modem', mixins, {})
        WalterModemRsp(*(
            field
            for mixin in mixins if hasattr(mixin, 'MODEM_RSP_FIELDS')
            for field in mixin.MODEM_RSP_FIELDS
        ))

        if __debug__:
            log('DEBUG', 'Creating Modem with: '
            + ', '.join(b.__name__ for b in ModemClass.__bases__))

        cls._instance = ModemClass()
        gc.collect()
        return cls._instance