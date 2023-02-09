from unittest.mock import call

from pytest_mock import MockFixture


def test_power_off(mocker: MockFixture):
    from zeversolar import ZeverSolarClient, PowerMode
    mock_self = mocker.Mock(spec=ZeverSolarClient)

    result = ZeverSolarClient.power_off(self=mock_self)

    assert result is mock_self.ctrl_power.return_value
    mock_self.assert_has_calls(calls=[call.ctrl_power(mode=PowerMode.OFF)])
