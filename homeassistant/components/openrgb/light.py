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
        self._name = light.name
        self._hs_value = color_util.color_RGB_to_hs(*self._rgb_tuple(light.colors[0]))
        self._brightness = 100.0
        self._state = True
        self._effect = None

        self.entity_id = ENTITY_ID_FORMAT.format(self.object_id)

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        dev_id = self.entity_id
        self.hass.data[DOMAIN]["entities"][dev_id] = dev_id
        async_dispatcher_connect(self.hass, SIGNAL_DELETE_ENTITY, self._delete_callback)
        async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._update_callback)

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
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return None

    @property
    def hs_color(self):
        """Return the hue and saturation color value [float, float]."""
        return None

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        return None

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        effects = list(map(lambda x: x.name, self._light.modes))

        return effects

    @property
    def effect(self):
        """Return the current effect."""
        return None

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._light.off()
        self._state = False

    def turn_on(self, **kwargs):
        """Turn the device on, and set colors / modes."""
        if ATTR_HS_COLOR in kwargs:
            self._hs_value = kwargs.get(ATTR_HS_COLOR)

        if ATTR_EFFECT in kwargs:
            mode_name = kwargs.get(ATTR_EFFECT)
            self._light.set_mode(mode_name)

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs.get(ATTR_BRIGHTNESS)

        color = color_util.color_hsv_to_RGB(
            *(self._hs_value), 100.0 * (self._brightness / 255.0)
        )

        self._light.set_color(RGBUtils.RGBColor(*color))
        self._state = True

    def _rgb_tuple(self, rgbcolor):
        """Unpacks the RGB Object provided by the library."""
        return (rgbcolor.red, rgbcolor.green, rgbcolor.blue)

    def update(self):
        """Fetch new state data for this light."""
        pass

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

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

        return {key: val for key, val in data.items() if val is not None}

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
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)
