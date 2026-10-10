from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf),
    path("owner/register/", views.owner_register),
    path("owner/verify-email/", views.verify_email),
    path("owner/resend-verification/", views.resend_verification),
    path("owner/password-reset/", views.request_password_reset),
    path("owner/password-reset/confirm/", views.confirm_password_reset),
    path("owner/login/", views.owner_login),
    path("owner/logout/", views.owner_logout),
    path("owner/session/", views.owner_session),
    path("owner/dashboard/", views.owner_dashboard),
    path("owner/dogs/", views.owner_dogs),
    path("owner/dogs/<int:dog_id>/", views.owner_dog_detail),
    path("notifications/", views.notification_list),
    path("notifications/<int:notification_id>/read/", views.notification_read),
    path("auth/login/", views.manager_login),
    path("auth/logout/", views.manager_logout),
    path("auth/session/", views.manager_session),
    path("stay-requests/", views.create_stay_request),
    path("management/stay-requests/", views.list_stay_requests),
    path("management/stay-requests/<int:request_id>/decision/", views.decide_stay_request),
    path("management/stay-requests/<int:request_id>/link-owner/", views.link_request_owner),
    path("management/bookings/", views.list_bookings),
    path("management/bookings/<int:booking_id>/status/", views.update_booking_status),
    path("management/bookings/<int:booking_id>/updates/", views.create_stay_update),
    path("management/dogs/<int:dog_id>/internal-notes/", views.create_internal_note),
]
