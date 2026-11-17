#!/usr/bin/env python3
"""NOTE: cooking oil/butter rows in the FDC Foundation download carry no protein/carbohydrate/energy values, so oils are NOT part of the dataset;
recipe steps say "a little oil" and the energy of that oil is NOT included in the recipe nutrition (disclosed in the UI).
Builds backend/nutrition_engine/data/{demo_foods_fdc.json,demo_curation.json,demo_recipes.json}.

Food composition: UNMODIFIED USDA FoodData Central Foundation Foods rows (declared public domain / CC0 by FDC), taken from a public
GitHub copy of the FDC download (chris-wamae/json-filter, foundationDownload.json). Only a hand-picked subset of rows and the nutrient
fields the importer reads are kept; no value is edited or invented.
Curation (Persian names, allergens, diet tags) and recipes are AI-curated, NOT expert reviewed: records stay `pending_review`.
Usage: python3 tools/build_demo_nutrition.py /path/to/foundationDownload.json
"""
import json, sys, pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "backend/nutrition_engine/data"
M, E, F, W, SO, SE, TN, PN, SH = "milk", "egg", "fish", "wheat", "soy", "sesame", "tree_nut", "peanut", "shellfish"
V, VG, H, GF, LF = "vegetarian", "vegan", "halal", "gluten_free", "lactose_free"
PLANT = (V, VG, H, GF, LF)
# fdcId: (key, name_fa, allergens, diet_tags, extra notes)
FOODS = {
 2512381: ("rice_white", "برنج سفید (خام)", (), PLANT),
 2512380: ("rice_brown", "برنج قهوه‌ای (خام)", (), PLANT),
 2346396: ("oats", "جو دوسر پرک", (), (V, VG, H, LF)),
 335240: ("bread_wholewheat", "نان سبوس‌دار", (W, SO, M), (V, H)),
 2644282: ("chickpeas_dry", "نخود (خشک)", (), PLANT),
 2644283: ("lentils_dry", "عدس (خشک)", (), PLANT),
 2644288: ("chickpeas_canned", "نخود کنسروی (آبکش‌شده)", (), PLANT),
 321358: ("hummus", "حمص", (SE,), (V, VG, H, LF)),
 2646170: ("chicken_breast", "سینه مرغ (خام)", (), (H, GF, LF)),
 2646171: ("chicken_thigh", "ران مرغ بدون پوست (خام)", (), (H, GF, LF)),
 2514743: ("beef_ground", "گوشت چرخ‌کرده گاو ۹۰٪ (خام)", (), (H, GF, LF)),
 2646173: ("beef_round", "گوشت ران گاو (خام)", (), (H, GF, LF)),
 2684441: ("salmon", "ماهی سالمون (خام)", (F,), (H, GF, LF)),
 2684442: ("tilapia", "ماهی تیلاپیا (خام)", (F,), (H, GF, LF)),
 334194: ("tuna_canned", "تن ماهی در آب (آبکش‌شده)", (F,), (H, GF, LF)),
 2684443: ("shrimp", "میگو (خام)", (SH,), (GF, LF)),
 748967: ("egg", "تخم‌مرغ", (E,), (V, H, GF, LF)),
 2259793: ("yogurt_whole", "ماست کامل چرب", (M,), (V, H, GF)),
 330137: ("yogurt_greek_nonfat", "ماست یونانی بدون چربی", (M,), (V, H, GF)),
 746782: ("milk_whole", "شیر کامل چرب", (M,), (V, H, GF)),
 746772: ("milk_lowfat", "شیر کم‌چرب ۱٪", (M,), (V, H, GF)),
 2259796: ("feta", "پنیر فتا", (M,), (V, H, GF)),
 2346384: ("cottage", "پنیر لور (کاتیج)", (M,), (V, H, GF)),
 1999630: ("soy_milk", "شیر سویا ساده", (SO,), PLANT),
 2346393: ("almonds", "بادام خام", (TN,), PLANT),
 2346394: ("walnuts", "گردو", (TN,), PLANT),
 2515379: ("pistachio", "پسته خام", (TN,), PLANT),
 2262072: ("peanut_butter", "کره بادام‌زمینی", (PN,), PLANT),
 2515380: ("pumpkin_seeds", "تخمه کدو خام", (), PLANT),
 2262075: ("flaxseed", "بذر کتان آسیاب‌شده", (), PLANT),
 1105314: ("banana", "موز", (), PLANT),
 1750340: ("apple", "سیب", (), PLANT),
 2346409: ("strawberry", "توت‌فرنگی", (), PLANT),
 325430: ("peach", "هلو", (), PLANT),
 746771: ("orange", "پرتقال", (), PLANT),
 746773: ("pear", "گلابی", (), PLANT),
 746770: ("cantaloupe", "خربزه", (), PLANT),
 327046: ("kiwi", "کیوی", (), PLANT),
 746768: ("figs_dried", "انجیر خشک", (), PLANT),
 2346406: ("cucumber", "خیار", (), PLANT),
 1999634: ("tomato", "گوجه‌فرنگی", (), PLANT),
 2685573: ("cauliflower", "گل‌کلم", (), PLANT),
 747447: ("broccoli", "کلم بروکلی", (), PLANT),
 2685570: ("butternut", "کدو حلوایی", (), PLANT),
 2644285: ("black_beans_canned", "لوبیا سیاه کنسروی (آبکش‌شده)", (), PLANT),
 2685577: ("eggplant", "بادمجان", (), PLANT),
 2258586: ("carrot", "هویج", (), PLANT),
 2258590: ("bell_pepper_red", "فلفل دلمه‌ای قرمز", (), PLANT),
 790646: ("onion", "پیاز", (), PLANT),
 1104647: ("garlic", "سیر", (), PLANT),
 1999632: ("spinach", "اسفناج", (), PLANT),
 2346401: ("potato", "سیب‌زمینی", (), PLANT),
 2346404: ("sweet_potato", "سیب‌زمینی شیرین", (), PLANT),
 2346407: ("cabbage", "کلم سبز", (), PLANT),
 2346389: ("lettuce", "کاهو رومی", (), PLANT),
 1999629: ("mushroom", "قارچ دکمه‌ای", (), PLANT),
 2685580: ("tomato_paste", "رب گوجه‌فرنگی (بدون نمک)", (), PLANT),
}

