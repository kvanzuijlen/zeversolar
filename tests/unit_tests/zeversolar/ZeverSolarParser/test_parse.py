from datetime import datetime

import dataclasses

import pytest
from pytest_mock import MockFixture

from zeversolar.exceptions import ZeverSolarInvalidData


@dataclasses.dataclass
class ZeverSolarTestData:
    wifi_enabled: bool
    serial_or_registry_id: str
    registry_key: str
    hardware_version: str
    software_version: str
    reported_datetime: datetime
    communication_status: str
    num_inverters: int
    serial_number: str
    pac: int
    energy_today: float
    status: str
    meter_status: str


@pytest.mark.parametrize(argnames=["zeversolar_response", "expected_result"], argvalues=(
    (
        "1 1 EAB961888888 ABWDWHTQXXXXXXXX M10 16415-562R+16413-561R 15:57 02/02/2023 Error 1 BS15006011999999 V610-01037-04 30 0.0 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EAB961888888",
            registry_key="ABWDWHTQXXXXXXXX",
            hardware_version="M10",
            software_version="16415-562R+16413-561R",
            reported_datetime=datetime(year=2023, month=2, day=2, hour=15, minute=57),
            communication_status="ERROR",
            num_inverters=1,
            serial_number="BS15006011999999",
            pac=30,
            energy_today=0.0,
            status="OK",
            meter_status="ERROR",
        ),
    ),
    (
        "1 0 EAB971444444 GHKXWHTQXXXXXXXX M11 19703-826R+17511-707R 15:53 06/03/2022 0 1 EL36806011555555 3187 14.48 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EAB971444444",
            registry_key="GHKXWHTQXXXXXXXX",
            hardware_version="M11",
            software_version="19703-826R+17511-707R",
            reported_datetime=datetime(year=2022, month=3, day=6, hour=15, minute=53),
            communication_status="OK",
            num_inverters=1,
            serial_number="EL36806011555555",
            pac=3187,
            energy_today=14.48,
            status="OK",
            meter_status="ERROR",
        ),
    ),
    (
        "1 1 EAB241666666 ZYXTBGERXXXXXXXX M10 18625-797R+17829-719R 16:22 20/02/2022 1 1 ZS15004513777777 1234 8.9 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EAB241666666",
            registry_key="ZYXTBGERXXXXXXXX",
            hardware_version="M10",
            software_version="18625-797R+17829-719R",
            reported_datetime=datetime(year=2022, month=2, day=20, hour=16, minute=22),
            communication_status="ERROR",
            num_inverters=1,
            serial_number="ZS15004513777777",
            pac=1234,
            energy_today=8.09,
            status="OK",
            meter_status="ERROR",
        ),
    ),
    (
        "1 1 EAB961777777 WSMQKHTQXXXXXXXX M10 17717-709R+17511-707R 13:59 04/02/2023 0 1 BS20006011888888 226 0.89 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EAB961777777",
            registry_key="WSMQKHTQXXXXXXXX",
            hardware_version="M10",
            software_version="17717-709R+17511-707R",
            reported_datetime=datetime(year=2023, month=2, day=4, hour=13, minute=59),
            communication_status="OK",
            num_inverters=1,
            serial_number="BS20006011888888",
            pac=226,
            energy_today=0.89,
            status="OK",
            meter_status="ERROR",
        ),
    ),
    (
        "1 1 EAB961555555 KS4GLDHNXXXXXXXX M11 16B21-663R+16B21-658R 16:47 03/02/2023 Error 1 SX0004016666666 2425 19.70 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EAB961555555",
            registry_key="KS4GLDHNXXXXXXXX",
            hardware_version="M11",
            software_version="16B21-663R+16B21-658R",
            reported_datetime=datetime(year=2023, month=2, day=3, hour=16, minute=47),
            communication_status="ERROR",
            num_inverters=1,
            serial_number="SX0004016666666",
            pac=2425,
            energy_today=19.7,
            status="OK",
            meter_status="ERROR",
        ),
    ),
    (
        "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error 1 BS0004016666666 40 3.85 OK Error",
        ZeverSolarTestData(
            wifi_enabled=True,
            serial_or_registry_id="EA3061888888",
            registry_key="FGSJDHNXXXXXXXX",
            hardware_version="M10",
            software_version="16B21-663R+16B21-658R",
            reported_datetime=datetime(year=2023, month=2, day=6, hour=16, minute=59),
            communication_status="ERROR",
            num_inverters=1,
            serial_number="BS0004016666666",
            pac=40,
            energy_today=3.85,
            status="OK",
            meter_status="ERROR",
        ),
    ),
))
def test_parse(
        mocker: MockFixture,
        zeversolar_response: str,
        expected_result: ZeverSolarTestData,
):
    from zeversolar import ZeverSolarParser, ZeverSolarData, StatusEnum
    mock_self = mocker.Mock(spec=ZeverSolarParser, **{
        "zeversolar_response": zeversolar_response,
    })

    result = ZeverSolarParser.parse(self=mock_self)
    assert isinstance(result, ZeverSolarData)
    assert result.wifi_enabled == expected_result.wifi_enabled
    assert result.serial_or_registry_id == expected_result.serial_or_registry_id
    assert result.registry_key == expected_result.registry_key
    assert result.hardware_version == expected_result.hardware_version
    assert result.software_version == expected_result.software_version
    assert result.reported_datetime == expected_result.reported_datetime
    assert result.communication_status is StatusEnum(expected_result.communication_status)
    assert result.num_inverters == expected_result.num_inverters
    assert result.serial_number == expected_result.serial_number
    assert result.pac == expected_result.pac
    assert result.energy_today == mock_self._fix_leading_zero.return_value
    assert result.status is StatusEnum(expected_result.status)


