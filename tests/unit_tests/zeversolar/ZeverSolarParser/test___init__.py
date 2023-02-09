import pytest_mock


def test___init__(mocker: pytest_mock.MockerFixture):
    from zeversolar import ZeverSolarParser
    fake = mocker.Mock(**{
        "instance": mocker.Mock(spec=ZeverSolarParser),
        "response": mocker.Mock(spec=str),
    })

    ZeverSolarParser.__init__(self=fake.instance, zeversolar_response=fake.response)

    assert fake.instance.zeversolar_response == fake.response
