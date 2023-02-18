from unittest.mock import call

import pytest
import pytest_mock


@pytest.mark.parametrize("host", ("mock_host", "http://mock_host", "https://mock_host"))
def test___init__(mocker: pytest_mock.MockerFixture, host: str):
    fake_urllib = mocker.patch("zeversolar.urllib.parse")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(**{
        "instance": mocker.Mock(spec=ZeverSolarClient),
    })

    ZeverSolarClient.__init__(self=fake.instance, host=host)

    if "http" not in host:
        host = f"http://{host}"
    assert fake.instance.host == fake_urllib.urlparse.return_value.netloc.strip.return_value
    assert fake.instance._timeout == 10
    assert fake.instance._serial_number is None
    fake_urllib.assert_has_calls(calls=[
        call.urlparse(url=host),
        call.urlparse().netloc.strip("/"),
    ])
