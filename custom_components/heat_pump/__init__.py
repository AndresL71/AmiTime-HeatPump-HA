"""The Heat Pump integration."""

import logging
import asyncio
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "heat_pump"

class HeatPumpCommunicator:
    """Class to communicate with the heat pump via a serial server."""
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._reader = None
        self._writer = None

    async def _connect(self):
        """Establish a TCP connection to the serial server."""
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
            _LOGGER.info("Connected to serial server at %s:%s", self._host, self._port)
        except (ConnectionRefusedError, OSError) as e:
            _LOGGER.error("Failed to connect to serial server: %s", e)
            self._reader = None
            self._writer = None
            raise UpdateFailed(f"Connection failed: {e}")

    async def _close(self):
        """Close the TCP connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            _LOGGER.info("Connection to serial server closed.")

    async def get_data(self):
        """Send a request and decode the response from the heat pump."""
        await self._connect()
        if not self._reader or not self._writer:
            raise UpdateFailed("Connection not established.")

        try:
            # Assuming a simple command to request data. You may need to adjust this.
            # Example request: a simple byte array.
            request_packet = bytes([0xAA, 0x55, 0x01, 0x00, 0x00])
            _LOGGER.debug("Sending request packet: %s", request_packet.hex())
            self._writer.write(request_packet)
            await self._writer.drain()

            # Read the response. Let's assume a fixed packet size for now based on previous discussions.
            response_packet = await asyncio.wait_for(self._reader.read(300), timeout=5.0)
            
            if not response_packet:
                raise UpdateFailed("No data received from the serial server.")

            _LOGGER.debug("Received response packet of size %d", len(response_packet))
            return self._decode_packet(response_packet)

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for response from serial server.")
            raise UpdateFailed("Timeout waiting for response.")
        except Exception as e:
            _LOGGER.error("Error during communication: %s", e)
            raise UpdateFailed(f"Communication error: {e}")
        finally:
            await self._close()

    def _get_bits(self, packet, start_bit, num_bits):
        """Reads a specified number of bits from a byte string."""
        if (start_bit + num_bits) > len(packet) * 8:
            _LOGGER.error("Attempted to read beyond packet boundary.")
            return 0
        
        result = 0
        for i in range(num_bits):
            bit_index = start_bit + i
            byte_index = bit_index // 8
            bit_in_byte = 7 - (bit_index % 8)
            
            if (packet[byte_index] >> bit_in_byte) & 0x01:
                result |= (1 << (num_bits - 1 - i))
        return result

    def _decode_packet(self, packet):
        """Decodes the binary packet using the provided bit-level map."""
        data = {}
        
        # Mapping from the provided list
        # Tuo (51-58)
        data["tuo"] = self._get_bits(packet, 51, 8) / 10.0
        # Tui (59-66)
        data["tui"] = self._get_bits(packet, 59, 8) / 10.0
        # Tup (67-74)
        data["tup"] = self._get_bits(packet, 67, 8) / 10.0
        # Tw (75-82)
        data["tw"] = self._get_bits(packet, 75, 8) / 10.0
        # Tc (83-90)
        data["tc"] = self._get_bits(packet, 83, 8) / 10.0
        # Tv1 (91-98)
        data["tv1"] = self._get_bits(packet, 91, 8) / 10.0
        # Tv2 (99-106)
        data["tv2"] = self._get_bits(packet, 99, 8) / 10.0
        # Tr (107-114)
        data["tr"] = self._get_bits(packet, 107, 8) / 10.0
        # PWM (131-138)
        data["pwm"] = self._get_bits(packet, 131, 8) / 10.0
        # Frequency (203-210)
        data["frequency"] = self._get_bits(packet, 203, 8) / 10.0
        # Pd (219-226)
        data["pd"] = self._get_bits(packet, 219, 8) / 10.0
        # Ps (227-234)
        data["ps"] = self._get_bits(packet, 227, 8) / 10.0
        # Ta (235-242)
        data["ta"] = self._get_bits(packet, 235, 8) / 10.0
        # Td (243-250)
        data["td"] = self._get_bits(packet, 243, 8) / 10.0
        # Ts (251-258)
        data["ts"] = self._get_bits(packet, 251, 8) / 10.0
        # Tp (259-266)
        data["tp"] = self._get_bits(packet, 259, 8) / 10.0
        # Fan (267-274)
        data["fan"] = self._get_bits(packet, 267, 8) / 10.0
        # Current (283-290)
        data["current"] = self._get_bits(packet, 283, 8) / 10.0
        # Voltage (291-298)
        data["voltage"] = self._get_bits(packet, 291, 8) / 10.0
        # P0 (307-314)
        data["p0"] = self._get_bits(packet, 307, 8) / 10.0
        # P1 (315-322)
        data["p1"] = self._get_bits(packet, 315, 8) / 10.0
        # P2 (323-330)
        data["p2"] = self._get_bits(packet, 323, 8) / 10.0

        # Function (43-50)
        func_val = self._get_bits(packet, 43, 8)
        data["function"] = "Heating" if func_val == 1 else "Cooling" if func_val == 0 else "Unknown"

        # Thermostat (187-194)
        thermo_val = self._get_bits(packet, 187, 8)
        data["thermostat"] = "ON" if thermo_val == 1 else "OFF" if thermo_val == 0 else "Unknown"

        # Valve op (211-218)
        valve_val = self._get_bits(packet, 211, 8)
        data["valve_op"] = "Open" if valve_val == 1 else "Closed" if valve_val == 0 else "Unknown"
        
        return data


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the heat pump component."""
    _LOGGER.info("Setting up heat pump integration.")

    # You will need to configure the host and port in your configuration.yaml
    host = "your_serial_server_ip"
    port = 8888  # Replace with the port of your serial server

    communicator = HeatPumpCommunicator(host, port)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=communicator.get_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise UpdateFailed("Failed to fetch initial data.")

    hass.data[DOMAIN] = coordinator

    hass.async_create_task(
        hass.helpers.discovery.async_load_platform("sensor", DOMAIN, {}, config)
    )

    return True
