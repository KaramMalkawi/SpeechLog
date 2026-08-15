import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CommunityMembership, User
from apps.accounts.services import mark_user_verified
from apps.events.models import Event
from apps.events.services import create_event, create_event_ticket
from apps.gatherings.models import Gathering
from apps.gatherings.services import create_gathering, join_gathering
from apps.guidebook.models import PartnerCategory, PartnerScope
from apps.guidebook.services import upsert_partner_by_name
from apps.tenancy.models import City, Community, Country
from core.storage import put_object_bytes

# Default copy used when a gathering has no unique description (matches mobile design).
DEFAULT_GATHERING_DESCRIPTION = (
    "A relaxed monthly gathering for Amman's expat community. Meet new faces, "
    "share stories from around the world, and connect with others who understand "
    "the expat experience. Open to all nationalities and backgrounds — everyone "
    "is welcome at the table! The exact venue is shared once you're confirmed "
    "so we can keep the vibe intimate."
)

# Temporary test pin: Amman city center (opened via “View in Google Maps”).
AMMAN_TEST_MAP_LINK = (
    "https://www.google.com/maps?q=31.9539,35.9106&ll=31.9539,35.9106"
)
AMMAN_TEST_EXACT_LOCATION = "Amman"

NOODLE_HOUSE_SHORT = (
    "Authentic Pan-Asian cuisine in\nThe heart of DIFC. Show your ..."
)
NOODLE_HOUSE_FULL = (
    "Authentic Pan-Asian cuisine in the heart of DIFC. Show your Mixed Miles "
    "membership to unlock an exclusive 15% discount on all orders. Known for "
    "vibrant flavors inspired by Southeast Asian street food culture and a warm, "
    "energetic atmosphere."
)

DEMO_PASSWORD = "DemoPass123!"
ASSET_DIR = Path(settings.BASE_DIR) / "seed_assets"


def _read_asset(name: str) -> bytes:
    path = ASSET_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing seed asset: {path}")
    return path.read_bytes()


def _detect_content_type(body: bytes) -> tuple[str, str]:
    """Return (content_type, file_extension) from magic bytes."""
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    return "application/octet-stream", ".bin"


def _upload_cover(*, prefix: str, uploader_id, filename: str) -> str:
    body = _read_asset(filename)
    content_type, extension = _detect_content_type(body)
    object_key = f"{prefix}/{uploader_id}/{uuid.uuid4()}{extension}"
    put_object_bytes(object_key=object_key, body=body, content_type=content_type)
    return object_key


def _ensure_user(
    *,
    email: str,
    full_name: str,
    role: str,
    community: Community,
    membership_role: str,
) -> User:
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            password=DEMO_PASSWORD,
            full_name=full_name,
            role=role,
            active_community_id=community.id,
        )
    else:
        user.full_name = full_name
        user.role = role
        user.active_community_id = community.id
        user.set_password(DEMO_PASSWORD)
        user.save()

    mark_user_verified(user)
    CommunityMembership.objects.update_or_create(
        user=user,
        community_id=community.id,
        defaults={
            "city_id": community.city_id,
            "role": membership_role,
        },
    )
    return user


