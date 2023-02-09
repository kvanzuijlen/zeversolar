import dataclasses
import typing
import asyncio
import urllib.parse
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from dataclasses import MISSING

import aiohttp

from zeversolar.exceptions import ZeverSolarTimeout, ZeverSolarHTTPError, ZeverSolarHTTPNotFound, ZeverSolarInvalidData

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
    communication_status: bool
    num_inverters: int
    serial_number: str
    pac: Watt
    energy_today: kWh
    status: StatusEnum


async def async_zeversolar_parse(zeversolar_response: str) -> ZeverSolarData:
    response_parts = zeversolar_response.split()

    if len(response_parts) <= Values.NUM_INVERTERS:
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
    except ValueError:
        raise ZeverSolarInvalidData()

    communication_status = response_parts[Values.COMMUNICATION_STATUS]
    if communication_status.startswith(StatusEnum.OK.value):
        communication_status = True
    elif communication_status.startswith(StatusEnum.ERROR.value):
        communication_status = False
    else:
        communication_status = communication_status == "0"

    try:
        num_inverters = int(response_parts[Values.NUM_INVERTERS])
    except ValueError:
        raise ZeverSolarInvalidData()

    # inverters = {}  # {serial_number: pac,energy_today,status}
    # for i in range(min(num_inverters, 5)):
    # Just parsing one inverter for now though
    if num_inverters < 1:
        raise ZeverSolarInvalidData()

    if len(response_parts) < Values.INVERTERS + num_inverters*4 + 1:
        raise ZeverSolarInvalidData()

    index = Values.INVERTERS

    serial_number = response_parts[index]
    index += 1

    try:
        pac = Watt(int(response_parts[index]))
    except ValueError:
        # ? = response_parts[index]
        index += 1
        try:
            pac = Watt(int(response_parts[index]))
        except ValueError:
            raise ZeverSolarInvalidData()
    index += 1

    try:
        energy_today = kWh(await _async_fix_leading_zero(response_parts[index]))
    except ValueError:
        raise ZeverSolarInvalidData()
    index += 1

    try:
        status = StatusEnum(response_parts[index])
    except ValueError:
        raise ZeverSolarInvalidData()
    index += 1

    # We don't necessarily know how many fields in each inverter if more than one
    # try:
    #     meter_status = StatusEnum(response_parts[index])
    # except ValueError:
    #     raise ZeverSolarInvalidData()
    # index += 1
    # if len(response_parts) < index + 4:
    #     raise ZeverSolarInvalidData()

    return ZeverSolarData(
        wifi_enabled=wifi_enabled,
        serial_or_registry_id=serial_or_registry_id,
        registry_key=registry_key,
        hardware_version=hardware_version,
        software_version=software_version,
        communication_status=communication_status,
        num_inverters=num_inverters,
        serial_number=serial_number,
        pac=pac,
        energy_today=energy_today,
        status=status,
        reported_datetime=reported_datetime,
    )


async def _async_fix_leading_zero(string_value: str) -> float:
    split_values = string_value.split(".")
    if len(decimals := split_values[1]) == 1:
        string_value = f"{split_values[0]}.0{decimals}"
    return float(string_value)


class ZeverSolarClient:
    def __init__(self, host: str) -> None:
        if "http" not in host:
            # noinspection HttpUrlsUsage
            host = f"http://{host}"
        self.host = urllib.parse.urlparse(url=host).netloc.strip("/")
        self._timeout = aiohttp.ClientTimeout(total=10)
        self._retries = 3
        self._serial_number = MISSING

    async def async_get_data(self) -> ZeverSolarData:
        exception = None
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            for i in range(self._retries):
                try:
                    async with session.get(f"http://{self.host}/home.cgi") as resp:
                        if resp.status != 200:
                            if resp.status == 404:
                                raise ZeverSolarHTTPNotFound()
                            raise ZeverSolarHTTPError()
                        text = await resp.text()
                        try:
                            data = await async_zeversolar_parse(zeversolar_response=text)
                        except ZeverSolarInvalidData as err:
                            exception = err
                            if i < self._retries-1:
                                await asyncio.sleep(self._timeout.total)
                            continue
                        return data
                except asyncio.TimeoutError:
                    exception = ZeverSolarTimeout()
                    continue
        raise exception

    async def async_power_on(self) -> None:
        return await self.async_ctrl_power(mode=PowerMode.ON)

    async def async_power_off(self) -> None:
        return await self.async_ctrl_power(mode=PowerMode.OFF)

    async def async_ctrl_power(self, mode: PowerMode) -> None:
        if self._serial_number is MISSING:
            data = await self.async_get_data()
            self._serial_number = data.serial_number

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            try:
                async with session.post(
                        url=f"http://{self.host}/inv_ctrl.cgi",
                        data={"sn": self._serial_number, "mode": mode.value},
                    ) as resp:
                    if resp.status != 200:
                        if resp.status == 404:
                            raise ZeverSolarHTTPNotFound()
                        raise ZeverSolarHTTPError()
            except asyncio.TimeoutError:
                raise ZeverSolarTimeout()