R = lambda *a: a
# id: (name_en, name_fa, slots, [(foodkey, grams)], servings, minutes, steps_fa)
RECIPES = {
 "oatmeal_banana_walnut": ("Oatmeal with banana and walnuts", "فرنی جو دوسر با موز و گردو", ("breakfast",), [("oats",50),("milk_whole",200),("banana",100),("walnuts",15)], 1, 10,
   ["شیر را روی حرارت ملایم گرم کنید.", "جو دوسر را اضافه کنید و ۵ دقیقه هم بزنید تا غلیظ شود.", "موز خرد‌شده و گردو را روی آن بریزید."]),
 "oatmeal_soy_banana": ("Vegan oatmeal with soy milk and banana", "فرنی جو دوسر با شیر سویا و موز", ("breakfast",), [("oats",50),("soy_milk",250),("banana",100),("pumpkin_seeds",15)], 1, 10,
   ["شیر سویا را گرم کنید.", "جو دوسر را اضافه کنید و ۵ دقیقه بپزید.", "موز و تخمه کدو را روی آن بریزید."]),
 "veg_omelette": ("Vegetable omelette", "املت سبزیجات", ("breakfast","dinner"), [("egg",150),("tomato",100),("onion",40),("spinach",40)], 1, 15,
   ["پیاز را خرد کنید و با کمی روغن سرخ کنید.", "گوجه و اسفناج خرد‌شده را اضافه کنید و ۳ دقیقه تفت دهید.", "تخم‌مرغ‌ها را بشکنید، روی سبزیجات بریزید و بپزید تا جا بیفتد."]),
 "yogurt_berry_bowl": ("Greek yogurt bowl with strawberries and almonds", "کاسه ماست یونانی با توت‌فرنگی و بادام", ("breakfast","snack"), [("yogurt_greek_nonfat",200),("strawberry",100),("almonds",15),("oats",20)], 1, 5,
   ["ماست را در کاسه بریزید.", "توت‌فرنگی‌های برش‌خورده، بادام و جو دوسر را روی آن بپاشید."]),
 "cottage_toast": ("Cottage cheese toast with cucumber and tomato", "نان و پنیر لور با خیار و گوجه", ("breakfast","snack"), [("bread_wholewheat",60),("cottage",100),("cucumber",80),("tomato",80)], 1, 5,
   ["نان را برشته کنید.", "پنیر لور را رویش بمالید.", "خیار و گوجه‌ی ورقه‌شده را اضافه کنید."]),
 "egg_toast": ("Scrambled eggs with bread and cucumber", "نیمرو/املت ساده با نان و خیار", ("breakfast",), [("egg",150),("bread_wholewheat",60),("cucumber",80)], 1, 10,
   ["کمی روغن را در ماهیتابه گرم کنید.", "تخم‌مرغ‌ها را بشکنید و هم بزنید تا بپزد.", "با نان و خیار سرو کنید."]),
 "pb_banana_toast": ("Peanut butter banana toast", "نان با کره بادام‌زمینی و موز", ("breakfast","snack"), [("bread_wholewheat",60),("peanut_butter",20),("banana",100)], 1, 5,
   ["نان را برشته کنید.", "کره بادام‌زمینی را بمالید و موز ورقه‌شده را روی آن بچینید."]),
 "bread_cheese_walnut": ("Bread, feta and walnut breakfast", "صبحانه‌ی نان، پنیر و گردو", ("breakfast",), [("bread_wholewheat",80),("feta",40),("walnuts",20),("cucumber",80),("tomato",80)], 1, 5,
   ["نان، پنیر و گردو را در بشقاب بگذارید.", "خیار و گوجه را برش بزنید و کنارش سرو کنید."]),
 "chicken_rice_veg": ("Chicken and rice with vegetables", "مرغ و برنج با سبزیجات", ("lunch","dinner"), [("chicken_breast",300),("rice_white",160),("carrot",120),("butternut",200)], 2, 40,
   ["برنج را بشویید و آبکش کنید یا با دو برابر آب بپزید (۱۵–۲۰ دقیقه).", "سینه مرغ را قطعه کنید و با کمی روغن تفت دهید تا کاملاً پخته شود (دمای مرکز ۷۴ درجه).", "هویج و کدو را اضافه کنید و ۸ دقیقه بپزید.", "همه را با برنج سرو کنید."]),
 "lentil_soup": ("Lentil soup", "سوپ عدس", ("lunch","dinner"), [("lentils_dry",150),("onion",100),("carrot",100),("potato",150),("tomato_paste",30),("garlic",10)], 3, 45,
   ["پیاز و سیر را با کمی روغن سرخ کنید.", "رب را اضافه کنید و ۱ دقیقه تفت دهید.", "عدس شسته، هویج و سیب‌زمینی خرد‌شده و ۱ لیتر آب بریزید.", "۳۰ تا ۳۵ دقیقه بپزید تا نرم شود و در صورت دلخواه با گوشت‌کوب له کنید."]),
 "chickpea_stew": ("Chickpea and spinach stew", "خوراک نخود و اسفناج", ("lunch","dinner"), [("chickpeas_dry",150),("onion",100),("tomato",200),("spinach",100)], 3, 60,
   ["نخود را شب قبل خیس کنید و ۴۵ دقیقه بپزید تا نرم شود.", "پیاز را با کمی روغن سرخ کنید و گوجه خرد‌شده اضافه کنید.", "نخود پخته و اسفناج را بریزید و ۱۰ دقیقه بپزید."]),
 "salmon_potato_broccoli": ("Baked salmon with potatoes and broccoli", "سالمون کباب‌شده با سیب‌زمینی و بروکلی", ("lunch","dinner"), [("salmon",300),("potato",300),("broccoli",200)], 2, 35,
   ["فر را روی ۲۰۰ درجه گرم کنید.", "سیب‌زمینی‌های قطعه‌شده را با کمی روغن ۱۵ دقیقه بپزید.", "سالمون و بروکلی را اضافه کنید و ۱۵ دقیقه دیگر بپزید تا ماهی کاملاً پخته شود (دمای مرکز ۶۳ درجه)."]),
 "beef_eggplant": ("Ground beef and eggplant skillet", "تابه‌ی گوشت چرخ‌کرده و بادمجان", ("lunch","dinner"), [("beef_ground",250),("eggplant",400),("tomato",200),("onion",100)], 3, 40,
   ["بادمجان را حلقه کنید و با کمی روغن تفت دهید تا نرم شود و کنار بگذارید.", "پیاز و گوشت را سرخ کنید تا کاملاً پخته شود.", "گوجه و بادمجان را اضافه کنید و ۱۰ دقیقه با حرارت ملایم بپزید."]),
 "tuna_chickpea_salad": ("Tuna and chickpea salad", "سالاد تن ماهی و نخود", ("lunch","dinner"), [("tuna_canned",160),("chickpeas_canned",200),("cucumber",150),("tomato",150),("lettuce",100)], 2, 10,
   ["سبزیجات را خرد کنید.", "تن ماهی و نخود آبکش‌شده را اضافه کنید.", "کمی روغن زیتون اضافه کنید و مخلوط کنید."]),
 "chicken_potato_tray": ("Chicken thigh and potato tray bake", "ران مرغ و سیب‌زمینی در فر", ("lunch","dinner"), [("chicken_thigh",300),("potato",400),("bell_pepper_red",150),("onion",100)], 2, 50,
   ["فر را روی ۲۰۰ درجه گرم کنید.", "همه‌ی مواد را با روغن در سینی بریزید.", "۴۰ دقیقه بپزید تا مرغ کاملاً پخته شود (دمای مرکز ۷۴ درجه)."]),
 "lentil_rice_yogurt": ("Lentil rice with yogurt", "عدس‌پلوی ساده با ماست", ("lunch","dinner"), [("rice_white",150),("lentils_dry",100),("onion",100),("yogurt_whole",200)], 3, 45,
   ["عدس را ۱۵ دقیقه جداگانه بپزید.", "پیاز را سرخ کنید.", "برنج و عدس را با دو برابر آب بپزید تا آب جذب شود.", "پیاز را روی آن بریزید و با ماست سرو کنید."]),
 "shrimp_veg_rice": ("Shrimp and vegetable rice", "برنج با میگو و سبزیجات", ("lunch","dinner"), [("shrimp",250),("rice_white",150),("bell_pepper_red",150),("butternut",150)], 2, 35,
   ["برنج را بپزید.", "سبزیجات را با کمی روغن تفت دهید.", "میگو را اضافه کنید و ۳–۴ دقیقه بپزید تا کاملاً صورتی شود.", "با برنج مخلوط و سرو کنید."]),
 "blackbean_sweetpotato": ("Black bean and sweet potato bowl", "کاسه‌ی لوبیا سیاه و سیب‌زمینی شیرین", ("lunch","dinner"), [("black_beans_canned",250),("sweet_potato",300),("bell_pepper_red",100),("onion",60)], 2, 35,
   ["لوبیای آبکش‌شده را آماده کنید.", "سیب‌زمینی شیرین مکعبی را در فر ۲۰۰ درجه ۲۵ دقیقه بپزید.", "پیاز و فلفل را تفت دهید و همه را در کاسه مخلوط کنید."]),
 "mushroom_spinach_omelette": ("Mushroom, spinach and feta omelette", "املت قارچ، اسفناج و پنیر", ("lunch","dinner"), [("egg",200),("mushroom",150),("spinach",80),("feta",40)], 2, 20,
   ["قارچ را با کمی روغن تفت دهید تا آبش کشیده شود.", "اسفناج را اضافه کنید تا خشک شود.", "تخم‌مرغ را بریزید، پنیر را پخش کنید و بپزید تا جا بیفتد."]),
 "cauliflower_chickpea_curry": ("Cauliflower and chickpea curry", "خوراک گل‌کلم و نخود", ("lunch","dinner"), [("cauliflower",300),("chickpeas_canned",200),("tomato",200),("onion",100)], 2, 30,
   ["پیاز را با کمی روغن سرخ کنید.", "گوجه خرد‌شده را اضافه کنید و ۵ دقیقه بپزید.", "گل‌کلم و نخود را بریزید و با ۱ لیوان آب ۱۵ دقیقه بپزید."]),
 "beef_broccoli_rice": ("Beef and broccoli stir-fry with rice", "گوشت و بروکلی تفت‌داده با برنج", ("lunch","dinner"), [("beef_round",200),("rice_white",120),("broccoli",200),("carrot",100)], 2, 35,
   ["برنج را بپزید.", "گوشت را نازک برش بزنید و با کمی روغن داغ تفت دهید تا کاملاً پخته شود.", "هویج و بروکلی را اضافه کنید و ۵ دقیقه بپزید.", "با برنج سرو کنید."]),
 "tilapia_cabbage": ("Tilapia with cabbage and rice", "ماهی تیلاپیا با کلم و برنج", ("lunch","dinner"), [("tilapia",300),("cabbage",250),("rice_brown",120)], 2, 35,
   ["برنج قهوه‌ای را بپزید (۲۵–۳۰ دقیقه).", "کلم را با کمی روغن تفت دهید.", "ماهی را در ماهیتابه ۴ دقیقه هر طرف بپزید تا کاملاً پخته شود."]),
 "lentil_rice_vegan": ("Lentil rice (vegan)", "عدس‌پلو گیاهی", ("lunch","dinner"), [("rice_white",200),("lentils_dry",120),("onion",100),("carrot",100),("tomato_paste",20)], 2, 45,
   ["عدس را ۱۵ دقیقه بپزید.", "پیاز و هویج را با کمی روغن تفت دهید و رب را اضافه کنید.", "برنج و عدس را با دو برابر آب بپزید تا آب جذب شود و با تفت مخلوط کنید."]),
 "chickpea_potato_stew": ("Chickpea and potato stew", "خوراک نخود و سیب‌زمینی", ("lunch","dinner"), [("chickpeas_dry",150),("potato",400),("onion",100),("tomato",200)], 2, 60,
   ["نخود را شب قبل خیس کنید و ۴۵ دقیقه بپزید.", "پیاز را تفت دهید، گوجه و سیب‌زمینی قطعه‌شده را اضافه کنید.", "نخود و ۲ لیوان آب بریزید و ۲۰ دقیقه بپزید."]),
 "rice_beans_bowl": ("Rice and beans bowl", "کاسه‌ی برنج و لوبیا", ("lunch","dinner"), [("rice_white",160),("black_beans_canned",300),("bell_pepper_red",100),("onion",60)], 2, 30,
   ["برنج را بپزید.", "پیاز و فلفل را با کمی روغن تفت دهید.", "لوبیای آبکش‌شده را اضافه کنید و ۵ دقیقه گرم کنید و با برنج سرو کنید."]),
 "big_vegan_oats": ("Big vegan oat bowl", "کاسه‌ی بزرگ جو دوسر گیاهی", ("breakfast",), [("oats",80),("soy_milk",300),("banana",120),("walnuts",30),("flaxseed",10)], 1, 10,
   ["شیر سویا را گرم کنید و جو دوسر را ۵ دقیقه بپزید.", "موز، گردو و بذر کتان را روی آن بریزید."]),
 "hummus_veg_plate": ("Hummus and vegetable plate", "بشقاب حمص و سبزیجات", ("snack","lunch"), [("hummus",80),("carrot",80),("cucumber",80),("bread_wholewheat",40)], 1, 5,
   ["سبزیجات را به شکل چوب برش بزنید.", "با حمص و نان سرو کنید."]),
 "apple_almonds": ("Apple with almonds", "سیب و بادام", ("snack",), [("apple",150),("almonds",20)], 1, 2, ["سیب را برش بزنید و با بادام بخورید."]),
 "yogurt_walnut": ("Yogurt with walnuts", "ماست و گردو", ("snack",), [("yogurt_whole",150),("walnuts",15)], 1, 2, ["گردو را خرد کنید و روی ماست بریزید."]),
 "banana_pb": ("Banana with peanut butter", "موز و کره بادام‌زمینی", ("snack",), [("banana",120),("peanut_butter",20)], 1, 2, ["موز را برش بزنید و با کره بادام‌زمینی بخورید."]),
 "orange_pistachio": ("Orange with pistachios", "پرتقال و پسته", ("snack",), [("orange",150),("pistachio",20)], 1, 2, ["پرتقال را پوست بگیرید و با پسته بخورید."]),
 "boiled_eggs_tomato": ("Boiled eggs with tomato", "تخم‌مرغ آب‌پز و گوجه", ("snack",), [("egg",100),("tomato",100)], 1, 12, ["تخم‌مرغ‌ها را ۹–۱۰ دقیقه بجوشانید و با گوجه بخورید."]),
 "pear_walnut": ("Pear with walnuts", "گلابی و گردو", ("snack",), [("pear",150),("walnuts",15)], 1, 2, ["گلابی را برش بزنید و با گردو بخورید."]),
 "cottage_cucumber": ("Cottage cheese with cucumber", "پنیر لور و خیار", ("snack",), [("cottage",120),("cucumber",100)], 1, 3, ["خیار را خرد کنید و با پنیر لور مخلوط کنید."]),
 "fruit_plate": ("Fruit plate with figs and almonds", "بشقاب میوه با انجیر و بادام", ("snack",), [("kiwi",100),("peach",120),("figs_dried",30),("almonds",15)], 1, 3, ["میوه‌ها را برش بزنید و با انجیر و بادام سرو کنید."]),
}

