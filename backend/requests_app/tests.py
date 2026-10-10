from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import Booking, Dog, Notification, OwnerProfile, StayRequest, StayUpdate
from .services import create_verification_token


def payload(**overrides):
    values = {
        "contact_name": "נועה ישראלי",
        "phone": "050-1234567",
        "email": "noa@example.com",
        "dog_name": "לולה",
        "dog_age": "3.5",
        "dog_sex": "female",
        "care_notes": "רגישה לרעש",
        "service": "overnight",
        "start_date": str(date.today() + timedelta(days=2)),
        "end_date": str(date.today() + timedelta(days=4)),
    }
    values.update(overrides)
    return values


class StayRequestFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user("manager1", password="A-very-strong-pass-123!", is_staff=True)
        self.other_manager = User.objects.create_user("manager2", password="Another-strong-pass-456!", is_staff=True)
        self.owner = User.objects.create_user("owner", password="Owner-strong-pass-789!")
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_client(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.get("/api/auth/csrf/")
        client.credentials(HTTP_X_CSRFTOKEN=response.data["csrfToken"])
        return client

    def test_public_request_is_created_pending(self):
        client = self.csrf_client()
        response = client.post("/api/stay-requests/", payload(), format="json")
        self.assertEqual(response.status_code, 201)
        saved = StayRequest.objects.get()
        self.assertEqual(saved.status, StayRequest.Status.PENDING)
        self.assertIsNone(saved.reviewed_by)

    def test_public_request_requires_csrf(self):
        response = self.client.post("/api/stay-requests/", payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(StayRequest.objects.count(), 0)

    def test_rejects_invalid_date_range_and_past_start(self):
        client = self.csrf_client()
        response = client.post("/api/stay-requests/", payload(end_date=str(date.today())), format="json")
        self.assertEqual(response.status_code, 400)
        response = client.post("/api/stay-requests/", payload(start_date=str(date.today() - timedelta(days=1))), format="json")
        self.assertEqual(response.status_code, 400)

    def test_non_staff_cannot_list_or_decide(self):
        stay_request = StayRequest.objects.create(**payload())
        client = APIClient()
        self.assertEqual(client.get("/api/management/stay-requests/").status_code, 403)
        client.force_authenticate(self.owner)
        self.assertEqual(client.get("/api/management/stay-requests/").status_code, 403)
        self.assertEqual(client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "approved"}).status_code, 403)

    def test_manager_can_approve_and_audit_is_recorded(self):
        stay_request = StayRequest.objects.create(**payload())
        client = APIClient()
        client.force_authenticate(self.manager)
        response = client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "approved"}, format="json")
        self.assertEqual(response.status_code, 200)
        stay_request.refresh_from_db()
        self.assertEqual(stay_request.status, StayRequest.Status.APPROVED)
        self.assertEqual(stay_request.reviewed_by, self.manager)
        self.assertIsNotNone(stay_request.reviewed_at)
        self.assertEqual(Booking.objects.filter(request=stay_request).count(), 1)

    def test_manager_can_reject_and_second_decision_conflicts(self):
        stay_request = StayRequest.objects.create(**payload())
        client = APIClient()
        client.force_authenticate(self.manager)
        first = client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "rejected"}, format="json")
        self.assertEqual(first.status_code, 200)
        client.force_authenticate(self.other_manager)
        second = client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "approved"}, format="json")
        self.assertEqual(second.status_code, 409)
        stay_request.refresh_from_db()
        self.assertEqual(stay_request.status, StayRequest.Status.REJECTED)
        self.assertEqual(stay_request.reviewed_by, self.manager)

    def test_login_rejects_regular_user_and_accepts_manager(self):
        client = self.csrf_client()
        regular = client.post("/api/auth/login/", {"username": "owner", "password": "Owner-strong-pass-789!"}, format="json")
        self.assertEqual(regular.status_code, 401)
        manager = client.post("/api/auth/login/", {"username": "manager1", "password": "A-very-strong-pass-123!"}, format="json")
        self.assertEqual(manager.status_code, 200)


class OwnerPortalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user("manager", password="Manager-strong-pass-123!", is_staff=True)
        self.owner = User.objects.create_user("owner@example.com", email="owner@example.com", password="Owner-strong-pass-123!", first_name="נועה")
        OwnerProfile.objects.create(user=self.owner, phone="0501234567", email_verified_at=timezone.now())
        self.other_owner = User.objects.create_user("other@example.com", email="other@example.com", password="Other-strong-pass-123!")
        OwnerProfile.objects.create(user=self.other_owner, phone="0507654321", email_verified_at=timezone.now())
        self.dog = Dog.objects.create(owner=self.owner, name="לולה", allergies="רגישה לעוף")

    def csrf_client(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.get("/api/auth/csrf/")
        client.credentials(HTTP_X_CSRFTOKEN=response.data["csrfToken"])
        return client

    def test_owner_registration_requires_email_verification(self):
        client = self.csrf_client()
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post("/api/owner/register/", {"email": "new@example.com", "password": "New-owner-pass-987!", "full_name": "דנה ישראלי", "phone": "0520000000"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(OwnerProfile.objects.filter(user__email="new@example.com").exists())
        self.assertEqual(client.get("/api/owner/session/").status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

        user = get_user_model().objects.get(email="new@example.com")
        verified = client.post("/api/owner/verify-email/", {"token": create_verification_token(user)}, format="json")
        self.assertEqual(verified.status_code, 200)
        user.owner_profile.refresh_from_db()
        self.assertIsNotNone(user.owner_profile.email_verified_at)

    def test_owner_can_only_read_and_edit_their_own_dogs(self):
        client = APIClient()
        client.force_authenticate(self.other_owner)
        self.assertEqual(client.get(f"/api/owner/dogs/{self.dog.id}/").status_code, 404)
        self.assertEqual(client.patch(f"/api/owner/dogs/{self.dog.id}/", {"name": "שם אחר"}, format="json").status_code, 404)
        self.dog.refresh_from_db()
        self.assertEqual(self.dog.name, "לולה")

    def test_linked_request_approval_creates_owner_booking_once(self):
        stay_request = StayRequest.objects.create(owner=self.owner, dog=self.dog, **payload(email=self.owner.email))
        client = APIClient()
        client.force_authenticate(self.manager)
        first = client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "approved"}, format="json")
        second = client.post(f"/api/management/stay-requests/{stay_request.id}/decision/", {"decision": "approved"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        booking = Booking.objects.get(request=stay_request)
        self.assertEqual(booking.owner, self.owner)
        self.assertEqual(booking.dog, self.dog)

    def test_owner_dashboard_hides_private_updates_and_other_bookings(self):
        own_request = StayRequest.objects.create(owner=self.owner, dog=self.dog, status="approved", **payload(email=self.owner.email))
        own_booking = Booking.objects.create(request=own_request, owner=self.owner, dog=self.dog, service=own_request.service, start_date=own_request.start_date, end_date=own_request.end_date, status="active")
        StayUpdate.objects.create(booking=own_booking, kind="walk", message="טיול נעים", visible_to_owner=True, created_by=self.manager)
        StayUpdate.objects.create(booking=own_booking, kind="general", message="הערה פנימית", visible_to_owner=False, created_by=self.manager)
        other_dog = Dog.objects.create(owner=self.other_owner, name="מוקה")
        other_request = StayRequest.objects.create(owner=self.other_owner, dog=other_dog, status="approved", **payload(email=self.other_owner.email, dog_name="מוקה"))
        Booking.objects.create(request=other_request, owner=self.other_owner, dog=other_dog, service=other_request.service, start_date=other_request.start_date, end_date=other_request.end_date)

        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.get("/api/owner/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["bookings"]), 1)
        messages = [item["message"] for item in response.data["bookings"][0]["updates"]]
        self.assertEqual(messages, ["טיול נעים"])

    def test_owner_cannot_link_another_owners_dog_to_request(self):
        client = APIClient()
        client.force_authenticate(self.other_owner)
        response = client.post("/api/stay-requests/", payload(dog_id=self.dog.id, email=self.other_owner.email), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StayRequest.objects.count(), 0)

    def test_verification_links_matching_guest_requests_and_booking(self):
        user = get_user_model().objects.create_user("claim@example.com", email="claim@example.com", password="Claim-owner-pass-123!")
        OwnerProfile.objects.create(user=user, phone="0500000000")
        stay_request = StayRequest.objects.create(status="approved", **payload(email="claim@example.com"))
        booking = Booking.objects.create(request=stay_request, service=stay_request.service, start_date=stay_request.start_date, end_date=stay_request.end_date)
        client = self.csrf_client()
        response = client.post("/api/owner/verify-email/", {"token": create_verification_token(user)}, format="json")
        self.assertEqual(response.status_code, 200)
        stay_request.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(stay_request.owner, user)
        self.assertEqual(booking.owner, user)
        self.assertTrue(Notification.objects.filter(recipient=user, kind="request_linked").exists())

    def test_password_reset_response_is_generic_and_token_is_single_use(self):
        client = self.csrf_client()
        existing = client.post("/api/owner/password-reset/", {"email": self.owner.email}, format="json")
        missing = client.post("/api/owner/password-reset/", {"email": "missing@example.com"}, format="json")
        self.assertEqual(existing.data, missing.data)
        uid = urlsafe_base64_encode(force_bytes(self.owner.pk))
        token = default_token_generator.make_token(self.owner)
        first = client.post("/api/owner/password-reset/confirm/", {"uid": uid, "token": token, "password": "Changed-owner-pass-987!"}, format="json")
        second = client.post("/api/owner/password-reset/confirm/", {"uid": uid, "token": token, "password": "Another-owner-pass-987!"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    def test_rate_limit_blocks_repeated_login_attempts(self):
        cache.clear()
        client = self.csrf_client()
        responses = [client.post("/api/owner/login/", {"email": "nobody@example.com", "password": "wrong"}, format="json") for _ in range(11)]
        self.assertEqual(responses[-1].status_code, 429)

    def test_notifications_are_private_to_recipient(self):
        own = Notification.objects.create(recipient=self.owner, kind="account_verified", title="שלי", message="פרטי")
        other = Notification.objects.create(recipient=self.other_owner, kind="account_verified", title="לא שלי", message="פרטי")
        client = APIClient()
        client.force_authenticate(self.owner)
        listed = client.get("/api/notifications/")
        self.assertEqual([item["id"] for item in listed.data], [own.id])
        self.assertEqual(client.post(f"/api/notifications/{other.id}/read/").status_code, 404)
        self.assertEqual(client.post(f"/api/notifications/{own.id}/read/").status_code, 200)

    def test_unverified_owner_cannot_access_private_portal(self):
        user = get_user_model().objects.create_user("unverified@example.com", email="unverified@example.com", password="Unverified-pass-123!")
        OwnerProfile.objects.create(user=user, phone="0500000001")
        client = APIClient()
        client.force_authenticate(user)
        self.assertEqual(client.get("/api/owner/dashboard/").status_code, 403)
