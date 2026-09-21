"""Python-side adapters for native hot paths.

An adapter module named after a ``FUNCTIONS`` entry exposes the same attribute
as its pure twin, flattens the input into arrays, calls ``jevdual._core``, and
rebuilds the twin's return type. ``available()`` says whether the core has the
functions the adapter needs, so a half-built extension falls back cleanly.
"""
