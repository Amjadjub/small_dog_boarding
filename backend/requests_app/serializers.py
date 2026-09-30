from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Booking, Dog, EmergencyContact, InternalCareNote, OwnerProfile, StayRequest, StayUpdate


class OwnerRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12)
    full_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=30)

    def validate_email(self, value):
        email = value.strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists() or get_user_model().objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError("כבר קיים חשבון עם כתובת הדוא״ל הזאת.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        User = get_user_model()
        full_name = validated_data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        user = User.objects.create_user(username=validated_data["email"], email=validated_data["email"], password=validated_data["password"], first_name=first_name, last_name=last_name)
        OwnerProfile.objects.create(user=user, phone=validated_data["phone"])
        return user


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["name", "phone", "relationship"]


class DogSerializer(serializers.ModelSerializer):
    emergency_contact = EmergencyContactSerializer(required=False, allow_null=True)

    class Meta:
        model = Dog
        fields = ["id", "name", "birth_date", "sex", "feeding_instructions", "allergies", "medications", "behavior_notes", "veterinarian_name", "veterinarian_phone", "emergency_contact", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        contact = validated_data.pop("emergency_contact", None)
        dog = Dog.objects.create(owner=self.context["request"].user, **validated_data)
        if contact:
            EmergencyContact.objects.create(dog=dog, **contact)
        return dog

    def update(self, instance, validated_data):
        contact = validated_data.pop("emergency_contact", None)
        instance = super().update(instance, validated_data)
        if contact is not None:
            EmergencyContact.objects.update_or_create(dog=instance, defaults=contact)
        return instance


class PublicStayRequestSerializer(serializers.ModelSerializer):
    dog_id = serializers.PrimaryKeyRelatedField(source="dog", queryset=Dog.objects.all(), required=False, allow_null=True, write_only=True)

    class Meta:
        model = StayRequest
        fields = ["id", "contact_name", "phone", "email", "dog_name", "dog_age", "dog_sex", "care_notes", "service", "start_date", "end_date", "status", "created_at", "dog_id"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_start_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("תאריך ההתחלה לא יכול להיות בעבר.")
        return value

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "תאריך הסיום חייב להיות זהה לתאריך ההתחלה או מאוחר ממנו."})
        user = self.context["request"].user
        dog = attrs.get("dog")
        if dog and (not user.is_authenticated or dog.owner_id != user.id):
            raise serializers.ValidationError({"dog_id": "אין הרשאה להשתמש בכרטיס הכלב הזה."})
        return attrs


class AdminStayRequestSerializer(serializers.ModelSerializer):
    service_label = serializers.CharField(source="get_service_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True, allow_null=True)

    class Meta:
        model = StayRequest
        fields = "__all__"


class OwnerStayRequestSerializer(serializers.ModelSerializer):
    service_label = serializers.CharField(source="get_service_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = StayRequest
        fields = ["id", "dog", "dog_name", "service", "service_label", "start_date", "end_date", "status", "status_label", "created_at", "reviewed_at"]


class StayUpdateSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = StayUpdate
        fields = ["id", "kind", "kind_label", "message", "visible_to_owner", "created_by_name", "created_at"]
        read_only_fields = ["id", "created_by_name", "created_at"]


class OwnerBookingSerializer(serializers.ModelSerializer):
    dog_name = serializers.CharField(source="dog.name", read_only=True, allow_null=True)
    service_label = serializers.CharField(source="get_service_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    updates = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ["id", "service", "service_label", "start_date", "end_date", "status", "status_label", "dog", "dog_name", "updates"]

    def get_updates(self, obj):
        return StayUpdateSerializer(obj.updates.filter(visible_to_owner=True), many=True).data


class AdminBookingSerializer(serializers.ModelSerializer):
    dog_name = serializers.CharField(source="dog.name", read_only=True, allow_null=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True, allow_null=True)
    service_label = serializers.CharField(source="get_service_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    updates = StayUpdateSerializer(many=True, read_only=True)
    internal_notes = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ["id", "request", "owner", "owner_email", "dog", "dog_name", "service", "service_label", "start_date", "end_date", "status", "status_label", "updates", "internal_notes"]

    def get_internal_notes(self, obj):
        if not obj.dog_id:
            return []
        return InternalCareNoteSerializer(obj.dog.internal_notes.all(), many=True).data


class InternalCareNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = InternalCareNote
        fields = ["id", "dog", "note", "created_by_name", "created_at"]
        read_only_fields = ["id", "created_by_name", "created_at"]
