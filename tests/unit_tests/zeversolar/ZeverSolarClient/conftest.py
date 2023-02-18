import pytest
from pytest_mock import MockFixture


@pytest.fixture(autouse=True)
def patch_retry(mocker: MockFixture):
    def no_retries(f, *args, **kw):
        return f()
    mocker.patch('retry.api.__retry_internal', no_retries)


@pytest.fixture()
def instance(mocker: MockFixture):
    from datetime import timedelta
    from zeversolar import ZeverSolarClient
    return mocker.Mock(spec=ZeverSolarClient, **{
        "host": mocker.Mock(spec=str),
        "_serial_number": None,
        "_timeout": mocker.Mock(spec=timedelta),
    })
