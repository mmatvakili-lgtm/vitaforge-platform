# Single source of truth for DOC-05 (ERD) and DOC-06 (Data Dictionary).
# Field DSL: "name|type|null(Y/N)|default|constraint|description"
# constraint tokens: PK, UQ, FK->table.col, CK:<expr>, IDX
ID = "id|uuid|N|gen_random_uuid()|PK|شناسه پایدار"
TS = ["created_at|timestamptz|N|now()||زمان ایجاد (UTC)"]
UP = ["updated_at|timestamptz|N|now()||زمان آخرین تغییر (UTC)"]

E = []  # (ENT, table, module, status, description, [fields], [extra constraints])
def ent(table, module, desc, fields, extra=None, status="MVP"):
    E.append(dict(table=table, module=module, desc=desc, fields=fields, extra=extra or [], status=status))

# ---------------- identity ----------------
ent("users","identity","حساب کاربری",[ID,
 "email|varchar(254)|Y||UQ (lower)|ایمیل نرمال‌شده",
 "phone|varchar(20)|Y||UQ|موبایل E.164",
 "password_hash|varchar(256)|N||| هش رمز (Argon2/PBKDF2)",
 "status|enum(pending_verification,active,locked,deletion_pending,deleted)|N|pending_verification||وضعیت چرخه عمر",
 "date_of_birth|date|N||CK:سن ثبت‌نام ≥ adult_age (سرویس + تست)|برای کنترل سن بزرگسالی (DEC-115)",
 "email_verified_at|timestamptz|Y|||زمان تأیید",
 "failed_login_count|int|N|0|CK:>=0|شمارنده ورود ناموفق",
 "locked_until|timestamptz|Y|||قفل موقت",
 "deleted_at|timestamptz|Y|||حذف نرم (DEC-112)"]+TS+UP,
 ["CK: email IS NOT NULL OR phone IS NOT NULL"])
ent("user_roles","identity","نقش‌های کاربر",[ID,
 "user_id|uuid|N||FK->users.id|کاربر",
 "role|enum(user,professional,support_admin,content_admin,exercise_reviewer,nutrition_reviewer,clinical_safety_reviewer,finance_admin,super_admin)|N|||نقش",
 "granted_by|uuid|Y||FK->users.id|اعطاکننده",
 "granted_at|timestamptz|N|now()||زمان اعطا",
 "revoked_at|timestamptz|Y|||ابطال"],["UQ(user_id, role) WHERE revoked_at IS NULL"])
ent("user_sessions","identity","نشست‌های فعال",[ID,
 "user_id|uuid|N||FK->users.id|کاربر",
 "session_hash|varchar(128)|N||UQ|هش شناسه نشست",
 "ip_hash|varchar(64)|Y|||هش IP (بدون ذخیره خام)",
 "user_agent|varchar(300)|Y|||",
 "last_seen_at|timestamptz|N|now()||",
 "expires_at|timestamptz|N|||انقضا",
 "revoked_at|timestamptz|Y|||ابطال"]+TS)
ent("authentication_events","identity","رویدادهای احراز هویت (ممیزی)",[ID,
 "user_id|uuid|Y||FK->users.id|کاربر (در صورت شناخته‌شدن)",
 "event_type|enum(register,verify,login,logout,login_failed,password_reset_request,password_reset,session_revoked,lockout)|N|||نوع",
 "success|bool|N|||موفقیت",
 "ip_hash|varchar(64)|Y|||",
 "user_agent|varchar(300)|Y|||"]+TS)
ent("health_data_access_grants","identity","مجوز زمان‌دار دسترسی ادمین به داده سلامت",[ID,
 "grantee_id|uuid|N||FK->users.id|دریافت‌کننده",
 "subject_user_id|uuid|N||FK->users.id|صاحب داده",
 "reason|text|N|||علت (الزامی)",
 "granted_at|timestamptz|N|now()||",
 "expires_at|timestamptz|N||CK:expires_at>granted_at|انقضا",
 "revoked_at|timestamptz|Y|||"])
