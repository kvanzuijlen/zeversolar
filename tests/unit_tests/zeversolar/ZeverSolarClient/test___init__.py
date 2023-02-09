from unittest.mock import call

import pytest
import pytest_mock


@pytest.mark.parametrize("host", ("mock_host", "http://mock_host", "https://mock_host"))
def test___init__(mocker: pytest_mock.MockerFixture, host: str):
    mock_urllib = mocker.patch("zeversolar.urllib.parse")
    from zeversolar import ZeverSolarClient
    mock_self = mocker.Mock(spec=ZeverSolarClient)

    ZeverSolarClient.__init__(self=mock_self, host=host)

    if "http" not in host:
        host = f"http://{host}"
    assert mock_self.host == mock_urllib.urlparse.return_value.netloc.strip.return_value
    assert mock_self._timeout == 10
    assert mock_self._serial_number is None
    mock_urllib.assert_has_calls(calls=[
        call.urlparse(url=host),
        call.urlparse().netloc.strip("/"),
    ])
