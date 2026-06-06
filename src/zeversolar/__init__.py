import dataclasses
import threading
import time
import typing
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum, IntEnum

import retry
import requests

from zeversolar.exceptions import (
    ZeverSolarError,
    ZeverSolarHTTPError,
    ZeverSolarHTTPNotFound,
    ZeverSolarInvalidData,
    ZeverSolarPowerLimitNotSupported,
    ZeverSolarTimeout,
)

kWh = typing.NewType("kWh", float)  # pragma: no mutate
Watt = typing.NewType("Watt", int)  # pragma: no mutate

MINIMUM_LIMIT: int = 5    # % — inverter won't accept lower
RAMP_STEP: int = 10       # % per ramp step
RAMP_RATE_UP: int = 10    # seconds between steps when increasing output
RAMP_RATE_DOWN: int = 20  # seconds between steps when decreasing output


class PowerMode(IntEnum):
    ON = 0
    OFF = 1


class PowerLimitMode(IntEnum):
    PERCENTAGE = 1  # % of inverter AC capacity
    WATT = 2        # W based on energy meter
    DRM7 = 3        # AS DRM7 Q command
    DRM_LOAD = 4    # AS DRMs Safety load speed


class Values(IntEnum):
    WIFI_ENABLED = 0           # bool (0|1)
    # ? = 1                    # int
    SERIAL_OR_REGISTRY_ID = 2  # string
    REGISTRY_KEY = 3           # string
    HARDWARE_VERSION = 4       # string
    SOFTWARE_VERSION = 5       # string
    REPORTED_TIME = 6          # HH:MM
    REPORTED_DATE = 7          # DD/MM/YYYY
    COMMUNICATION_STATUS = 8   # int|OK|error
    NUM_INVERTERS = 9          # int (0-4)
    INVERTERS = 10             # start of inverter data


class StatusEnum(Enum):
    OK = "OK"
    ERROR = "ERROR"


@dataclasses.dataclass
class ZeverSolarData:
    wifi_enabled: bool
    serial_or_registry_id: str
    registry_key: str
    hardware_version: str
    software_version: str
    reported_datetime: datetime
    communication_status: StatusEnum
    num_inverters: int
    serial_number: str
    pac: Watt
    energy_today: kWh
    status: StatusEnum
    meter_status: StatusEnum


@dataclasses.dataclass
class ZeverSolarPowerLimitData:
    mode: PowerLimitMode
    limit_pct: int


class ZeverSolarParser:
    def __init__(self, zeversolar_response: str):
        self.zeversolar_response = zeversolar_response

    def parse(self) -> ZeverSolarData:
        response_parts = self.zeversolar_response.split()

        if len(response_parts) <= Values.NUM_INVERTERS.value:
            raise ZeverSolarInvalidData()

        wifi_enabled = response_parts[Values.WIFI_ENABLED] == "1"
        serial_or_registry_id = response_parts[Values.SERIAL_OR_REGISTRY_ID]
        registry_key = response_parts[Values.REGISTRY_KEY]
        hardware_version = response_parts[Values.HARDWARE_VERSION]
        software_version = response_parts[Values.SOFTWARE_VERSION]

        reported_time = response_parts[Values.REPORTED_TIME]
        reported_date = response_parts[Values.REPORTED_DATE]
        try:
            reported_datetime = datetime.strptime(f"{reported_date} {reported_time}", "%d/%m/%Y %H:%M")
        except ValueError as exception:
            raise ZeverSolarInvalidData() from exception

        communication_status_value = response_parts[Values.COMMUNICATION_STATUS]
        try:
            communication_status = StatusEnum(communication_status_value.upper())
        except ValueError as exception:
            if not communication_status_value.isnumeric():
                raise ZeverSolarInvalidData from exception
            communication_status = StatusEnum.OK if communication_status_value == "0" else StatusEnum.ERROR

        try:
            num_inverters = int(response_parts[Values.NUM_INVERTERS])
        except ValueError as exception:
            raise ZeverSolarInvalidData() from exception

        if num_inverters < 1:
            raise ZeverSolarInvalidData()

        index = Values.INVERTERS.value

        serial_number = response_parts[index]
        index += 1

        try:
            pac = Watt(int(response_parts[index]))
        except ValueError:
            # ? = response_parts[index]
            index += 1
            try:
                pac = Watt(int(response_parts[index]))
            except ValueError as exception:
                raise ZeverSolarInvalidData() from exception
        index += 1

        try:
            energy_today = kWh(self._fix_leading_zero(response_parts[index]))
        except ValueError as exception:
            raise ZeverSolarInvalidData() from exception
        index += 1

        try:
            status = StatusEnum(response_parts[index].upper())
        except ValueError as exception:
            raise ZeverSolarInvalidData() from exception
        index += 1

        try:
            meter_status = StatusEnum(response_parts[index].upper())
        except ValueError as exception:
            raise ZeverSolarInvalidData() from exception

        return ZeverSolarData(
            wifi_enabled=wifi_enabled,
            serial_or_registry_id=serial_or_registry_id,
            registry_key=registry_key,
            hardware_version=hardware_version,
            software_version=software_version,
            reported_datetime=reported_datetime,
            communication_status=communication_status,
            num_inverters=num_inverters,
            serial_number=serial_number,
            pac=pac,
            energy_today=energy_today,
            status=status,
            meter_status=meter_status,
        )

    @staticmethod
    def _fix_leading_zero(string_value: str) -> float:
        split_values = string_value.split(".")
        if len(decimals := split_values[1]) == 1:
            string_value = f"{split_values[0]}.0{decimals}"
        return float(string_value)


