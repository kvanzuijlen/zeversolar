import pytest
from pytest_mock import MockFixture


@pytest.mark.parametrize(
    "string_value, expected_result",
    (
        ("14.9", 14.09),
        ("14.09", 14.09),
        ("14.20", 14.20),
        ("0.89", 0.89),
    )
)
def test__leading_zero(string_value: str, expected_result: str):
    from zeversolar import ZeverSolarParser

    result = ZeverSolarParser._fix_leading_zero(string_value=string_value)

    assert result == expected_result
