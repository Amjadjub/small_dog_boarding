import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="StayRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contact_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("dog_name", models.CharField(max_length=80)),
                ("dog_age", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("dog_sex", models.CharField(choices=[("female", "נקבה"), ("male", "זכר"), ("unknown", "לא צוין")], default="unknown", max_length=10)),
                ("care_notes", models.TextField(blank=True, max_length=2000)),
                ("service", models.CharField(choices=[("overnight", "לינה"), ("daycare", "אירוח יומי"), ("transport", "איסוף והחזרה")], max_length=20)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("pending", "ממתינה"), ("approved", "אושרה"), ("rejected", "נדחתה")], db_index=True, default="pending", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_stay_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="stayrequest", index=models.Index(fields=["status", "created_at"], name="request_status_created_idx")),
    ]