class ZeverSolarClient:
    def __init__(self, host: str):
        if "http" not in host:
            # noinspection HttpUrlsUsage
            host = f"http://{host}"
        self.host = urllib.parse.urlparse(url=host).netloc.strip("/")
        self._timeout = timedelta(seconds=10).total_seconds()
        self._serial_number: typing.Optional[str] = None
        self._hardware_version: typing.Optional[str] = None
        self._ramp_stop: threading.Event = threading.Event()
        self._ramp_lock: threading.Lock = threading.Lock()

    @retry.retry(exceptions=(ZeverSolarTimeout, ZeverSolarInvalidData), tries=3)  # pragma: no mutate
    def get_data(self) -> ZeverSolarData:
        try:
            response = requests.get(url=f"http://{self.host}/home.cgi", timeout=self._timeout)
        except requests.exceptions.Timeout as exception:
            raise ZeverSolarTimeout() from exception
        except Exception as exception:
            raise ZeverSolarError() from exception

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exception:
            if response.status_code == 404:
                raise ZeverSolarHTTPNotFound() from exception
            raise ZeverSolarHTTPError() from exception

        data = ZeverSolarParser(zeversolar_response=response.text).parse()
        self._hardware_version = data.hardware_version
        return data

    def get_power_limit(self) -> ZeverSolarPowerLimitData:
        """Read current power limit from adv.cgi. Works on M10 and M11."""
        try:
            response = requests.get(url=f"http://{self.host}/adv.cgi", timeout=self._timeout)
        except requests.exceptions.Timeout as exception:
            raise ZeverSolarTimeout() from exception
        except Exception as exception:
            raise ZeverSolarError() from exception

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exception:
            if response.status_code == 404:
                raise ZeverSolarPowerLimitNotSupported() from exception
            raise ZeverSolarHTTPError() from exception

        # adv.cgi returns one field per line (0-indexed):
        #   line 11 = ac_value1 — current power limit %
        #   line 12 = ac_value2
        #   line 13 = ac_value3
        #   line 14 = ac_mode   — active limit mode
        lines = response.text.splitlines()
        if len(lines) < 15:
            raise ZeverSolarInvalidData()

        try:
            limit_pct = int(float(lines[11].strip()))
            mode = PowerLimitMode(int(lines[14].strip()))
        except (ValueError, KeyError) as exception:
            raise ZeverSolarInvalidData() from exception

        return ZeverSolarPowerLimitData(mode=mode, limit_pct=limit_pct)

    def set_power_limit(
        self,
        limit_pct: int,
        ramp_rate: int | None = None,
        on_step: Callable[[int], None] | None = None,
    ) -> None:
        """Start ramping output to target percentage. Returns immediately.

        Cancels any ramp already in progress and starts a fresh daemon thread.
        The ramp runs in the background; on_step is called from that thread
        after each write (must be thread-safe in HA context).

        ramp_rate controls step size in %:
          - None (default): RAMP_STEP (10%) steps
          - 100: single write, jumps directly to target
          - 5: finer 5% steps for a more gradual transition

        Sleep between steps is fixed by direction: RAMP_RATE_UP when
        increasing, RAMP_RATE_DOWN when decreasing.
        """
        # Lock ensures stop+create+start is atomic — prevents two concurrent
        # calls from each reading the same _ramp_stop before it is replaced.
        with self._ramp_lock:
            self._ramp_stop.set()
            self._ramp_stop = threading.Event()

            thread = threading.Thread(
                target=self._do_ramp,
                args=(limit_pct, ramp_rate, on_step, self._ramp_stop),
                daemon=True,
            )
            thread.start()

    def _do_ramp(
        self,
        limit_pct: int,
        ramp_rate: int | None,
        on_step: Callable[[int], None] | None,
        stop: threading.Event,
    ) -> None:
        """Ramp loop running in a daemon thread. Blocking writes are intentional."""
        limit_pct = max(MINIMUM_LIMIT, min(100, limit_pct))

        current = self.get_power_limit().limit_pct
        if current == limit_pct:
            return

        ramping_down = limit_pct < current
        step_size = ramp_rate if ramp_rate is not None else RAMP_STEP
        sleep_interval = RAMP_RATE_DOWN if ramping_down else RAMP_RATE_UP
        direction = -step_size if ramping_down else step_size

        next_val = current
        while next_val != limit_pct and not stop.is_set():
            next_val += direction
            if (direction < 0 and next_val < limit_pct) or (direction > 0 and next_val > limit_pct):
                next_val = limit_pct
            next_val = max(MINIMUM_LIMIT, min(100, next_val))

            self._write_power_limit(next_val)

            if on_step is not None:
                on_step(next_val)

            if next_val != limit_pct:
                # Use Event.wait() so the sleep is interruptible when stop is set.
                stop.wait(timeout=sleep_interval)

    def _write_power_limit(self, limit_pct: int) -> None:
        """POST a single power limit step to the inverter.

        M11 uses pwrlim.cgi; M10 uses adv.cgi. Hardware version is populated
        after the first get_data() call.
        """
        endpoint = "adv.cgi" if self._is_m10() else "pwrlim.cgi"
        data = {
            "enlim": "on",
            "ac_sys": "0",
            "ac_mode": "1",
            "ac_value1": str(limit_pct),
            "ac_value2": "0",
            "em_ml": "0",
            "ac_value3": "60",
            "drm_sp": "16.67",
        }
        try:
            response = requests.post(
                url=f"http://{self.host}/{endpoint}",
                data=data,
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectionError:
            # Inverter closes the TCP connection after processing the POST
            # without sending an HTTP response — treat as success.
            return
        except requests.exceptions.Timeout as exception:
            raise ZeverSolarTimeout() from exception
        except Exception as exception:
            raise ZeverSolarError() from exception

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exception:
            if response.status_code == 404:
                raise ZeverSolarHTTPNotFound() from exception
            raise ZeverSolarHTTPError() from exception

    def _is_m10(self) -> bool:
        if self._hardware_version is None:
            self.get_data()
        return self._hardware_version is not None and self._hardware_version.startswith("M10")

    def power_on(self) -> PowerMode | None:
        """Restore full output.

        M10: hard on via inv_ctrl.cgi (existing behaviour).
        M11: ramp to 100% via pwrlim.cgi.
        Returns PowerMode.ON on M10, None on M11.
        """
        if self._is_m10():
            return self.ctrl_power(mode=PowerMode.ON)
        self.set_power_limit(100)
        return None

    def power_off(self) -> PowerMode | None:
        """Reduce output to minimum.

        M10: hard off via inv_ctrl.cgi (existing behaviour).
        M11: ramp to MINIMUM_LIMIT% via pwrlim.cgi.
        Returns PowerMode.OFF on M10, None on M11.
        """
        if self._is_m10():
            return self.ctrl_power(mode=PowerMode.OFF)
        self.set_power_limit(MINIMUM_LIMIT)
        return None

    @retry.retry(exceptions=ZeverSolarTimeout, tries=3)  # pragma: no mutate
    def ctrl_power(self, mode: PowerMode) -> PowerMode:
        if self._serial_number is None:
            self._serial_number = self.get_data().serial_number

        try:
            response = requests.post(
                url=f"http://{self.host}/inv_ctrl.cgi",
                data={'sn': self._serial_number, 'mode': mode.value},
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exception:
            raise ZeverSolarTimeout() from exception
        except Exception as exception:
            raise ZeverSolarError() from exception

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exception:
            if response.status_code == 404:
                raise ZeverSolarHTTPNotFound() from exception
            raise ZeverSolarHTTPError() from exception

        return mode