# ---------------- profiles ----------------
ent("user_profiles","profiles","پروفایل و تنظیمات i18n",[
 "user_id|uuid|N||PK, FK->users.id|کاربر",
 "display_name|varchar(80)|Y|||نام نمایشی",
 "sex|enum(female,male,unspecified)|N|unspecified||فقط برای محاسبات دارای ارتباط معتبر",
 "country|char(2)|Y|||ISO-3166",
 "city|varchar(80)|Y|||",
 "timezone|varchar(64)|N|UTC||IANA",
 "language|enum(fa,en)|N|fa||زبان رابط",
 "calendar|enum(jalali,gregorian)|N|jalali||نمایش تاریخ (DEC-003)",
 "unit_system|enum(metric,imperial)|N|metric||",
 "digit_style|enum(latin,persian)|N|latin||",
 "onboarding_status|enum(not_started,in_progress,completed)|N|not_started||"]+UP)
ent("user_preferences","profiles","ترجیحات رابط/اعلان",[ID,
 "user_id|uuid|N||UQ, FK->users.id|",
 "theme|enum(light,dark,system)|N|system||",
 "notify_email|bool|N|true||"]+UP)
# ---------------- onboarding ----------------
ent("assessments","onboarding","ارزیابی/Onboarding نسخه‌دار",[ID,
 "user_id|uuid|N||FK->users.id|",
 "version|int|N|1|CK:>=1|نسخه پرسش‌نامه",
 "status|enum(in_progress,completed)|N|in_progress||",
 "current_step|smallint|N|1|CK:between 1 and 14|مرحله جاری",
 "started_at|timestamptz|N|now()||",
 "completed_at|timestamptz|Y|||"])
ent("assessment_answers","onboarding","پاسخ‌های ارزیابی",[ID,
 "assessment_id|uuid|N||FK->assessments.id|",
 "question_key|varchar(80)|N|||شناسه پرسش",
 "answer|jsonb|N|||پاسخ (ساختاریافته، بدون متن آزاد سلامت؛ آن در health)",
 "is_sensitive|bool|N|false||"]+TS,["UQ(assessment_id, question_key)"])
ent("user_goals","onboarding","اهداف",[ID,
 "user_id|uuid|N||FK->users.id|",
 "goal_type|enum(muscle_gain,strength,fat_loss,weight_gain,weight_maintenance,endurance,general_fitness,mobility,sport_performance,return_to_activity)|N|||",
 "is_primary|bool|N|false||",
 "target_weight_kg|numeric(5,2)|Y||CK:>0|"]+TS,["UQ(user_id) WHERE is_primary"])
ent("training_profiles","onboarding","سطح و سابقه تمرین",[
 "user_id|uuid|N||PK, FK->users.id|",
 "level|enum(beginner,intermediate,advanced)|N|||",
 "sessions_per_week_history|smallint|Y||CK:between 0 and 14|",
 "years_training|numeric(4,1)|Y||CK:>=0|"]+UP)
ent("availability_schedules","onboarding","روزها و مدت آزاد",[ID,
 "user_id|uuid|N||FK->users.id|",
 "weekday|smallint|N||CK:between 0 and 6|0=شنبه یا طبق تقویم کاربر (ذخیره ISO: 1=Mon..7=Sun در سرویس)",
 "session_minutes|smallint|N||CK:between 10 and 240|"],["UQ(user_id, weekday)"])
ent("equipment_inventory","onboarding","تجهیزات در دسترس کاربر",[ID,
 "user_id|uuid|N||FK->users.id|",
 "equipment_id|uuid|N||FK->equipment.id|",
 "available|bool|N|true||"],["UQ(user_id, equipment_id)"])
# ---------------- body ----------------
ent("body_measurements","body_metrics","اندازه‌گیری‌ها (SI) با منبع و روش",[ID,
 "user_id|uuid|N||FK->users.id|",
 "metric|enum(height,weight,waist,abdomen,chest,arm,forearm,thigh,calf,body_fat_pct,lean_mass)|N|||",
 "value|numeric(8,3)|N||CK:>0|مقدار به واحد SI",
 "unit|enum(cm,kg,pct)|N|||واحد ذخیره‌شده",
 "source|enum(measured,estimated)|N|||تخمین جدا از اندازه‌گیری (PRI-008)",
 "method|varchar(80)|Y|||روش اندازه‌گیری",
 "measured_at|timestamptz|N|||"]+TS)
