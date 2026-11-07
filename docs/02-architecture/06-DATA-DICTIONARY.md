<div dir="rtl">

# سند ۶ — Data Dictionary

| فیلد | مقدار |
|---|---|
| Document ID | DOC-06 |
| Version | 0.1 |
| Status | Draft — Complete برای دامنه MVP (جداول Deferred فقط فهرست) |
| Created / Updated | 2026-11-07 |
| Owner | Database Architect |
| Related Documents | DOC-03، DOC-07، DOC-09، DOC-15 |
| Related Decisions | DEC-003، 004، 112، 121، 125، 126؛ ADR-0003، ADR-0004 |

قالب ستون‌ها: فیلد | نوع | Nullable | Default | محدودیت | توضیح. `PK`=کلید اصلی، `UQ`=یکتا، `FK->t.c`=کلید خارجی، `CK`=قید بررسی.


## ماژول `identity`

### ENT-001 — `users`
حساب کاربری

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `email` | `varchar(254)` | بله | — | UQ (lower) | ایمیل نرمال‌شده |
| `phone` | `varchar(20)` | بله | — | UQ | موبایل E.164 |
| `password_hash` | `varchar(256)` | خیر | — | — |  هش رمز (Argon2/PBKDF2) |
| `status` | `enum(pending_verification,active,locked,deletion_pending,deleted)` | خیر | `pending_verification` | — | وضعیت چرخه عمر |
| `date_of_birth` | `date` | خیر | — | CK:سن ثبت‌نام ≥ adult_age (سرویس + تست) | برای کنترل سن بزرگسالی (DEC-115) |
| `email_verified_at` | `timestamptz` | بله | — | — | زمان تأیید |
| `failed_login_count` | `int` | خیر | `0` | CK:>=0 | شمارنده ورود ناموفق |
| `locked_until` | `timestamptz` | بله | — | — | قفل موقت |
| `deleted_at` | `timestamptz` | بله | — | — | حذف نرم (DEC-112) |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

محدودیت‌های جدول: CK: `email IS NOT NULL OR phone IS NOT NULL`

### ENT-002 — `user_roles`
نقش‌های کاربر

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id | کاربر |
| `role` | `enum(user,professional,support_admin,content_admin,exercise_reviewer,nutrition_reviewer,clinical_safety_reviewer,finance_admin,super_admin)` | خیر | — | — | نقش |
| `granted_by` | `uuid` | بله | — | FK->users.id | اعطاکننده |
| `granted_at` | `timestamptz` | خیر | `now()` | — | زمان اعطا |
| `revoked_at` | `timestamptz` | بله | — | — | ابطال |

محدودیت‌های جدول: UQ(user_id, role) WHERE revoked_at IS NULL

### ENT-003 — `user_sessions`
نشست‌های فعال

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id | کاربر |
| `session_hash` | `varchar(128)` | خیر | — | UQ | هش شناسه نشست |
| `ip_hash` | `varchar(64)` | بله | — | — | هش IP (بدون ذخیره خام) |
| `user_agent` | `varchar(300)` | بله | — | — |  |
| `last_seen_at` | `timestamptz` | خیر | `now()` | — |  |
| `expires_at` | `timestamptz` | خیر | — | — | انقضا |
| `revoked_at` | `timestamptz` | بله | — | — | ابطال |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-004 — `authentication_events`
رویدادهای احراز هویت (ممیزی)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | بله | — | FK->users.id | کاربر (در صورت شناخته‌شدن) |
| `event_type` | `enum(register,verify,login,logout,login_failed,password_reset_request,password_reset,session_revoked,lockout)` | خیر | — | — | نوع |
| `success` | `bool` | خیر | — | — | موفقیت |
| `ip_hash` | `varchar(64)` | بله | — | — |  |
| `user_agent` | `varchar(300)` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-005 — `health_data_access_grants`
مجوز زمان‌دار دسترسی ادمین به داده سلامت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `grantee_id` | `uuid` | خیر | — | FK->users.id | دریافت‌کننده |
| `subject_user_id` | `uuid` | خیر | — | FK->users.id | صاحب داده |
| `reason` | `text` | خیر | — | — | علت (الزامی) |
| `granted_at` | `timestamptz` | خیر | `now()` | — |  |
| `expires_at` | `timestamptz` | خیر | — | CK:expires_at>granted_at | انقضا |
| `revoked_at` | `timestamptz` | بله | — | — |  |

## ماژول `profiles`

