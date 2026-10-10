from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils.html import escape

from .models import Booking, Notification, StayRequest

VERIFICATION_SALT = "owner-email-verification-v1"


def create_verification_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFICATION_SALT, compress=True)


def read_verification_token(token):
    data = signing.loads(token, salt=VERIFICATION_SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT)
    user = get_user_model().objects.select_related("owner_profile").get(pk=data["uid"], email__iexact=data["email"])
    return user


def send_message(email, subject, text, action_url=None, action_label=None):
    if not email:
        return
    html = f"<div dir='rtl' style='font-family:Arial,sans-serif;line-height:1.6'><h2>{escape(subject)}</h2><p>{escape(text).replace(chr(10), '<br>')}</p>"
    if action_url and action_label:
        html += f"<p><a href='{escape(action_url)}' style='background:#0c5c57;color:white;padding:12px 18px;border-radius:10px;text-decoration:none'>{escape(action_label)}</a></p>"
    html += "<p style='color:#5d716f'>פנסיון קטן בבית — סביבת בדיקה</p></div>"
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [email])
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=True)


def send_verification_email(user):
    token = create_verification_token(user)
    url = f"{settings.FRONTEND_ORIGIN}/owner/verify?token={token}"
    transaction.on_commit(lambda: send_message(user.email, "אימות כתובת הדוא״ל", "כדי להפעיל את האזור האישי, יש לאמת את כתובת הדוא״ל. הקישור תקף לזמן מוגבל.", url, "אימות החשבון"))


def create_notification(recipient, kind, title, message, stay_request=None, booking=None):
    if recipient:
        return Notification.objects.create(recipient=recipient, kind=kind, title=title, message=message, stay_request=stay_request, booking=booking)
    return None


def notify_managers(kind, title, message, stay_request=None, booking=None):
    managers = get_user_model().objects.filter(is_staff=True, is_active=True)
    Notification.objects.bulk_create([Notification(recipient=user, kind=kind, title=title, message=message, stay_request=stay_request, booking=booking) for user in managers])


def link_verified_requests(user):
    if not user.owner_profile.email_verified_at:
        return 0
    with transaction.atomic():
        requests = list(StayRequest.objects.select_for_update().filter(owner__isnull=True, email__iexact=user.email))
        if not requests:
            return 0
        request_ids = [item.id for item in requests]
        StayRequest.objects.filter(id__in=request_ids).update(owner=user)
        Booking.objects.filter(request_id__in=request_ids, owner__isnull=True).update(owner=user)
        for item in requests:
            create_notification(user, Notification.Kind.REQUEST_LINKED, "בקשה קודמת קושרה לחשבון", f"בקשה מספר {item.id} קושרה לחשבון לאחר אימות הדוא״ל.", stay_request=item)
        return len(requests)
