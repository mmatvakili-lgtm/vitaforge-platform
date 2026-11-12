import yaml, json
# (id, method, path, tag, summary, auth, roles, req_schema, resp_schema, success, errors, extra_params)
U="user"; PUB="public"
EP=[
("API-AUTH-001","post","/auth/register","auth","ثبت‌نام (سن ≥ ۱۸)",PUB,"", "RegisterRequest","Message","201",["400","409","422","429"]),
("API-AUTH-002","post","/auth/verify","auth","تأیید حساب",PUB,"","VerifyRequest","Message","200",["400","410","429"]),
("API-AUTH-003","post","/auth/login","auth","ورود",PUB,"","LoginRequest","SessionInfo","200",["400","401","423","429"]),
("API-AUTH-004","post","/auth/logout","auth","خروج",U,"",None,"Message","200",["401"]),
("API-AUTH-005","post","/auth/password-reset/request","auth","درخواست بازیابی رمز",PUB,"","EmailOnlyRequest","Message","202",["400","429"]),
("API-AUTH-006","post","/auth/password-reset/confirm","auth","تأیید بازیابی رمز",PUB,"","PasswordResetConfirm","Message","200",["400","410"]),
("API-AUTH-007","get","/auth/sessions","auth","نشست‌های فعال",U,"",None,"SessionList","200",["401"]),
("API-AUTH-008","delete","/auth/sessions/{session_id}","auth","ابطال نشست",U,"",None,"Message","200",["401","404"]),
("API-AUTH-009","post","/auth/verify/resend","auth","ارسال مجدد کد تأیید",PUB,"","EmailOnlyRequest","Message","202",["400","429"]),
("API-PRO-001","get","/profile","profile","دریافت پروفایل",U,"",None,"Profile","200",["401"]),
("API-PRO-002","patch","/profile","profile","به‌روزرسانی پروفایل/تنظیمات i18n",U,"","ProfileUpdate","Profile","200",["400","401","422"]),
("API-PRIV-001","get","/consents/documents","privacy","متن‌های رضایت فعال",U,"",None,"ConsentDocumentList","200",["401"]),
("API-PRIV-002","post","/consents","privacy","ثبت/لغو رضایت",U,"","ConsentRequest","Consent","201",["400","401","404"]),
("API-PRIV-003","post","/privacy/export","privacy","درخواست خروجی داده",U,"",None,"DataRequest","202",["401","429"]),
("API-PRIV-004","post","/privacy/delete","privacy","درخواست حذف حساب/داده",U,"","DeleteRequest","DataRequest","202",["400","401"]),
("API-PRIV-005","get","/privacy/requests/{request_id}","privacy","وضعیت درخواست",U,"",None,"DataRequest","200",["401","404"]),
("API-PRIV-006","get","/privacy/export/{request_id}","privacy","دانلود خروجی داده (۲۴ ساعت)",U,"",None,"PrivacyExport","200",["401","404","410"]),
("API-ONB-001","get","/onboarding","onboarding","وضعیت Onboarding",U,"",None,"Onboarding","200",["401"]),
("API-ONB-002","put","/onboarding/steps/{step}","onboarding","ثبت پاسخ مرحله",U,"","OnboardingStepRequest","Onboarding","200",["400","401","422"]),
("API-ONB-003","post","/onboarding/complete","onboarding","تأیید نهایی و تکمیل",U,"",None,"Onboarding","200",["401","409","422"]),
("API-BODY-001","get","/body/overview","body","خلاصه بدن (BMI/WHtR برچسب شاخص غربالگری)",U,"",None,"BodyOverview","200",["401"]),
("API-BODY-002","post","/body/measurements","body","ثبت اندازه‌گیری",U,"","MeasurementRequest","Measurement","201",["400","401","422"]),
("API-HEALTH-001","get","/health/profile","health","پروفایل سلامت (نیازمند رضایت)",U,"",None,"HealthProfile","200",["401","403"]),
("API-HEALTH-002","post","/health/conditions","health","ثبت محدودیت/درد/آسیب",U,"","ConditionRequest","Condition","201",["400","401","403","422"]),
("API-HEALTH-003","patch","/health/conditions/{condition_id}","health","به‌روزرسانی مورد",U,"","ConditionUpdate","Condition","200",["400","401","403","404"]),
("API-HEALTH-004","post","/health/symptoms","health","ثبت علائم (فقط آنلاین)",U,"","SymptomRequest","Symptom","201",["400","401","403","422"]),
("API-HEALTH-005","post","/health/pain-logs","health","ثبت درد حین/بعد تمرین",U,"","PainLogRequest","PainLog","201",["400","401","403","422"]),
("API-HEALTH-006","post","/health/screening","health","ارسال غربالگری هشدار و دریافت SafetyDecision",U,"","ScreeningRequest","SafetyDecision","200",["400","401","403","422"]),
("API-HEALTH-007","post","/health/out-of-scope-flags","health","ثبت بارداری/شرایط پرخطر",U,"","OutOfScopeRequest","SafetyDecision","201",["400","401","403"]),
("API-EX-001","get","/exercises","exercises","فهرست حرکات منتشرشده",U,"",None,"ExerciseList","200",["400","401"]),
("API-EX-002","get","/exercises/{exercise_id}","exercises","جزئیات حرکت (با سازگاری برای کاربر)",U,"",None,"ExerciseDetail","200",["401","404"]),
("API-EX-003","get","/exercises/{exercise_id}/alternatives","exercises","جایگزین‌های معتبر (از Safety Core)",U,"",None,"AlternativesResult","200",["401","403","404"]),
("API-WO-001","post","/workouts/generate","workouts","تولید برنامه؛ فقط با SafetyDecision مجاز",U,"","GenerateRequest","GenerateResponse","200",["401","403","409","422"]),
("API-WO-002","get","/workouts/current","workouts","برنامه فعال",U,"",None,"WorkoutPlan","200",["401","404"]),
("API-WO-003","get","/workouts/plans/{plan_id}/versions","workouts","نسخه‌های برنامه",U,"",None,"PlanVersionList","200",["401","404"]),
("API-WO-004","post","/workouts/plans/{plan_id}/substitute","workouts","جایگزینی حرکت",U,"","SubstituteRequest","WorkoutPlan","200",["401","403","404","409","422"]),
("API-LOG-001","post","/workouts/sessions","logs","شروع جلسه",U,"","SessionStartRequest","WorkoutSession","201",["401","403","409","422"]),
("API-LOG-002","post","/workouts/sessions/{session_id}/logs","logs","ثبت ست (idempotent با client_uuid)",U,"","SetLogRequest","SetLog","201",["400","401","404","409","422"]),
("API-LOG-003","post","/workouts/sessions/{session_id}/finish","logs","پایان جلسه",U,"","SessionFinishRequest","SessionSummary","200",["400","401","404","409"]),
("API-LOG-004","get","/workouts/sessions","logs","تاریخچه جلسات",U,"",None,"SessionList2","200",["400","401"]),
("API-PROG-001","get","/progress/weekly","progress","گزارش هفتگی",U,"",None,"ProgressReport","200",["401"]),
("API-PROG-002","get","/progress/monthly","progress","گزارش ماهانه (Essential+)",U,"",None,"ProgressReport","200",["401","402"]),
("API-DASH-001","get","/dashboard","progress","داشبورد امروز",U,"",None,"Dashboard","200",["401"]),
("API-SUB-001","get","/subscriptions/plans","subscriptions","پلن‌ها و Entitlementها",PUB,"",None,"PlanCatalog","200",[]),
("API-SUB-002","get","/subscriptions/me","subscriptions","اشتراک و سهمیه من",U,"",None,"MySubscription","200",["401"]),
("API-SUB-003","post","/subscriptions/checkout","subscriptions","شروع پرداخت (PaymentProvider)",U,"","CheckoutRequest","CheckoutSession","201",["400","401","501"]),
("API-SUB-004","post","/subscriptions/cancel","subscriptions","لغو اشتراک",U,"",None,"MySubscription","200",["401","404"]),
("API-AI-001","post","/ai/chat","ai","گفتگو (Provider-agnostic؛ پس از Validator)",U,"","AiChatRequest","AiChatResponse","200",["400","401","402","403","429","503"]),
("API-ADM-001","get","/admin/exercises","admin","فهرست حرکات (همه وضعیت‌ها)","staff","content_admin|exercise_reviewer|super_admin",None,"ExerciseAdminList","200",["401","403"]),
("API-ADM-002","post","/admin/exercises","admin","ایجاد حرکت Draft","staff","content_admin|super_admin","ExerciseAdminWrite","ExerciseAdmin","201",["400","401","403","422"]),
("API-ADM-003","post","/admin/exercises/{exercise_id}/transition","admin","انتقال در گردش بازبینی","staff","exercise_reviewer|clinical_safety_reviewer|super_admin","TransitionRequest","ExerciseAdmin","200",["400","401","403","404","409"]),
("API-ADM-004","get","/admin/safety/rule-sets","admin","نسخه‌های قواعد ایمنی","staff","clinical_safety_reviewer|content_admin|super_admin",None,"RuleSetList","200",["401","403"]),
("API-ADM-005","post","/admin/safety/rule-sets/{rule_set_id}/publish","admin","انتشار نسخه قواعد (نیازمند Reviewer)","staff","clinical_safety_reviewer","PublishRuleSetRequest","RuleSet","200",["400","401","403","404","409"]),
("API-ADM-006","get","/admin/users","admin","کاربران (بدون داده سلامت)","staff","support_admin|super_admin",None,"AdminUserList","200",["401","403"]),
("API-ADM-007","post","/admin/health-access-grants","admin","اعطای دسترسی زمان‌دار به داده سلامت","staff","super_admin","HealthGrantRequest","HealthGrant","201",["400","401","403"]),
("API-ADM-008","put","/admin/plans/{plan_id}/features","admin","تنظیم قابلیت‌های پلن (safety_critical غیرقابل‌خاموش)","staff","super_admin|finance_admin","PlanFeaturesRequest","PlanCatalog","200",["400","401","403","404","422"]),
("API-NUT-001","put","/nutrition/profile","nutrition","ثبت پروفایل تغذیه و دریافت برآورد انرژی (نیازمند رضایت سلامت؛ پشت Safety Core)",U,"","NutritionProfileRequest","NutritionEstimate","200",["400","401","403","422"]),
("API-NUT-002","get","/nutrition/estimate","nutrition","برآورد فعلی انرژی/درشت‌مغذی‌ها (نیازمند رضایت سلامت)",U,"",None,"NutritionEstimate","200",["401","403","404"]),
("API-FOOD-001","get","/foods","foods","مرور غذاها (فقط داده‌ی بازبینی‌شده؛ آزمایشی با برچسب)",U,"",None,"FoodList","200",["400","401"]),
("API-FOOD-002","get","/foods/{food_id}","foods","جزئیات غذا با منبع و مجوز",U,"",None,"FoodDetail","200",["401","404"]),
("API-REC-001","get","/recipes","foods","مرور دستورهای پخت",U,"",None,"RecipeList","200",["400","401"]),
("API-REC-002","get","/recipes/{recipe_id}","foods","جزئیات دستور پخت با ارزش غذایی هر وعده",U,"",None,"RecipeDetail","200",["401","404"]),
("API-NUT-004","post","/nutrition/meals","nutrition","ثبت وعده (از غذا، دستور پخت یا ورودی کاربر؛ نیازمند رضایت سلامت و نتیجه‌ی تغذیه OK)",U,"","MealLogRequest","MealEntry","201",["400","401","403","404","409","422"]),
("API-NUT-005","get","/nutrition/meals","nutrition","وعده‌های ثبت‌شده‌ی یک روز",U,"",None,"MealLogDay","200",["400","401","403","404","409"]),
("API-NUT-006","delete","/nutrition/meals/{meal_id}","nutrition","حذف وعده‌ی ثبت‌شده",U,"",None,"Message","200",["401","403","404","409"]),
("API-NUT-007","post","/nutrition/water","nutrition","ثبت آب مصرفی",U,"","WaterRequest","WaterTotal","201",["400","401","403","422"]),
("API-NUT-008","get","/nutrition/summary","nutrition","خلاصه‌ی روز در برابر برآورد (نیازمند نتیجه‌ی OK)",U,"",None,"NutritionDaySummary","200",["400","401","403","404","409"]),
("API-NUT-009","get","/nutrition/prices","nutrition","قیمت‌های واردشده‌ی کاربر",U,"",None,"UserPriceList","200",["401"]),
("API-NUT-010","put","/nutrition/prices","nutrition","ثبت قیمت هر کیلو توسط کاربر (برای بودجه)",U,"","UserPriceRequest","UserPrice","200",["400","401","404","422"]),
("API-NUT-011","delete","/nutrition/prices/{food_id}","nutrition","حذف قیمت واردشده",U,"",None,"Message","200",["401","404"]),
("API-NUT-012","get","/nutrition/shopping-state","nutrition","وضعیت تیک‌خوردن لیست خرید",U,"",None,"ShoppingState","200",["401"]),
("API-NUT-013","put","/nutrition/shopping-state","nutrition","ذخیره‌ی وضعیت لیست خرید",U,"","ShoppingState","ShoppingState","200",["400","401","422"]),
("API-WO-005","get","/workouts/progression","workouts","پیشنهاد پیشرفت قابل‌توضیح برای حرکت‌های برنامه (فقط پیشنهاد)",U,"",None,"ProgressionList","200",["401","404","409"]),
("API-NUT-003","post","/nutrition/meal-plan","nutrition","برنامه غذایی هفتگی؛ بدون داده بازبینی‌شده NEEDS_CONTENT (نیازمند رضایت سلامت)",U,"","MealPlanRequest","MealPlanResponse","200",["400","401","403","404","422"]),
("API-SYS-001","get","/health/live","system","Liveness (بدون وابستگی)",PUB,"",None,"Message","200",[]),
("API-SYS-002","get","/health/ready","system","Readiness (DB/Redis)",PUB,"",None,"Message","200",["503"]),
]
ERR_TXT={"400":"درخواست نامعتبر","401":"احراز هویت لازم","402":"نیازمند ارتقای پلن (غیرایمنی)","403":"دسترسی/رضایت/مجوز لازم","404":"یافت نشد","409":"تعارض وضعیت","410":"منقضی","422":"خطای اعتبارسنجی","423":"حساب قفل","429":"محدودیت نرخ","501":"درگاه پرداخت پیکربندی نشده","503":"سرویس در دسترس نیست"}
schemas={}
def obj(props,req=None,desc=None):
    d={"type":"object","properties":props,"additionalProperties":False}
    if req:d["required"]=req
    if desc:d["description"]=desc
    return d
