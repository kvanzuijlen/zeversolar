import pytest_mock


def test___init__(mocker: pytest_mock.MockerFixture):
    from zeversolar import ZeverSolarParser
    mock_self = mocker.Mock(spec=ZeverSolarParser)
    mock_response = mocker.Mock(spec=str)

    ZeverSolarParser.__init__(self=mock_self, zeversolar_response=mock_response)

    assert mock_self.zeversolar_response == mock_response