### ENT-006 — `user_profiles`
پروفایل و تنظیمات i18n

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | — | PK, FK->users.id | کاربر |
| `display_name` | `varchar(80)` | بله | — | — | نام نمایشی |
| `sex` | `enum(female,male,unspecified)` | خیر | `unspecified` | — | فقط برای محاسبات دارای ارتباط معتبر |
| `country` | `char(2)` | بله | — | — | ISO-3166 |
| `city` | `varchar(80)` | بله | — | — |  |
| `timezone` | `varchar(64)` | خیر | `UTC` | — | IANA |
| `language` | `enum(fa,en)` | خیر | `fa` | — | زبان رابط |
| `calendar` | `enum(jalali,gregorian)` | خیر | `jalali` | — | نمایش تاریخ (DEC-003) |
| `unit_system` | `enum(metric,imperial)` | خیر | `metric` | — |  |
| `digit_style` | `enum(latin,persian)` | خیر | `latin` | — |  |
| `onboarding_status` | `enum(not_started,in_progress,completed)` | خیر | `not_started` | — |  |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

### ENT-007 — `user_preferences`
ترجیحات رابط/اعلان

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | UQ, FK->users.id |  |
| `theme` | `enum(light,dark,system)` | خیر | `system` | — |  |
| `notify_email` | `bool` | خیر | `true` | — |  |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

## ماژول `onboarding`

### ENT-008 — `assessments`
ارزیابی/Onboarding نسخه‌دار

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `version` | `int` | خیر | `1` | CK:>=1 | نسخه پرسش‌نامه |
| `status` | `enum(in_progress,completed)` | خیر | `in_progress` | — |  |
| `current_step` | `smallint` | خیر | `1` | CK:between 1 and 14 | مرحله جاری |
| `started_at` | `timestamptz` | خیر | `now()` | — |  |
| `completed_at` | `timestamptz` | بله | — | — |  |

### ENT-009 — `assessment_answers`
پاسخ‌های ارزیابی

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `assessment_id` | `uuid` | خیر | — | FK->assessments.id |  |
| `question_key` | `varchar(80)` | خیر | — | — | شناسه پرسش |
| `answer` | `jsonb` | خیر | — | — | پاسخ (ساختاریافته، بدون متن آزاد سلامت؛ آن در health) |
| `is_sensitive` | `bool` | خیر | `false` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: UQ(assessment_id, question_key)

### ENT-010 — `user_goals`
اهداف

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `goal_type` | `enum(muscle_gain,strength,fat_loss,weight_gain,weight_maintenance,endurance,general_fitness,mobility,sport_performance,return_to_activity)` | خیر | — | — |  |
| `is_primary` | `bool` | خیر | `false` | — |  |
| `target_weight_kg` | `numeric(5,2)` | بله | — | CK:>0 |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: UQ(user_id) WHERE is_primary

### ENT-011 — `training_profiles`
سطح و سابقه تمرین

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | — | PK, FK->users.id |  |
| `level` | `enum(beginner,intermediate,advanced)` | خیر | — | — |  |
| `sessions_per_week_history` | `smallint` | بله | — | CK:between 0 and 14 |  |
| `years_training` | `numeric(4,1)` | بله | — | CK:>=0 |  |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

### ENT-012 — `availability_schedules`
روزها و مدت آزاد

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `weekday` | `smallint` | خیر | — | CK:between 0 and 6 | 0=شنبه یا طبق تقویم کاربر (ذخیره ISO: 1=Mon..7=Sun در سرویس) |
| `session_minutes` | `smallint` | خیر | — | CK:between 10 and 240 |  |

محدودیت‌های جدول: UQ(user_id, weekday)

### ENT-013 — `equipment_inventory`
تجهیزات در دسترس کاربر

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `equipment_id` | `uuid` | خیر | — | FK->equipment.id |  |
| `available` | `bool` | خیر | `true` | — |  |

محدودیت‌های جدول: UQ(user_id, equipment_id)

## ماژول `body_metrics`

### ENT-014 — `body_measurements`
اندازه‌گیری‌ها (SI) با منبع و روش

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `metric` | `enum(height,weight,waist,abdomen,chest,arm,forearm,thigh,calf,body_fat_pct,lean_mass)` | خیر | — | — |  |
| `value` | `numeric(8,3)` | خیر | — | CK:>0 | مقدار به واحد SI |
| `unit` | `enum(cm,kg,pct)` | خیر | — | — | واحد ذخیره‌شده |
| `source` | `enum(measured,estimated)` | خیر | — | — | تخمین جدا از اندازه‌گیری (PRI-008) |
| `method` | `varchar(80)` | بله | — | — | روش اندازه‌گیری |
| `measured_at` | `timestamptz` | خیر | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `compliance`

### ENT-015 — `consent_documents`
متن رضایت نسخه‌دار

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `type` | `enum(terms,health_data,photo,device)` | خیر | — | — |  |
| `version` | `int` | خیر | — | — |  |
| `locale` | `enum(fa,en)` | خیر | — | — |  |
| `body` | `text` | خیر | — | — |  |
| `published_at` | `timestamptz` | خیر | — | — |  |

محدودیت‌های جدول: UQ(type, version, locale)

