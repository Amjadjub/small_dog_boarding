from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Dog, Notification, StayRequest
from .permissions import IsStaffManager, IsVerifiedOwner
from .security import rate_limit
from .serializers import AdminBookingSerializer, AdminStayRequestSerializer, DogSerializer, InternalCareNoteSerializer, NotificationSerializer, OwnerBookingSerializer, OwnerRegistrationSerializer, OwnerStayRequestSerializer, PublicStayRequestSerializer, StayUpdateSerializer
from .services import create_notification, link_verified_requests, notify_managers, read_verification_token, send_message, send_verification_email


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("owner-register", 5, 3600)
def owner_register(request):
    serializer = OwnerRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    send_verification_email(user)
    return Response({"email": user.email, "message": "החשבון נוצר. נשלח קישור אימות לדוא״ל."}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("owner-login", 10, 900)
def owner_login(request):
    email = request.data.get("email", "").strip().lower()
    user = authenticate(request, username=email, password=request.data.get("password", ""))
    if user is None or user.is_staff or not user.is_active:
        return Response({"detail": "פרטי הכניסה אינם תקינים."}, status=status.HTTP_401_UNAUTHORIZED)
    if not getattr(user, "owner_profile", None) or not user.owner_profile.email_verified_at:
        return Response({"detail": "יש לאמת את כתובת הדוא״ל לפני הכניסה.", "code": "email_not_verified"}, status=status.HTTP_403_FORBIDDEN)
    login(request, user)
    return Response({"email": user.email, "name": user.get_full_name()})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("email-verification", 10, 3600)
def verify_email(request):
    try:
        user = read_verification_token(request.data.get("token", ""))
    except (signing.BadSignature, signing.SignatureExpired, get_user_model().DoesNotExist, KeyError):
        return Response({"detail": "קישור האימות אינו תקין או שפג תוקפו."}, status=status.HTTP_400_BAD_REQUEST)
    if user.owner_profile.email_verified_at:
        return Response({"detail": "כתובת הדוא״ל כבר אומתה."})
    with transaction.atomic():
        user.owner_profile.email_verified_at = timezone.now()
        user.owner_profile.save(update_fields=["email_verified_at"])
        linked = link_verified_requests(user)
        create_notification(user, Notification.Kind.ACCOUNT_VERIFIED, "החשבון אומת", "כתובת הדוא״ל אומתה והאזור האישי פעיל.")
    return Response({"detail": "כתובת הדוא״ל אומתה בהצלחה.", "linked_requests": linked})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("verification-resend", 3, 3600)
def resend_verification(request):
    user = get_user_model().objects.filter(email__iexact=request.data.get("email", "").strip(), is_staff=False, is_active=True).first()
    if user and getattr(user, "owner_profile", None) and not user.owner_profile.email_verified_at:
        send_verification_email(user)
    return Response({"detail": "אם החשבון קיים וטרם אומת, נשלח קישור חדש."})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("password-reset-request", 5, 3600)
def request_password_reset(request):
    user = get_user_model().objects.filter(email__iexact=request.data.get("email", "").strip(), is_staff=False, is_active=True).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = f"{settings.FRONTEND_ORIGIN}/owner/reset-password?uid={uid}&token={token}"
        transaction.on_commit(lambda: send_message(user.email, "איפוס סיסמה", "התקבלה בקשה לאיפוס הסיסמה. הקישור תקף לזמן מוגבל וניתן לשימוש פעם אחת.", url, "איפוס הסיסמה"))
    return Response({"detail": "אם קיים חשבון מתאים, נשלח אליו קישור לאיפוס סיסמה."})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("password-reset-confirm", 10, 3600)
def confirm_password_reset(request):
    try:
        user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(request.data.get("uid", ""))))
    except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
        user = None
    token = request.data.get("token", "")
    password = request.data.get("password", "")
    if not user or not default_token_generator.check_token(user, token):
        return Response({"detail": "קישור האיפוס אינו תקין או שפג תוקפו."}, status=status.HTTP_400_BAD_REQUEST)
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return Response({"password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password)
    user.save(update_fields=["password"])
    return Response({"detail": "הסיסמה עודכנה. אפשר להתחבר כעת."})


@api_view(["GET"])
@permission_classes([IsVerifiedOwner])
def owner_session(request):
    return Response({"email": request.user.email, "name": request.user.get_full_name() or request.user.email, "email_verified": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def owner_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsVerifiedOwner])
def owner_dogs(request):
    if request.method == "GET":
        return Response(DogSerializer(Dog.objects.filter(owner=request.user).select_related("emergency_contact"), many=True).data)
    serializer = DogSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([IsVerifiedOwner])
def owner_dog_detail(request, dog_id):
    dog = get_object_or_404(Dog.objects.select_related("emergency_contact"), pk=dog_id, owner=request.user)
    if request.method == "GET":
        return Response(DogSerializer(dog).data)
    serializer = DogSerializer(dog, data=request.data, partial=True, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsVerifiedOwner])
def owner_dashboard(request):
    stay_requests = StayRequest.objects.filter(owner=request.user).select_related("dog")
    bookings = Booking.objects.filter(owner=request.user).select_related("dog").prefetch_related("updates")
    return Response({"requests": OwnerStayRequestSerializer(stay_requests, many=True).data, "bookings": OwnerBookingSerializer(bookings, many=True).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    return Response(NotificationSerializer(request.user.notifications.all()[:100], many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read(request, notification_id):
    item = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    if not item.read_at:
        item.read_at = timezone.now()
        item.save(update_fields=["read_at"])
    return Response(NotificationSerializer(item).data)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("stay-request", 10, 3600)
def create_stay_request(request):
    serializer = PublicStayRequestSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    owner = request.user if request.user.is_authenticated and not request.user.is_staff and getattr(request.user, "owner_profile", None) and request.user.owner_profile.email_verified_at else None
    stay_request = serializer.save(status=StayRequest.Status.PENDING, owner=owner)
    transaction.on_commit(lambda: send_message(stay_request.email, "בקשת האירוח התקבלה", f"בקשה מספר {stay_request.id} נקלטה וממתינה לבדיקת מנהל. זו עדיין אינה הזמנה מאושרת."))
    notify_managers(Notification.Kind.REQUEST_RECEIVED, "בקשת אירוח חדשה", f"בקשה מספר {stay_request.id} ממתינה לטיפול.", stay_request=stay_request)
    if owner:
        create_notification(owner, Notification.Kind.REQUEST_RECEIVED, "הבקשה התקבלה", f"בקשה מספר {stay_request.id} ממתינה לבדיקת מנהל.", stay_request=stay_request)
    return Response({"id": stay_request.id, "status": stay_request.status, "message": "הבקשה נקלטה וממתינה לבדיקה של מנהל."}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@rate_limit("manager-login", 10, 900)
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
    if request.query_params.get("status") in StayRequest.Status.values:
        queryset = queryset.filter(status=request.query_params["status"])
    return Response(AdminStayRequestSerializer(queryset, many=True).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def decide_stay_request(request, request_id):
    decision = request.data.get("decision")
    if decision not in {StayRequest.Status.APPROVED, StayRequest.Status.REJECTED}:
        return Response({"decision": ["יש לבחור אישור או דחייה."]}, status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        stay_request = get_object_or_404(StayRequest.objects.select_for_update(), pk=request_id)
        if stay_request.status != StayRequest.Status.PENDING:
            return Response({"detail": "הבקשה כבר טופלה ואינה ניתנת לשינוי."}, status=status.HTTP_409_CONFLICT)
        stay_request.status, stay_request.reviewed_by, stay_request.reviewed_at = decision, request.user, timezone.now()
        stay_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        booking = None
        if decision == StayRequest.Status.APPROVED:
            booking = Booking.objects.create(request=stay_request, owner=stay_request.owner, dog=stay_request.dog, service=stay_request.service, start_date=stay_request.start_date, end_date=stay_request.end_date)
        label = "אושרה" if decision == StayRequest.Status.APPROVED else "נדחתה"
        transaction.on_commit(lambda: send_message(stay_request.email, f"בקשת האירוח {label}", f"בקשה מספר {stay_request.id} {label}."))
        if stay_request.owner:
            kind = Notification.Kind.REQUEST_APPROVED if decision == StayRequest.Status.APPROVED else Notification.Kind.REQUEST_REJECTED
            create_notification(stay_request.owner, kind, f"הבקשה {label}", f"בקשה מספר {stay_request.id} {label}.", stay_request=stay_request, booking=booking)
    return Response(AdminStayRequestSerializer(stay_request).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def link_request_owner(request, request_id):
    stay_request = get_object_or_404(StayRequest.objects.select_related("booking"), pk=request_id)
    email = request.data.get("email", "").strip()
    owner = None
    if email:
        owner = get_user_model().objects.filter(email__iexact=email, is_staff=False, owner_profile__email_verified_at__isnull=False).first()
        if not owner:
            return Response({"email": ["לא נמצא חשבון בעלים מאומת."]}, status=status.HTTP_400_BAD_REQUEST)
    stay_request.owner = owner
    if not owner:
        stay_request.dog = None
    stay_request.save(update_fields=["owner", "dog", "updated_at"])
    Booking.objects.filter(request=stay_request).update(owner=owner, dog=stay_request.dog)
    if owner:
        create_notification(owner, Notification.Kind.REQUEST_LINKED, "בקשה קושרה לחשבון", f"בקשה מספר {stay_request.id} קושרה לחשבון על ידי מנהל.", stay_request=stay_request)
    return Response(AdminStayRequestSerializer(stay_request).data)


@api_view(["GET"])
@permission_classes([IsStaffManager])
def list_bookings(request):
    return Response(AdminBookingSerializer(Booking.objects.select_related("owner", "dog", "request").prefetch_related("updates", "dog__internal_notes"), many=True).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.data.get("status") not in Booking.Status.values:
        return Response({"status": ["סטטוס לא תקין."]}, status=status.HTTP_400_BAD_REQUEST)
    booking.status = request.data["status"]
    booking.save(update_fields=["status", "updated_at"])
    return Response(AdminBookingSerializer(booking).data)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def create_stay_update(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("owner"), pk=booking_id)
    serializer = StayUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    update = serializer.save(booking=booking, created_by=request.user)
    if update.visible_to_owner and booking.owner:
        create_notification(booking.owner, Notification.Kind.STAY_UPDATE, "עדכון חדש מהשהות", update.message, booking=booking)
        transaction.on_commit(lambda: send_message(booking.owner.email, "עדכון חדש מהשהות", f"{update.get_kind_display()}\n\n{update.message}"))
    return Response(StayUpdateSerializer(update).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsStaffManager])
def create_internal_note(request, dog_id):
    dog = get_object_or_404(Dog, pk=dog_id)
    serializer = InternalCareNoteSerializer(data={**request.data, "dog": dog.id})
    serializer.is_valid(raise_exception=True)
    return Response(InternalCareNoteSerializer(serializer.save(created_by=request.user)).data, status=status.HTTP_201_CREATED)
