from unittest.mock import call

from pytest_mock import MockFixture


def test_power_off(mocker: MockFixture):
    from zeversolar import ZeverSolarClient, PowerMode
    fake = mocker.Mock(**{
        "instance": mocker.Mock(spec=ZeverSolarClient),
    })

    result = ZeverSolarClient.power_off(self=fake.instance)

    assert result is fake.instance.ctrl_power.return_value
    fake.instance.assert_has_calls(calls=[call.ctrl_power(mode=PowerMode.OFF)])
