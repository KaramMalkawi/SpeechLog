from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CommunityMembership, User
from apps.accounts.services import mark_user_verified
from apps.events.exceptions import EventAtCapacity
from apps.events.models import EventJoinRequest, EventTicket
from apps.events.services import create_event, create_event_ticket, join_event
from apps.tenancy.models import City, Community, Country
from core.tenancy import TenantContext, set_tenant_context


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
    return Community.objects.create(city=city, name="Amman General", slug="amman-general-events")


@pytest.fixture
def community_b(db, city):
    return Community.objects.create(city=city, name="Amman Other", slug="amman-other-events")


def _attach_community(user: User, community: Community, role: str) -> User:
    CommunityMembership.objects.create(
        user=user,
        community_id=community.id,
        city_id=community.city_id,
        role=role,
    )
    return user


@pytest.fixture
def founder_user(db, community):
    user = User.objects.create_user(
        email="founder-events@example.com",
        password="Passw0rd!",
        full_name="Founder User",
        role=User.Role.CITY_FOUNDER,
        active_community_id=community.id,
    )
    mark_user_verified(user)
    return _attach_community(user, community, CommunityMembership.Role.CITY_FOUNDER)


@pytest.fixture
def founder_b(db, community_b):
    user = User.objects.create_user(
        email="founder-b-events@example.com",
        password="Passw0rd!",
        full_name="Founder B",
        role=User.Role.CITY_FOUNDER,
        active_community_id=community_b.id,
    )
    mark_user_verified(user)
    return _attach_community(user, community_b, CommunityMembership.Role.CITY_FOUNDER)


@pytest.fixture
def member_user(db, community):
    user = User.objects.create_user(
        email="member-events@example.com",
        password="Passw0rd!",
        full_name="Member User",
        role=User.Role.MEMBER,
        active_community_id=community.id,
        nationality_code="JO",
    )
    mark_user_verified(user)
    return _attach_community(user, community, CommunityMembership.Role.MEMBER)


@pytest.fixture
def non_member_user(db, community):
    user = User.objects.create_user(
        email="nonmember-events@example.com",
        password="Passw0rd!",
        full_name="Non Member User",
        role=User.Role.NON_MEMBER,
        active_community_id=community.id,
    )
    mark_user_verified(user)
    return _attach_community(user, community, CommunityMembership.Role.MEMBER)


@pytest.fixture
def event_data():
    return {
        "title": "City Walk",
        "description": "A curated cultural walk.",
        "location": "Downtown",
        "starts_at": "2026-08-01T18:00:00Z",
        "ends_at": "2026-08-01T20:00:00Z",
        "price": "15.00",
        "category": "social",
        "capacity": 30,
    }


