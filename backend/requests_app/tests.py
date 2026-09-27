from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import StayRequest


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