# ---------------- compliance ----------------
ent("consent_documents","compliance","متن رضایت نسخه‌دار",[ID,
 "type|enum(terms,health_data,photo,device)|N|||",
 "version|int|N|||",
 "locale|enum(fa,en)|N|||",
 "body|text|N|||",
 "published_at|timestamptz|N|||"],["UQ(type, version, locale)"])
ent("user_consents","compliance","رضایت‌های کاربر",[ID,
 "user_id|uuid|N||FK->users.id|",
 "document_id|uuid|N||FK->consent_documents.id|",
 "granted|bool|N|||",
 "granted_at|timestamptz|N|now()||",
 "revoked_at|timestamptz|Y|||",
 "ip_hash|varchar(64)|Y|||"])
ent("audit_logs","compliance","ممیزی تغییرناپذیر (بدون داده سلامت خام)",[ID,
 "actor_id|uuid|Y||FK->users.id|عامل",
 "subject_user_id|uuid|Y||FK->users.id|صاحب داده",
 "action|varchar(80)|N|||",
 "resource_type|varchar(60)|N|||",
 "resource_id|uuid|Y|||",
 "detail|jsonb|N|{}||فقط فراداده؛ PHI ممنوع"]+TS)
ent("data_requests","compliance","درخواست export/حذف",[ID,
 "user_id|uuid|N||FK->users.id|",
 "type|enum(export,delete)|N|||",
 "status|enum(requested,processing,completed,failed)|N|requested||",
 "requested_at|timestamptz|N|now()||",
 "completed_at|timestamptz|Y|||",
 "artifact_ref|varchar(200)|Y|||"])
ent("outbox_events","compliance","Outbox رویدادهای دامنه",[ID,
 "event_type|varchar(80)|N|||",
 "payload|jsonb|N|||بدون PHI",
 "status|enum(pending,sent,failed)|N|pending||",
 "attempts|int|N|0||"]+TS)
# ---------------- health ----------------
REG="enum(lower_back,spine_other,neck,mid_back,shoulder,elbow,wrist,hand,hip,groin,knee,ankle,foot,muscle_tendon,other)"
ent("health_conditions","health","محدودیت/درد/آسیب (خوداظهاری ≠ تشخیص)",[ID,
 "user_id|uuid|N||FK->users.id|",
 f"region|{REG}|N|||ناحیه",
 "side|enum(left,right,both,na)|N|na||",
 "problem_type|enum(pain,limited_motion,diagnosed_injury,surgery_history,other)|N|||",
 "status|enum(no_known_limitation,self_reported_symptom,professionally_assessed,active_professional_restriction,cleared_to_return,needs_reassessment,needs_urgent_referral)|N|self_reported_symptom||۷ وضعیت سند مادر",
 "source|enum(self_reported,professional)|N|self_reported||",
 "onset_date|date|Y|||",
 "trend|enum(better,same,worse,unknown)|N|unknown||",
 "self_severity|smallint|Y||CK:between 0 and 10|",
 "aggravating_factors|text|Y|||متن آزاد (رمزنگاری سطح اپ)",
 "relieving_factors|text|Y|||",
 "professional_diagnosis|text|Y||CK:source='professional' یا NULL|فقط توسط متخصص",
 "professional_restriction_text|text|Y||CK:source='professional' یا NULL|",
 "review_due_at|date|Y|||"]+TS+UP)
ent("symptom_records","health","ثبت علائم در زمینه‌های مختلف",[ID,
 "user_id|uuid|N||FK->users.id|",
 "condition_id|uuid|Y||FK->health_conditions.id|",
 "context|enum(screening,before_session,during_session,after_session,checkin)|N|||",
 f"region|{REG}|N|||",
 "severity|smallint|Y||CK:between 0 and 10|",
 "note_enc|text|Y|||یادداشت رمزنگاری‌شده",
 "recorded_at|timestamptz|N|now()||"])
ent("pain_logs","health","ثبت درد حین/بعد تمرین (فقط آنلاین، DEC-004)",[ID,
 "user_id|uuid|N||FK->users.id|",
 "session_id|uuid|Y||FK->workout_sessions.id|",
 f"region|{REG}|N|||",
 "side|enum(left,right,both,na)|N|na||",
 "intensity|smallint|N||CK:between 0 and 10|",
 "timing|enum(before,during,after,general)|N|||",
 "recorded_at|timestamptz|N|now()||"])
