"""RAM-only physical disk permissions; no ROM changes required. MIT."""
def patch_floppy(payload,manifest,writable=None):
    data=bytearray(payload)
    if manifest.get('drive_support',1)<4:
        if writable:raise ValueError('platform lacks floppy support')
        return bytes(data)
    offset=manifest['runtime_offsets']['floppy_write_mask']
    if data[offset]!=0:raise ValueError('unrecognized default floppy permissions')
    data[offset]=sum(bit for letter,bit in [('C',1),('D',2)] if letter in (writable or ''))
    return bytes(data)
