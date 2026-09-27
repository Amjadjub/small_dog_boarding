from datetime import date

from rest_framework import serializers

from .models import StayRequest


class PublicStayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StayRequest
        fields = ["id", "contact_name", "phone", "email", "dog_name", "dog_age", "dog_sex", "care_notes", "service", "start_date", "end_date", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_start_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("תאריך ההתחלה לא יכול להיות בעבר.")
        return value

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "תאריך הסיום חייב להיות זהה לתאריך ההתחלה או מאוחר ממנו."})
        return attrs


class AdminStayRequestSerializer(serializers.ModelSerializer):
    service_label = serializers.CharField(source="get_service_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)

    class Meta:
        model = StayRequest
        fields = "__all__"