ent("screening_responses","health","پاسخ غربالگری هشدار/ناحیه‌ای",[ID,
 "user_id|uuid|N||FK->users.id|",
 "screening_version|int|N|||نسخه فهرست (Draft تا EXP-001)",
 "question_key|varchar(80)|N|||",
 "answer|jsonb|N|||",
 "recorded_at|timestamptz|N|now()||"])
ent("medical_restrictions","health","محدودیت ساختاریافته برای فیلتر سخت",[ID,
 "condition_id|uuid|N||FK->health_conditions.id|",
 "restricted_pattern_id|uuid|Y||FK->movement_patterns.id|",
 "restricted_exercise_id|uuid|Y||FK->exercises.id|",
 "restricted_region|"+REG+"|Y|||",
 "max_loading|enum(none,low,moderate)|Y|||",
 "valid_until|date|Y|||",
 "source|enum(professional)|N|professional||"]+TS,["CK: restricted_pattern_id OR restricted_exercise_id OR restricted_region IS NOT NULL"])
ent("professional_clearances","health","مجوز بازگشت به فعالیت",[ID,
 "condition_id|uuid|N||FK->health_conditions.id|",
 "clearance_type|enum(return_to_activity,partial,none)|N|||",
 "document_ref|varchar(200)|Y|||",
 "issued_at|date|N|||",
 "valid_until|date|Y|||"]+TS)
ent("out_of_scope_flags","health","بارداری/شرایط پرخطر (DEC-121)",[ID,
 "user_id|uuid|N||FK->users.id|",
 "flag_type|enum(pregnancy,high_risk_condition,other)|N|||",
 "status|enum(active,cleared_by_professional)|N|active||",
 "source|enum(self_reported)|N|self_reported||"]+TS+["cleared_at|timestamptz|Y|||"])
# ---------------- safety ----------------
ent("scientific_sources","safety","منابع (verified/unverified)",[ID,
 "title|varchar(300)|N|||",
 "publisher|varchar(200)|Y|||",
 "published_on|date|Y|||",
 "url|varchar(500)|Y|||",
 "doi|varchar(120)|Y|||",
 "evidence_level|enum(none,consensus,guideline,systematic_review)|N|none||",
 "population|varchar(200)|Y|||",
 "scope_notes|text|Y|||",
 "accessed_on|date|Y|||",
 "verification|enum(verified,unverified)|N|unverified||"]+TS)
ent("safety_rule_versions","safety","نسخه مجموعه قواعد (immutable پس از انتشار)",[ID,
 "version|int|N||UQ|",
 "status|enum(draft_unreviewed,clinical_reviewed,published,retired)|N|draft_unreviewed||",
 "created_by|uuid|N||FK->users.id|",
 "reviewed_by|uuid|Y||FK->users.id|",
 "reviewed_at|timestamptz|Y|||",
 "published_at|timestamptz|Y|||",
 "notes|text|Y|||"]+TS,["CK: status='published' → reviewed_by NOT NULL"])
ent("safety_rules","safety","قواعد داده‌محور",[ID,
 "rule_set_version_id|uuid|N||FK->safety_rule_versions.id|",
 "rule_code|varchar(20)|N|||SAF-Rnnn",
 "name|varchar(160)|N|||",
 "stage|smallint|N||CK:between 1 and 10|مرحله اولویت (DOC-09 §5)",
 "condition|jsonb|N|||JSON-logic",
 "action|jsonb|N|||",
 "severity|enum(critical,high,medium)|N|||",
 "is_structural|bool|N|false||قاعده غیر‌بالینی",
 "evidence_level|enum(none,consensus,guideline,systematic_review)|N|none||",
 "source_ref_id|uuid|Y||FK->scientific_sources.id|",
 "review_status|enum(draft_unreviewed,clinical_reviewed,published)|N|draft_unreviewed||"],
 ["UQ(rule_set_version_id, rule_code)","CK: review_status='published' AND NOT is_structural → source_ref_id NOT NULL"])