### ENT-016 — `user_consents`
رضایت‌های کاربر

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `document_id` | `uuid` | خیر | — | FK->consent_documents.id |  |
| `granted` | `bool` | خیر | — | — |  |
| `granted_at` | `timestamptz` | خیر | `now()` | — |  |
| `revoked_at` | `timestamptz` | بله | — | — |  |
| `ip_hash` | `varchar(64)` | بله | — | — |  |

### ENT-017 — `audit_logs`
ممیزی تغییرناپذیر (بدون داده سلامت خام)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `actor_id` | `uuid` | بله | — | FK->users.id | عامل |
| `subject_user_id` | `uuid` | بله | — | FK->users.id | صاحب داده |
| `action` | `varchar(80)` | خیر | — | — |  |
| `resource_type` | `varchar(60)` | خیر | — | — |  |
| `resource_id` | `uuid` | بله | — | — |  |
| `detail` | `jsonb` | خیر | `{}` | — | فقط فراداده؛ PHI ممنوع |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-018 — `data_requests`
درخواست export/حذف

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `type` | `enum(export,delete)` | خیر | — | — |  |
| `status` | `enum(requested,processing,completed,failed)` | خیر | `requested` | — |  |
| `requested_at` | `timestamptz` | خیر | `now()` | — |  |
| `completed_at` | `timestamptz` | بله | — | — |  |
| `artifact_ref` | `varchar(200)` | بله | — | — |  |

### ENT-019 — `outbox_events`
Outbox رویدادهای دامنه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `event_type` | `varchar(80)` | خیر | — | — |  |
| `payload` | `jsonb` | خیر | — | — | بدون PHI |
| `status` | `enum(pending,sent,failed)` | خیر | `pending` | — |  |
| `attempts` | `int` | خیر | `0` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `health`

### ENT-020 — `health_conditions`
محدودیت/درد/آسیب (خوداظهاری ≠ تشخیص)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | خیر | — | — | ناحیه |
| `side` | `enum(left,right,both,na)` | خیر | `na` | — |  |
| `problem_type` | `enum(pain,limited_motion,diagnosed_injury,surgery_history,other)` | خیر | — | — |  |
| `status` | `enum(no_known_limitation,self_reported_symptom,professionally_assessed,active_professional_restriction,cleared_to_return,needs_reassessment,needs_urgent_referral)` | خیر | `self_reported_symptom` | — | ۷ وضعیت سند مادر |
| `source` | `enum(self_reported,professional)` | خیر | `self_reported` | — |  |
| `onset_date` | `date` | بله | — | — |  |
| `trend` | `enum(better,same,worse,unknown)` | خیر | `unknown` | — |  |
| `self_severity` | `smallint` | بله | — | CK:between 0 and 10 |  |
| `aggravating_factors` | `text` | بله | — | — | متن آزاد (رمزنگاری سطح اپ) |
| `relieving_factors` | `text` | بله | — | — |  |
| `professional_diagnosis` | `text` | بله | — | CK:source='professional' یا NULL | فقط توسط متخصص |
| `professional_restriction_text` | `text` | بله | — | CK:source='professional' یا NULL |  |
| `review_due_at` | `date` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

### ENT-021 — `symptom_records`
ثبت علائم در زمینه‌های مختلف

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `condition_id` | `uuid` | بله | — | FK->health_conditions.id |  |
| `context` | `enum(screening,before_session,during_session,after_session,checkin)` | خیر | — | — |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | خیر | — | — |  |
| `severity` | `smallint` | بله | — | CK:between 0 and 10 |  |
| `note_enc` | `text` | بله | — | — | یادداشت رمزنگاری‌شده |
| `recorded_at` | `timestamptz` | خیر | `now()` | — |  |

### ENT-022 — `pain_logs`
ثبت درد حین/بعد تمرین (فقط آنلاین، DEC-004)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `session_id` | `uuid` | بله | — | FK->workout_sessions.id |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | خیر | — | — |  |
| `side` | `enum(left,right,both,na)` | خیر | `na` | — |  |
| `intensity` | `smallint` | خیر | — | CK:between 0 and 10 |  |
| `timing` | `enum(before,during,after,general)` | خیر | — | — |  |
| `recorded_at` | `timestamptz` | خیر | `now()` | — |  |

### ENT-023 — `screening_responses`
پاسخ غربالگری هشدار/ناحیه‌ای

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `screening_version` | `int` | خیر | — | — | نسخه فهرست (Draft تا EXP-001) |
| `question_key` | `varchar(80)` | خیر | — | — |  |
| `answer` | `jsonb` | خیر | — | — |  |
| `recorded_at` | `timestamptz` | خیر | `now()` | — |  |

