from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf),
    path("auth/login/", views.manager_login),
    path("auth/logout/", views.manager_logout),
    path("auth/session/", views.manager_session),
    path("stay-requests/", views.create_stay_request),
    path("management/stay-requests/", views.list_stay_requests),
    path("management/stay-requests/<int:request_id>/decision/", views.decide_stay_request),
]
