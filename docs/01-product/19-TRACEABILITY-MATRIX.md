# سند ۱۹ — Requirements Traceability Matrix

| فیلد | مقدار |
|---|---|
| Document ID | DOC-19 |
| Version | 0.1 |
| Status | Draft — تولیدشده خودکار توسط `tools/gen_trace.py`؛ پوشش P0/P1 بررسی‌شده |
| Created / Updated | 2026-11-07 |
| Owner | QA Lead / Architect |
| Related Documents | DOC-01، DOC-02، DOC-03، DOC-05، DOC-07، DOC-14، DOC-16 |

زنجیره: **Requirement → User Story → UI (PG) → API → Entity → Business Logic → Test**.
وضعیت واقعی پیاده‌سازی در ستون «وضعیت»: `Not Started` تا Milestone مربوط (به‌روزرسانی در IMPLEMENTATION_PLAN)، `Deferred` برای Backlog.
شناسه تست `TST-*` در ستون «Test» **شناسه رزرو‌شده** است؛ تا اجرای واقعی تست‌ها، نتیجه «Not Run» است.

| FR | اولویت/فاز | شرح | US | PG | API | Entity | Logic | Test (رزرو) | وضعیت |
|---|---|---|---|---|---|---|---|---|---|
| FR-ACC-001 | P0 / 1 | ثبت‌نام با ایمیل/موبایل (Interface کانال) و رمز عبور | US-ACC-001 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-001..004 | Not Started |
| FR-ACC-002 | P0 / 1 | تأیید حساب | US-ACC-002 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-005 | Not Started |
| FR-ACC-003 | P0 / 1 | ورود/خروج، مدیریت نشست و ابطال نشست‌ها | US-ACC-003 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-006..009 | Not Started |
| FR-ACC-004 | P0 / 1 | بازیابی رمز عبور | US-ACC-004 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-010 | Not Started |
| FR-ACC-005 | P0 / 1 | نقش‌ها: user، professional، و نقش‌های ادمین | US-ACC-005 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-011..013 | Not Started |
| FR-ACC-006 | P0 / 1 | ثبت رویدادهای احراز هویت | US-ACC-003 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-006..009 | Not Started |
| FR-ACC-007 | P2 / 6 | احراز دومرحله‌ای (اختیاری) | — | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | — | Deferred |
| FR-ACC-008 | P0 / 1 | بررسی سن حداقل ۱۸ و مسدودسازی زیر ۱۸ (DEC-115) | US-ACC-001 | PG-AUTH-001..004 | API-AUTH-001..008 | users, user_roles, user_sessions, authentication_events | SVC-IdentityService | TST-ACC-001..004 | Not Started |
| FR-ADM-001 | P1 / 1–2 | مدیریت کاربران/نقش‌ها (حداقل دسترسی) | US-ADM-001 | PG-ADM-001..004 | API-ADM-001..008 | user_roles, health_data_access_grants, safety_rule_versions | SVC-AdminService | TST-ADM-001..004 | Not Started |
| FR-ADM-002 | P0 / 1 | مدیریت بانک حرکات و گردش بازبینی | US-ADM-003 | PG-ADM-001..004 | API-ADM-001..008 | user_roles, health_data_access_grants, safety_rule_versions | SVC-AdminService | TST-ADM-008 | Not Started |
| FR-ADM-003 | P0 / 1 | مدیریت نسخه قوانین ایمنی | US-ADM-002 | PG-ADM-001..004 | API-ADM-001..008 | user_roles, health_data_access_grants, safety_rule_versions | SVC-AdminService | TST-ADM-005..007 | Not Started |
| FR-ADM-004 | P0 / 1 | ادمین فنی بدون دسترسی پیش‌فرض به داده سلامت | US-ADM-001 | PG-ADM-001..004 | API-ADM-001..008 | user_roles, health_data_access_grants, safety_rule_versions | SVC-AdminService | TST-ADM-001..004 | Not Started |
| FR-AI-001 | P2 | Pipeline اجباری ۹ مرحله‌ای سند مادر | — | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | — | Deferred |
| FR-AI-002 | P2 | RAG با منابع نسخه‌دار | — | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | — | Deferred |
| FR-AI-003 | P2 | Output Validator | — | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | — | Deferred |
| FR-AI-004 | P2 | Evaluation System | — | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | — | Deferred |
| FR-AI-005 | P2 | Provider Abstraction، Redaction، سقف مصرف | US-AI-001 | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | TST-AI-001..006 | Deferred |
| FR-AI-006 | P2 | ثبت تصمیم ایمنی و منبع هر پاسخ | — | PG-AI-001 | API-AI-001 | ai_conversations, ai_messages, prompt_versions, ai_model_versions… | ai_gateway.pipeline | — | Deferred |
| FR-BODY-001 | P0 / 1 | ثبت قد، وزن، دورها با واحد، تاریخ، روش | US-BODY-001 | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | TST-BODY-001..003 | Not Started |
| FR-BODY-002 | P1 / 1 | محاسبه BMI، WHtR (برچسب: شاخص غربالگری) | US-BODY-002 | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | TST-BODY-004..006 | Not Started |
| FR-BODY-003 | P1 / 3 | BMR/TDEE تخمینی با برچسب تخمین (DEC-118) | US-BODY-003 | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | — | Not Started |
| FR-BODY-004 | P0 / 1 | جداسازی اندازه‌گیری مستقیم از تخمین | US-BODY-001 | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | TST-BODY-001..003 | Not Started |
| FR-BODY-005 | P1 / 1 | روند وزن/اندازه‌ها؛ عدم اعلام پیشرفت کمتر از خطای اندازه‌گیری | US-BODY-002 | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | TST-BODY-004..006 | Not Started |
| FR-BODY-006 | P2 / 5 | ترکیب بدن همراه روش و سطح اطمینان | — | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | — | Deferred |
| FR-BODY-007 | P2 / 5 | عکس بدن با رضایت جدا و حذف | — | PG-BODY-001 | API-BODY-001/002 | body_measurements | SVC-BodyMetricsService | — | Deferred |
| FR-BUD-001 | P2 | بودجه ورزش/غذا و اثر آن بر برنامه | — | — | — | Deferred | Deferred | — | Deferred |
| FR-EX-001 | P0 / 1 | رکورد حرکت با فیلدهای سند مادر بخش ۱۰ | US-EX-004 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-009..013 | Not Started |
| FR-EX-002 | P0 / 1 | نام فارسی/انگلیسی و مترادف | US-EX-004 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-009..013 | Not Started |
| FR-EX-003 | P0 / 1 | برچسب‌های ایمنی ساختاریافته (ناحیه، الگو، دامنه، احتیاط، منع، سطح شواه… | US-EX-004 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-009..013 | Not Started |
| FR-EX-004 | P0 / 1 | جایگزین/رگرسیون/پروگرشن | US-EX-004 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-009..013 | Not Started |
| FR-EX-005 | P0 / 1 | رسانه با وضعیت مجوز (DEC-107) | US-EX-004 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-009..013 | Not Started |
| FR-EX-006 | P0 / 1 | گردش انتشار: نگارش → بازبینی علمی → بازبینی ایمنی → انتشار نسخه‌دار | US-EX-003 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-005..008 | Not Started |
| FR-EX-007 | P0 / 1 | صفحه جزئیات حرکت با دلیل انتخاب و سازگاری | US-EX-002 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-004 | Not Started |
| FR-EX-008 | P0 / 1 | جست‌وجو/فیلتر | US-EX-001 | PG-EX-001, PG-EX-002, PG-ADM-001 | API-EX-001..003, API-ADM-001..003 | exercises, exercise_translations, exercise_muscles, exercise_equipment… | SVC-ExerciseCatalogService | TST-EX-001..003 | Not Started |
| FR-FOOD-001 | P2 | بانک غذا با منبع و تاریخ | — | — | — | Deferred | Deferred | — | Deferred |
| FR-FOOD-002 | P2 | جایگزینی هوشمند (نه صرفاً کالری) | — | — | — | Deferred | Deferred | — | Deferred |
| FR-HEALTH-001 | P0 / 1 | ثبت مورد: ناحیه، سمت، نوع، شروع، مدت، روند، شدت خوداظهاری | US-HEALTH-001 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-001..005 | Not Started |
| FR-HEALTH-002 | P0 / 1 | ثبت تشخیص متخصص و محدودیت مکتوب (جدا از خوداظهاری) | US-HEALTH-001 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-001..005 | Not Started |
| FR-HEALTH-003 | P0 / 1 | هفت وضعیت: بدون محدودیت، خوداظهاری، ارزیابی‌شده، محدودیت فعال متخصص، م… | US-HEALTH-001 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-001..005 | Not Started |
| FR-HEALTH-004 | P0 / 1 | خوداظهاری هرگز به‌عنوان تشخیص ذخیره نمی‌شود | US-HEALTH-001 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-001..005 | Not Started |
| FR-HEALTH-005 | P1 / 2 | تاریخ بازبینی و یادآوری بازبینی | US-HEALTH-002 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-006..009 | Not Started |
| FR-HEALTH-006 | P1 / 2 | ثبت درد قبل/حین/بعد تمرین (آنلاین فقط، DEC-004) | US-HEALTH-002 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-006..009 | Not Started |
| FR-HEALTH-007 | P0 / 1 | ثبت بارداری/شرایط پرخطر و مسیر ارجاع (DEC-121) | US-HEALTH-003 | PG-HEALTH-001 | API-HEALTH-001..007 | health_conditions, symptom_records, pain_logs, screening_responses… | SVC-HealthService | TST-HEALTH-010 | Not Started |
| FR-I18N-001 | P0 | فارسی/انگلیسی کامل | US-I18N-001 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-001..005 | Not Started |
| FR-I18N-002 | P0 | RTL/LTR واقعی | US-I18N-001 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-001..005 | Not Started |
| FR-I18N-003 | P0 | ترجمه جدا از کد | US-I18N-001 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-001..005 | Not Started |
| FR-I18N-004 | P0 | تقویم شمسی/میلادی، نمایش از UTC (DEC-003) | US-I18N-002 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-006..010 | Not Started |
| FR-I18N-005 | P0 | متریک/امپریال | US-I18N-002 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-006..010 | Not Started |
| FR-I18N-006 | P0 | نام انگلیسی حرکات کنار ترجمه | US-I18N-002 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-006..010 | Not Started |
| FR-I18N-007 | P1 | ارقام فارسی/لاتین بر اساس ترجیح | US-I18N-002 | همه صفحات | — | translations, user_profiles | frontend i18n + SVC-LocalizationService | TST-I18N-006..010 | Not Started |
| FR-LOG-001 | P0 / 1 | شروع جلسه و تایمر استراحت | US-LOG-001 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-LOG-001..008 | Not Started |
| FR-LOG-002 | P0 / 1 | ثبت وزنه/تکرار/ست/RPE/RIR | US-LOG-001 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-LOG-001..008 | Not Started |
| FR-LOG-003 | P0 / 1 | جایگزینی/انجام‌نشده با علت | US-LOG-001 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-LOG-001..008 | Not Started |
| FR-LOG-004 | P0 / 1 | یادداشت و پایان جلسه + خلاصه | US-LOG-001 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-LOG-001..008 | Not Started |
| FR-LOG-005 | P1 / 2 | ثبت علائم حین تمرین (آنلاین) | US-HEALTH-002 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-HEALTH-006..009 | Not Started |
| FR-LOG-006 | P0 / 1 | قطع اینترنت هنگام ثبت: فقط داده **غیرحساس** تمرین (وزنه/تکرار/ست/RPE) … | US-LOG-002 | PG-WO-002, PG-LOG-001 | API-LOG-001..004 | workout_sessions, exercise_logs, personal_records | SVC-WorkoutLogService | TST-LOG-009..011 | Not Started |
| FR-NUT-001 | P2 | تغذیه اختیاری؛ غیرفعال‌بودن، تمرین را مختل نکند | — | — | — | Deferred | Deferred | — | Deferred |
| FR-NUT-002 | P2 | انرژی/ماکرو/آب تخمینی و قابل بازبینی | — | — | — | Deferred | Deferred | — | Deferred |
| FR-NUT-003 | P2 | آلرژی = محدودیت سخت | — | — | — | Deferred | Deferred | — | Deferred |
| FR-NUT-004 | P2 | رد رژیم محدودکننده در نشانه اختلال خوردن | — | — | — | Deferred | Deferred | — | Deferred |
| FR-NUT-005 | P2 | رد اهداف افراطی/انرژی خطرناک | — | — | — | Deferred | Deferred | — | Deferred |
| FR-ONB-001 | P0 / 1 | Onboarding مرحله‌ای، شرطی، قابل ادامه (۱۴ مرحله سند مادر) | US-ONB-001 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | TST-ONB-001..005 | Not Started |
| FR-ONB-002 | P0 / 1 | توضیح دلیل دریافت داده حساس در هر مرحله | US-ONB-001 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | TST-ONB-001..005 | Not Started |
| FR-ONB-003 | P0 / 1 | خلاصه و تأیید پیش از تولید برنامه | US-ONB-001 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | TST-ONB-001..005 | Not Started |
| FR-ONB-004 | P0 / 1 | غربالگری ایمنی اجباری پیش از اولین برنامه | US-ONB-003 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | TST-ONB-007 | Not Started |
| FR-ONB-005 | P0 / 1 | اهداف اصلی/فرعی | US-ONB-001, US-ONB-002 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | TST-ONB-001..005, TST-ONB-006 | Not Started |
| FR-ONB-006 | P1 / 3 | تغذیه اختیاری (فعال‌سازی) | US-ONB-004 | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | — | Not Started |
| FR-ONB-007 | P2 / 3 | بودجه | — | PG-ONB-001 | API-ONB-001..003 | assessments, assessment_answers, user_goals, training_profiles… | SVC-OnboardingService | — | Deferred |
| FR-PRF-001 | P2 / 6 | پنل مربی/متخصص با رضایت کاربر | — | — | — | Deferred | Deferred | — | Deferred |
| FR-PRF-002 | P2 / 6 | راستی‌آزمایی صلاحیت (DEC-120) | — | — | — | Deferred | Deferred | — | Deferred |
| FR-PRIV-001 | P0 / 1 | رضایت جداگانه و نسخه‌دار برای: شرایط استفاده، داده سلامت، عکس بدن، اتص… | US-PRIV-001 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-001..004 | Not Started |
| FR-PRIV-002 | P0 / 1 | عدم تولید برنامه بدون رضایت داده سلامت لازم | US-PRIV-001 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-001..004 | Not Started |
| FR-PRIV-003 | P0 / 1 | مشاهده و اصلاح داده | US-PRIV-002 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-005..008 | Not Started |
| FR-PRIV-004 | P0 / 1 | خروجی گرفتن از داده (قالب ماشین‌خوان) | US-PRIV-002 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-005..008 | Not Started |
| FR-PRIV-005 | P0 / 1 | حذف حساب و داده طبق سیاست retention (DEC-112) | US-PRIV-002 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-005..008 | Not Started |
| FR-PRIV-006 | P0 / 1 | لغو رضایت و اثر آن بر قابلیت‌ها | US-PRIV-001 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-001..004 | Not Started |
| FR-PRIV-007 | P0 / 1 | ممیزی دسترسی به داده حساس | US-PRIV-003 | PG-PRIV-001, PG-ONB-001 | API-PRIV-001..005 | consent_documents, user_consents, data_requests, audit_logs | SVC-ConsentService, SVC-DataRightsService | TST-PRIV-009 | Not Started |
| FR-PRO-001 | P0 / 1 | پروفایل: نام نمایشی، تاریخ تولد، کشور، منطقه زمانی، زبان، واحد، تقویم … | US-PRO-001 | PG-PRO-001 | API-PRO-001/002 | user_profiles, user_preferences | SVC-ProfileService | TST-PRO-001..003 | Not Started |
| FR-PRO-002 | P0 / 1 | جنسیت فقط در محاسبات دارای ارتباط معتبر؛ فیلد اختیاری | US-PRO-002 | PG-PRO-001 | API-PRO-001/002 | user_profiles, user_preferences | SVC-ProfileService | TST-PRO-004 | Not Started |
| FR-PROG-001 | P1 / 1–2 | گزارش هفتگی/ماهانه (پایبندی، حجم، رکورد) | US-LOG-003, US-DASH-001 | PG-PROG-001, PG-DASH-001 | API-PROG-001/002, API-DASH-001 | workout_sessions, exercise_logs | SVC-ProgressService | TST-DASH-001..003, TST-LOG-012..013 | Not Started |
| FR-PROG-002 | P0 / 1 | عدم استنتاج پزشکی از داده ناقص | US-PROG-002 | PG-PROG-001, PG-DASH-001 | API-PROG-001/002, API-DASH-001 | workout_sessions, exercise_logs | SVC-ProgressService | TST-PROG-001 | Not Started |
| FR-REC-001 | P1 / 2 | چک‌این روزانه (خواب، انرژی، خستگی، درد) | US-REC-001 | — | — | daily_checkins (Deferred) | Deferred | — | Deferred |
| FR-REC-002 | P2 / 4 | خلاصه ریکاوری و پیشنهاد بازبینی | — | — | — | daily_checkins (Deferred) | Deferred | — | Deferred |
| FR-SAFE-001 | P0 / 1 | غربالگری علائم هشدار پیش از هر تولید برنامه | US-SAFE-001 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-001..003 | Not Started |
| FR-SAFE-002 | P0 / 1 | توقف و ارجاع در صورت علائم هشدار؛ بدون تولید برنامه | US-SAFE-001 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-001..003 | Not Started |
| FR-SAFE-003 | P0 / 1 | فیلتر سخت حرکات بر اساس محدودیت و منع | US-SAFE-002 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-004..009 | Not Started |
| FR-SAFE-004 | P0 / 1 | سازگاری حرکت با وضعیت فرد (برچسب‌های ساختاریافته) | US-SAFE-002 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-004..009 | Not Started |
| FR-SAFE-005 | P0 / 1 | مسیر A (سابقه بدون درد فعال) | US-SAFE-003 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-010..012 | Not Started |
| FR-SAFE-006 | P0 / 1 | مسیر B (درد جدید/نامشخص) — طراحی عملیاتی در سند 9 §7.2؛ قواعد Draft تا… | US-SAFE-004 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-013..016 | Not Started |
| FR-SAFE-007 | P2 / 2+ (نیازمند EXP-005) | مسیر C — اجرای برنامه تأییدشده متخصص | — | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | — | Deferred |
| FR-SAFE-008 | P0 / 1 | جایگزین معتبر یا اعلام «جایگزین نداریم» | US-SAFE-002, US-WO-003 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-004..009, TST-WO-014..016 | Not Started |
| FR-SAFE-009 | P0 / 1 | امکان کاهش شدت، جایگزینی و توقف تمرین در جلسه | US-SAFE-007, US-WO-003 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-023, TST-WO-014..016 | Not Started |
| FR-SAFE-010 | P0 / 1 | ثبت هر تصمیم ایمنی با نسخه قانون (قابل ممیزی) | US-SAFE-006 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-020..022 | Not Started |
| FR-SAFE-011 | P0 / 1 | Fail-safe: خطا/ابهام در Safety Core → عدم نمایش برنامه | US-SAFE-006 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-020..022 | Not Started |
| FR-SAFE-012 | P0 / 1 | هیچ تشویقی به تحمل درد | US-SAFE-008 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-024 | Not Started |
| FR-SAFE-013 | P1 / 2 | پایش علائم و ارجاع در تشدید | US-SAFE-007 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-023 | Not Started |
| FR-SAFE-014 | P0 / 1 | گروه‌های خارج از دامنه (DEC-121) | US-SAFE-005 | PG-HEALTH-001, PG-WO-001, PG-WO-002, PG-EX-002 | API-HEALTH-006, API-EX-003, API-WO-001 | safety_rule_versions, safety_rules, safety_decisions, red_flag_events | safety_core.engine | TST-SAFE-017..019 | Not Started |
| FR-SUB-001 | P0 / 1 | پلن Free با ایمنی کامل و هسته قابل‌استفاده (DEC-005/110/126، §5.13.1) | US-SUB-001 | PG-PUB-002, PG-SUB-001, PG-ADM-004 | API-SUB-001..004, API-ADM-008 | features, subscription_plans, plan_features, plan_quotas… | SVC-EntitlementService | TST-SUB-001..004 | Not Started |
| FR-SUB-002 | P1 / 1–6 | پلن‌های Essential/Pro/Elite/Professional قابل پیکربندی | US-SUB-002 | PG-PUB-002, PG-SUB-001, PG-ADM-004 | API-SUB-001..004, API-ADM-008 | features, subscription_plans, plan_features, plan_quotas… | SVC-EntitlementService | TST-SUB-005 | Not Started |
| FR-SUB-003 | P0 / 1 | Feature gating که ایمنی را قفل نکند | US-SUB-001 | PG-PUB-002, PG-SUB-001, PG-ADM-004 | API-SUB-001..004, API-ADM-008 | features, subscription_plans, plan_features, plan_quotas… | SVC-EntitlementService | TST-SUB-001..004 | Not Started |
| FR-SUB-004 | P2 / 6 | لغو ساده، صورتحساب، بازپرداخت | — | PG-PUB-002, PG-SUB-001, PG-ADM-004 | API-SUB-001..004, API-ADM-008 | features, subscription_plans, plan_features, plan_quotas… | SVC-EntitlementService | — | Deferred |
| FR-SUB-005 | P1 / 1 | PaymentProvider Interface | US-SUB-003 | PG-PUB-002, PG-SUB-001, PG-ADM-004 | API-SUB-001..004, API-ADM-008 | features, subscription_plans, plan_features, plan_quotas… | SVC-EntitlementService | TST-SUB-006 | Not Started |
| FR-SUP-001 | P2 | دانشنامه مکمل با شواهد/عوارض/تداخل | — | — | — | Deferred | Deferred | — | Deferred |
| FR-WO-001 | P0 / 1 | تولید برنامه بر اساس هدف، سطح، تجهیزات، زمان، محدودیت | US-WO-001 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-001..010 | Not Started |
| FR-WO-002 | P0 / 1 | ساختارهای Full Body، Upper/Lower، PPL، Hybrid، شخصی؛ بدون تحمیل | US-WO-001 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-001..010 | Not Started |
| FR-WO-003 | P0 / 1 | هر جلسه: گرم‌کردن، اصلی، کمکی، سردکردن، ست/تکرار، RPE/RIR، استراحت | US-WO-001 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-001..010 | Not Started |
| FR-WO-004 | P1 / 1–2 | پیشرفت تدریجی (Double/Linear Progression) و Deload | US-WO-004 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-017..019 | Not Started |
| FR-WO-005 | P0 / 1 | نمایش دلیل انتخاب و سطح اطمینان | US-WO-001 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-001..010 | Not Started |
| FR-WO-006 | P0 / 1 | نسخه‌بندی برنامه و ثبت رویداد تغییر | US-WO-002 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-011..013 | Not Started |
| FR-WO-007 | P0 / 1 | عبور تمام حرکات از Safety Core | US-WO-001 | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | TST-WO-001..010 | Not Started |
| FR-WO-008 | P2 / 4–5 | رشته‌های ورزشی (دویدن، شنا، …) | — | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | — | Deferred |
| FR-WO-009 | P2 / 4 | تطبیق برنامه بر اساس عملکرد/ریکاوری | — | PG-WO-001 | API-WO-001..004 | workout_plans, workout_plan_versions, workout_phases, workout_days… | workout_engine.planner | — | Deferred |

## خلاصه پوشش
- کل FR: 112؛ دارای US (غیر Deferred): 85؛ Deferred: 27؛ **بدون پوشش (P0/P1): 0** 
- US ها: 51
- هر API (DOC-07) در ستون API یا Deferred مرتبط است؛ بررسی خودکار: `tools/check_api_trace.py`.

## NFR/Safety Acceptance → تست
| معیار | تست/کنترل | سند |
|---|---|---|
| AC-SAF-001..006 | tests/architecture + safety suite | DOC-09 |
| AC-ARCH-001..005 | import-linter + AST | DOC-03 |
| AC-SEC-001..009 | permission matrix + scans | DOC-15 |
| AC-WO-001..007 | workout_engine tests | DOC-11 |
| AC-EX-001..005 | exercise catalog tests | DOC-10 |
| AC-AI-001..006 | ai_gateway tests | DOC-08 |
| AC-UI-001..005 | Playwright | DOC-14 |
| AC-DS-001..004 | lint + a11y | DOC-13 |
| AC-OPS-001..004 | CI | DOC-17 |
