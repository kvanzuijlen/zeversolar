import pytest
import pytest_mock


@pytest.mark.parametrize("host", ("mock_host", "http://mock_host"))
def test___init__(mocker: pytest_mock.MockerFixture, host: str):
    from zeversolar import ZeverSolarClient
    mock_self = mocker.Mock(ZeverSolarClient)

    ZeverSolarClient.__init__(self=mock_self, host=host)

    expected_host = host.replace("http://", "")
    assert mock_self.host == expected_host
    assert mock_self._timeout == 10
