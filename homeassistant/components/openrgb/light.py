"""Platform for OpenRGB Integration."""
import logging

from openrgb import utils as RGBUtils

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    DOMAIN as SENSOR_DOMAIN,
    ENTITY_ID_FORMAT,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_EFFECT,
    LightEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import homeassistant.util.color as color_util

from .const import (
    DOMAIN,
    ICONS,
    ORGB_DISCOVERY_NEW,
    SIGNAL_DELETE_ENTITY,
    SIGNAL_UPDATE_ENTITY,
)
from .helpers import orgb_tuple

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up OpenRGB devices dynamically."""

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered openrgb sensor."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids,)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, ORGB_DISCOVERY_NEW.format(SENSOR_DOMAIN), async_discover_sensor
    )

    device_ids = hass.data[DOMAIN]["pending"].pop(SENSOR_DOMAIN)
    await async_discover_sensor(device_ids)


def _setup_entities(hass, dev_ids):
    """Set up OpenRGB Light device."""
    entities = []
    for dev_id in dev_ids:
        if dev_id is None:
            continue
        entities.append(OpenRGBLight(dev_id))
    return entities


class OpenRGBLight(LightEntity):
    """Representation of a OpenRGB Device."""

    def __init__(self, light):
        """Initialize an OpenRGB light."""
        self._light = light
        self._brightness = 100.0
        # For restoring the previous state when the light is power cycled.
        self._prev_brightness = 100.0
        self._prev_hs_value = (0.0, 0.0)
        self._prev_effect = self._light.modes[self._light.active_mode].name
        self._state = True
        self._assumed_state = True
        self.update()

        self.entity_id = ENTITY_ID_FORMAT.format(self.object_id)

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        dev_id = self.entity_id
        self.hass.data[DOMAIN]["entities"][dev_id] = dev_id
        async_dispatcher_connect(self.hass, SIGNAL_DELETE_ENTITY, self._delete_callback)
        async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._update_callback)

    # Device Properties

    @property
    def object_id(self):
        """Return the OpenRGB id."""
        return f"{self._light.name}-{self._light.device_id}"

    @property
    def unique_id(self):
        """Give each Device a unique ID."""
        return f"openrgb.{self.object_id}"

    @property
    def icon(self):
        """Give this device an icon representing what it is."""
        return "mdi:{}".format(ICONS.get(self._light.type, "lightbulb"))

    @property
    def name(self):
        """Return the display name of the light."""
        return self._name

    @property
    def available(self):
        """Return if the device is online."""
        return self.hass.data[DOMAIN]["online"]

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def hs_color(self):
        """Return the hue and saturation color value [float, float]."""
        return self._hs_value

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effects

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def assumed_state(self):
        """Return if the state is assumed."""
        return self._assumed_state

    @property
    def supported_features(self):
        """Return the supported features for this device."""
        return SUPPORT_EFFECT | SUPPORT_COLOR | SUPPORT_BRIGHTNESS

    @property
    def state_attributes(self):
        """Return state attributes."""
        if not self.is_on:
            return None

        data = {}
        supported_features = self.supported_features

        if supported_features & SUPPORT_BRIGHTNESS:
            data[ATTR_BRIGHTNESS] = self.brightness

        if supported_features & SUPPORT_COLOR and self.hs_color:
            # pylint: disable=unsubscriptable-object,not-an-iterable
            hs_color = self.hs_color
            data[ATTR_HS_COLOR] = (round(hs_color[0], 3), round(hs_color[1], 3))

        if supported_features & SUPPORT_EFFECT:
            data[ATTR_EFFECT] = self._effect

    # Public interfaces to control the device

    def turn_on(self, **kwargs):
        """Turn the device on, and set colors / modes."""
        if ATTR_HS_COLOR in kwargs:
            self._hs_value = kwargs.get(ATTR_HS_COLOR)

        if ATTR_EFFECT in kwargs:
            self._effect = kwargs.get(ATTR_EFFECT)
            self._set_effect()

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs.get(ATTR_BRIGHTNESS)

        # Restore the state if the light just gets turned on
        if not kwargs:
            self._hs_value = self._prev_hs_value
            self._brightness = self._prev_brightness
            self._effect = self._prev_effect

        self._set_color()
        self._state = True

    def turn_off(self, **kwargs):
        """Turn the device off."""
        # preserve the state
        self._prev_brightness = self._brightness
        self._prev_hs_value = self._hs_value
        self._prev_effect = self._effect

        # Instead of using the libraries off() method, setting the brightness
        # preserves the color for when it gets turned on again.
        self._brightness = 0.0

        self._set_color()
        self._state = False

    def update(self):
        """Single function to update the devices state."""
        self._name = self._light.name
        self._hs_value = color_util.color_RGB_to_hs(*orgb_tuple(self._light.colors[0]))
        self._effect = self._light.modes[self._light.active_mode].name
        self._effects = list(map(lambda x: x.name, self._light.modes))

        # For many devices, if OpenRGB hasn't set it, the initial state is
        # unknown as they don't otherwise provide a way of reading it.
        #
        # So, we have to assume if we get a color of (0.0, 0.0) and we
        # haven't changed the state ourselves, that this is an assumed state.
        if self._assumed_state:
            if self._hs_value != (0.0, 0.0):
                self._assumed_state = False

    # Functions to modify the devices state
    def _set_effect(self):
        """Set the devices effect."""
        self._light.set_mode(self._effect)

    def _set_color(self):
        """Set the devices color using the library."""
        color = color_util.color_hsv_to_RGB(
            *(self._hs_value), 100.0 * (self._brightness / 255.0)
        )

        self._light.set_color(RGBUtils.RGBColor(*color))
        self._assumed_state = False

    # Callbacks
    @callback
    async def _delete_callback(self, dev_id):
        """Remove this entity."""
        if dev_id == self.object_id:
            entity_registry = (
                await self.hass.helpers.entity_registry.async_get_registry()
            )
            if entity_registry.async_is_registered(self.entity_id):
                entity_registry.async_remove(self.entity_id)
            else:
                await self.async_remove()

    @callback
    async def _update_callback(self):
        """Call update method."""
        self.update()
        self.async_schedule_update_ha_state(True)
