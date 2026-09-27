from django.conf import settings
from django.db import models


class StayRequest(models.Model):
    class Service(models.TextChoices):
        OVERNIGHT = "overnight", "לינה"
        DAYCARE = "daycare", "אירוח יומי"
        TRANSPORT = "transport", "איסוף והחזרה"

    class Status(models.TextChoices):
        PENDING = "pending", "ממתינה"
        APPROVED = "approved", "אושרה"
        REJECTED = "rejected", "נדחתה"

    class DogSex(models.TextChoices):
        FEMALE = "female", "נקבה"
        MALE = "male", "זכר"
        UNKNOWN = "unknown", "לא צוין"

    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    dog_name = models.CharField(max_length=80)
    dog_age = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    dog_sex = models.CharField(max_length=10, choices=DogSex.choices, default=DogSex.UNKNOWN)
    care_notes = models.TextField(blank=True, max_length=2000)
    service = models.CharField(max_length=20, choices=Service.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_stay_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="request_status_created_idx")]

    def __str__(self):
        return f"{self.dog_name} — {self.get_service_display()}"