### ENT-024 — `medical_restrictions`
محدودیت ساختاریافته برای فیلتر سخت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `condition_id` | `uuid` | خیر | — | FK->health_conditions.id |  |
| `restricted_pattern_id` | `uuid` | بله | — | FK->movement_patterns.id |  |
| `restricted_exercise_id` | `uuid` | بله | — | FK->exercises.id |  |
| `restricted_region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | بله | — | — |  |
| `max_loading` | `enum(none,low,moderate)` | بله | — | — |  |
| `valid_until` | `date` | بله | — | — |  |
| `source` | `enum(professional)` | خیر | `professional` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: CK: restricted_pattern_id OR restricted_exercise_id OR restricted_region `IS NOT NULL`

### ENT-025 — `professional_clearances`
مجوز بازگشت به فعالیت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `condition_id` | `uuid` | خیر | — | FK->health_conditions.id |  |
| `clearance_type` | `enum(return_to_activity,partial,none)` | خیر | — | — |  |
| `document_ref` | `varchar(200)` | بله | — | — |  |
| `issued_at` | `date` | خیر | — | — |  |
| `valid_until` | `date` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-026 — `out_of_scope_flags`
بارداری/شرایط پرخطر (DEC-121)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `flag_type` | `enum(pregnancy,high_risk_condition,other)` | خیر | — | — |  |
| `status` | `enum(active,cleared_by_professional)` | خیر | `active` | — |  |
| `source` | `enum(self_reported)` | خیر | `self_reported` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |
| `cleared_at` | `timestamptz` | بله | — | — |  |

## ماژول `safety`

### ENT-027 — `scientific_sources`
منابع (verified/unverified)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `title` | `varchar(300)` | خیر | — | — |  |
| `publisher` | `varchar(200)` | بله | — | — |  |
| `published_on` | `date` | بله | — | — |  |
| `url` | `varchar(500)` | بله | — | — |  |
| `doi` | `varchar(120)` | بله | — | — |  |
| `evidence_level` | `enum(none,consensus,guideline,systematic_review)` | خیر | `none` | — |  |
| `population` | `varchar(200)` | بله | — | — |  |
| `scope_notes` | `text` | بله | — | — |  |
| `accessed_on` | `date` | بله | — | — |  |
| `verification` | `enum(verified,unverified)` | خیر | `unverified` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-028 — `safety_rule_versions`
نسخه مجموعه قواعد (immutable پس از انتشار)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `version` | `int` | خیر | — | UQ |  |
| `status` | `enum(draft_unreviewed,clinical_reviewed,published,retired)` | خیر | `draft_unreviewed` | — |  |
| `created_by` | `uuid` | خیر | — | FK->users.id |  |
| `reviewed_by` | `uuid` | بله | — | FK->users.id |  |
| `reviewed_at` | `timestamptz` | بله | — | — |  |
| `published_at` | `timestamptz` | بله | — | — |  |
| `notes` | `text` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: CK: status='published' → reviewed_by NOT NULL

### ENT-029 — `safety_rules`
قواعد داده‌محور

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `rule_set_version_id` | `uuid` | خیر | — | FK->safety_rule_versions.id |  |
| `rule_code` | `varchar(20)` | خیر | — | — | SAF-Rnnn |
| `name` | `varchar(160)` | خیر | — | — |  |
| `stage` | `smallint` | خیر | — | CK:between 1 and 10 | مرحله اولویت (DOC-09 §5) |
| `condition` | `jsonb` | خیر | — | — | JSON-logic |
| `action` | `jsonb` | خیر | — | — |  |
| `severity` | `enum(critical,high,medium)` | خیر | — | — |  |
| `is_structural` | `bool` | خیر | `false` | — | قاعده غیر‌بالینی |
| `evidence_level` | `enum(none,consensus,guideline,systematic_review)` | خیر | `none` | — |  |
| `source_ref_id` | `uuid` | بله | — | FK->scientific_sources.id |  |
| `review_status` | `enum(draft_unreviewed,clinical_reviewed,published)` | خیر | `draft_unreviewed` | — |  |

محدودیت‌های جدول: UQ(rule_set_version_id, rule_code)؛ CK: review_status='published' AND NOT is_structural → source_ref_id NOT NULL

### ENT-030 — `safety_decisions`
تصمیم‌های ایمنی (append-only)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `context_type` | `enum(plan_generation,substitution,ai_output,session)` | خیر | — | — |  |
| `status` | `enum(ALLOW,ALLOW_WITH_MODIFICATION,RESTRICT,NEEDS_INFO,STOP_AND_REFER,BLOCK_OUT_OF_SCOPE,BLOCK_CONSENT,ERROR_FAILSAFE)` | خیر | — | — |  |
| `per_item` | `jsonb` | خیر | `[]` | — |  |
| `reasons` | `jsonb` | خیر | `[]` | — |  |
| `rule_set_version_id` | `uuid` | خیر | — | FK->safety_rule_versions.id |  |
| `inputs_hash` | `char(64)` | خیر | — | — | SHA-256 ورودی‌ها |
| `evaluated_at` | `timestamptz` | خیر | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-031 — `red_flag_events`
رخدادهای هشدار

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `decision_id` | `uuid` | خیر | — | FK->safety_decisions.id |  |
| `severity` | `enum(urgent,non_urgent)` | خیر | — | — |  |
| `referral_shown` | `varchar(80)` | خیر | — | — | کلید متن ارجاع |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `exercises`

### ENT-032 — `muscle_groups`
گروه‌های عضلانی (lookup)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `code` | `varchar(40)` | خیر | — | UQ |  |
| `name_en` | `varchar(80)` | خیر | — | — |  |
| `name_fa` | `varchar(80)` | خیر | — | — |  |

### ENT-033 — `movement_patterns`
الگوهای حرکتی (lookup)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `code` | `varchar(40)` | خیر | — | UQ |  |
| `name_en` | `varchar(80)` | خیر | — | — |  |
| `name_fa` | `varchar(80)` | خیر | — | — |  |

### ENT-034 — `equipment`
تجهیزات (lookup)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `code` | `varchar(40)` | خیر | — | UQ |  |
| `name_en` | `varchar(80)` | خیر | — | — |  |
| `name_fa` | `varchar(80)` | خیر | — | — |  |

### ENT-035 — `exercises`
حرکات

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `stable_code` | `varchar(60)` | خیر | — | UQ | شناسه پایدار قابل‌خواندن |
| `movement_pattern_id` | `uuid` | خیر | — | FK->movement_patterns.id |  |
| `exercise_type` | `enum(strength,cardio,mobility,core,plyometric,other)` | خیر | — | — |  |
| `difficulty` | `enum(beginner,intermediate,advanced)` | خیر | — | — |  |
| `skill_level` | `smallint` | خیر | — | CK:between 1 and 5 | مهارت پیش‌نیاز |
| `default_tempo` | `varchar(20)` | بله | — | — |  |
| `review_status` | `enum(draft,scientific_review,safety_review,published,retired)` | خیر | `draft` | — | گردش انتشار |
| `version` | `int` | خیر | `1` | — |  |
| `evidence_level` | `enum(none,consensus,guideline,systematic_review)` | خیر | `none` | — |  |
| `safety_tags_complete` | `bool` | خیر | `false` | — | برچسب ایمنی کامل؟ |
| `published_at` | `timestamptz` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

محدودیت‌های جدول: CK: review_status='published' → safety_tags_complete = true

### ENT-036 — `exercise_translations`
ترجمه/متن حرکت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `locale` | `enum(fa,en)` | خیر | — | — |  |
| `name` | `varchar(160)` | خیر | — | — |  |
| `synonyms` | `text[]` | خیر | `{}` | — |  |
| `description` | `text` | خیر | — | — |  |
| `setup` | `text` | بله | — | — | وضعیت شروع |
| `execution_steps` | `jsonb` | خیر | `[]` | — |  |
| `breathing` | `text` | بله | — | — |  |
| `common_mistakes` | `jsonb` | خیر | `[]` | — |  |
| `safety_notes` | `text` | بله | — | — |  |

محدودیت‌های جدول: UQ(exercise_id, locale)

### ENT-037 — `exercise_muscles`
عضلات هدف/کمکی

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `muscle_group_id` | `uuid` | خیر | — | FK->muscle_groups.id |  |
| `role` | `enum(primary,secondary)` | خیر | — | — |  |

محدودیت‌های جدول: UQ(exercise_id, muscle_group_id)

### ENT-038 — `exercise_equipment`
تجهیزات لازم

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `equipment_id` | `uuid` | خیر | — | FK->equipment.id |  |
| `required` | `bool` | خیر | `true` | — |  |

محدودیت‌های جدول: UQ(exercise_id, equipment_id)

### ENT-039 — `exercise_region_loads`
بارگذاری نواحی بدن (برچسب ایمنی)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | خیر | — | — |  |
| `loading` | `enum(none,low,moderate,high)` | خیر | — | — |  |

محدودیت‌های جدول: UQ(exercise_id, region)

### ENT-040 — `exercise_cautions`
احتیاط‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | بله | — | — |  |
| `caution_code` | `varchar(60)` | خیر | — | — |  |
| `text_key` | `varchar(120)` | خیر | — | — | کلید ترجمه |

### ENT-041 — `exercise_contraindications`
منع‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `region` | `enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)` | بله | — | — |  |
| `contraindication_code` | `varchar(60)` | خیر | — | — |  |
| `requires_professional_clearance` | `bool` | خیر | `true` | — |  |
| `text_key` | `varchar(120)` | خیر | — | — |  |

### ENT-042 — `exercise_alternatives`
جایگزین/رگرسیون/پروگرشن

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `alternative_exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `relation` | `enum(alternative,regression,progression)` | خیر | — | — |  |
| `rationale_code` | `varchar(60)` | خیر | — | — |  |

