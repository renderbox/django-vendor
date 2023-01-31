"""
The encoder and decoder are used for data that gets temporarily stored in the user's session.

To use set the VENDOR_DATA_ENCODER to 'vendor.encrypt.cleartext' in settings.py

This is a 'passthrough encoder' (which is the default) for development.  It should be replaced with a proper encoder to protect user data.

To make your own, the module expects to have 'encode' and 'decode' functions.  Everything else is up to you.
"""

def encode(data):
    return data

def decode(data):
    return data
