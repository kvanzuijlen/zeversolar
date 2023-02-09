import dataclasses
import typing
import urllib.parse
from datetime import datetime, timedelta
from enum import Enum, IntEnum

import retry
import requests

from zeversolar.exceptions import ZeverSolarTimeout, ZeverSolarHTTPError, ZeverSolarHTTPNotFound, ZeverSolarInvalidData, \
    ZeverSolarError

kWh = typing.NewType("kWh", float)
Watt = typing.NewType("Watt", int)


class PowerMode(IntEnum):
    ON = 0
    OFF = 1


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

    @retry.retry(exceptions=(ZeverSolarTimeout, ZeverSolarInvalidData), tries=3)
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

        return ZeverSolarParser(zeversolar_response=response.text).parse()

    def power_on(self) -> PowerMode:
        return self.ctrl_power(mode=PowerMode.ON)

    def power_off(self) -> PowerMode:
        return self.ctrl_power(mode=PowerMode.OFF)

    @retry.retry(exceptions=ZeverSolarTimeout, tries=3)
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