def main(src):
    rows = {r["fdcId"]: r for r in json.load(open(src))["FoundationFoods"]}
    keep = {}
    for fid, (key, fa, al, tags) in FOODS.items():
        r = rows[fid]
        keep[str(fid)] = {"fdcId": r["fdcId"], "description": r["description"], "publicationDate": r.get("publicationDate"),
                          "foodCategory": r.get("foodCategory"), "foodPortions": r.get("foodPortions", []),
                          "foodNutrients": [n for n in r["foodNutrients"] if str(n["nutrient"].get("number")) in
                                            ("208","957","958","203","204","205","291","269","269.3","307","301","303","306","401")]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "demo_foods_fdc.json").write_text(json.dumps({"FoundationFoods": list(keep.values())}, ensure_ascii=False, indent=1) + "\n")
    cur = {f"fdc_{fid}": {"key": k, "name_fa": fa, "allergens": list(al), "diet_tags": list(t)} for fid, (k, fa, al, t) in FOODS.items()}
    (OUT / "demo_curation.json").write_text(json.dumps(cur, ensure_ascii=False, indent=1) + "\n")
    key2id = {k: f"fdc_{fid}" for fid, (k, *_r) in FOODS.items()}
    rec = []
    for rid, (en, fa, slots, ing, sv, mins, steps) in RECIPES.items():
        rec.append({"id": f"demo_{rid}", "name_en": en, "name_fa": fa, "slots": list(slots), "ingredients": [[key2id[k], g] for k, g in ing],
                    "servings": sv, "cook_minutes": mins, "steps": steps})
    (OUT / "demo_recipes.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    print(len(keep), "foods", len(rec), "recipes")

if __name__ == "__main__":
    main(sys.argv[1])