محدودیت‌های جدول: UQ(exercise_id, alternative_exercise_id, relation)؛ CK: exercise_id <> alternative_exercise_id

### ENT-043 — `exercise_media`
رسانه با مجوز

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `media_type` | `enum(image,video)` | خیر | — | — |  |
| `storage_key` | `varchar(300)` | خیر | — | — |  |
| `license_status` | `enum(licensed,pending,rejected)` | خیر | `pending` | — |  |
| `license_ref` | `varchar(300)` | بله | — | — |  |
| `attribution` | `varchar(300)` | بله | — | — |  |

محدودیت‌های جدول: CK: `usable only when` license_status='licensed'

### ENT-044 — `exercise_sources`
منابع حرکت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `source_id` | `uuid` | خیر | — | FK->scientific_sources.id |  |

محدودیت‌های جدول: UQ(exercise_id, source_id)

### ENT-045 — `exercise_review_events`
تاریخچه گردش بازبینی

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `version` | `int` | خیر | — | — |  |
| `from_status` | `varchar(30)` | خیر | — | — |  |
| `to_status` | `varchar(30)` | خیر | — | — |  |
| `actor_id` | `uuid` | خیر | — | FK->users.id |  |
| `notes` | `text` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `workout_engine`

### ENT-046 — `workout_plans`
برنامه (سرپوش نسخه‌ها)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `status` | `enum(active,archived)` | خیر | `active` | — |  |
| `current_version_id` | `uuid` | بله | — | FK->workout_plan_versions.id |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: UQ(user_id) WHERE status='active' (Free: ۱ برنامه؛ حد پلن در سرویس)

