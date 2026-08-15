# Mixed Miles — Backend Implementation Roadmap

Build order is dependency-driven. Do NOT jump ahead — each milestone assumes the
previous ones exist. FR references map to `docs/SRS.md`.

> Chat is deferred to MVP Phase 2. White Label is NOT built now, but its data model
> hooks (community_id / city_id) MUST exist from Milestone 1.

---

## Milestone 0 — Project foundation
Goal: a running, stateless skeleton with tooling and CI.

- [x] Django 5 + DRF project; `settings/` split (base/dev/prod)
- [x] Postgres + Redis via docker-compose
- [x] Celery + Celery Beat wired to Redis; a no-op sample task runs
- [x] drf-spectacular at /api/docs/ (Swagger) + /api/redoc/
- [x] Tooling: black, ruff, mypy, pytest + pytest-django, factory_boy
- [x] CI pipeline runs lint + type-check + tests
- [x] Health-check endpoint `/api/v1/health/`
- [x] Structured logging + Sentry hook

## Milestone 1 — Tenancy foundation (do this before ANY feature)
Goal: multi-tenancy baked into the core so all later data inherits it.

- [x] `tenancy` app: `Country`, `City`, `Community` models
- [x] Community carries `city_id`, `type` (general/nationality/interest), branding fields
- [x] Abstract base models: `TenantScoped` (community_id + city_id) and `CityScoped` (city_id only)
- [x] Tenant-aware default manager (auto-filters querysets)
- [x] Tenant-resolution middleware (from auth context / request)
- [x] Partner scope enum groundwork: `community | city_wide`
- [x] Tests: community A cannot read community B; city-shared visible across communities

## Milestone 2 — Accounts, auth & roles
Goal: identity and permission layer for all 5 actors. (FR 1–13, 93–106)

- [x] Custom User model (email login), Argon2 hashing
- [x] Registration: name, email, area, nationality, phone, password, ID/Passport upload
- [x] JWT auth (simplejwt): login, refresh, password reset via email (FR 3–6)
- [ ] Social sign-in: Google + Apple (FR 4)
- [x] Role model/enum: Admin, City Founder, Team Member, Member, Non-Member
- [x] DRF permission classes per role + object-level checks
- [x] PII handling for ID/passport: encrypted-at-rest storage, restricted access, retention policy
- [x] Profile: photo, bio, followers/following counts, membership status (FR 93–100)
- [ ] Follow/unfollow (FR 94–95); connect requests (FR 96)
- [ ] More Menu / Settings endpoints: account mgmt, notif prefs, deletion, logout (FR 104–106)

## Milestone 3 — Notifications infrastructure (cross-cutting)
Goal: build once, reuse everywhere. Many later features depend on it.

- [ ] Notification service abstraction (channel-agnostic)
- [ ] FCM + APNs push (device token registry)
- [ ] Email provider (SES/SendGrid) integration
- [ ] WhatsApp Business API integration
- [ ] All sends are async Celery tasks with idempotency + retry + dead-letter

## Milestone 4 — Membership, subscriptions & payments
Goal: money + membership lifecycle. (FR 8–11, 107–116; NFR 12)

- [ ] Payment gateway integration (decide provider first)
- [ ] Member subscription: monthly + annual, recurring billing (FR 107)
- [ ] Webhook-driven subscription state (never client-driven)
- [ ] Lifecycle via Celery Beat: renewal, expiry, 1-week grace, revocation (FR 109, 111–113)
- [ ] Payment receipts via email (FR 110); idempotency keys on all charges
- [ ] Payment methods: cards, Apple/Google Pay, cash-on-arrival (FR 115–116)
- [ ] Expat verification logic: auto-approve expat members, else pending → admin (FR 8–11)
- [ ] Membership QR code: user_id + server-signed token (FR 51–52)

## Milestone 5 — Events (attendee + founder side)
Goal: the core product loop. (FR 37–47, 160–169; Flows B & C)

- [ ] Event model (tenant-scoped) + CRUD for City Founders (FR 160–162)
- [ ] Edit restrictions: no price/location edits after creation (FR 161)
- [ ] Event browse/list/detail, filters by city/date/category (FR 37–40)
- [ ] Member instant join/purchase (FR 41); Non-Member join request flow (FR 42)
- [ ] City Founder accept/reject join requests (FR 167); attendee list (FR 166)
- [ ] Ticket generation: signed QR (user_id + event_id + tamper-proof token) (FR 45, 47)
- [ ] Async ticket delivery via WhatsApp + email + in-app within 60s (FR 43, 46, 168)
- [ ] Change/cancel push notifications to attendees (FR 163–164)
- [ ] Nationality breakdown per event (FR 169)
- [ ] My Tickets endpoint

## Milestone 6 — Guidebook & discount redemption
Goal: partner discounts via member QR. (FR 48–57; Flow A)

