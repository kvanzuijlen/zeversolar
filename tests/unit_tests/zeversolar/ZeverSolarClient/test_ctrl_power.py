from unittest.mock import call

from pytest_mock import MockFixture


def test_ctrl_power(mocker: MockFixture):
    patched_requests = mocker.patch("zeversolar.requests")
    from zeversolar import ZeverSolarClient, PowerMode
    from datetime import timedelta
    mock_host = mocker.Mock(spec=str)
    mock_timeout = mocker.Mock(spec=timedelta)
    mock_self = mocker.Mock(spec=ZeverSolarClient, **{
        "host": mock_host,
        "_serial_number": None,
        "_timeout": mock_timeout,
    })
    mock_self._serial_number = None
    mock_power_mode = mocker.Mock(spec=PowerMode).ON

    result = ZeverSolarClient.ctrl_power(self=mock_self, mode=mock_power_mode)

    mock_self.get_data.assert_called_once()
    assert mock_self._serial_number is mock_self.get_data.return_value.serial_number
    patched_requests.assert_has_calls(calls=[
        call.post(
            url=f"http://{mock_host}/inv_ctrl.cgi",
            data={
                'sn': mock_self._serial_number,
                'mode': mock_power_mode.value,
            },
            timeout=mock_timeout,
        ),
    ])
    assert result is mock_power_mode
