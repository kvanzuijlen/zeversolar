import pytest
from pytest_mock import MockFixture


@pytest.fixture(autouse=True)
def patch_retry(mocker: MockFixture):
    def no_retries(f, *args, **kw):
        return f()
    mocker.patch('retry.api.__retry_internal', no_retries)


@pytest.fixture()
def mock_self(mocker: MockFixture):
    from datetime import timedelta
    from zeversolar import ZeverSolarClient
    mock_host = mocker.Mock(spec=str)
    mock_timeout = mocker.Mock(spec=timedelta)
    mock_self = mocker.Mock(spec=ZeverSolarClient, **{
        "host": mock_host,
        "_serial_number": None,
        "_timeout": mock_timeout,
    })
    mock_self._serial_number = None
    return mock_self
