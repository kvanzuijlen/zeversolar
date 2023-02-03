import pytest


@pytest.mark.parametrize(argnames=["zeversolar_response", "pac", "energy_today"], argvalues=(
    (
        "1 1 EAB961670747 ABWDWHTQ3JBL5XH4 M10 16415-562R+16413-561R 15:57 02/02/2023 Error 1 BS15006011670374 V610-01037-04 30 0.0 OK Error",
        30,
        0.0,
    ),
    (
        "1 0 EAB971770016 GHKXWHTQ3JPQQSVM M11 19703-826R+17511-707R 15:53 06/03/2022 0 1 EL36806011640036 3187 14.48 OK Error",
        3187,
        14.48,
    ),
    (
        "1 0 EAB971770016 GHKXWHTQ3JPQQSVM M11 19703-826R+17511-707R 15:53 06/03/2022 0 1 EL36806011640036 3187 14.20 OK Error",
        3187,
        14.20,
    ),
))
def test_parse_multiple_zeversolar_hardware_version_strings(zeversolar_response: str, pac: int, energy_today: int):
    from zeversolar import ZeverSolarParser
    assert ZeverSolarParser(zeversolar_response).parse().pac == pac
    assert ZeverSolarParser(zeversolar_response).parse().energy_today == energy_today
