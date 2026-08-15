from __future__ import annotations

from dataclasses import dataclass

import pycountry
from django.utils.text import slugify


@dataclass(frozen=True, slots=True)
class CountryInfo:
    code: str
    name: str
    slug: str


def _to_country_info(country: pycountry.db.Data) -> CountryInfo:
    return CountryInfo(
        code=country.alpha_2,
        name=country.name,
        slug=slugify(country.name),
    )


def get_country_by_code(code: str) -> CountryInfo | None:
    country = pycountry.countries.get(alpha_2=code.upper())
    if country is None:
        return None
    return _to_country_info(country)


def alpha3_to_alpha2(alpha3: str) -> str | None:
    country = pycountry.countries.get(alpha_3=alpha3.upper())
    return country.alpha_2 if country else None


def list_nationality_countries() -> list[CountryInfo]:
    return sorted(
        (_to_country_info(country) for country in pycountry.countries),
        key=lambda country: country.name,
    )


def list_residence_countries(*, allowed_codes: list[str]) -> list[CountryInfo]:
    countries: list[CountryInfo] = []
    for code in allowed_codes:
        country = get_country_by_code(code)
        if country is not None:
            countries.append(country)
    return sorted(countries, key=lambda country: country.name)