ent("safety_decisions","safety","تصمیم‌های ایمنی (append-only)",[ID,
 "user_id|uuid|N||FK->users.id|",
 "context_type|enum(plan_generation,substitution,ai_output,session)|N|||",
 "status|enum(ALLOW,ALLOW_WITH_MODIFICATION,RESTRICT,NEEDS_INFO,STOP_AND_REFER,BLOCK_OUT_OF_SCOPE,BLOCK_CONSENT,ERROR_FAILSAFE)|N|||",
 "per_item|jsonb|N|[]||",
 "reasons|jsonb|N|[]||",
 "rule_set_version_id|uuid|N||FK->safety_rule_versions.id|",
 "inputs_hash|char(64)|N|||SHA-256 ورودی‌ها",
 "evaluated_at|timestamptz|N|||"]+TS)
ent("red_flag_events","safety","رخدادهای هشدار",[ID,
 "user_id|uuid|N||FK->users.id|",
 "decision_id|uuid|N||FK->safety_decisions.id|",
 "severity|enum(urgent,non_urgent)|N|||",
 "referral_shown|varchar(80)|N|||کلید متن ارجاع"]+TS)
# ---------------- exercises ----------------
ent("muscle_groups","exercises","گروه‌های عضلانی (lookup)",[ID,"code|varchar(40)|N||UQ|","name_en|varchar(80)|N|||","name_fa|varchar(80)|N|||"])
ent("movement_patterns","exercises","الگوهای حرکتی (lookup)",[ID,"code|varchar(40)|N||UQ|","name_en|varchar(80)|N|||","name_fa|varchar(80)|N|||"])
ent("equipment","exercises","تجهیزات (lookup)",[ID,"code|varchar(40)|N||UQ|","name_en|varchar(80)|N|||","name_fa|varchar(80)|N|||"])
ent("exercises","exercises","حرکات",[ID,
 "stable_code|varchar(60)|N||UQ|شناسه پایدار قابل‌خواندن",
 "movement_pattern_id|uuid|N||FK->movement_patterns.id|",
 "exercise_type|enum(strength,cardio,mobility,core,plyometric,other)|N|||",
 "difficulty|enum(beginner,intermediate,advanced)|N|||",
 "skill_level|smallint|N||CK:between 1 and 5|مهارت پیش‌نیاز",
 "default_tempo|varchar(20)|Y|||",
 "review_status|enum(draft,scientific_review,safety_review,published,retired)|N|draft||گردش انتشار",
 "version|int|N|1||",
 "evidence_level|enum(none,consensus,guideline,systematic_review)|N|none||",
 "safety_tags_complete|bool|N|false||برچسب ایمنی کامل؟",
 "published_at|timestamptz|Y|||"]+TS+UP,
 ["CK: review_status='published' → safety_tags_complete = true"])
ent("exercise_translations","exercises","ترجمه/متن حرکت",[ID,
 "exercise_id|uuid|N||FK->exercises.id|",
 "locale|enum(fa,en)|N|||",
 "name|varchar(160)|N|||",
 "synonyms|text[]|N|{}||",
 "description|text|N|||",
 "setup|text|Y|||وضعیت شروع",
 "execution_steps|jsonb|N|[]||",
 "breathing|text|Y|||",
 "common_mistakes|jsonb|N|[]||",
 "safety_notes|text|Y|||"],["UQ(exercise_id, locale)"])
ent("exercise_muscles","exercises","عضلات هدف/کمکی",[ID,"exercise_id|uuid|N||FK->exercises.id|","muscle_group_id|uuid|N||FK->muscle_groups.id|","role|enum(primary,secondary)|N|||"],["UQ(exercise_id, muscle_group_id)"])
ent("exercise_equipment","exercises","تجهیزات لازم",[ID,"exercise_id|uuid|N||FK->exercises.id|","equipment_id|uuid|N||FK->equipment.id|","required|bool|N|true||"],["UQ(exercise_id, equipment_id)"])
ent("exercise_region_loads","exercises","بارگذاری نواحی بدن (برچسب ایمنی)",[ID,
 "exercise_id|uuid|N||FK->exercises.id|",
 f"region|{REG}|N|||",
 "loading|enum(none,low,moderate,high)|N|||"],["UQ(exercise_id, region)"])