@pytest.mark.django_db
def test_city_founder_can_create_event(api_client, founder_user, community, event_data):
    api_client.force_authenticate(founder_user)
    response = api_client.post(reverse("event-list-create"), event_data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["title"] == event_data["title"]
    assert response.data["community_id"] == str(community.id)
    assert response.data["city_id"] == str(community.city_id)


@pytest.mark.django_db
def test_price_and_location_cannot_change_after_creation(api_client, founder_user, event_data):
    api_client.force_authenticate(founder_user)
    create_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = create_response.data["id"]

    patch_response = api_client.patch(
        reverse("event-detail", kwargs={"id": event_id}),
        {"price": "20.00", "location": "New Venue"},
        format="json",
    )

    assert patch_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "price" in patch_response.data or "location" in patch_response.data


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_member_instant_join_creates_ticket(
    mock_delay,
    api_client,
    founder_user,
    member_user,
    event_data,
    django_capture_on_commit_callbacks,
):
    api_client.force_authenticate(founder_user)
    event_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = event_response.data["id"]

    api_client.force_authenticate(member_user)
    with django_capture_on_commit_callbacks(execute=True):
        join_response = api_client.post(
            reverse("event-join", kwargs={"event_id": event_id}), format="json"
        )

    assert join_response.status_code == status.HTTP_201_CREATED
    assert EventTicket.all_objects.filter(event_id=event_id, user=member_user).exists()
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_non_member_join_request_is_pending(api_client, founder_user, non_member_user, event_data):
    api_client.force_authenticate(founder_user)
    event_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = event_response.data["id"]

    api_client.force_authenticate(non_member_user)
    join_response = api_client.post(
        reverse("event-join", kwargs={"event_id": event_id}), format="json"
    )

    assert join_response.status_code == status.HTTP_201_CREATED
    assert join_response.data["status"] == EventJoinRequest.Status.PENDING
    assert EventJoinRequest.all_objects.filter(event_id=event_id, user=non_member_user).exists()


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_city_founder_can_accept_join_request(
    mock_delay,
    api_client,
    founder_user,
    non_member_user,
    event_data,
    django_capture_on_commit_callbacks,
):
    api_client.force_authenticate(founder_user)
    event_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = event_response.data["id"]

    api_client.force_authenticate(non_member_user)
    join_response = api_client.post(
        reverse("event-join", kwargs={"event_id": event_id}), format="json"
    )
    request_id = join_response.data["id"]

    api_client.force_authenticate(founder_user)
    with django_capture_on_commit_callbacks(execute=True):
        accept_response = api_client.post(
            reverse(
                "event-join-request-accept",
                kwargs={"event_id": event_id, "request_id": request_id},
            ),
            format="json",
        )

    assert accept_response.status_code == status.HTTP_200_OK
    assert accept_response.data["status"] == EventJoinRequest.Status.APPROVED
    # Approval fully admits the attendee (ticket + View Ticket) until M4 payments.
    assert EventTicket.all_objects.filter(event_id=event_id, user=non_member_user).exists()
    mock_delay.assert_called_once()

    api_client.force_authenticate(non_member_user)
    detail = api_client.get(
        reverse("event-detail", kwargs={"id": event_id}),
        format="json",
    )
    assert detail.status_code == status.HTTP_200_OK
    assert detail.data["viewer_join_status"] == "joined"

    tickets_response = api_client.get(reverse("event-my-tickets"), format="json")
    assert tickets_response.status_code == status.HTTP_200_OK
    assert any(str(row["event"]) == str(event_id) for row in tickets_response.data["results"])


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_my_tickets_returns_user_tickets(
    mock_delay, api_client, founder_user, member_user, event_data
):
    api_client.force_authenticate(founder_user)
    event_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = event_response.data["id"]

    api_client.force_authenticate(member_user)
    api_client.post(reverse("event-join", kwargs={"event_id": event_id}), format="json")

    tickets_response = api_client.get(reverse("event-my-tickets"), format="json")

    assert tickets_response.status_code == status.HTTP_200_OK
    results = tickets_response.data["results"]
    assert len(results) == 1
    assert str(results[0]["event"]) == str(event_id)


@pytest.mark.django_db
def test_list_events_isolated_by_community(
    api_client, founder_user, founder_b, community, community_b, event_data
):
    api_client.force_authenticate(founder_user)
    api_client.post(reverse("event-list-create"), event_data, format="json")

    api_client.force_authenticate(founder_b)
    other_payload = {**event_data, "title": "Other Community Event"}
    api_client.post(reverse("event-list-create"), other_payload, format="json")

    list_a = api_client.get(
        reverse("event-list-create"),
        {"community_id": str(community.id)},
        format="json",
    )
    assert list_a.status_code == status.HTTP_200_OK
    titles_a = {row["title"] for row in list_a.data["results"]}
    assert "City Walk" in titles_a
    assert "Other Community Event" not in titles_a

    list_b = api_client.get(
        reverse("event-list-create"),
        {"community_id": str(community_b.id)},
        format="json",
    )
    titles_b = {row["title"] for row in list_b.data["results"]}
    assert "Other Community Event" in titles_b
    assert "City Walk" not in titles_b


@pytest.mark.django_db
def test_capacity_enforced_atomically(community, member_user, founder_user):
    set_tenant_context(TenantContext.from_community(community))
    starts = timezone.now() + timedelta(days=7)
    event = create_event(
        creator=founder_user,
        community=community,
        title="Cap Event",
        location="Hall",
        starts_at=starts,
        ends_at=starts + timedelta(hours=2),
        capacity=1,
    )
    create_event_ticket(event=event, user=member_user)

    second = User.objects.create_user(
        email="member2-events@example.com",
        password="Passw0rd!",
        full_name="Member Two",
        role=User.Role.MEMBER,
        active_community_id=community.id,
    )
    mark_user_verified(second)

    with pytest.raises(EventAtCapacity):
        create_event_ticket(event=event, user=second)


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_signed_ticket_token_roundtrip(mock_delay, community, member_user, founder_user):
    from apps.events.services import verify_ticket_token

    starts = timezone.now() + timedelta(days=7)
    event = create_event(
        creator=founder_user,
        community=community,
        title="Token Event",
        location="Hall",
        starts_at=starts,
        ends_at=starts + timedelta(hours=2),
    )
    kind, ticket = join_event(event_id=event.id, user=member_user)
    assert kind == "ticket"
    payload = verify_ticket_token(ticket.token)
    assert payload["user_id"] == str(member_user.id)
    assert payload["event_id"] == str(event.id)


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_event_detail_payload_enrichment(
    mock_delay, api_client, founder_user, member_user, community, event_data, city
):
    founder_user.profile_photo_key = f"profile-photos/{founder_user.id}/photo.jpg"
    founder_user.save(update_fields=["profile_photo_key"])

    api_client.force_authenticate(founder_user)
    create_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = create_response.data["id"]

    api_client.force_authenticate(member_user)
    api_client.post(reverse("event-join", kwargs={"event_id": event_id}), format="json")

    detail = api_client.get(reverse("event-detail", kwargs={"id": event_id}), format="json")
    assert detail.status_code == status.HTTP_200_OK
    body = detail.data
    assert body["currency"] == "JOD"
    assert body["spots_total"] == 30
    assert body["spots_left"] == 29
    assert body["attendee_count"] == 1
    assert body["viewer_join_status"] == "joined"
    assert body["requires_approval"] is False
    assert body["organizer"]["full_name"] == founder_user.full_name
    assert body["organizer"]["role_label"] == f"City Founder · {city.name}"
    assert body["organizer"]["photo_url"].endswith(founder_user.profile_photo_key)
    assert len(body["attendee_previews"]) == 1
    assert body["attendee_extra_count"] == 0


@pytest.mark.django_db
def test_non_member_requires_approval_and_pending_status(
    api_client, founder_user, non_member_user, event_data
):
    api_client.force_authenticate(founder_user)
    create_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = create_response.data["id"]

    api_client.force_authenticate(non_member_user)
    api_client.post(reverse("event-join", kwargs={"event_id": event_id}), format="json")

    detail = api_client.get(reverse("event-detail", kwargs={"id": event_id}), format="json")
    assert detail.data["requires_approval"] is True
    assert detail.data["viewer_join_status"] == "pending"


@pytest.mark.django_db
@patch("apps.events.tasks.deliver_event_ticket_notification_task.delay")
def test_member_can_list_public_attendees(
    mock_delay, api_client, founder_user, member_user, event_data
):
    api_client.force_authenticate(founder_user)
    create_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = create_response.data["id"]

    api_client.force_authenticate(member_user)
    api_client.post(reverse("event-join", kwargs={"event_id": event_id}), format="json")

    attendees = api_client.get(
        reverse("event-attendee-list", kwargs={"event_id": event_id}),
        format="json",
    )
    assert attendees.status_code == status.HTTP_200_OK
    results = attendees.data["results"]
    assert len(results) == 1
    assert "user_id" in results[0]
    assert "full_name" in results[0]
    assert "user_email" not in results[0]


@pytest.mark.django_db
@patch("apps.events.services.is_s3_configured", return_value=True)
@patch("apps.events.services.generate_presigned_upload_url")
def test_event_cover_presign(mock_presign, mock_configured, api_client, founder_user, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "test-bucket"
    mock_presign.return_value = {
        "upload_url": "https://s3.example.com/upload",
        "object_key": f"event-covers/{founder_user.id}/cover.jpg",
        "expires_in": 900,
        "headers": {"Content-Type": "image/jpeg", "Content-Length": "2048"},
    }

    api_client.force_authenticate(founder_user)
    response = api_client.post(
        reverse("event-cover-presign"),
        {"content_type": "image/jpeg", "content_length": 2048},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["upload_url"] == "https://s3.example.com/upload"
    mock_presign.assert_called_once()


@pytest.mark.django_db
@patch("apps.events.services.delete_object")
@patch("apps.events.services.get_object_metadata")
def test_event_cover_confirm(
    mock_metadata, mock_delete, api_client, founder_user, event_data, settings
):
    settings.MEDIA_CDN_BASE_URL = "https://cdn.example.com"
    object_key = f"event-covers/{founder_user.id}/cover.jpg"
    mock_metadata.return_value = {"content_length": 2048, "content_type": "image/jpeg"}

    api_client.force_authenticate(founder_user)
    create_response = api_client.post(reverse("event-list-create"), event_data, format="json")
    event_id = create_response.data["id"]

    response = api_client.post(
        reverse("event-cover-confirm", kwargs={"event_id": event_id}),
        {"object_key": object_key},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["cover_image_url"].endswith(object_key)

    detail = api_client.get(reverse("event-detail", kwargs={"id": event_id}), format="json")
    assert detail.data["cover_image_url"].endswith(object_key)
