""" Basic Sunpower PVS Tool """

import logging
import time

import requests
import simplejson

_LOGGER = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]  # Seconds between retries


class ConnectionException(Exception):
    """Any failure to connect to sunpower PVS"""


class ParseException(Exception):
    """Any failure to parse JSON response from PVS"""


class SunPowerMonitor:
    """Basic Class to talk to sunpower pvs 5/6 via the management interface 'API'.
    This is not a public API so it might fail at any time.
    if you find this useful please complain to sunpower and your sunpower dealer that they
    do not have a public API"""

    def __init__(self, host):
        """Initialize."""
        self.host = host
        self.command_url = "http://{0}/cgi-bin/dl_cgi?Command=".format(host)

    def _request_with_retry(self, url, timeout=120):
        """Make a request with retry logic for transient failures."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, timeout=timeout)
                return response.json()
            except requests.exceptions.ConnectionError as error:
                last_error = error
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    _LOGGER.warning(
                        "PVS connection failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, MAX_RETRIES, delay, error
                    )
                    time.sleep(delay)
                else:
                    _LOGGER.error("PVS connection failed after %d attempts: %s", MAX_RETRIES, error)
            except requests.exceptions.Timeout as error:
                # Don't retry timeouts - they already waited long enough
                _LOGGER.error("PVS request timed out after %ds: %s", timeout, error)
                raise ConnectionException(f"PVS request timed out after {timeout}s") from error
            except requests.exceptions.RequestException as error:
                last_error = error
                _LOGGER.error("PVS request failed: %s", error)
                break
            except simplejson.errors.JSONDecodeError as error:
                _LOGGER.error("PVS returned invalid JSON: %s", error)
                raise ParseException(f"Invalid JSON response from PVS: {error}") from error

        raise ConnectionException(f"Failed to connect to PVS after {MAX_RETRIES} attempts: {last_error}") from last_error

    def generic_command(self, command):
        """All 'commands' to the PVS module use this url pattern and return json
        The PVS system can take a very long time to respond so timeout is at 2 minutes"""
        return self._request_with_retry(self.command_url + command, timeout=120)

    def device_list(self):
        """Get a list of all devices connected to the PVS"""
        return self.generic_command("DeviceList")

    def energy_storage_system_status(self):
        """Get the status of the energy storage system"""
        url = "http://{0}/cgi-bin/dl_cgi/energy-storage-system/status".format(self.host)
        return self._request_with_retry(url, timeout=120)

    def network_status(self):
        """Get a list of network interfaces on the PVS"""
        return self.generic_command("Get_Comm")
