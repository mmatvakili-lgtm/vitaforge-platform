"""Persistence tables for the unit-of-work store (ADR-0013 amended). NEEDS LOCAL VERIFICATION: written without a Django runtime.

`KVRecord` holds every domain collection (users, sessions, profiles, plans, ...) as one row per key with an indexed `owner`
(user id) column: per-user reads/erase are query-level, and every write happens inside one request-wide transaction.
Relational normalisation of individual collections (typed columns, FKs) is a later, per-collection migration."""
from django.db import models


class KVRecord(models.Model):
    coll = models.CharField(max_length=40)
    k = models.CharField(max_length=300)
    owner = models.CharField(max_length=60, null=True, blank=True)
    data = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["coll", "k"], name="kv_unique_coll_key")]
        indexes = [models.Index(fields=["coll", "owner"], name="kv_coll_owner_idx")]


class IdSequence(models.Model):
    name = models.CharField(max_length=40, unique=True)
    n = models.BigIntegerField(default=0)