ent("exercise_cautions","exercises","احتیاط‌ها",[ID,"exercise_id|uuid|N||FK->exercises.id|",f"region|{REG}|Y|||","caution_code|varchar(60)|N|||","text_key|varchar(120)|N|||کلید ترجمه"])
ent("exercise_contraindications","exercises","منع‌ها",[ID,"exercise_id|uuid|N||FK->exercises.id|",f"region|{REG}|Y|||","contraindication_code|varchar(60)|N|||","requires_professional_clearance|bool|N|true||","text_key|varchar(120)|N|||"])
ent("exercise_alternatives","exercises","جایگزین/رگرسیون/پروگرشن",[ID,
 "exercise_id|uuid|N||FK->exercises.id|",
 "alternative_exercise_id|uuid|N||FK->exercises.id|",
 "relation|enum(alternative,regression,progression)|N|||",
 "rationale_code|varchar(60)|N|||"],["UQ(exercise_id, alternative_exercise_id, relation)","CK: exercise_id <> alternative_exercise_id"])
ent("exercise_media","exercises","رسانه با مجوز",[ID,
 "exercise_id|uuid|N||FK->exercises.id|",
 "media_type|enum(image,video)|N|||",
 "storage_key|varchar(300)|N|||",
 "license_status|enum(licensed,pending,rejected)|N|pending||",
 "license_ref|varchar(300)|Y|||",
 "attribution|varchar(300)|Y|||"],["CK: usable only when license_status='licensed'"])
ent("exercise_sources","exercises","منابع حرکت",[ID,"exercise_id|uuid|N||FK->exercises.id|","source_id|uuid|N||FK->scientific_sources.id|"],["UQ(exercise_id, source_id)"])
ent("exercise_review_events","exercises","تاریخچه گردش بازبینی",[ID,
 "exercise_id|uuid|N||FK->exercises.id|",
 "version|int|N|||",
 "from_status|varchar(30)|N|||","to_status|varchar(30)|N|||",
 "actor_id|uuid|N||FK->users.id|","notes|text|Y|||"]+TS)
# ---------------- workout ----------------
ent("workout_plans","workout_engine","برنامه (سرپوش نسخه‌ها)",[ID,
 "user_id|uuid|N||FK->users.id|",
 "status|enum(active,archived)|N|active||",
 "current_version_id|uuid|Y||FK->workout_plan_versions.id|"]+TS,["UQ(user_id) WHERE status='active' (Free: ۱ برنامه؛ حد پلن در سرویس)"])
ent("workout_plan_versions","workout_engine","نسخه تغییرناپذیر برنامه",[ID,
 "plan_id|uuid|N||FK->workout_plans.id|",
 "version_no|int|N||CK:>=1|",
 "structure|enum(full_body,upper_lower,push_pull_legs,hybrid,custom)|N|||",
 "goal|varchar(40)|N|||",
 "safety_decision_id|uuid|N||FK->safety_decisions.id|الزامی (PRI-001)",
 "rationale|jsonb|N|{}||دلیل انتخاب",
 "confidence|enum(high,medium,low)|N|||",
 "generated_by|enum(rule_engine,manual)|N|rule_engine||"]+TS,["UQ(plan_id, version_no)","CK: safety_decision.status IN (ALLOW, ALLOW_WITH_MODIFICATION) (سرویس + تست)"])
ent("workout_phases","workout_engine","فازهای برنامه",[ID,"plan_version_id|uuid|N||FK->workout_plan_versions.id|","phase_no|smallint|N|||","name|varchar(80)|N|||","weeks|smallint|N||CK:>=1|"])
ent("workout_days","workout_engine","روزهای برنامه",[ID,"plan_version_id|uuid|N||FK->workout_plan_versions.id|","day_index|smallint|N|||","title|varchar(120)|N|||","focus|varchar(80)|Y|||","est_minutes|smallint|N||CK:between 10 and 240|"],["UQ(plan_version_id, day_index)"])
ent("workout_exercises","workout_engine","حرکات هر روز",[ID,
 "day_id|uuid|N||FK->workout_days.id|",
 "exercise_id|uuid|N||FK->exercises.id|",
 "order_no|smallint|N|||",
 "role|enum(warmup,main,accessory,cooldown)|N|||",
 "rationale_code|varchar(60)|N|||",
 "substituted_from_exercise_id|uuid|Y||FK->exercises.id|"],["UQ(day_id, order_no)"])