### ENT-047 — `workout_plan_versions`
نسخه تغییرناپذیر برنامه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_id` | `uuid` | خیر | — | FK->workout_plans.id |  |
| `version_no` | `int` | خیر | — | CK:>=1 |  |
| `structure` | `enum(full_body,upper_lower,push_pull_legs,hybrid,custom)` | خیر | — | — |  |
| `goal` | `varchar(40)` | خیر | — | — |  |
| `safety_decision_id` | `uuid` | خیر | — | FK->safety_decisions.id | الزامی (PRI-001) |
| `rationale` | `jsonb` | خیر | `{}` | — | دلیل انتخاب |
| `confidence` | `enum(high,medium,low)` | خیر | — | — |  |
| `generated_by` | `enum(rule_engine,manual)` | خیر | `rule_engine` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: UQ(plan_id, version_no)؛ CK: safety_decision.status IN (ALLOW, ALLOW_WITH_MODIFICATION) (سرویس + تست)

### ENT-048 — `workout_phases`
فازهای برنامه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_version_id` | `uuid` | خیر | — | FK->workout_plan_versions.id |  |
| `phase_no` | `smallint` | خیر | — | — |  |
| `name` | `varchar(80)` | خیر | — | — |  |
| `weeks` | `smallint` | خیر | — | CK:>=1 |  |

### ENT-049 — `workout_days`
روزهای برنامه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_version_id` | `uuid` | خیر | — | FK->workout_plan_versions.id |  |
| `day_index` | `smallint` | خیر | — | — |  |
| `title` | `varchar(120)` | خیر | — | — |  |
| `focus` | `varchar(80)` | بله | — | — |  |
| `est_minutes` | `smallint` | خیر | — | CK:between 10 and 240 |  |

محدودیت‌های جدول: UQ(plan_version_id, day_index)

### ENT-050 — `workout_exercises`
حرکات هر روز

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `day_id` | `uuid` | خیر | — | FK->workout_days.id |  |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `order_no` | `smallint` | خیر | — | — |  |
| `role` | `enum(warmup,main,accessory,cooldown)` | خیر | — | — |  |
| `rationale_code` | `varchar(60)` | خیر | — | — |  |
| `substituted_from_exercise_id` | `uuid` | بله | — | FK->exercises.id |  |

محدودیت‌های جدول: UQ(day_id, order_no)

### ENT-051 — `workout_sets`
تجویز ست‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `workout_exercise_id` | `uuid` | خیر | — | FK->workout_exercises.id |  |
| `set_no` | `smallint` | خیر | — | — |  |
| `reps_min` | `smallint` | بله | — | CK:>=1 |  |
| `reps_max` | `smallint` | بله | — | CK:>=reps_min |  |
| `duration_sec` | `int` | بله | — | CK:>0 |  |
| `target_rpe` | `numeric(3,1)` | بله | — | CK:between 1 and 10 |  |
| `target_rir` | `smallint` | بله | — | CK:between 0 and 10 |  |
| `rest_sec` | `int` | خیر | `60` | CK:between 0 and 600 |  |
| `tempo` | `varchar(20)` | بله | — | — |  |

محدودیت‌های جدول: UQ(workout_exercise_id, set_no)؛ CK: (reps_min `IS NOT NULL`) <> (duration_sec `IS NOT NULL`) `OR both allowed per type`

### ENT-052 — `plan_change_events`
رویداد تغییر برنامه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_id` | `uuid` | خیر | — | FK->workout_plans.id |  |
| `from_version` | `int` | بله | — | — |  |
| `to_version` | `int` | خیر | — | — |  |
| `reason_code` | `varchar(60)` | خیر | — | — |  |
| `actor` | `enum(system,user,reviewer)` | خیر | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `workout_logs`