- [ ] Partner model with `scope` (community/city_wide) + CRUD (FR 157–159)
- [ ] Guidebook list/detail, filter by category/city (FR 48–50)
- [ ] Partner-side QR verification endpoint, server-side only (FR 53–55)
- [ ] Rate-limit scans in Redis: 10/min/user (NFR 11)
- [ ] Async redemption logging (timestamp, user, partner) (FR 56)
- [ ] Non-Member cannot redeem (FR 57)

## Milestone 7 — Social feed, posts & gatherings
Goal: engagement layer. (FR 17–38, 26–38)

- [ ] Posts: up to 5 images + caption, like, comment (single-level nesting) (FR 26–29, 19)
- [ ] Gatherings: create rules (Member ≥1 event, Non-Member ≥3 events), max 20 cap (FR 31–35)
- [ ] Atomic attendee cap enforcement; location hidden until joined (FR 34–35)
- [ ] Unified Home feed: posts + events + gatherings (+ store/property later) (FR 17, 24)
- [ ] Cursor pagination + Redis caching of feed pages (NFR 1, <2s)
- [ ] Activity history in profile (FR 25, 30, 100)

## Milestone 8 — City Founder dashboard
Goal: founder tooling + publish eligibility gate. (FR 157–185)

- [ ] Application flow: apply → Admin approval (FR 105)
- [x] City Founder web dashboard login + empty overview (role-gated)
- [ ] Eligibility gate: ≥10 partners, ≥2 speakers, ≥1 creator, 3 events/month; block publish until met
- [ ] Team management + minimum enforcement (≥2 speakers, ≥1 creator) (FR 170–174)
- [ ] Media Area: uploads via S3 presigned URLs, async transcoding, albums (FR 175–180)
- [ ] Community stats + revenue split per event (FR 181–182)
- [ ] Team-member read-only scoped access (FR 184–185)

## Milestone 9 — Admin dashboard
Goal: oversight + moderation (leverage Django admin heavily). (FR 130–156)

- [ ] Secure admin access + 2FA (FR 130–131)
- [x] Immutable audit log of all admin actions (FR 132) — list + filter in Settings
- [x] City Founder management: view/add/edit/deactivate/delete (FR 133–137) — `apps.founders`
- [ ] Member/user management: view/search/filter/edit/deactivate/delete (FR 138–140)
- [x] Member/user management: list all + delete with self/superadmin guards (FR 138–140 partial)
- [x] Member/user management: edit user role (syncs permissions via apply_user_role, audited)
- [x] City Founder applications: Google Sheets sync (12:00/18:00 UTC + manual) → DB cache, status workflow
- [ ] Event + content moderation (FR 141–147)
- [ ] Pending membership review queue (non-expat applicants) (FR 148)
- [ ] Partner management (FR 149)
- [ ] Analytics: KPIs, filters, trends, Excel export via async job on read replica (FR 150–153)

## Milestone 10 — Trust voting
Goal: post-event founder trust score. (FR 117–129)

- [ ] Post-event vote prompt to checked-in attendees, 2h after end (FR 117)
- [ ] Vote (Trusted/Not + optional comment), one per attendee, 48h window (FR 118–120)
- [ ] Celery Beat job: on window close, compute weighted moving average, persist (FR 121–123)
- [ ] Display score on profile; hide voter identities (FR 124, 127)
- [ ] Admin: score dashboard, flag >20pt drops, review comments (FR 125–126, 128)
- [ ] Min 40% (after 10 votes) to stay active → admin alert (FR 129)

## Milestone 11 — Non-functional hardening
- [ ] Load test toward 20k concurrent (NFR 5); tune indexes, caching, replicas
- [ ] Verify <500ms API, <2s feed/QR (NFR 1–3)
- [ ] Offline caching contract for tickets/profile (NFR 19)
- [ ] Automated daily backups (NFR 20); horizontal autoscaling config (NFR 25)
- [ ] Security pass: TLS, JWT everywhere, rate limits, PII encryption audit

---

# MVP Phase 2 (later)

## M12 — Store / marketplace
Products, offers (make/accept/counter/decline), listing limits, moderation (FR 63–84, 154–156).
Non-Member = 1 listing; Member = unlimited. Store cards appear in feed.

## M13 — Property rental
City-scoped listings, amenities, search/filter, contact owner (FR 58–62).
Housing is CityScoped (shared across communities in a city).

## M14 — Chat (moved here)
Django Channels + Redis. DM vs message-requests, image attachments, block,
unread badges, push on new message (FR 85–91).

## M15 — White Label activation
Expose the multi-tenancy already in the data model: admin creates/configures
communities, per-community branding, shared city assets, per-community revenue
reports, "Powered by Mixed Miles" attribution (White Label FR 1–10).