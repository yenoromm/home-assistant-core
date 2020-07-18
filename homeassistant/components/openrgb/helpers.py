"""Helper functions for the OpenRGB Integration."""


def orgb_tuple(color):
    """Unpack the RGB Object provided by the client library."""
    return (color.red, color.green, color.blue)
