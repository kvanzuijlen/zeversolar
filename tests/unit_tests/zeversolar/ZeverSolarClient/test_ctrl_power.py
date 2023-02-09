import pytest
import requests
import typing
from unittest.mock import call, Mock

from pytest_mock import MockFixture

from zeversolar.exceptions import ZeverSolarError, ZeverSolarTimeout, ZeverSolarHTTPNotFound, ZeverSolarHTTPError


def test_ctrl_power(mocker: MockFixture, mock_self: Mock):
    patched_post = mocker.patch("zeversolar.requests.post")
    from zeversolar import ZeverSolarClient, PowerMode
    mock_power_mode = mocker.Mock(spec=PowerMode).ON

    result = ZeverSolarClient.ctrl_power(self=mock_self, mode=mock_power_mode)

    mock_self.get_data.assert_called_once()
    assert mock_self._serial_number is mock_self.get_data.return_value.serial_number
    patched_post.assert_has_calls(calls=[
        call(
            url=f"http://{mock_self.host}/inv_ctrl.cgi",
            data={
                'sn': mock_self._serial_number,
                'mode': mock_power_mode.value,
            },
            timeout=mock_self._timeout,
        ),
    ])
    assert result is mock_power_mode


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
        mock_self: Mock,
):
    patched_post = mocker.patch("zeversolar.requests.post")
    if response_status is None:
        patched_post.side_effect = [requests_side_effect]
    else:
        patched_post.return_value.raise_for_status.side_effect = [requests_side_effect]
        patched_post.return_value.status_code = response_status

    from zeversolar import ZeverSolarClient, PowerMode
    mock_power_mode = mocker.Mock(spec=PowerMode).ON

    with pytest.raises(expected_exception=expected_exception):
        ZeverSolarClient.ctrl_power(self=mock_self, mode=mock_power_mode)

    mock_self.get_data.assert_called_once()
    assert mock_self._serial_number is mock_self.get_data.return_value.serial_number
    patched_post.assert_has_calls(calls=[
        call.post(
            url=f"http://{mock_self.host}/inv_ctrl.cgi",
            data={
                'sn': mock_self._serial_number,
                'mode': mock_power_mode.value,
            },
            timeout=mock_self._timeout,
        ),
    ])
