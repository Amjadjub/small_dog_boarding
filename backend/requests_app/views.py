from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import StayRequest
from .permissions import IsStaffManager
from .serializers import AdminStayRequestSerializer, PublicStayRequestSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def create_stay_request(request):
    serializer = PublicStayRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    stay_request = serializer.save(status=StayRequest.Status.PENDING)
    return Response({"id": stay_request.id, "status": stay_request.status, "message": "הבקשה נקלטה וממתינה לבדיקה של מנהל."}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def manager_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
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
    queryset = StayRequest.objects.select_related("reviewed_by").all()
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

    return Response(AdminStayRequestSerializer(stay_request).data)
