"""Provider adapter package.

Each adapter is an independent module so the import cost of unused
providers (and the security blast radius of their SDKs) stays out of
core cantus. Shared translation helpers live in `_translate.py`.
"""