ent("workout_sets","workout_engine","تجویز ست‌ها",[ID,
 "workout_exercise_id|uuid|N||FK->workout_exercises.id|",
 "set_no|smallint|N|||",
 "reps_min|smallint|Y||CK:>=1|","reps_max|smallint|Y||CK:>=reps_min|",
 "duration_sec|int|Y||CK:>0|",
 "target_rpe|numeric(3,1)|Y||CK:between 1 and 10|",
 "target_rir|smallint|Y||CK:between 0 and 10|",
 "rest_sec|int|N|60|CK:between 0 and 600|",
 "tempo|varchar(20)|Y|||"],["UQ(workout_exercise_id, set_no)","CK: (reps_min IS NOT NULL) <> (duration_sec IS NOT NULL) OR both allowed per type"])
ent("plan_change_events","workout_engine","رویداد تغییر برنامه",[ID,"plan_id|uuid|N||FK->workout_plans.id|","from_version|int|Y|||","to_version|int|N|||","reason_code|varchar(60)|N|||","actor|enum(system,user,reviewer)|N|||"]+TS)
# ---------------- logs ----------------
ent("workout_sessions","workout_logs","جلسه تمرین",[ID,
 "user_id|uuid|N||FK->users.id|",
 "plan_version_id|uuid|Y||FK->workout_plan_versions.id|",
 "day_id|uuid|Y||FK->workout_days.id|",
 "status|enum(in_progress,completed,aborted)|N|in_progress||",
 "started_at|timestamptz|N|||",
 "ended_at|timestamptz|Y||CK:>=started_at|",
 "perceived_difficulty|smallint|Y||CK:between 1 and 10|",
 "aborted_reason|enum(pain,fatigue,time,other)|Y|||",
 "notes|text|Y|||"]+TS)
ent("exercise_logs","workout_logs","ثبت ست‌ها",[ID,
 "session_id|uuid|N||FK->workout_sessions.id|",
 "workout_exercise_id|uuid|Y||FK->workout_exercises.id|",
 "exercise_id|uuid|N||FK->exercises.id|",
 "set_no|smallint|N|||",
 "reps|smallint|Y||CK:>=0|",
 "load_kg|numeric(6,2)|Y||CK:>=0|",
 "duration_sec|int|Y||CK:>=0|",
 "rpe|numeric(3,1)|Y||CK:between 1 and 10|",
 "rir|smallint|Y||CK:between 0 and 10|",
 "rest_sec|int|Y||CK:>=0|",
 "skipped|bool|N|false||",
 "skipped_reason|varchar(80)|Y|||",
 "substituted_exercise_id|uuid|Y||FK->exercises.id|",
 "client_uuid|uuid|N||UQ|شناسه سمت کلاینت برای idempotency/همگام‌سازی"]+TS)
