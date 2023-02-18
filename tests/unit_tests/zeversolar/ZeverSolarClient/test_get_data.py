import pytest
import requests
import typing
from unittest.mock import Mock, call

from pytest_mock import MockFixture

from zeversolar import ZeverSolarError, ZeverSolarTimeout, ZeverSolarHTTPNotFound, ZeverSolarHTTPError


def test_get_data(mocker: MockFixture, instance: Mock):
    patched_get = mocker.patch("zeversolar.requests.get")
    patched_parser = mocker.patch("zeversolar.ZeverSolarParser")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(**{
        "instance": instance,
    })

    result = ZeverSolarClient.get_data(self=fake.instance)

    patched_get.assert_has_calls(calls=[
        call(
            url=f"http://{fake.instance.host}/home.cgi",
            timeout=fake.instance._timeout,
        ),
    ])
    assert result is patched_parser.return_value.parse.return_value
    patched_parser.assert_has_calls(calls=[
        call(zeversolar_response=patched_get.return_value.text),
        call().parse(),
    ])


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
def test_get_data_exception(
        mocker: MockFixture,
        requests_side_effect: requests.exceptions.RequestException,
        response_status: typing.Optional[int],
        expected_exception: type[Exception],
        instance: Mock,
):
    patched_get = mocker.patch("zeversolar.requests.get")
    patched_parser = mocker.patch("zeversolar.ZeverSolarParser")
    if response_status is None:
        patched_get.side_effect = [requests_side_effect]
    else:
        patched_get.return_value.raise_for_status.side_effect = [requests_side_effect]
        patched_get.return_value.status_code = response_status

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(**{
        "instance": instance,
    })

    with pytest.raises(expected_exception=expected_exception):
        ZeverSolarClient.get_data(self=fake.instance)

    patched_get.assert_has_calls(calls=[
        call(
            url=f"http://{fake.instance.host}/home.cgi",
            timeout=fake.instance._timeout,
        ),
    ])
    patched_parser.assert_not_called()

