from django.contrib import admin

from apps.accounts.models import CommunityMembership, IdentityVerificationSession, User, UserFollow
from apps.accounts.services import apply_user_role


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "full_name",
        "role",
        "resident_type",
        "verification_status",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = (
        "role",
        "resident_type",
        "verification_status",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    search_fields = ("email", "full_name", "official_full_name", "phone_number")
    readonly_fields = ("created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "official_full_name",
                    "bio",
                    "location",
                    "profile_photo_key",
                    "profile_onboarding_completed",
                    "phone_number",
                    "nationality_code",
                    "residence_country_code",
                    "date_of_birth",
                    "document_expiration_date",
                    "age",
                    "gender",
                ),
            },
        ),
        (
            "Access",
            {
                "fields": (
                    "role",
                    "resident_type",
                    "verification_status",
                    "registration_step",
                    "manual_verification_approved",
                    "active_community_id",
                    "gathering_attendance_credit",
                    "bypass_gathering_attendance",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
                "description": (
                    "Product access is controlled by Role (and DRF permission classes). "
                    "Only superusers may use Django admin; Groups/Permissions are not used. "
                    "Gathering gate: Members need 1 scanned event, Non-Members need 3. "
                    "Use attendance credit or bypass for demos."
                ),
            },
        ),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(["role", "is_staff", "is_superuser"])
        return readonly

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.is_staff = False
            obj.is_superuser = False

        if (
            obj.resident_type == User.ResidentType.LOCAL
            and obj.verification_status == User.VerificationStatus.VERIFIED
        ):
            obj.manual_verification_approved = True
            obj.registration_step = 2
        elif obj.resident_type == User.ResidentType.LOCAL and change:
            previous = User.objects.filter(pk=obj.pk).first()
            if previous and previous.verification_status == User.VerificationStatus.VERIFIED:
                if obj.verification_status != User.VerificationStatus.VERIFIED:
                    obj.manual_verification_approved = False
                    if obj.registration_step < 3:
                        obj.registration_step = 3

        # Persist non-role fields first, then sync role flags / clear Django perms.
        super().save_model(request, obj, form, change)
        apply_user_role(obj, obj.role)


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "community_id", "city_id", "role")
    list_filter = ("role",)
    search_fields = ("user__email",)


admin.site.register(IdentityVerificationSession)


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__email", "following__email")
    raw_id_fields = ("follower", "following")
