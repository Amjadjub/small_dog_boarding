from django.conf import settings
from django.db import models


class OwnerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owner_profile")
    phone = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Dog(models.Model):
    class Sex(models.TextChoices):
        FEMALE = "female", "נקבה"
        MALE = "male", "זכר"
        UNKNOWN = "unknown", "לא צוין"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dogs")
    name = models.CharField(max_length=80)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, choices=Sex.choices, default=Sex.UNKNOWN)
    feeding_instructions = models.TextField(blank=True, max_length=2000)
    allergies = models.TextField(blank=True, max_length=2000)
    medications = models.TextField(blank=True, max_length=2000)
    behavior_notes = models.TextField(blank=True, max_length=2000)
    veterinarian_name = models.CharField(max_length=120, blank=True)
    veterinarian_phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class EmergencyContact(models.Model):
    dog = models.OneToOneField(Dog, on_delete=models.CASCADE, related_name="emergency_contact")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    relationship = models.CharField(max_length=80, blank=True)


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
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="stay_requests")
    dog = models.ForeignKey(Dog, null=True, blank=True, on_delete=models.SET_NULL, related_name="stay_requests")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="request_status_created_idx")]

    def __str__(self):
        return f"{self.dog_name} — {self.get_service_display()}"


class Booking(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "עתידית"
        ACTIVE = "active", "פעילה"
        COMPLETED = "completed", "הסתיימה"
        CANCELED = "canceled", "בוטלה"

    request = models.OneToOneField(StayRequest, on_delete=models.PROTECT, related_name="booking")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    dog = models.ForeignKey(Dog, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    service = models.CharField(max_length=20, choices=StayRequest.Service.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPCOMING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-id"]


class StayUpdate(models.Model):
    class Kind(models.TextChoices):
        GENERAL = "general", "עדכון כללי"
        MEAL = "meal", "אוכל ושתייה"
        WALK = "walk", "טיול"
        MEDICATION = "medication", "תרופה"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="updates")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.GENERAL)
    message = models.TextField(max_length=2000)
    visible_to_owner = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stay_updates")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class InternalCareNote(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name="internal_notes")
    note = models.TextField(max_length=2000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="internal_care_notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Notification(models.Model):
    class Kind(models.TextChoices):
        REQUEST_RECEIVED = "request_received", "בקשה התקבלה"
        REQUEST_APPROVED = "request_approved", "בקשה אושרה"
        REQUEST_REJECTED = "request_rejected", "בקשה נדחתה"
        STAY_UPDATE = "stay_update", "עדכון מהשהות"
        ACCOUNT_VERIFIED = "account_verified", "החשבון אומת"
        REQUEST_LINKED = "request_linked", "בקשה קושרה לחשבון"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=160)
    message = models.TextField(max_length=2000)
    stay_request = models.ForeignKey(StayRequest, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    booking = models.ForeignKey(Booking, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "read_at", "created_at"], name="notification_inbox_idx")]