class Command(BaseCommand):
    help = (
        "Seed Amman community, demo users, events, gatherings, and guidebook "
        "partners with cover images for local mobile testing."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        country, _ = Country.objects.get_or_create(
            code="JO",
            defaults={"name": "Jordan", "slug": "jordan", "is_active": True},
        )
        city, _ = City.objects.get_or_create(
            country=country,
            slug="amman",
            defaults={"name": "Amman", "is_active": True},
        )
        community, _ = Community.objects.get_or_create(
            city=city,
            slug="amman-expats",
            defaults={
                "name": "Amman Expats",
                "community_type": Community.CommunityType.GENERAL,
                "is_active": True,
            },
        )

        founder = _ensure_user(
            email="founder@mixedmiles.com",
            full_name="Baraa Malkawi",
            role=User.Role.CITY_FOUNDER,
            community=community,
            membership_role=CommunityMembership.Role.CITY_FOUNDER,
        )
        member = _ensure_user(
            email="member@mixedmiles.com",
            full_name="Sara Nabil",
            role=User.Role.MEMBER,
            community=community,
            membership_role=CommunityMembership.Role.MEMBER,
        )
        _ensure_user(
            email="newcomer@mixedmiles.com",
            full_name="Adam Newcomer",
            role=User.Role.NON_MEMBER,
            community=community,
            membership_role=CommunityMembership.Role.MEMBER,
        )
        guest = _ensure_user(
            email="ali@mixedmiles.com",
            full_name="Ali Ahmed",
            role=User.Role.MEMBER,
            community=community,
            membership_role=CommunityMembership.Role.MEMBER,
        )

        now = timezone.now()

        # Replace older seed titles so Explore shows the mobile demo events only.
        Event.all_objects.filter(
            community_id=community.id,
            title__in=(
                "Dubai Expats Rooftop Mixer",
                "Weekend Park Picnic",
            ),
            is_cancelled=False,
        ).update(is_cancelled=True)

        event_specs = [
            {
                "title": "Digital Nomads Meetup",
                "description": (
                    "Tired of working solo from your apartment or hotel room? "
                    "Let’s swap the isolation for inspiration! Join us for a productive "
                    "day of co-working followed by a casual networking mixer. Whether "
                    "you're a freelancer, remote worker, or digital entrepreneur, this "
                    "is your chance to connect with like-minded people and build real "
                    "relationships. Bring your laptop, your ideas, and your best self."
                ),
                "location": "Dabouk, Amman",
                "category": "social",
                "price": Decimal("30.00"),
                "cover": "event-meetup.png",
                "capacity": 30,
                "starts_offset_days": 2,
            },
            {
                "title": "Friends Forever Party.",
                "description": (
                    "Join us for a special night dedicated to celebrating the bond that "
                    "never fades. Good food, old stories, and the best company await. "
                    "Catch up with friends, make new memories, and dance the night away."
                ),
                "location": "Dabouk, Amman",
                "category": "social",
                "price": Decimal("30.00"),
                "cover": "event-party.png",
                "capacity": 30,
                "starts_offset_days": 5,
            },
        ]

        events = []
        for spec in event_specs:
            cover_key = _upload_cover(
                prefix=settings.EVENT_COVER_KEY_PREFIX,
                uploader_id=founder.id,
                filename=spec["cover"],
            )
            starts = now + timedelta(days=spec["starts_offset_days"], hours=18)
            ends = starts + timedelta(hours=3)
            existing = (
                Event.all_objects.filter(
                    community_id=community.id,
                    title=spec["title"],
                    is_cancelled=False,
                )
                .order_by("starts_at")
                .first()
            )
            if existing is not None:
                existing.description = spec["description"]
                existing.location = spec["location"]
                existing.cover_image_key = cover_key
                existing.starts_at = starts
                existing.ends_at = ends
                existing.price = spec["price"]
                existing.category = spec["category"]
                existing.capacity = spec["capacity"]
                existing.save()
                events.append(existing)
            else:
                event = create_event(
                    creator=founder,
                    community=community,
                    title=spec["title"],
                    description=spec["description"],
                    location=spec["location"],
                    starts_at=starts,
                    ends_at=ends,
                    price=spec["price"],
                    category=spec["category"],
                    capacity=spec["capacity"],
                    cover_image_key=cover_key,
                )
                events.append(event)

        # Give demo users gathering eligibility via attendance credit (scan path
        # still works separately when tickets are checked in on event day).
        for user in (member, guest, founder):
            user.gathering_attendance_credit = max(
                user.gathering_attendance_credit or 0,
                3 if user.role == User.Role.NON_MEMBER else 1,
            )
            user.save(update_fields=["gathering_attendance_credit", "updated_at"])

        for user in (member, guest, founder):
            for event in events:
                try:
                    create_event_ticket(event=event, user=user)
                except Exception:
                    pass

        # Mobile Explore/Home design gatherings (titles, copy, cover assets).
        # Upsert by title so re-seeding refreshes covers/descriptions without dupes.
        gathering_specs = [
            {
                "title": "Dubai Expat Mixer – July Edition",
                "description": DEFAULT_GATHERING_DESCRIPTION,
                "area": "Amman",
                "exact_location": AMMAN_TEST_EXACT_LOCATION,
                "map_link": AMMAN_TEST_MAP_LINK,
                "cover": "gathering-mixer.png",
                "max_attendees": 20,
                "starts_offset_days": 1,
                "creator": founder,
                "fill_joins": True,
            },
            {
                "title": "Sunset Rooftop Hang",
                "description": (
                    "Soft drinks, skyline views, and easy sunset conversation. "
                    "A small rooftop hang for Amman's expat community — meet new "
                    "faces and unwind before the week starts. Exact pin unlocks "
                    "once you join so we can keep the vibe intimate."
                ),
                "area": "Amman",
                "exact_location": AMMAN_TEST_EXACT_LOCATION,
                "map_link": AMMAN_TEST_MAP_LINK,
                "cover": "gathering-iftar.png",
                "max_attendees": 20,
                "starts_offset_days": 4,
                "creator": founder,
                "fill_joins": True,
            },
            {
                "title": "Ramadan Iftar Gathering",
                "description": (
                    "Shared iftar table for Amman's community — bring a dish if "
                    "you can. Meet new faces, share stories, and break fast "
                    "together. Exact venue unlocks after you join."
                ),
                "area": "Amman",
                "exact_location": AMMAN_TEST_EXACT_LOCATION,
                "map_link": AMMAN_TEST_MAP_LINK,
                "cover": "gathering-iftar.png",
                "max_attendees": 20,
                "starts_offset_days": 8,
                "creator": member,
                "fill_joins": True,
            },
            {
                "title": "Board Games Night",
                "description": (
                    "Casual board games night for strategy lovers and beginners "
                    "alike. Bring a favorite game or try something new with the "
                    "group. Exact venue unlocks after you join."
                ),
                "area": "Amman",
                "exact_location": AMMAN_TEST_EXACT_LOCATION,
                "map_link": AMMAN_TEST_MAP_LINK,
                "cover": "gathering-games.png",
                "max_attendees": 20,
                "starts_offset_days": 3,
                "creator": founder,
                "fill_joins": True,
            },
            {
                "title": "Neighborhood Coffee Meetup",
                "description": DEFAULT_GATHERING_DESCRIPTION,
                "area": "Amman",
                "exact_location": AMMAN_TEST_EXACT_LOCATION,
                "map_link": AMMAN_TEST_MAP_LINK,
                "cover": "gathering-iftar.png",
                "max_attendees": 20,
                "starts_offset_days": 2,
                "creator": guest,
                "fill_joins": False,
            },
        ]

        design_titles = {spec["title"] for spec in gathering_specs}
        Gathering.all_objects.filter(
            community_id=community.id,
            is_cancelled=False,
        ).exclude(title__in=design_titles).update(is_cancelled=True)

        gatherings = []
        for spec in gathering_specs:
            creator = spec["creator"]
            cover_key = _upload_cover(
                prefix=settings.GATHERING_COVER_KEY_PREFIX,
                uploader_id=creator.id,
                filename=spec["cover"],
            )
            starts = now + timedelta(days=spec["starts_offset_days"], hours=18)
            description = (spec.get("description") or "").strip() or DEFAULT_GATHERING_DESCRIPTION
            existing = (
                Gathering.all_objects.filter(
                    community_id=community.id,
                    title=spec["title"],
                    is_cancelled=False,
                )
                .order_by("starts_at")
                .first()
            )
            if existing is not None:
                existing.description = description
                existing.area = spec["area"]
                existing.exact_location = spec["exact_location"]
                existing.map_link = spec.get("map_link") or ""
                existing.cover_image_key = cover_key
                existing.starts_at = starts
                existing.ends_at = starts + timedelta(hours=2)
                existing.max_attendees = spec["max_attendees"]
                existing.save()
                gathering = existing
            else:
                gathering = create_gathering(
                    creator=creator,
                    community=community,
                    title=spec["title"],
                    description=description,
                    area=spec["area"],
                    exact_location=spec["exact_location"],
                    map_link=spec.get("map_link") or "",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=2),
                    max_attendees=spec["max_attendees"],
                    cover_image_key=cover_key,
                )
            gatherings.append((gathering, spec))

        # Social proof joins (skip creator already joined). Capacity demo fills up.
        for gathering, spec in gatherings:
            if not spec.get("fill_joins"):
                continue
            for user in (member, guest, founder):
                if user.id == gathering.creator_id:
                    continue
                try:
                    join_gathering(
                        gathering_id=gathering.id,
                        community_id=gathering.community_id,
                        user=user,
                    )
                except Exception:
                    if spec.get("fill_to_capacity"):
                        break
                    pass

        # City-wide guidebook partner (visible to every community in this city).
        image_key = _upload_cover(
            prefix=settings.PARTNER_IMAGE_KEY_PREFIX,
            uploader_id=founder.id,
            filename="partner-noodle.jpg",
        )
        cover_key = _upload_cover(
            prefix=settings.PARTNER_IMAGE_KEY_PREFIX,
            uploader_id=founder.id,
            filename="partner-detail-hero.jpg",
        )
        map_key = _upload_cover(
            prefix=settings.PARTNER_IMAGE_KEY_PREFIX,
            uploader_id=founder.id,
            filename="map-preview.png",
        )
        partner = upsert_partner_by_name(
            city_id=community.city_id,
            name="The Noodle House",
            scope=PartnerScope.CITY_WIDE,
            category=PartnerCategory.RESTAURANT,
            area="DIFC",
            short_description=NOODLE_HOUSE_SHORT,
            description=NOODLE_HOUSE_FULL,
            discount_percent=15,
            rating=Decimal("4.7"),
            address="Gate Village, Building 4, DIFC, Dubai",
            hours_label="Open today",
            hours_range="11:00 AM – 11:00 PM",
            website="thenoodlehouse.com",
            website_url="https://thenoodlehouse.com",
            maps_url="https://maps.google.com/?q=The+Noodle+House+DIFC",
            image_key=image_key,
            cover_image_key=cover_key,
            map_image_key=map_key,
            is_active=True,
            sort_order=0,
        )

        self.stdout.write(self.style.SUCCESS("Demo content ready."))
        self.stdout.write(f"Community: {community.name} ({community.id})")
        self.stdout.write(
            f"Events: {len(events)} | Gatherings: {len(gatherings)} | "
            f"Partners: 1 ({partner.name})"
        )
        self.stdout.write("")
        self.stdout.write("Login accounts (password for all):")
        self.stdout.write(f"  {DEMO_PASSWORD}")
        self.stdout.write("  founder@mixedmiles.com  — city founder (eligible)")
        self.stdout.write("  member@mixedmiles.com   — member (eligible)")
        self.stdout.write("  ali@mixedmiles.com       — member (eligible)")
        self.stdout.write(
            "  newcomer@mixedmiles.com — non-member (locked until 3 events)"
        )