ent("personal_records","workout_logs","رکوردها",[ID,"user_id|uuid|N||FK->users.id|","exercise_id|uuid|N||FK->exercises.id|","record_type|enum(max_load,max_reps,est_1rm,best_time)|N|||","value|numeric(10,2)|N|||","unit|varchar(10)|N|||","achieved_at|timestamptz|N|||","log_id|uuid|Y||FK->exercise_logs.id|"])
# ---------------- subscriptions ----------------
ent("features","subscriptions","قابلیت‌ها و پرچم ایمنی",[ID,"code|varchar(60)|N||UQ|","name_key|varchar(120)|N|||","safety_critical|bool|N|false||هرگز Gate پولی ندارد (ADR-0003)"])
ent("subscription_plans","subscriptions","پلن‌ها",[ID,"code|varchar(40)|N||UQ|","name_key|varchar(120)|N|||","is_free|bool|N|false||","sort_order|smallint|N|0||","active|bool|N|true||","price_config|jsonb|Y|||پیکربندی قیمت؛ تعیین نشده (DEC-104)"])
ent("plan_features","subscriptions","نگاشت پلن-قابلیت",[ID,"plan_id|uuid|N||FK->subscription_plans.id|","feature_id|uuid|N||FK->features.id|","enabled|bool|N|true||"],["UQ(plan_id, feature_id)","CK(سرویس+تست): feature.safety_critical → enabled=true برای همه پلن‌ها"])
ent("plan_quotas","subscriptions","سهمیه‌ها",[ID,"plan_id|uuid|N||FK->subscription_plans.id|","quota_key|varchar(60)|N|||","limit_value|int|Y||CK:>=0|NULL=نامحدود","period|enum(day,month,none)|N|none||"],["UQ(plan_id, quota_key)"])
ent("subscriptions","subscriptions","اشتراک کاربر",[ID,"user_id|uuid|N||FK->users.id|","plan_id|uuid|N||FK->subscription_plans.id|","status|enum(trial,active,cancelled,expired)|N|active||","started_at|timestamptz|N|now()||","current_period_end|timestamptz|Y|||","cancel_at|timestamptz|Y|||","provider_ref|varchar(120)|Y|||"],["UQ(user_id) WHERE status IN ('trial','active')"])
# ---------------- ai ----------------
ent("prompt_versions","ai_gateway","نسخه Prompt",[ID,"name|varchar(80)|N|||","version|int|N|||","template|text|N|||","output_schema|jsonb|N|||","status|enum(draft,approved,retired)|N|draft||"]+TS,["UQ(name, version)"])
ent("ai_model_versions","ai_gateway","نسخه مدل/Provider",[ID,"provider_code|varchar(40)|N|||","model_ref|varchar(80)|N|||","external_allowed|bool|N|false||مجاز برای داده غیرسلامت؟","status|enum(active,retired)|N|active||"]+TS)
ent("ai_conversations","ai_gateway","گفتگو (محتوا Redact‌شده)",[ID,"user_id|uuid|N||FK->users.id|","purpose|enum(explain_plan,technique,general)|N|||"]+TS)
ent("ai_messages","ai_gateway","پیام‌ها",[ID,"conversation_id|uuid|N||FK->ai_conversations.id|","role|enum(user,assistant,system)|N|||","content_redacted|text|N|||","safety_decision_id|uuid|Y||FK->safety_decisions.id|","prompt_version_id|uuid|Y||FK->prompt_versions.id|","model_version_id|uuid|Y||FK->ai_model_versions.id|"]+TS)
ent("ai_usage","ai_gateway","مصرف AI برای سهمیه",[ID,"user_id|uuid|N||FK->users.id|","model_version_id|uuid|N||FK->ai_model_versions.id|","tokens_in|int|N|0||","tokens_out|int|N|0||","purpose|varchar(40)|N|||"]+TS)
# ---------------- misc ----------------
ent("notifications","notifications","اعلان‌ها",[ID,"user_id|uuid|N||FK->users.id|","channel|enum(email,sms,in_app)|N|||","template|varchar(80)|N|||","status|enum(pending,sent,failed)|N|pending||","scheduled_at|timestamptz|Y|||","sent_at|timestamptz|Y|||"]+TS)
ent("translations","localization","ترجمه محتوا/رابط پویا",[ID,"namespace|varchar(60)|N|||","key|varchar(160)|N|||","locale|enum(fa,en)|N|||","value|text|N|||"]+UP,["UQ(namespace, key, locale)"])

DEFERRED = {
 "nutrition/foods (Phase 3)":["foods","food_translations","food_nutrients","food_allergens","recipes","recipe_ingredients","meal_plans","meal_plan_days","meals","nutrition_logs","food_substitutions","food_prices","shopping_lists","budget_profiles"],
 "supplements (Phase 3)":["supplements","supplement_interactions"],
 "recovery (Phase 2/4)":["daily_checkins","sleep_records","fatigue_records","activity_records","recovery_summaries"],
 "sports (Phase 4-5)":["sports","sport_disciplines"],
 "professionals (Phase 6)":["professionals","professional_credentials","client_relationships"],
 "protocols — Pending Specialist Approval (مسیر C)":["clinical_protocols","protocol_versions","protocol_steps","protocol_eligibility_rules","injury_records"],
 "body/vision (Phase 5)":["body_composition_records","progress_photos","photo_consents","device_connections"],
 "billing (Phase 6)":["invoices","payments","refunds","coupons"],
 "calendar/ai-ext":["calendar_events","ai_recommendations","ai_tool_calls","ai_sources","ai_evaluations","kb_documents","kb_chunks (pgvector)","feedback_records","content_items"],
}
