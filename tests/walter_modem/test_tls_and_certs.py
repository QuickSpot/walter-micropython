import micropython # type: ignore
micropython.opt_level(1)

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.mixins.tls_certs import (
    TLSCertsMixin,
    WalterModemTlsValidation,
    WalterModemTlsVersion
)

CERT = """-----BEGIN CERTIFICATE-----
MIIBNTCB3AICEAEwCgYIKoZIzj0EAwMwJDELMAkGA1UEBhMCQkUxFTATBgNVBAMM
DGludGVybWVkaWF0ZTAeFw0yNDAzMjUxMDU5MzRaFw00NDA0MDkxMDU5MzRaMCkx
CzAJBgNVBAYTAkJFMRowGAYDVQQDDBFsaXRlMDAwMS4xMTExMTExMTBZMBMGByqG
SM49AgEGCCqGSM49AwEHA0IABPnA7m6yDd0w6iNuKWJ5T3eMB38Upk1yfM+fUUth
AY/qh/BM8JYqG0KFpbR0ymNe+KU0m2cUCPR1QIUVvp3sIYYwCgYIKoZIzj0EAwMD
SAAwRQIgDkAa7P78ieIamFqj8el2zL0oL/VHBYcTQL9/ZzsJBSkCIQCRFMsbIHc/
AiKVsr/pbTYtxbyz0UJKUlVoM2S7CjeAKg==
-----END CERTIFICATE-----"""

SLOT_IDX = 19
"""
CAREFUL; the tests will overwrite/delete this slot's content.
If there's something in this index you wish not to be overwriten/deleted, change the slot idx.
"""

TLS_PROFILE_ID = 6
"""
CAREFUL; the tests will overwrite this profile.
If there is a profile with this ID you wish not to be overwritten, change this id.
"""

modem = Modem(TLSCertsMixin)

class TestTLSAndCertificates(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        await modem.begin()

    # ---
    # tls_write_credential()

    async def test_tls_write_credential_runs_write(self):
        self.assert_true(await modem.tls_write_credential(
            is_private_key=False,
            slot_idx=SLOT_IDX,
            credential=CERT
        ))
    
    async def test_tls_write_credential_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+SQNSNVW="certificate",{SLOT_IDX},{len(CERT)}',
            lambda: modem.tls_write_credential(
                is_private_key=False,
                slot_idx=SLOT_IDX,
                credential=CERT
            )
        )
    
    async def test_tls_write_credential_runs_delete(self):
        self.assert_true(await modem.tls_write_credential(
            is_private_key=False,
            slot_idx=SLOT_IDX,
            credential=''
        ))

    # ---
    # tls_config_profile()
    
    async def test_tls_config_profile(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+SQNSPCFG={TLS_PROFILE_ID},3,"",0,,,,"","",0,0,0',
            lambda: modem.tls_config_profile(
                profile_id=TLS_PROFILE_ID,
                tls_validation=WalterModemTlsValidation.NONE,
                tls_version=WalterModemTlsVersion.TLS_VERSION_13
            )
        )
    
    async def test_tls_config_profile_runs(self):
        self.assert_true(await modem.tls_config_profile(
            profile_id=TLS_PROFILE_ID,
            tls_validation=WalterModemTlsValidation.NONE,
            tls_version=WalterModemTlsVersion.TLS_VERSION_12
        ))

test_tls_and_certificates = TestTLSAndCertificates()
test_tls_and_certificates.run()