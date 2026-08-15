from django.urls import path

from apps.accounts.didit.views import DiditWebhookView
from apps.accounts.profile_views import (
    IdentityVerificationStartView,
    IdentityVerificationStatusView,
    MemberChangePasswordView,
    MembershipActivateView,
    MyProfileView,
    ProfileOnboardingCompleteView,
    ProfilePhotoConfirmView,
    ProfilePhotoDeleteView,
    ProfilePhotoPresignView,
    UserProfileView,
)
from apps.accounts.views import (
    AdminLoginView,
    DashboardChangePasswordView,
    DashboardLoginView,
    DashboardProfileUpdateView,
    LoginView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshTokenView,
    RegisterView,
    RegistrationStatusView,
    ResendEmailOTPView,
    StartVerificationView,
    VerifyEmailOTPView,
    VerifyTestPageView,
)
from apps.accounts.admin_user_views import AdminUserDetailView, AdminUserListView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "register/verify-email/",
        VerifyEmailOTPView.as_view(),
        name="register-verify-email",
    ),
    path(
        "register/resend-email-otp/",
        ResendEmailOTPView.as_view(),
        name="register-resend-email-otp",
    ),
    path(
        "register/status/",
        RegistrationStatusView.as_view(),
        name="register-status",
    ),
    path(
        "register/verification/",
        StartVerificationView.as_view(),
        name="register-verification",
    ),
    path("webhooks/didit/", DiditWebhookView.as_view(), name="didit-webhook"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/admin/login/", AdminLoginView.as_view(), name="auth-admin-login"),
    path(
        "auth/dashboard/login/",
        DashboardLoginView.as_view(),
        name="auth-dashboard-login",
    ),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("me/", MeView.as_view(), name="me"),
    path(
        "me/change-password/",
        DashboardChangePasswordView.as_view(),
        name="dashboard-change-password",
    ),
    path(
        "me/profile-settings/",
        DashboardProfileUpdateView.as_view(),
        name="dashboard-profile-update",
    ),
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "users/<uuid:user_id>/",
        AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path("me/profile/", MyProfileView.as_view(), name="me-profile"),
    path(
        "me/password/",
        MemberChangePasswordView.as_view(),
        name="me-change-password",
    ),
    path(
        "me/identity/verify/",
        IdentityVerificationStartView.as_view(),
        name="me-identity-verify",
    ),
    path(
        "me/identity/",
        IdentityVerificationStatusView.as_view(),
        name="me-identity-status",
    ),
    path(
        "me/membership/activate/",
        MembershipActivateView.as_view(),
        name="me-membership-activate",
    ),
    path(
        "me/profile/onboarding/complete/",
        ProfileOnboardingCompleteView.as_view(),
        name="me-profile-onboarding-complete",
    ),
    path(
        "me/profile/photo/presign/",
        ProfilePhotoPresignView.as_view(),
        name="me-profile-photo-presign",
    ),
    path(
        "me/profile/photo/confirm/",
        ProfilePhotoConfirmView.as_view(),
        name="me-profile-photo-confirm",
    ),
    path(
        "me/profile/photo/",
        ProfilePhotoDeleteView.as_view(),
        name="me-profile-photo-delete",
    ),
    path(
        "users/<uuid:user_id>/profile/",
        UserProfileView.as_view(),
        name="user-profile",
    ),
    path("verify-test/", VerifyTestPageView.as_view(), name="verify-test"),
]
