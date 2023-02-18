import pytest
import requests
import typing
from unittest.mock import call, Mock

from pytest_mock import MockFixture

from zeversolar import PowerMode
from zeversolar.exceptions import ZeverSolarError, ZeverSolarTimeout, ZeverSolarHTTPNotFound, ZeverSolarHTTPError


@pytest.mark.parametrize(
    argnames=("power_mode", "power_mode_value"),
    argvalues=((PowerMode.ON, 0), (PowerMode.OFF, 1)),
)
def test_ctrl_power(mocker: MockFixture, instance: Mock, power_mode: PowerMode, power_mode_value: int):
    patched_post = mocker.patch("zeversolar.requests.post")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(**{
        "instance": instance,
    })

    result = ZeverSolarClient.ctrl_power(self=fake.instance, mode=power_mode)

    fake.instance.get_data.assert_called_once()
    assert fake.instance._serial_number is fake.instance.get_data.return_value.serial_number
    patched_post.assert_has_calls(calls=[
        call(
            url=f"http://{fake.instance.host}/inv_ctrl.cgi",
            data={
                'sn': fake.instance._serial_number,
                'mode': power_mode_value,
            },
            timeout=fake.instance._timeout,
        ),
    ])
    assert result is power_mode


@pytest.mark.parametrize(
    argnames="requests_side_effect,response_status,expected_exception",
    argvalues=(
        (
            Exception,
            None,
            ZeverSolarError,
        ),
        (
            requests.exceptions.Timeout,
            None,
            ZeverSolarTimeout,
        ),
        (
            requests.exceptions.HTTPError,
            404,
            ZeverSolarHTTPNotFound,
        ),
        (
            requests.exceptions.HTTPError,
            500,
            ZeverSolarHTTPError,
        ),
    ))
def test_ctrl_power_exception(
        mocker: MockFixture,
        requests_side_effect: requests.exceptions.RequestException,
        response_status: typing.Optional[int],
        expected_exception: type[Exception],
        instance: Mock,
):
    patched_post = mocker.patch("zeversolar.requests.post")
    if response_status is None:
        patched_post.side_effect = [requests_side_effect]
    else:
        patched_post.return_value.raise_for_status.side_effect = [requests_side_effect]
        patched_post.return_value.status_code = response_status

    from zeversolar import ZeverSolarClient, PowerMode
    fake = mocker.Mock(**{
        "instance": instance,
        "power_mode": mocker.Mock(spec=PowerMode).ON,
    })

    with pytest.raises(expected_exception=expected_exception):
        ZeverSolarClient.ctrl_power(self=fake.instance, mode=fake.power_mode)

    fake.instance.get_data.assert_called_once()
    assert fake.instance._serial_number is fake.instance.get_data.return_value.serial_number
    patched_post.assert_has_calls(calls=[
        call.post(
            url=f"http://{fake.instance.host}/inv_ctrl.cgi",
            data={
                'sn': fake.instance._serial_number,
                'mode': fake.power_mode.value,
            },
            timeout=fake.instance._timeout,
        ),
    ])
