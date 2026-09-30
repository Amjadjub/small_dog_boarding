from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Dog, StayRequest
from .permissions import IsStaffManager
from .serializers import (
    AdminBookingSerializer,
    AdminStayRequestSerializer,
    DogSerializer,
    InternalCareNoteSerializer,
    OwnerBookingSerializer,
    OwnerRegistrationSerializer,
    OwnerStayRequestSerializer,
    PublicStayRequestSerializer,
    StayUpdateSerializer,
)


def notify(email, subject, message):
    if email:
        transaction.on_commit(lambda: send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True))


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def owner_register(request):
    serializer = OwnerRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response({"email": user.email, "name": user.get_full_name()}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def owner_login(request):
    email = request.data.get("email", "").strip().lower()
    user = authenticate(request, username=email, password=request.data.get("password", ""))
    if user is None or user.is_staff or not user.is_active:
        return Response({"detail": "פרטי הכניסה אינם תקינים."}, status=status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    return Response({"email": user.email, "name": user.get_full_name()})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_session(request):
    if request.user.is_staff:
        return Response({"detail": "זהו חשבון מנהל."}, status=status.HTTP_403_FORBIDDEN)
    return Response({"email": request.user.email, "name": request.user.get_full_name() or request.user.email})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def owner_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def owner_dogs(request):
    if request.user.is_staff:
        return Response({"detail": "נדרשת הרשאת בעלים."}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "GET":
        dogs = Dog.objects.filter(owner=request.user).select_related("emergency_contact")
        return Response(DogSerializer(dogs, many=True).data)
    serializer = DogSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def owner_dog_detail(request, dog_id):
    if request.user.is_staff:
        return Response({"detail": "נדרשת הרשאת בעלים."}, status=status.HTTP_403_FORBIDDEN)
    dog = get_object_or_404(Dog.objects.select_related("emergency_contact"), pk=dog_id, owner=request.user)
    if request.method == "GET":
        return Response(DogSerializer(dog).data)
    serializer = DogSerializer(dog, data=request.data, partial=True, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_dashboard(request):
    if request.user.is_staff:
        return Response({"detail": "נדרשת הרשאת בעלים."}, status=status.HTTP_403_FORBIDDEN)
    stay_requests = StayRequest.objects.filter(owner=request.user).select_related("dog")
    bookings = Booking.objects.filter(owner=request.user).select_related("dog").prefetch_related("updates")
    return Response({"requests": OwnerStayRequestSerializer(stay_requests, many=True).data, "bookings": OwnerBookingSerializer(bookings, many=True).data})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def create_stay_request(request):
    serializer = PublicStayRequestSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    owner = request.user if request.user.is_authenticated and not request.user.is_staff else None
    stay_request = serializer.save(status=StayRequest.Status.PENDING, owner=owner)
    notify(stay_request.email, "בקשת האירוח התקבלה", f"שלום {stay_request.contact_name},\n\nבקשה מספר {stay_request.id} נקלטה וממתינה לבדיקת מנהל. זו עדיין אינה הזמנה מאושרת.")
    return Response({"id": stay_request.id, "status": stay_request.status, "message": "הבקשה נקלטה וממתינה לבדיקה של מנהל."}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def manager_login(request):
    user = authenticate(request, username=request.data.get("username", ""), password=request.data.get("password", ""))
    if user is None or not user.is_staff or not user.is_active:
        return Response({"detail": "פרטי הכניסה אינם תקינים."}, status=status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    return Response({"username": user.username})


@api_view(["POST"])
@permission_classes([IsStaffManager])
def manager_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsStaffManager])
def manager_session(request):
    return Response({"username": request.user.username})


@api_view(["GET"])
@permission_classes([IsStaffManager])
def list_stay_requests(request):
    queryset = StayRequest.objects.select_related("reviewed_by", "owner", "dog").all()
    requested_status = request.query_params.get("status")
    if requested_status in StayRequest.Status.values:
        queryset = queryset.filter(status=requested_status)
    return Response(AdminStayRequestSerializer(queryset, many=True).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def decide_stay_request(request, request_id):
    decision = request.data.get("decision")
    if decision not in {StayRequest.Status.APPROVED, StayRequest.Status.REJECTED}:
        return Response({"decision": ["יש לבחור אישור או דחייה."]}, status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        try:
            stay_request = StayRequest.objects.select_for_update().get(pk=request_id)
        except StayRequest.DoesNotExist:
            return Response({"detail": "הבקשה לא נמצאה."}, status=status.HTTP_404_NOT_FOUND)
        if stay_request.status != StayRequest.Status.PENDING:
            return Response({"detail": "הבקשה כבר טופלה ואינה ניתנת לשינוי."}, status=status.HTTP_409_CONFLICT)
        stay_request.status = decision
        stay_request.reviewed_by = request.user
        stay_request.reviewed_at = timezone.now()
        stay_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        if decision == StayRequest.Status.APPROVED:
            Booking.objects.create(request=stay_request, owner=stay_request.owner, dog=stay_request.dog, service=stay_request.service, start_date=stay_request.start_date, end_date=stay_request.end_date)
        label = "אושרה" if decision == StayRequest.Status.APPROVED else "נדחתה"
        notify(stay_request.email, f"בקשת האירוח {label}", f"בקשה מספר {stay_request.id} {label}. ניתן לראות את הפרטים באזור האישי אם הבקשה נשלחה מתוך החשבון.")
    return Response(AdminStayRequestSerializer(stay_request).data)


@api_view(["GET"])
@permission_classes([IsStaffManager])
def list_bookings(request):
    bookings = Booking.objects.select_related("owner", "dog", "request").prefetch_related("updates", "dog__internal_notes")
    return Response(AdminBookingSerializer(bookings, many=True).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    new_status = request.data.get("status")
    if new_status not in Booking.Status.values:
        return Response({"status": ["סטטוס לא תקין."]}, status=status.HTTP_400_BAD_REQUEST)
    booking.status = new_status
    booking.save(update_fields=["status", "updated_at"])
    return Response(AdminBookingSerializer(booking).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def create_stay_update(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("owner"), pk=booking_id)
    serializer = StayUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    stay_update = serializer.save(booking=booking, created_by=request.user)
    if stay_update.visible_to_owner and booking.owner:
        notify(booking.owner.email, "עדכון חדש מהשהות", f"נוסף עדכון חדש: {stay_update.get_kind_display()}\n\n{stay_update.message}")
    return Response(StayUpdateSerializer(stay_update).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def create_internal_note(request, dog_id):
    dog = get_object_or_404(Dog, pk=dog_id)
    serializer = InternalCareNoteSerializer(data={**request.data, "dog": dog.id})
    serializer.is_valid(raise_exception=True)
    note = serializer.save(created_by=request.user)
    return Response(InternalCareNoteSerializer(note).data, status=status.HTTP_201_CREATED)