S=lambda **k:{"type":"string",**k}
schemas.update({
"Error":obj({"code":S(),"message":S(),"details":{"type":"object","additionalProperties":True},"request_id":S()},["code","message"]),
"Message":obj({"message":S()},["message"]),
"RegisterRequest":obj({"email":S(format="email"),"phone":S(pattern=r"^\+[1-9]\d{6,14}$"),"password":S(minLength=10,maxLength=128),"date_of_birth":S(format="date"),"language":{"enum":["fa","en"]}},["password","date_of_birth"]),
"VerifyRequest":obj({"identifier":S(),"code":S(minLength=6,maxLength=6)},["identifier","code"]),
"LoginRequest":obj({"identifier":S(),"password":S()},["identifier","password"]),
"EmailOnlyRequest":obj({"identifier":S()},["identifier"]),
"PasswordResetConfirm":obj({"token":S(),"new_password":S(minLength=10)},["token","new_password"]),
"SessionInfo":obj({"user_id":S(format="uuid"),"expires_at":S(format="date-time"),"onboarding_status":{"enum":["not_started","in_progress","completed"]}}),
"SessionList":{"type":"array","items":obj({"id":S(format="uuid"),"last_seen_at":S(format="date-time"),"user_agent":S(),"current":{"type":"boolean"}})},
"Profile":obj({"display_name":S(),"sex":{"enum":["female","male","unspecified"]},"country":S(),"timezone":S(),"language":{"enum":["fa","en"]},"calendar":{"enum":["jalali","gregorian"]},"unit_system":{"enum":["metric","imperial"]},"digit_style":{"enum":["latin","persian"]},"onboarding_status":S()}),
"ProfileUpdate":obj({"display_name":S(maxLength=80),"sex":{"enum":["female","male","unspecified"]},"country":S(minLength=2,maxLength=2),"timezone":S(),"language":{"enum":["fa","en"]},"calendar":{"enum":["jalali","gregorian"]},"unit_system":{"enum":["metric","imperial"]},"digit_style":{"enum":["latin","persian"]}}),
"ConsentDocumentList":{"type":"array","items":obj({"id":S(format="uuid"),"type":{"enum":["terms","health_data","photo","device"]},"version":{"type":"integer"},"locale":S(),"body":S()})},
"ConsentRequest":obj({"document_id":S(format="uuid"),"granted":{"type":"boolean"}},["document_id","granted"]),
"Consent":obj({"id":S(format="uuid"),"type":S(),"granted":{"type":"boolean"},"granted_at":S(format="date-time")}),
"DeleteRequest":obj({"password":S(),"confirm":{"const":True}},["password","confirm"]),
"PrivacyExport":{"type":"object","additionalProperties":True,"description":"خروجی کامل داده‌های کاربر؛ بدون رمز و توکن؛ فقط برای مالک و ۲۴ ساعت."},
"DataRequest":obj({"id":S(format="uuid"),"type":{"enum":["export","delete"]},"status":{"enum":["requested","processing","completed","failed"]}}),
"Onboarding":obj({"status":S(),"current_step":{"type":"integer","minimum":1,"maximum":14},"answers":{"type":"object","additionalProperties":True},"summary_ready":{"type":"boolean"},"safety_screening_complete":{"type":"boolean"}}),
"OnboardingStepRequest":obj({"answers":{"type":"object","additionalProperties":True}},["answers"]),
"MeasurementRequest":obj({"metric":{"enum":["height","weight","waist","abdomen","chest","arm","forearm","thigh","calf","body_fat_pct","lean_mass"]},"value":{"type":"number","exclusiveMinimum":0},"unit":S(),"source":{"enum":["measured","estimated"]},"method":S(),"measured_at":S(format="date-time")},["metric","value","unit","source"]),
"Measurement":obj({"id":S(format="uuid"),"metric":S(),"value":{"type":"number"},"unit":S(),"source":S(),"measured_at":S(format="date-time")}),
"BodyOverview":obj({"latest":{"type":"object","additionalProperties":True},"bmi":obj({"value":{"type":"number"},"label":{"const":"screening_index"}}),"whtr":obj({"value":{"type":"number"},"label":{"const":"screening_index"}}),"trend_notes":{"type":"array","items":S()}}),
"HealthProfile":obj({"conditions":{"type":"array","items":{"$ref":"#/components/schemas/Condition"}},"out_of_scope":{"type":"array","items":S()},"latest_decision":{"$ref":"#/components/schemas/SafetyDecision"}}),
"ConditionRequest":obj({"region":S(),"side":{"enum":["left","right","both","na"]},"problem_type":{"enum":["pain","limited_motion","diagnosed_injury","surgery_history","other"]},"onset_date":S(format="date"),"trend":{"enum":["better","same","worse","unknown"]},"self_severity":{"type":"integer","minimum":0,"maximum":10},"aggravating_factors":S(),"relieving_factors":S()},["region","problem_type"],"خوداظهاری؛ فیلدهای تشخیص/محدودیت متخصص پذیرفته نمی‌شوند (mass-assignment محافظت‌شده)."),
"ConditionUpdate":obj({"trend":S(),"self_severity":{"type":"integer","minimum":0,"maximum":10},"aggravating_factors":S(),"relieving_factors":S()}),
"Condition":obj({"id":S(format="uuid"),"region":S(),"side":S(),"problem_type":S(),"status":S(),"source":{"enum":["self_reported","professional"]},"trend":S(),"self_severity":{"type":"integer"}}),
"SymptomRequest":obj({"context":{"enum":["screening","before_session","during_session","after_session","checkin"]},"region":S(),"severity":{"type":"integer","minimum":0,"maximum":10},"note":S(maxLength=500)},["context","region"]),
"Symptom":obj({"id":S(format="uuid"),"recorded_at":S(format="date-time")}),
"PainLogRequest":obj({"session_id":S(format="uuid"),"region":S(),"side":S(),"intensity":{"type":"integer","minimum":0,"maximum":10},"timing":{"enum":["before","during","after","general"]}},["region","intensity","timing"]),
"PainLog":obj({"id":S(format="uuid"),"decision":{"$ref":"#/components/schemas/SafetyDecision"}}),
"ScreeningRequest":obj({"screening_version":{"type":"integer"},"answers":{"type":"object","additionalProperties":True}},["screening_version","answers"]),
"OutOfScopeRequest":obj({"flag_type":{"enum":["pregnancy","high_risk_condition","other"]}},["flag_type"]),
"SafetyDecision":obj({"decision_id":S(format="uuid"),"status":{"enum":["ALLOW","ALLOW_WITH_MODIFICATION","RESTRICT","NEEDS_INFO","STOP_AND_REFER","BLOCK_OUT_OF_SCOPE","BLOCK_CONSENT","ERROR_FAILSAFE"]},"reasons":{"type":"array","items":obj({"code":S(),"message_key":S()})},"required_questions":{"type":"array","items":S()},"referral":obj({"urgency":{"enum":["urgent","non_urgent"]},"message_key":S(),"content_status":{"enum":["draft_unreviewed","clinical_reviewed","published"]}}),"rule_set_version":{"type":"integer"},"evaluated_at":S(format="date-time")},["decision_id","status"]),
"ExerciseList":obj({"count":{"type":"integer"},"next":S(),"results":{"type":"array","items":{"$ref":"#/components/schemas/ExerciseSummary"}}}),
"ExerciseSummary":obj({"id":S(format="uuid"),"code":S(),"name":S(),"name_en":S(),"difficulty":S(),"muscles":{"type":"array","items":S()},"equipment":{"type":"array","items":S()},"has_media":{"type":"boolean"},"review_status":S(),"movement_pattern":S()}),
"ExerciseDetail":obj({"id":S(format="uuid"),"code":S(),"name":S(),"name_en":S(),"description":S(),"steps":{"type":"array","items":S()},"breathing":S(),"common_mistakes":{"type":"array","items":S()},"safety_notes":S(),"compatibility":obj({"status":{"enum":["allowed","caution","blocked","unknown"]},"reasons":{"type":"array","items":S()}}),"media":{"type":"array","items":obj({"type":S(),"url":S()})},"review_status":S()}),
"AlternativesResult":obj({"alternatives":{"type":"array","items":{"$ref":"#/components/schemas/ExerciseSummary"}},"none_valid":{"type":"boolean"},"decision":{"$ref":"#/components/schemas/SafetyDecision"}}),
"GenerateRequest":obj({"preferred_structure":{"enum":["auto","full_body","upper_lower","push_pull_legs","hybrid"]},"regenerate_reason":S()}),
"GenerateResponse":obj({"decision":{"$ref":"#/components/schemas/SafetyDecision"},"plan":{"oneOf":[{"$ref":"#/components/schemas/WorkoutPlan"},{"type":"null"}]}},["decision"],"plan فقط وقتی decision.status ∈ {ALLOW, ALLOW_WITH_MODIFICATION}"),
"WorkoutPlan":obj({"plan_id":S(format="uuid"),"version_no":{"type":"integer"},"structure":S(),"goal":S(),"confidence":{"enum":["high","medium","low"]},"rationale":{"type":"object","additionalProperties":True},"safety_decision_id":S(format="uuid"),"days":{"type":"array","items":{"$ref":"#/components/schemas/WorkoutDay"}}},["plan_id","version_no","safety_decision_id"]),
"WorkoutDay":obj({"day_id":S(format="uuid"),"day_index":{"type":"integer"},"title":S(),"est_minutes":{"type":"integer"},"exercises":{"type":"array","items":obj({"workout_exercise_id":S(format="uuid"),"exercise_id":S(format="uuid"),"name":S(),"role":{"enum":["warmup","main","accessory","cooldown"]},"sets":{"type":"array","items":obj({"set_no":{"type":"integer"},"reps_min":{"type":"integer"},"reps_max":{"type":"integer"},"duration_sec":{"type":"integer"},"target_rpe":{"type":"number"},"rest_sec":{"type":"integer"}})},"stop_criteria_key":S()})}}),
"PlanVersionList":{"type":"array","items":obj({"version_no":{"type":"integer"},"created_at":S(format="date-time"),"safety_decision_id":S(format="uuid")})},
"SubstituteRequest":obj({"workout_exercise_id":S(format="uuid"),"reason":{"enum":["pain","equipment","preference","other"]}},["workout_exercise_id","reason"]),
"SessionStartRequest":obj({"day_id":S(format="uuid")},["day_id"]),
"WorkoutSession":obj({"id":S(format="uuid"),"status":S(),"started_at":S(format="date-time"),"day_title":S(),"sets_done":{"type":"integer"},"volume_kg":{"type":"number"},"duration_min":{"type":"integer"},"perceived_difficulty":{"type":"integer"},"aborted_reason":S(),"logged_sets":{"type":"array","items":obj({"exercise_id":S(format="uuid"),"set_no":{"type":"integer"},"reps":{"type":"integer"},"load_kg":{"type":"number"},"skipped":{"type":"boolean"},"personal_record":{"type":"boolean"}})}}),
"SetLogRequest":obj({"client_uuid":S(format="uuid"),"exercise_id":S(format="uuid"),"set_no":{"type":"integer","minimum":1},"reps":{"type":"integer","minimum":0},"load_kg":{"type":"number","minimum":0},"duration_sec":{"type":"integer","minimum":0},"rpe":{"type":"number","minimum":1,"maximum":10},"rir":{"type":"integer","minimum":0,"maximum":10},"rest_sec":{"type":"integer","minimum":0},"skipped":{"type":"boolean"},"skipped_reason":S(),"substituted_exercise_id":S(format="uuid")},["client_uuid","exercise_id","set_no"]),
"SetLog":obj({"id":S(format="uuid"),"client_uuid":S(format="uuid"),"personal_record":{"type":"boolean"}}),
"SessionFinishRequest":obj({"perceived_difficulty":{"type":"integer","minimum":1,"maximum":10},"aborted_reason":{"enum":["pain","fatigue","time","other"]},"notes":S(maxLength=1000)}),
"SessionSummary":obj({"id":S(format="uuid"),"volume_kg":{"type":"number"},"sets_done":{"type":"integer"},"duration_min":{"type":"integer"},"safety_followup":{"$ref":"#/components/schemas/SafetyDecision"}}),
"SessionList2":{"type":"array","items":{"$ref":"#/components/schemas/WorkoutSession"}},
"ProgressReport":obj({"period":S(),"planned_sessions":{"type":"integer"},"completed_sessions":{"type":"integer"},"adherence_pct":{"type":"number"},"volume_kg":{"type":"number"},"records":{"type":"array","items":S()},"notes":{"type":"array","items":S()}}),
"Dashboard":obj({"today":{"type":"object","additionalProperties":True},"current_plan":{"type":"object","additionalProperties":True},"weekly_summary":{"type":"object","additionalProperties":True},"alerts":{"type":"array","items":{"$ref":"#/components/schemas/SafetyDecision"}}}),
"PlanCatalog":obj({"plans":{"type":"array","items":obj({"code":S(),"is_free":{"type":"boolean"},"features":{"type":"array","items":obj({"code":S(),"enabled":{"type":"boolean"},"safety_critical":{"type":"boolean"}})},"quotas":{"type":"object","additionalProperties":{"type":["integer","null"]}}})}}),
"MySubscription":obj({"plan_code":S(),"status":S(),"current_period_end":S(format="date-time"),"quotas_remaining":{"type":"object","additionalProperties":{"type":["integer","null"]}}}),
"CheckoutRequest":obj({"plan_code":S(),"billing_cycle":{"enum":["monthly","yearly"]}},["plan_code","billing_cycle"]),
"CheckoutSession":obj({"redirect_url":S(),"provider":S()}),
"AiChatRequest":obj({"purpose":{"enum":["explain_plan","technique","general"]},"message":S(maxLength=2000)},["purpose","message"]),
"AiChatResponse":obj({"answer":S(),"uncertainty":{"enum":["none","low","medium","high"]},"sources":{"type":"array","items":S()},"decision":{"$ref":"#/components/schemas/SafetyDecision"},"mode":{"enum":["llm","rule_based_fallback"]}},["answer","mode"]),
"ExerciseAdminList":{"type":"array","items":{"$ref":"#/components/schemas/ExerciseAdmin"}},
"ExerciseAdminWrite":obj({"stable_code":S(),"movement_pattern":S(),"difficulty":S(),"translations":{"type":"object","additionalProperties":True},"muscles":{"type":"array","items":S()},"equipment":{"type":"array","items":S()},"region_loads":{"type":"object","additionalProperties":{"type":"string"}}},["stable_code","movement_pattern","difficulty"]),
"ExerciseAdmin":obj({"id":S(format="uuid"),"stable_code":S(),"review_status":{"enum":["draft","scientific_review","safety_review","published","retired"]},"version":{"type":"integer"},"safety_tags_complete":{"type":"boolean"}}),
"TransitionRequest":obj({"to_status":{"enum":["scientific_review","safety_review","published","retired","draft"]},"notes":S()},["to_status"]),
"RuleSetList":{"type":"array","items":{"$ref":"#/components/schemas/RuleSet"}},
"RuleSet":obj({"id":S(format="uuid"),"version":{"type":"integer"},"status":{"enum":["draft_unreviewed","clinical_reviewed","published","retired"]},"reviewed_by":S(format="uuid")}),
"PublishRuleSetRequest":obj({"confirm_sources_attached":{"const":True},"notes":S()},["confirm_sources_attached"]),
"AdminUserList":{"type":"array","items":obj({"id":S(format="uuid"),"status":S(),"roles":{"type":"array","items":S()}})},
"HealthGrantRequest":obj({"grantee_id":S(format="uuid"),"subject_user_id":S(format="uuid"),"reason":S(minLength=10),"duration_minutes":{"type":"integer","minimum":1,"maximum":240}},["grantee_id","subject_user_id","reason","duration_minutes"]),
"HealthGrant":obj({"id":S(format="uuid"),"expires_at":S(format="date-time")}),
"NutritionProfileRequest":obj({"sex":{"enum":["male","female"]},"height_cm":{"type":"number","minimum":100,"maximum":250},"weight_kg":{"type":"number","minimum":25,"maximum":400},"activity":{"enum":["sedentary","light","moderate","active","very_active"]},"goal":{"enum":["maintain","lose","gain"]},"allergens":{"type":"array","items":{"enum":["milk","egg","fish","shellfish","tree_nut","peanut","wheat","soy","sesame"]},"maxItems":9,"uniqueItems":True},"diet_required":{"type":"array","items":{"enum":["vegetarian","vegan","halal","gluten_free","lactose_free"]},"maxItems":5,"uniqueItems":True},"screening":obj({"eating_disorder_risk":{"type":"boolean"},"medical_diet_needed":{"type":"boolean"},"pregnant_or_lactating":{"type":"boolean"}},["eating_disorder_risk","medical_diet_needed","pregnant_or_lactating"])},["height_cm","weight_kg","activity","screening"],"سن از Onboarding گرفته می‌شود. goal جز maintain تا بازبینی متخصص فقط برچسب می‌خورد (NUT-R03) و هدف عددی ساخته نمی‌شود."),
"NutritionEstimate":obj({"allergens":{"type":"array","items":S()},"diet_required":{"type":"array","items":S()},"status":{"enum":["OK","NEEDS_INFO","BLOCKED","REFER"]},"reasons":{"type":"array","items":S()},"questions":{"type":"array","items":S()},"bmr":{"type":["array","null"],"items":{"type":"number"},"minItems":3,"maxItems":3},"tdee":{"type":["array","null"],"items":{"type":"number"},"minItems":3,"maxItems":3},"macros":{"type":["object","null"],"additionalProperties":{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2}},"water_ml":{"type":["array","null"],"items":{"type":"number"},"minItems":2,"maxItems":2},"goal_adjustment":S(),"uncertainty":{"enum":["low","medium","high"]},"labels":{"type":"array","items":S()},"safety_decision_id":{"type":["string","null"]},"method":S()},["status","labels"],"برآورد است نه نسخه درمانی؛ برچسب‌ها و عدم‌قطعیت همیشه برگردانده می‌شوند."),
"MealPlanRequest":obj({"days":{"type":"integer","minimum":1,"maximum":7},"allergens":{"type":"array","items":{"enum":["milk","egg","fish","shellfish","tree_nut","peanut","wheat","soy","sesame"]},"maxItems":9},"excluded_food_ids":{"type":"array","items":S(maxLength=64),"maxItems":200},"diet_required":{"type":"array","items":{"enum":["vegetarian","vegan","halal","gluten_free","lactose_free"]},"maxItems":5},"max_cook_minutes":{"type":"integer","minimum":5,"maximum":240},"weekly_budget":{"type":"number","exclusiveMinimum":0},"currency":S(pattern=r"^[A-Z]{3}$"),"region":S(minLength=2,maxLength=16),"pantry":{"type":"array","items":S(maxLength=64),"maxItems":200}},None,"بودجه بدون currency و region معتبر نیست (NEEDS_INFO)."),
"MealPlanIngredient":obj({"food_id":S(),"name_en":S(),"name_fa":{"type":["string","null"]},"grams":{"type":"number"},"allergens":{"type":"array","items":S()},"allergens_known":{"type":"boolean"}}),
"MealPlanMeal":obj({"slot":{"enum":["breakfast","lunch","dinner","snack"]},"recipe_id":S(),"name_en":S(),"name_fa":{"type":["string","null"]},"portion":{"type":"number"},"kcal":{"type":"number"},"nutrients":{"type":"object","additionalProperties":{"type":"number"}},"missing_nutrients":{"type":"array","items":S()},"cook_minutes":{"type":"integer"},"cost":{"type":["number","null"]},"ingredients":{"type":"array","items":{"$ref":"#/components/schemas/MealPlanIngredient"}},"steps":{"type":"array","items":S()},"allergens":{"type":"array","items":S()},"allergens_known":{"type":"boolean"}}),
"MealPlanDay":obj({"index":{"type":"integer"},"date":S(format="date"),"meals":{"type":"array","items":{"$ref":"#/components/schemas/MealPlanMeal"}},"kcal":{"type":"number"},"protein_g":{"type":"number"},"missing_nutrients":{"type":"array","items":S()}}),
"ShoppingItem":obj({"food_id":S(),"name_en":S(),"grams":{"type":"number"},"cost":{"type":["number","null"]},"in_pantry":{"type":"boolean"}}),
"MealPlanResponse":obj({"status":{"enum":["OK","NEEDS_CONTENT","NEEDS_INFO","BLOCKED","REFER"]},"reasons":{"type":"array","items":S()},"days":{"type":"array","items":{"$ref":"#/components/schemas/MealPlanDay"}},"shopping":{"type":"array","items":{"$ref":"#/components/schemas/ShoppingItem"}},"total_cost":{"type":["number","null"]},"unpriced_food_ids":{"type":"array","items":S()},"budget_met":{"type":["boolean","null"]},"labels":{"type":"array","items":S()},"target_kcal":{"type":["number","null"]},"safety_decision_id":{"type":["string","null"]}},["status","reasons","days","shopping","labels"],"days فقط وقتی status=OK پر است؛ NEEDS_CONTENT یعنی محتوای غذایی/دستور پخت بازبینی‌شده وجود ندارد و هیچ برنامه‌ای ساخته نمی‌شود. مقادیر قیمت فقط از قیمت‌های تازه می‌آیند."),
"PlanFeaturesRequest":obj({"features":{"type":"array","items":obj({"code":S(),"enabled":{"type":"boolean"}},["code","enabled"])}},["features"],"تلاش برای خاموش‌کردن feature با safety_critical=true → 422"),
})
paths={}
for (i,m,p,tag,sm,auth,roles,req,resp,ok,errs) in EP:
    op={"operationId":i.replace("-","_").lower(),"tags":[tag],"summary":sm,"x-id":i,
        "security":[] if auth==PUB else [{"cookieAuth":[]}],
        "responses":{}}
    if roles: op["x-roles"]=roles.split("|")
    if auth=="staff": op["description"]="نقش‌های مجاز: "+"، ".join(roles.split("|"))+" + بررسی Object-level."
    params=[]
    import re
    for pn in re.findall(r"\{(\w+)\}",p):
        params.append({"name":pn,"in":"path","required":True,"schema":{"type":"string" if pn=="step" and False else ("integer" if pn=="step" else "string"),**({"format":"uuid"} if pn.endswith("_id") and pn not in ("food_id","recipe_id") else {}) }})
    if m=="get" and p in("/foods","/recipes"):
        params+= [{"name":"page","in":"query","schema":{"type":"integer","minimum":1}},{"name":"page_size","in":"query","schema":{"type":"integer","minimum":1,"maximum":100}},{"name":"q","in":"query","schema":{"type":"string"}},{"name":"diet","in":"query","schema":{"enum":["vegetarian","vegan","halal","gluten_free","lactose_free"]}},{"name":"avoid_allergens","in":"query","description":"فهرست جداشده با ویرگول؛ غذاهای با آلرژن نامعلوم هم حذف می‌شوند","schema":{"type":"string"}}]
        params+= [{"name":"category","in":"query","schema":{"type":"string"}}] if p=="/foods" else [{"name":"slot","in":"query","schema":{"enum":["breakfast","lunch","dinner","snack"]}},{"name":"max_minutes","in":"query","schema":{"type":"integer","minimum":1}}]
    if m=="get" and p in("/nutrition/meals","/nutrition/summary"):
        params.append({"name":"date","in":"query","schema":{"type":"string","format":"date"}})
    if m=="get" and p in("/exercises","/workouts/sessions"):
        params+= [{"name":"page","in":"query","schema":{"type":"integer","minimum":1}},{"name":"page_size","in":"query","schema":{"type":"integer","minimum":1,"maximum":100}}]
    if p=="/exercises":
        params+=[{"name":n,"in":"query","schema":{"type":"string"}} for n in("q","muscle","equipment","difficulty","pattern")]
    if params: op["parameters"]=params
    if req: op["requestBody"]={"required":True,"content":{"application/json":{"schema":{"$ref":f"#/components/schemas/{req}"}}}}
    op["responses"][ok]={"description":"موفق","content":{"application/json":{"schema":{"$ref":f"#/components/schemas/{resp}"}}}}
    for e in errs:
        op["responses"][e]={"description":ERR_TXT[e],"content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}}
    paths.setdefault(p,{})[m]=op
NUTR=obj({"kcal":{"type":"number"},"protein_g":{"type":"number"},"fat_g":{"type":"number"},"carbs_g":{"type":"number"},"fiber_g":{"type":"number"},"sugar_g":{"type":"number"},"sodium_mg":{"type":"number"},"calcium_mg":{"type":"number"},"iron_mg":{"type":"number"},"potassium_mg":{"type":"number"},"vitamin_c_mg":{"type":"number"}})
ALG={"type":"array","items":S()}
schemas.update({
"FoodSummary":obj({"id":S(),"name_en":S(),"name_fa":S(),"category":S(),"allergens":ALG,"allergens_known":{"type":"boolean"},"diet_tags":ALG,"review_status":{"enum":["reviewed","unreviewed"]},"per_100g":NUTR},["id","name_en","allergens","allergens_known","review_status","per_100g"],"نبود نام فارسی یعنی هنوز بازبینی ترجمه نشده؛ allergens_known=false یعنی وضعیت آلرژن نامعلوم است نه «بدون آلرژن»."),
"FoodList":obj({"count":{"type":"integer"},"next":S(),"results":{"type":"array","items":{"$ref":"#/components/schemas/FoodSummary"}}}),
"FoodDetail":obj({"id":S(),"name_en":S(),"name_fa":S(),"category":S(),"allergens":ALG,"allergens_known":{"type":"boolean"},"diet_tags":ALG,"review_status":{"enum":["reviewed","unreviewed"]},"per_100g":NUTR,"serving_g":{"type":"object","additionalProperties":{"type":"number"}},"basis":S(),"notes":ALG,"nutrient_refs":{"type":"object","additionalProperties":{"type":"object","additionalProperties":S()}},"source":obj({"dataset":S(),"record_id":S(),"license":S(),"license_verified":{"type":"boolean"}})},["id","name_en","per_100g","review_status"]),
"RecipeSummary":obj({"id":S(),"name_en":S(),"name_fa":S(),"slots":ALG,"cook_minutes":{"type":"integer"},"servings":{"type":"integer"},"per_serving":NUTR,"missing_nutrients":ALG,"allergens":ALG,"allergens_known":{"type":"boolean"},"diet_tags":ALG,"review_status":{"enum":["reviewed","unreviewed"]}},["id","name_en","per_serving","review_status","allergens","allergens_known"]),
"RecipeList":obj({"count":{"type":"integer"},"next":S(),"results":{"type":"array","items":{"$ref":"#/components/schemas/RecipeSummary"}}}),
"RecipeDetail":obj({"id":S(),"name_en":S(),"name_fa":S(),"slots":ALG,"cook_minutes":{"type":"integer"},"servings":{"type":"integer"},"per_serving":NUTR,"missing_nutrients":ALG,"allergens":ALG,"allergens_known":{"type":"boolean"},"diet_tags":ALG,"review_status":{"enum":["reviewed","unreviewed"]},"steps":ALG,"ingredients":{"type":"array","items":obj({"food_id":S(),"name_en":S(),"name_fa":S(),"grams":{"type":"number"},"allergens":ALG,"allergens_known":{"type":"boolean"}})}},["id","name_en","per_serving","review_status","ingredients"]),
"MealLogRequest":obj({"slot":{"enum":["breakfast","lunch","dinner","snack"]},"date":S(format="date"),"food_id":S(maxLength=64),"grams":{"type":"number","exclusiveMinimum":0,"maximum":3000},"recipe_id":S(maxLength=64),"servings":{"type":"number","exclusiveMinimum":0,"maximum":20},"name":S(minLength=1,maxLength=120),"kcal":{"type":"number","minimum":0,"maximum":5000},"protein_g":{"type":"number","minimum":0,"maximum":400},"carbs_g":{"type":"number","minimum":0,"maximum":1000},"fat_g":{"type":"number","minimum":0,"maximum":400}},["slot"],"دقیقاً یکی از food_id+grams، recipe_id+servings یا name(+مقادیر کاربر)."),
"MealEntry":obj({"id":S(format="uuid"),"date":S(format="date"),"slot":{"enum":["breakfast","lunch","dinner","snack"]},"name":S(),"name_fa":S(),"source":{"enum":["user_entered","catalog"]},"kcal":{"type":"number"},"protein_g":{"type":"number"},"carbs_g":{"type":"number"},"fat_g":{"type":"number"},"amount":{"type":"number"},"food_id":S(),"recipe_id":S(),"missing_nutrients":ALG,"allergens":ALG,"allergens_known":{"type":"boolean"},"review_status":S(),"allergen_alert":{"oneOf":[obj({"allergens":ALG,"unknown":{"type":"boolean"}}),{"type":"null"}]}},["id","date","slot","name","source","missing_nutrients","allergen_alert"],"allergen_alert وقتی پر است که آلرژن ثبت‌شده‌ی کاربر در غذا هست یا وضعیت آلرژن نامعلوم است؛ ثبت انجام می‌شود ولی هشدار باید نشان داده شود."),
"MealLogDay":obj({"date":S(format="date"),"meals":{"type":"array","items":{"$ref":"#/components/schemas/MealEntry"}}},["date","meals"]),
"WaterRequest":obj({"ml":{"type":"number","minimum":50,"maximum":3000},"date":S(format="date")},["ml"]),
"WaterTotal":obj({"date":S(format="date"),"water_ml":{"type":"number"}},["date","water_ml"]),
"NutritionDaySummary":obj({"date":S(format="date"),"meals":{"type":"integer"},"kcal":{"type":"number"},"protein_g":{"type":"number"},"carbs_g":{"type":"number"},"fat_g":{"type":"number"},"water_ml":{"type":"number"},"completeness":{"type":"object","additionalProperties":S()},"note":S(),"targets":obj({"tdee":{"type":["array","null"],"items":{"type":"number"}},"macros":{"type":["object","null"],"additionalProperties":{"type":"array","items":{"type":"number"}}},"water_ml":{"type":["array","null"],"items":{"type":"number"}}}),"uncertainty":S(),"labels":ALG},["date","meals","kcal","water_ml","targets","labels"],"مقادیر وارد‌نشده تخمین زده نمی‌شوند (completeness)."),
"UserPrice":obj({"food_id":S(),"price_per_kg":{"type":"number"},"currency":S(pattern=r"^[A-Z]{3}$"),"region":S(),"observed_on":S(format="date"),"source":{"const":"user_entered"}},["food_id","price_per_kg","currency","region","observed_on","source"]),
"UserPriceList":obj({"prices":{"type":"array","items":{"$ref":"#/components/schemas/UserPrice"}}},["prices"]),
"UserPriceRequest":obj({"food_id":S(maxLength=64),"price_per_kg":{"type":"number","exclusiveMinimum":0,"maximum":1000000000},"currency":S(pattern=r"^[A-Z]{3}$"),"region":S(minLength=2,maxLength=16)},["food_id","price_per_kg","currency","region"],"قیمت فقط از ورودی کاربر؛ مانند هر قیمت دیگر پس از ۴۵ روز کنار گذاشته می‌شود."),
"ShoppingState":obj({"checked":{"type":"array","items":S(maxLength=64),"maxItems":300,"uniqueItems":True}},["checked"]),
"ProgressionItem":obj({"exercise_id":S(format="uuid"),"action":{"enum":["increase_load","increase_reps","hold","reduce_load","suggest_deload","pause_pain","locked","insufficient_data"]},"reasons":ALG,"flags":ALG,"confidence":{"enum":["high","medium","low"]},"sessions_considered":{"type":"integer"},"last_load_kg":{"type":"number"},"last_reps":{"type":"integer"},"new_load_kg":{"type":"number"},"target_reps":{"type":"integer"},"factor":{"type":"number"}},["exercise_id","action","reasons","confidence"]),
"ProgressionList":obj({"items":{"type":"array","items":{"$ref":"#/components/schemas/ProgressionItem"}},"note":S()},["items"],"پیشنهادها فقط راهنما هستند؛ Safety Core تنها مرجع تأیید حرکت/برنامه است و درد یا پرچم قفل‌شده هر پیشنهاد افزایشی را متوقف می‌کند."),
})
doc={"openapi":"3.1.0","info":{"title":"AI Fitness & Health Ecosystem API","version":"0.1.0","description":"DOC-07 — پیش‌نویس کامل برای MVP. مسیرهای Backlog در بخش x-deferred فهرست شده‌اند. هیچ endpoint پرداخت واقعی بدون Provider پیکربندی‌شده فعال نیست (501)."},
"servers":[{"url":"/api/v1"}],
"components":{"securitySchemes":{"cookieAuth":{"type":"apiKey","in":"cookie","name":"sessionid","description":"نشست HttpOnly؛ برای متدهای تغییردهنده هدر X-CSRFToken الزامی است."}},"schemas":schemas},
"paths":paths,
"x-global-rules":["همه endpointهای تغییردهنده: CSRF + rate limit؛ ورود/ثبت‌نام/AI: rate limit سخت‌گیرانه","همه endpointهای health/*: رضایت health_data معتبر (وگرنه 403 با code=consent_required)","هیچ endpoint نمی‌تواند برنامه/حرکت را بدون SafetyDecision معتبر برگرداند","خطا: Error{code,message,request_id}؛ بدون افشای جزئیات داخلی","پاسخ‌های سلامت: Cache-Control: no-store"],
"x-deferred":["/supplements","/recovery/checkins","/calendar","/devices","/photos","/professional/*","/community/*","/billing/webhooks/{provider}"]}
yaml.safe_dump(doc,open('docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml','w',encoding='utf-8'),allow_unicode=True,sort_keys=False,width=140)
# structural validation
d=yaml.safe_load(open('docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml',encoding='utf-8'))
refs=set()
def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k=="$ref": refs.add(v.split('/')[-1])
            else: walk(v)
    elif isinstance(x,list): [walk(i) for i in x]
walk(d)
missing=refs-set(d['components']['schemas']); print("endpoints",sum(len(v) for v in d['paths'].values()),"schemas",len(d['components']['schemas']),"missing refs",missing)
ids=[e[0] for e in EP]; assert len(ids)==len(set(ids))
json.dump([(e[0],e[1].upper(),e[2],e[3]) for e in EP],open('tools/api_index.json','w'))
