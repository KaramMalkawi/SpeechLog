from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CommunityMembership, User
from apps.accounts.services import mark_user_verified
from apps.gatherings.exceptions import GatheringAtCapacity, GatheringIdentityRequired
from apps.gatherings.services import create_gathering, join_gathering
from apps.tenancy.models import City, Community, Country


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def country(db):
    country, _ = Country.objects.get_or_create(name="Jordan", code="JO", slug="jordan")
    return country


@pytest.fixture
def city(db, country):
    city, _ = City.objects.get_or_create(country=country, name="Amman", slug="amman")
    return city


@pytest.fixture
def community(db, city):
    return Community.objects.create(city=city, name="Amman Gatherings", slug="amman-gatherings")


def _attach(user: User, community: Community, role: str) -> User:
    CommunityMembership.objects.create(
        user=user,
        community_id=community.id,
        city_id=community.city_id,
        role=role,
    )
    return user


@pytest.fixture
def member_user(db, community):
    user = User.objects.create_user(
        email="g-member@example.com",
        password="Passw0rd!",
        full_name="Gathering Member",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(user)
    return _attach(user, community, CommunityMembership.Role.MEMBER)


@pytest.fixture
def non_member_user(db, community):
    user = User.objects.create_user(
        email="g-nonmember@example.com",
        password="Passw0rd!",
        full_name="Gathering NonMember",
        role=User.Role.NON_MEMBER,
        active_community_id=community.id,
        gathering_attendance_credit=3,
    )
    mark_user_verified(user)
    return _attach(user, community, CommunityMembership.Role.MEMBER)


@pytest.fixture
def founder_user(db, community):
    user = User.objects.create_user(
        email="g-founder@example.com",
        password="Passw0rd!",
        full_name="Gathering Founder",
        role=User.Role.CITY_FOUNDER,
        active_community_id=community.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(user)
    return _attach(user, community, CommunityMembership.Role.CITY_FOUNDER)


@pytest.fixture
def gathering_payload():
    starts = timezone.now() + timedelta(days=5)
    return {
        "title": "Board Games Night",
        "description": "Casual games.",
        "area": "Dabouk, Amman",
        "exact_location": "12 Hidden Street",
        "map_link": "https://maps.example.com/pin",
        "starts_at": starts.isoformat().replace("+00:00", "Z"),
        "max_attendees": 20,
    }


@pytest.mark.django_db
def test_member_can_create_with_attendance_credit(
    api_client, member_user, gathering_payload
):
    api_client.force_authenticate(member_user)
    ok = api_client.post(reverse("gathering-list-create"), gathering_payload, format="json")
    assert ok.status_code == status.HTTP_201_CREATED
    assert ok.data["title"] == "Board Games Night"
    # Creator can see the exact location (host), but is not treated as an attendee.
    assert ok.data["exact_location"] == "12 Hidden Street"
    assert ok.data["viewer_join_status"] == "creator"
    assert ok.data["area"] == "Dabouk, Amman"
    assert ok.data["hard_cap"] == 20


@pytest.mark.django_db
def test_non_member_can_create_with_attendance_credit(
    api_client, non_member_user, gathering_payload
):
    api_client.force_authenticate(non_member_user)
    ok = api_client.post(reverse("gathering-list-create"), gathering_payload, format="json")
    assert ok.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_member_blocked_without_attendance(
    api_client, member_user, gathering_payload
):
    member_user.gathering_attendance_credit = 0
    member_user.bypass_gathering_attendance = False
    member_user.save(
        update_fields=[
            "gathering_attendance_credit",
            "bypass_gathering_attendance",
            "updated_at",
        ]
    )
    api_client.force_authenticate(member_user)
    blocked = api_client.post(
        reverse("gathering-list-create"), gathering_payload, format="json"
    )
    assert blocked.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_location_hidden_until_joined(
    api_client, member_user, founder_user, community, gathering_payload
):
    api_client.force_authenticate(member_user)
    created = api_client.post(reverse("gathering-list-create"), gathering_payload, format="json")
    gathering_id = created.data["id"]

    # Another user still sees gated location before joining.
    api_client.force_authenticate(founder_user)
    detail = api_client.get(reverse("gathering-detail", kwargs={"id": gathering_id}))
    assert detail.data["location_revealed"] is False
    assert detail.data["exact_location"] == ""
    assert detail.data["map_link"] == ""

    join = api_client.post(reverse("gathering-join", kwargs={"gathering_id": gathering_id}))
    assert join.status_code == status.HTTP_201_CREATED

    detail2 = api_client.get(reverse("gathering-detail", kwargs={"id": gathering_id}))
    assert detail2.data["location_revealed"] is True
    assert detail2.data["exact_location"] == "12 Hidden Street"
    assert detail2.data["viewer_join_status"] == "joined"


@pytest.mark.django_db
def test_hard_cap_enforced(member_user, community):
    starts = timezone.now() + timedelta(days=2)
    gathering = create_gathering(
        creator=member_user,
        community=community,
        title="Tiny Cap",
        area="Amman",
        exact_location="Secret",
        starts_at=starts,
        max_attendees=2,
    )
    # Creator does not occupy an attendee seat; capacity applies to other users.

    second = User.objects.create_user(
        email="g-member2@example.com",
        password="Passw0rd!",
        full_name="Second Member",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(second)
    _attach(second, community, CommunityMembership.Role.MEMBER)
    join_gathering(gathering_id=gathering.id, community_id=community.id, user=second)

    third = User.objects.create_user(
        email="g-member3@example.com",
        password="Passw0rd!",
        full_name="Third Member",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(third)
    _attach(third, community, CommunityMembership.Role.MEMBER)

    # Second and third fill the 2-seat gathering.
    join_gathering(gathering_id=gathering.id, community_id=community.id, user=third)

    fourth = User.objects.create_user(
        email="g-member4@example.com",
        password="Passw0rd!",
        full_name="Fourth Member",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(fourth)
    _attach(fourth, community, CommunityMembership.Role.MEMBER)

    with pytest.raises(GatheringAtCapacity):
        join_gathering(gathering_id=gathering.id, community_id=community.id, user=fourth)


@pytest.mark.django_db
def test_join_allowed_without_events(non_member_user, community, member_user):
    gathering = create_gathering(
        creator=member_user,
        community=community,
        title="Mixer",
        area="Amman",
        starts_at=timezone.now() + timedelta(days=1),
    )
    joined = join_gathering(
        gathering_id=gathering.id, community_id=community.id, user=non_member_user
    )
    assert joined is not None


@pytest.mark.django_db
def test_join_requires_identity_verification(member_user, community):
    gathering = create_gathering(
        creator=member_user,
        community=community,
        title="ID Gate",
        area="Amman",
        starts_at=timezone.now() + timedelta(days=1),
    )
    unverified = User.objects.create_user(
        email="g-unverified@example.com",
        password="Passw0rd!",
        full_name="Unverified Joiner",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        email_verified=True,
        verification_status=User.VerificationStatus.UNVERIFIED,
        gathering_attendance_credit=1,
    )
    _attach(unverified, community, CommunityMembership.Role.MEMBER)

    with pytest.raises(GatheringIdentityRequired):
        join_gathering(
            gathering_id=gathering.id, community_id=community.id, user=unverified
        )


@pytest.mark.django_db
def test_list_isolated_by_community(
    api_client, member_user, community, city, gathering_payload
):
    other = Community.objects.create(city=city, name="Other G", slug="other-g")
    other_member = User.objects.create_user(
        email="g-other@example.com",
        password="Passw0rd!",
        full_name="Other",
        role=User.Role.MEMBER,
        active_community_id=other.id,
        gathering_attendance_credit=1,
    )
    mark_user_verified(other_member)
    _attach(other_member, other, CommunityMembership.Role.MEMBER)

    api_client.force_authenticate(member_user)
    api_client.post(reverse("gathering-list-create"), gathering_payload, format="json")

    api_client.force_authenticate(other_member)
    payload = {**gathering_payload, "title": "Other Community Gathering"}
    api_client.post(reverse("gathering-list-create"), payload, format="json")

    list_a = api_client.get(
        reverse("gathering-list-create"),
        {"community_id": str(community.id)},
    )
    titles = {row["title"] for row in list_a.data["results"]}
    assert "Board Games Night" in titles
    assert "Other Community Gathering" not in titles


@pytest.mark.django_db
def test_eligibility_endpoint_requires_attendance(api_client, member_user):
    member_user.gathering_attendance_credit = 0
    member_user.bypass_gathering_attendance = False
    member_user.save(
        update_fields=[
            "gathering_attendance_credit",
            "bypass_gathering_attendance",
            "updated_at",
        ]
    )
    api_client.force_authenticate(member_user)
    response = api_client.get(reverse("gathering-eligibility"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["events_required"] == 1
    assert response.data["can_create"] is False
    assert response.data["can_join"] is False


@pytest.mark.django_db
def test_eligibility_with_admin_attendance_credit(api_client, member_user):
    member_user.gathering_attendance_credit = 1
    member_user.bypass_gathering_attendance = False
    member_user.save(
        update_fields=[
            "gathering_attendance_credit",
            "bypass_gathering_attendance",
            "updated_at",
        ]
    )
    api_client.force_authenticate(member_user)
    response = api_client.get(reverse("gathering-eligibility"))
    assert response.data["can_create"] is True
    assert response.data["attendance_credit"] == 1
    assert response.data["events_required"] == 1
    assert response.data["role_label"] == "Member"


@pytest.mark.django_db
def test_non_member_unlocks_at_exactly_three_attended(api_client, non_member_user):
    """Non-members unlock at >= 3 attended events (not strictly more than 3)."""
    non_member_user.gathering_attendance_credit = 3
    non_member_user.bypass_gathering_attendance = False
    non_member_user.save(
        update_fields=[
            "gathering_attendance_credit",
            "bypass_gathering_attendance",
            "updated_at",
        ]
    )
    api_client.force_authenticate(non_member_user)
    response = api_client.get(reverse("gathering-eligibility"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["events_required"] == 3
    assert response.data["events_attended"] == 3
    assert response.data["can_join"] is True
    assert response.data["can_create"] is True
    assert response.data["role_label"] == "Non-Member"


@pytest.mark.django_db
def test_eligibility_bypass_flag(api_client, member_user):
    member_user.gathering_attendance_credit = 0
    member_user.bypass_gathering_attendance = True
    member_user.save(
        update_fields=[
            "gathering_attendance_credit",
            "bypass_gathering_attendance",
            "updated_at",
        ]
    )
    api_client.force_authenticate(member_user)
    response = api_client.get(reverse("gathering-eligibility"))
    assert response.data["can_create"] is True
    assert response.data["bypass_gathering_attendance"] is True


@pytest.mark.django_db
@patch("apps.gatherings.services.is_s3_configured", return_value=True)
@patch("apps.gatherings.services.generate_presigned_upload_url")
def test_cover_presign(mock_presign, mock_configured, api_client, member_user, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    mock_presign.return_value = {
        "upload_url": "https://s3.example.com/up",
        "object_key": f"gathering-covers/{member_user.id}/c.jpg",
        "expires_in": 900,
        "headers": {"Content-Type": "image/jpeg", "Content-Length": "100"},
    }
    api_client.force_authenticate(member_user)
    response = api_client.post(
        reverse("gathering-cover-presign"),
        {"content_type": "image/jpeg", "content_length": 100},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
