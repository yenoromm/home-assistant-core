"""Constants for the OpenRGB integration."""

from datetime import timedelta

from openrgb.utils import DeviceType

DOMAIN = "openrgb"
ORGB_DATA = "openrgb_data"
ORGB_TRACKER = "openrgb_tracker"
ORGB_DISCOVERY_NEW = "openrgb_discovery_new_{}"

SERVICE_FORCE_UPDATE = "force_update"
SERVICE_PULL_DEVICES = "pull_devices"

ENTRY_IS_SETUP = "openrgb_entry_is_setup"

SIGNAL_DELETE_ENTITY = "openrgb_delete"
SIGNAL_UPDATE_ENTITY = "openrgb_update"


ICONS = {
    DeviceType.DEVICE_TYPE_MOTHERBOARD: "view-dashboard-outline",
    DeviceType.DEVICE_TYPE_DRAM: "memory",
    DeviceType.DEVICE_TYPE_GPU: "expansion-card",
    DeviceType.DEVICE_TYPE_COOLER: "fan",
    DeviceType.DEVICE_TYPE_LEDSTRIP: "led-outline",
    DeviceType.DEVICE_TYPE_KEYBOARD: "keyboard",
    DeviceType.DEVICE_TYPE_MOUSE: "mouse",
    DeviceType.DEVICE_TYPE_MOUSEMAT: "rug",
    DeviceType.DEVICE_TYPE_HEADSET: "headset",
    DeviceType.DEVICE_TYPE_HEADSET_STAND: "headset-dock",
    DeviceType.DEVICE_TYPE_UNKNOWN: "crosshairs-question",
}


TRACK_INTERVAL = timedelta(seconds=30)

DEFAULT_PORT = 6742
DEFAULT_CLIENT_ID = "Home Assistant"
