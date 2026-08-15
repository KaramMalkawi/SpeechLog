import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import CommunityMembership, User
from apps.tenancy.models import City, CityAnnouncement, Community, CommunityAnnouncement, Country


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country

    name = factory.Sequence(lambda n: f"Test Country {n}")
    code = factory.Sequence(lambda n: f"{chr(ord('T') + n // 10)}{n % 10}")
    slug = factory.Sequence(lambda n: f"test-country-{n}")
    is_active = True


class CityFactory(DjangoModelFactory):
    class Meta:
        model = City

    country = factory.SubFactory(CountryFactory)
    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.Sequence(lambda n: f"city-{n}")
    is_active = True


class CommunityFactory(DjangoModelFactory):
    class Meta:
        model = Community

    city = factory.SubFactory(CityFactory)
    name = factory.Sequence(lambda n: f"Community {n}")
    slug = factory.Sequence(lambda n: f"community-{n}")
    community_type = Community.CommunityType.GENERAL
    is_active = True


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    is_active = True
    verification_status = User.VerificationStatus.VERIFIED
    email_verified = True
    profile_onboarding_completed = True
    registration_step = 2
    role = User.Role.NON_MEMBER

    class Params:
        admin = factory.Trait(role=User.Role.ADMIN)
        city_founder = factory.Trait(role=User.Role.CITY_FOUNDER)
        team_member = factory.Trait(role=User.Role.TEAM_MEMBER)
        member = factory.Trait(role=User.Role.MEMBER)
        non_member = factory.Trait(role=User.Role.NON_MEMBER)


class CommunityMembershipFactory(DjangoModelFactory):
    class Meta:
        model = CommunityMembership

    user = factory.SubFactory(UserFactory)
    community_id = factory.LazyAttribute(lambda o: o.community.id)
    city_id = factory.LazyAttribute(lambda o: o.community.city_id)

    class Params:
        community = factory.SubFactory(CommunityFactory)


class CommunityAnnouncementFactory(DjangoModelFactory):
    class Meta:
        model = CommunityAnnouncement

    community_id = factory.LazyAttribute(lambda o: o.community.id)
    city_id = factory.LazyAttribute(lambda o: o.community.city_id)
    title = factory.Sequence(lambda n: f"Announcement {n}")
    body = "Test body"

    class Params:
        community = factory.SubFactory(CommunityFactory)


class CityAnnouncementFactory(DjangoModelFactory):
    class Meta:
        model = CityAnnouncement

    city_id = factory.LazyAttribute(lambda o: o.city.id)
    title = factory.Sequence(lambda n: f"City news {n}")
    body = "Shared city content"

    class Params:
        city = factory.SubFactory(CityFactory)


class EventFactory(DjangoModelFactory):
    class Meta:
        model = "events.Event"

    title = factory.Sequence(lambda n: f"Event {n}")
    description = "Test event"
    location = "Test venue"
    starts_at = factory.Faker("future_datetime", end_date="+30d")
    ends_at = factory.Faker("future_datetime", end_date="+60d")
    price = 0
    category = "social"
    capacity = 50
    creator = factory.SubFactory(UserFactory, city_founder=True)
    community_id = factory.LazyAttribute(lambda o: o.community.id)
    city_id = factory.LazyAttribute(lambda o: o.community.city_id)

    class Params:
        community = factory.SubFactory(CommunityFactory)
