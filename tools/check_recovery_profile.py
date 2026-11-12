#!/usr/bin/env python3
"""MIT. A CRC rejection cannot execute and returns to checked ROM discovery."""
import tempfile
from pathlib import Path
from unittest.mock import Mock,patch
import recovery_profile as profile
with tempfile.TemporaryDirectory() as directory:
    port=Mock();port.fd=7
    config=dict(settings=dict(baud=19200,parity='O',stop_bits=1),
        boot_settings=dict(baud=19200,parity='O',stop_bits=1),session=directory,
        options=dict(platform=str(Path(directory)/'platform.cim'),image='unused',optimized=False))
    identity=dict(version=[3,0,0],parity='O',stop_bits=1)
    with patch.object(profile,'query',return_value=identity),patch.object(profile,'validate',return_value=b'payload'),patch.object(profile,'bootstrap',side_effect=ValueError('ROM rejected upload: 15; reset and retry')),patch.object(profile,'write_all') as execute:
        result=profile.recover(port,config)
        assert result['status']=='unknown' and result['upload_rejected']
        execute.assert_not_called()
print('RECOVERY-PROFILE: PASS (rejected upload never executes)')