### ENT-053 — `workout_sessions`
جلسه تمرین

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `plan_version_id` | `uuid` | بله | — | FK->workout_plan_versions.id |  |
| `day_id` | `uuid` | بله | — | FK->workout_days.id |  |
| `status` | `enum(in_progress,completed,aborted)` | خیر | `in_progress` | — |  |
| `started_at` | `timestamptz` | خیر | — | — |  |
| `ended_at` | `timestamptz` | بله | — | CK:>=started_at |  |
| `perceived_difficulty` | `smallint` | بله | — | CK:between 1 and 10 |  |
| `aborted_reason` | `enum(pain,fatigue,time,other)` | بله | — | — |  |
| `notes` | `text` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-054 — `exercise_logs`
ثبت ست‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `session_id` | `uuid` | خیر | — | FK->workout_sessions.id |  |
| `workout_exercise_id` | `uuid` | بله | — | FK->workout_exercises.id |  |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `set_no` | `smallint` | خیر | — | — |  |
| `reps` | `smallint` | بله | — | CK:>=0 |  |
| `load_kg` | `numeric(6,2)` | بله | — | CK:>=0 |  |
| `duration_sec` | `int` | بله | — | CK:>=0 |  |
| `rpe` | `numeric(3,1)` | بله | — | CK:between 1 and 10 |  |
| `rir` | `smallint` | بله | — | CK:between 0 and 10 |  |
| `rest_sec` | `int` | بله | — | CK:>=0 |  |
| `skipped` | `bool` | خیر | `false` | — |  |
| `skipped_reason` | `varchar(80)` | بله | — | — |  |
| `substituted_exercise_id` | `uuid` | بله | — | FK->exercises.id |  |
| `client_uuid` | `uuid` | خیر | — | UQ | شناسه سمت کلاینت برای idempotency/همگام‌سازی |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-055 — `personal_records`
رکوردها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `exercise_id` | `uuid` | خیر | — | FK->exercises.id |  |
| `record_type` | `enum(max_load,max_reps,est_1rm,best_time)` | خیر | — | — |  |
| `value` | `numeric(10,2)` | خیر | — | — |  |
| `unit` | `varchar(10)` | خیر | — | — |  |
| `achieved_at` | `timestamptz` | خیر | — | — |  |
| `log_id` | `uuid` | بله | — | FK->exercise_logs.id |  |

## ماژول `subscriptions`

### ENT-056 — `features`
قابلیت‌ها و پرچم ایمنی

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `code` | `varchar(60)` | خیر | — | UQ |  |
| `name_key` | `varchar(120)` | خیر | — | — |  |
| `safety_critical` | `bool` | خیر | `false` | — | هرگز Gate پولی ندارد (ADR-0003) |

### ENT-057 — `subscription_plans`
پلن‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `code` | `varchar(40)` | خیر | — | UQ |  |
| `name_key` | `varchar(120)` | خیر | — | — |  |
| `is_free` | `bool` | خیر | `false` | — |  |
| `sort_order` | `smallint` | خیر | `0` | — |  |
| `active` | `bool` | خیر | `true` | — |  |
| `price_config` | `jsonb` | بله | — | — | پیکربندی قیمت؛ تعیین نشده (DEC-104) |

