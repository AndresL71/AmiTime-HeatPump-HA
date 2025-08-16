"""Sensor platform for the Heat Pump integration."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text_sensor import TextSensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    coordinator = hass.data[hass.data["heat_pump"].domain]
    
    sensors = [
        HeatPumpSensor(coordinator, "Tuo", "°C", "mdi:thermometer", "tuo"),
        HeatPumpSensor(coordinator, "Tui", "°C", "mdi:thermometer", "tui"),
        HeatPumpSensor(coordinator, "Tup", "°C", "mdi:thermometer", "tup"),
        HeatPumpSensor(coordinator, "Tw", "°C", "mdi:thermometer", "tw"),
        HeatPumpSensor(coordinator, "Tc", "°C", "mdi:thermometer", "tc"),
        HeatPumpSensor(coordinator, "Tv1", "°C", "mdi:thermometer", "tv1"),
        HeatPumpSensor(coordinator, "Tv2", "°C", "mdi:thermometer", "tv2"),
        HeatPumpSensor(coordinator, "Tr", "°C", "mdi:thermometer", "tr"),
        HeatPumpSensor(coordinator, "PWM", "%", "mdi:fan", "pwm"),
        HeatPumpSensor(coordinator, "Frequency", "Hz", "mdi:pulse", "frequency"),
        HeatPumpSensor(coordinator, "Pd", "kPa", "mdi:gauge", "pd"),
        HeatPumpSensor(coordinator, "Ps", "kPa", "mdi:gauge", "ps"),
        HeatPumpSensor(coordinator, "Ta", "°C", "mdi:thermometer", "ta"),
        HeatPumpSensor(coordinator, "Td", "°C", "mdi:thermometer", "td"),
        HeatPumpSensor(coordinator, "Ts", "°C", "mdi:thermometer", "ts"),
        HeatPumpSensor(coordinator, "Tp", "°C", "mdi:thermometer", "tp"),
        HeatPumpSensor(coordinator, "Fan", "%", "mdi:fan", "fan"),
        HeatPumpSensor(coordinator, "Current", "A", "mdi:current-ac", "current"),
        HeatPumpSensor(coordinator, "Voltage", "V", "mdi:flash", "voltage"),
        HeatPumpSensor(coordinator, "P0", "kW", "mdi:power-socket-eu", "p0"),
        HeatPumpSensor(coordinator, "P1", "kW", "mdi:power-socket-eu", "p1"),
        HeatPumpSensor(coordinator, "P2", "kW", "mdi:power-socket-eu", "p2"),
    ]
    
    text_sensors = [
        HeatPumpTextSensor(coordinator, "Function", "mdi:water-boiler", "function"),
        HeatPumpTextSensor(coordinator, "Thermostat", "mdi:thermostat", "thermostat"),
        HeatPumpTextSensor(coordinator, "Valve op", "mdi:valve", "valve_op")
    ]
    
    async_add_entities(sensors + text_sensors)

class HeatPumpSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Heat Pump Sensor."""
    
    def __init__(self, coordinator, name, unit, icon, data_key):
        super().__init__(coordinator)
        self._name = f"Heat Pump {name}"
        self._unit = unit
        self._icon = icon
        self._data_key = data_key

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._data_key)
        
    @property
    def icon(self):
        """Icon to use in the frontend."""
        return self._icon
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.coordinator.name}_{self._data_key}"
        
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

class HeatPumpTextSensor(CoordinatorEntity, TextSensorEntity):
    """Representation of a Heat Pump Text Sensor."""
    
    def __init__(self, coordinator, name, icon, data_key):
        super().__init__(coordinator)
        self._name = f"Heat Pump {name}"
        self._icon = icon
        self._data_key = data_key
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._data_key)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return self._icon
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.coordinator.name}_{self._data_key}"
