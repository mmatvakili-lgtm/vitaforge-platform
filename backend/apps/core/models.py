# WRITTEN, NOT RUN: migrations must be generated with `manage.py makemigrations` once Django is available.
import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, default="user")
    plan = models.CharField(max_length=16, default="free")
    locale = models.CharField(max_length=2, default="fa")
    email_verified = models.BooleanField(default=False)
    failed_logins = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = "email"


class ApiSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    device = models.CharField(max_length=120, blank=True)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Consent(models.Model):                      # append-only: never updated or deleted by the app
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    doc_type = models.CharField(max_length=40)
    version = models.CharField(max_length=20, null=True)
    granted = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)


class Exercise(models.Model):
    code = models.CharField(max_length=60, unique=True)
    status = models.CharField(max_length=24, default="draft")
    version = models.PositiveIntegerField(default=1)
    movement_pattern = models.CharField(max_length=40)
    safety_tags_complete = models.BooleanField(default=False)
    is_sample = models.BooleanField(default=False)
    payload = models.JSONField(default=dict)


class PlanVersion(models.Model):                  # immutable by convention + DB trigger (planned)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    cause = models.CharField(max_length=40)
    result = models.JSONField()
    safety_decision_id = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("user", "version")