### ENT-058 — `plan_features`
نگاشت پلن-قابلیت

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_id` | `uuid` | خیر | — | FK->subscription_plans.id |  |
| `feature_id` | `uuid` | خیر | — | FK->features.id |  |
| `enabled` | `bool` | خیر | `true` | — |  |

محدودیت‌های جدول: UQ(plan_id, feature_id)؛ CK(سرویس+تست): feature.safety_critical → enabled=true برای همه پلن‌ها

### ENT-059 — `plan_quotas`
سهمیه‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `plan_id` | `uuid` | خیر | — | FK->subscription_plans.id |  |
| `quota_key` | `varchar(60)` | خیر | — | — |  |
| `limit_value` | `int` | بله | — | CK:>=0 | NULL=نامحدود |
| `period` | `enum(day,month,none)` | خیر | `none` | — |  |

محدودیت‌های جدول: UQ(plan_id, quota_key)

### ENT-060 — `subscriptions`
اشتراک کاربر

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `plan_id` | `uuid` | خیر | — | FK->subscription_plans.id |  |
| `status` | `enum(trial,active,cancelled,expired)` | خیر | `active` | — |  |
| `started_at` | `timestamptz` | خیر | `now()` | — |  |
| `current_period_end` | `timestamptz` | بله | — | — |  |
| `cancel_at` | `timestamptz` | بله | — | — |  |
| `provider_ref` | `varchar(120)` | بله | — | — |  |

محدودیت‌های جدول: UQ(user_id) `WHERE status IN` ('trial','active')

## ماژول `ai_gateway`

### ENT-061 — `prompt_versions`
نسخه Prompt

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `name` | `varchar(80)` | خیر | — | — |  |
| `version` | `int` | خیر | — | — |  |
| `template` | `text` | خیر | — | — |  |
| `output_schema` | `jsonb` | خیر | — | — |  |
| `status` | `enum(draft,approved,retired)` | خیر | `draft` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

محدودیت‌های جدول: UQ(name, version)

### ENT-062 — `ai_model_versions`
نسخه مدل/Provider

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `provider_code` | `varchar(40)` | خیر | — | — |  |
| `model_ref` | `varchar(80)` | خیر | — | — |  |
| `external_allowed` | `bool` | خیر | `false` | — | مجاز برای داده غیرسلامت؟ |
| `status` | `enum(active,retired)` | خیر | `active` | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-063 — `ai_conversations`
گفتگو (محتوا Redact‌شده)

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `purpose` | `enum(explain_plan,technique,general)` | خیر | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-064 — `ai_messages`
پیام‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `conversation_id` | `uuid` | خیر | — | FK->ai_conversations.id |  |
| `role` | `enum(user,assistant,system)` | خیر | — | — |  |
| `content_redacted` | `text` | خیر | — | — |  |
| `safety_decision_id` | `uuid` | بله | — | FK->safety_decisions.id |  |
| `prompt_version_id` | `uuid` | بله | — | FK->prompt_versions.id |  |
| `model_version_id` | `uuid` | بله | — | FK->ai_model_versions.id |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

### ENT-065 — `ai_usage`
مصرف AI برای سهمیه

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `model_version_id` | `uuid` | خیر | — | FK->ai_model_versions.id |  |
| `tokens_in` | `int` | خیر | `0` | — |  |
| `tokens_out` | `int` | خیر | `0` | — |  |
| `purpose` | `varchar(40)` | خیر | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `notifications`

### ENT-066 — `notifications`
اعلان‌ها

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `user_id` | `uuid` | خیر | — | FK->users.id |  |
| `channel` | `enum(email,sms,in_app)` | خیر | — | — |  |
| `template` | `varchar(80)` | خیر | — | — |  |
| `status` | `enum(pending,sent,failed)` | خیر | `pending` | — |  |
| `scheduled_at` | `timestamptz` | بله | — | — |  |
| `sent_at` | `timestamptz` | بله | — | — |  |
| `created_at` | `timestamptz` | خیر | `now()` | — | زمان ایجاد (UTC) |

## ماژول `localization`

### ENT-067 — `translations`
ترجمه محتوا/رابط پویا

| فیلد | نوع | Nullable | Default | محدودیت | توضیح |
|---|---|---|---|---|---|
| `id` | `uuid` | خیر | `gen_random_uuid()` | PK | شناسه پایدار |
| `namespace` | `varchar(60)` | خیر | — | — |  |
| `key` | `varchar(160)` | خیر | — | — |  |
| `locale` | `enum(fa,en)` | خیر | — | — |  |
| `value` | `text` | خیر | — | — |  |
| `updated_at` | `timestamptz` | خیر | `now()` | — | زمان آخرین تغییر (UTC) |

محدودیت‌های جدول: UQ(namespace, key, locale)

## جداول Deferred
- nutrition/foods (Phase 3): foods، food_translations، food_nutrients، food_allergens، recipes، recipe_ingredients، meal_plans، meal_plan_days، meals، nutrition_logs، food_substitutions، food_prices، shopping_lists، budget_profiles
- supplements (Phase 3): supplements، supplement_interactions
- recovery (Phase 2/4): daily_checkins، sleep_records، fatigue_records، activity_records، recovery_summaries
- sports (Phase 4-5): sports، sport_disciplines
- professionals (Phase 6): professionals، professional_credentials، client_relationships
- protocols — `Pending Specialist Approval` (مسیر C): clinical_protocols، protocol_versions، protocol_steps، protocol_eligibility_rules، injury_records
- body/vision (Phase 5): body_composition_records، progress_photos، photo_consents، device_connections
- billing (Phase 6): invoices، payments، refunds، coupons
- calendar/ai-ext: calendar_events، ai_recommendations، ai_tool_calls، ai_sources، ai_evaluations، kb_documents، kb_chunks (pgvector)، feedback_records، content_items

</div>