@pytest.mark.parametrize(
    argnames=["zeversolar_response", "expected_exception", "fix_leading_zero_side_effect", "invalid_date", "strptime_called"],
    argvalues=(
        (
            "1 1 EAB961555555 KS4GLDHNXXXXXXXX M11 16B21-663R+16B21-658R 16:41 03/02/2023 Error 0 Error",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
        (
            "1 0 000000000000 +16B21-658R 15:27 06/02/2023 Error 0 Error",
            ZeverSolarInvalidData,
            None,
            False,
            False,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 invalid Error 1 BS0004016666666 40 3.85 OK Error",
            ZeverSolarInvalidData,
            None,
            True,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Unknown 1 BS0004016666666 40 3.85 OK Error",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error One BS0004016666666 40 3.85 OK Error",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error 1 BS0004016666666 40.5 3.85 OK Error",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error 1 BS0004016666666 40 Unknown OK Error",
            ZeverSolarInvalidData,
            ValueError,
            False,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error 1 BS0004016666666 40 3.85 Unknown Error",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
        (
            "1 1 EA3061888888 FGSJDHNXXXXXXXX M10 16B21-663R+16B21-658R 16:59 06/02/2023 Error 1 BS0004016666666 40 3.85 OK Unknown",
            ZeverSolarInvalidData,
            None,
            False,
            True,
        ),
    )
)
def test_parse_invalid_response(
        mocker: MockFixture,
        zeversolar_response: str,
        expected_exception: type[Exception],
        fix_leading_zero_side_effect: type[Exception],
        invalid_date: bool,
        strptime_called: bool,
):
    mock_datetime = mocker.patch("zeversolar.datetime")
    if invalid_date:
        mock_datetime.strptime.side_effect = [ValueError]

    from zeversolar import ZeverSolarParser
    mock_self = mocker.Mock(spec=ZeverSolarParser, **{
        "zeversolar_response": zeversolar_response,
    })
    if fix_leading_zero_side_effect:
        mock_self._fix_leading_zero.side_effect = [fix_leading_zero_side_effect]

    with pytest.raises(expected_exception=expected_exception):
        ZeverSolarParser.parse(self=mock_self)

    if strptime_called:
        mock_datetime.strptime.assert_called_once()
    else:
        mock_datetime.strptime.assert_not_called()
