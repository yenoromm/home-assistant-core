"""Helper functions for the OpenRGB Integration."""
from homeassistant.components.light import ENTITY_ID_FORMAT


def orgb_tuple(color):
    """Unpack the RGB Object provided by the client library."""
    return (color.red, color.green, color.blue)


def orgb_object_id(instance):
    """Return the ORGB Devices object id."""
    return f"{instance.name} {instance.device_id}".replace(" ", "_").lower()


def orgb_entity_id(instance):
    """Return the ORGB devices entity ID."""
    return ENTITY_ID_FORMAT.format(orgb_object_id(instance))
