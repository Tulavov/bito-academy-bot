import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import anthropic

# ── CONFIG ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # Sizning Telegram ID'ingiz

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── DATABASE (JSON fayl — oddiy va ishonchli) ───────────────────────────
DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "id": uid,
            "name": "",
            "phone": "",
            "status": "new",       # new → entry_test → training → certified
            "entry_score": 0,
            "current_day": 0,
            "completed_days": [],
            "day_scores": {},
            "streak": 0,
            "last_active": "",
            "total_score": 0,
            "started_at": datetime.now().isoformat(),
            "certified_at": "",
            "frozen": False,
        }
        save_db(db)
    return db[uid]

def update_user(user_id, data: dict):
    db = load_db()
    uid = str(user_id)
    db[uid].update(data)
    db[uid]["last_active"] = datetime.now().isoformat()
    save_db(db)

# ── KIRISH FILTRI SAVOLLARI ─────────────────────────────────────────────
ENTRY_QUESTIONS = [
    {
        "q": "📱 Smartfondan ilovalar yuklab olganmisiz? (App Store / Play Store)",
        "options": ["Ha, doim qilaman", "Ha, bir necha marta", "Yo'q, bilmayman"],
        "correct": 0,
        "weight": 2
    },
    {
        "q": "🗣 Notanish odamga biror narsani tushuntira olasizmi?",
        "options": ["Ha, yaxshi tushuntiram", "Qiynalaman lekin harakat qilaman", "Yo'q, uyalaman"],
        "correct": 0,
        "weight": 3
    },
    {
        "q": "⏰ Har kuni 2-3 soat o'rganishga vaqt ajrata olasizmi?",
        "options": ["Ha, majburiyat qilaman", "Harakat qilaman", "Qiyin, band bo'laman"],
        "correct": 0,
        "weight": 3
    },
    {
        "q": "💼 Biznes yoki do'kon bilan ishlagan tajribangiz bormi?",
        "options": ["Ha, ishlagan", "Kuzatganman / yaqinlarimda bor", "Yo'q, umuman yo'q"],
        "correct": None,  # Barchasi to'g'ri, faqat ma'lumot uchun
        "weight": 1
    },
    {
        "q": "🎯 Nima uchun BITO integratori bo'lmoqchisiz?",
        "options": [
            "Daromad topish va kasbni o'rganish uchun",
            "Shunchaki sinab ko'rmoqchiman",
            "Boshqa ish topolmadim"
        ],
        "correct": 0,
        "weight": 3
    },
]

# ── 14 KUNLIK KURS ──────────────────────────────────────────────────────
DAYS = {
    1: {
        "title": "BITO nima va interfeys",
        "theory": """📚 *1-KUN: BITO NIMA VA NIMA UCHUN KERAK*

BITO — do'kon egasining barcha ishini bitta joyga yig'adigan dastur.

*Bugun o'rganasiz:*
• Bito.uz da ro'yxatdan o'tish
• Interfeys va navigatsiya
• Tashkilot yaratish

*Manba:* docs.bito.online/readme/asosiy-sahifa

⏱ Nazariya: 30 daqiqa
🛠 Amaliyot: 1.5 soat""",
        "tasks": [
            "Bito.uz dan ro'yxatdan o'ting",
            "Interfeys bilan tanishing — barcha bo'limlarni bosib ko'ring",
            "Tashkilot yarating (do'kon nomi, manzil)",
            "Profilni to'ldiring",
        ],
        "homework": "Bito interfeysining asosiy 5 bo'limini screenshot qilib yuboring",
        "test_question": "BITO dasturida tashkilot yaratgandan keyin qaysi bo'limga o'tiladi?",
        "test_options": ["Ombor bo'limiga", "Sotuv bo'limiga", "Sozlamalar bo'limiga", "Moliya bo'limiga"],
        "test_correct": 2,
    },
    2: {
        "title": "Ombor — mahsulotlar bazasi",
        "theory": """📚 *2-KUN: OMBOR — MAHSULOTLAR BAZASI*

Mahsulot = nomi + narxi + kategoriyasi + o'lchov birligi + rasmi

*Bugun o'rganasiz:*
• Mahsulot qo'shish
• Kategoriya yaratish
• Barkod bilan ishlash

*Manba:* docs.bito.online/readme/ombor""",
        "tasks": [
            "10 ta mahsulot kiriting (nomi, narxi, rasmi, kategoriyasi)",
            "3 ta kategoriya yarating",
            "Barkod bilan mahsulot qidiring",
            "Mahsulotga rasm qo'shing",
        ],
        "homework": "20 ta mahsulot kiritib, ombor sahifasining screenshot'ini yuboring",
        "test_question": "Mahsulotga barkod qo'shishning maqsadi nima?",
        "test_options": [
            "Faqat ko'rinish uchun",
            "Tez qidirish va sotishda xato qilmaslik uchun",
            "Soliqqa hisobot berish uchun",
            "Internetda ko'rsatish uchun"
        ],
        "test_correct": 1,
    },
    3: {
        "title": "Ombor — qoldiq va sklad",
        "theory": """📚 *3-KUN: OMBOR — QOLDIQ, SKLAD VA BOSHQARISH*

*Asosiy tushunchalar:*
• Sklad — tovarlar saqlanadigan joy
• Kirim — tovar kelishi
• Chiqim — tovar ketishi
• Inventarizatsiya — haqiqiy qoldiqni tekshirish

*Manba:* docs.bito.online/readme/ombor""",
        "tasks": [
            "2 ta sklad yarating (Asosiy ombor, Do'kon)",
            "20 ta mahsulotga boshlang'ich qoldiq kiriting",
            "Skladlar o'rtasida 5 ta mahsulot ko'chiring",
            "Inventarizatsiya o'tkazing",
            "2 ta mahsulotni hisobdan chiqaring",
        ],
        "homework": "Inventarizatsiya natijasi + 2 ta sklad qoldiq hisoboti screenshot",
        "test_question": "Inventarizatsiya nima uchun kerak?",
        "test_options": [
            "Dasturni yangilash uchun",
            "Haqiqiy qoldiq va dastur qoldig'ini solishtirish uchun",
            "Tovarlarni ranglash uchun",
            "Xaridorga ko'rsatish uchun"
        ],
        "test_correct": 1,
    },
    4: {
        "title": "Ta'minot — xarid va yetkazib beruvchilar",
        "theory": """📚 *4-KUN: TA'MINOT — XARID VA YETKAZIB BERUVCHILAR*

*Asosiy tushunchalar:*
• Ta'minotchi — tovar beruvchi
• Naqdga xarid — hoziroq to'lov
• Qarzga xarid — keyinroq to'lov
• Akt-sverka — hisob-kitob tekshirish

*Manba:* docs.bito.online/readme/taminot""",
        "tasks": [
            "5 ta ta'minotchi qo'shing (ism, telefon, manzil)",
            "3 ta ta'minotchidan naqdga xarid qiling",
            "2 ta ta'minotchidan qarzga xarid qiling",
            "1 ta qaytarish amalga oshiring",
            "Ta'minotchiga qarz to'lang",
        ],
        "homework": "Ta'minotchi akt-sverka hisoboti screenshot'ini yuboring",
        "test_question": "Ta'minotchidan qarzga xarid qilganda nima bo'ladi?",
        "test_options": [
            "Tovar kelmaydi",
            "Tovar keladi, pul keyinroq to'lanadi",
            "Chegirma beriladi",
            "Hisobot yopiladi"
        ],
        "test_correct": 1,
    },
    5: {
        "title": "Sotuv — eng muhim modul",
        "theory": """📚 *5-KUN: SOTUV — ENG MUHIM MODUL* 🔥

Bu eng muhim kun! 7 xil sotuv turini o'rganing:

1️⃣ Naqd sotuv
2️⃣ Karta + naqd aralash
3️⃣ Qarzga sotuv
4️⃣ Qisman qarzga
5️⃣ Bo'lib to'lash (5 oyga)
6️⃣ Valyutada sotuv
7️⃣ Chek bilan qaytarish

*Manba:* docs.bito.online/readme/savdo""",
        "tasks": [
            "Naqd sotuv qiling (3 ta)",
            "Karta + naqd aralash sotuv (2 ta)",
            "Qarzga sotuv (2 ta)",
            "Qisman pul olib qolganini qarzga berish (1 ta)",
            "Bo'lib to'lash — 5 oyga (1 ta)",
            "Valyutada sotuv — so'm + dollar (1 ta)",
            "Chek bilan qaytarish (1 ta)",
        ],
        "homework": "7 xil sotuv turini bajarib, har biridan screenshot yuboring",
        "test_question": "Mijoz karta bilan 50.000 so'm to'lab, qolgan 30.000 so'mni qarzga qoldirdi. Bu qaysi sotuv turi?",
        "test_options": [
            "Naqd sotuv",
            "Qisman naqd, qisman qarz (aralash sotuv)",
            "Bo'lib to'lash",
            "Valyutada sotuv"
        ],
        "test_correct": 1,
    },
    6: {
        "title": "CRM va Marketing",
        "theory": """📚 *6-KUN: CRM VA MARKETING*

CRM = Mijozlar bilan munosabatlar tizimi

*Bugun o'rganasiz:*
• Mijoz bazasi yaratish
• Segmentatsiya (guruhga ajratish)
• Chegirma va keshbek tizimi
• Buyurtmalar

*Manba:* docs.bito.online/readme/crm""",
        "tasks": [
            "10 ta mijoz qo'shing",
            "Mijozlarni hududlarga ajrating (3 ta kategoriya)",
            "2 ta mijozdan buyurtma oling va 1 tasini yakunlang",
            "Mijozdan pul oling (qarz to'lash)",
            "20% chegirma yarating (5 kun muddatli)",
            "Mijozlar kesmida 30% chegirma bering",
            "1% keshbek sozlang",
        ],
        "homework": "Mijozlar ro'yxati va bir mijozning to'liq tarixi screenshot'ini yuboring",
        "test_question": "Keshbek va chegirmaning farqi nima?",
        "test_options": [
            "Farqi yo'q, bir xil narsa",
            "Chegirma — hozir narx tushadi, Keshbek — keyingi xaridda bonus beriladi",
            "Keshbek faqat VIP mijozlarga",
            "Chegirma faqat naqd sotuvda"
        ],
        "test_correct": 1,
    },
    7: {
        "title": "Moliya va HR",
        "theory": """📚 *7-KUN: MOLIYA VA HR*

*Moliya:* Kassa, balans, xarajatlar, valyuta
*HR:* Xodimlar, lavozimlar, ruxsatlar

Bu ikki modul biznesdagi «pul» va «odam» ni boshqaradi.

*Manba:* docs.bito.online/readme/moliya""",
        "tasks": [
            "Mijoz, ta'minotchi va kassa balansini o'rnating",
            "2 xil kompaniya xarajatini kiriting",
            "Kassa topshiring",
            "Valyuta ayirboshlang",
            "Xodimlarga oylik bering",
            "3 bo'lim, 3 lavozim yarating",
            "2 xodim qo'shib login/parol bering",
            "Kassir va omborchi uchun ruxsatlar sozlang",
        ],
        "homework": "Kassir va omborchi ruxsatlarini solishtiruvchi 2 ta screenshot yuboring",
        "test_question": "Kassir nega omborning to'liq qoldiqlarini ko'rmasligi kerak?",
        "test_options": [
            "Dastur shunday ishlaydi",
            "Tijorat siri va narx ma'lumotlari sizib ketmasligi uchun",
            "Kassir o'qimagan bo'lishi mumkin",
            "Bu kerak emas"
        ],
        "test_correct": 1,
    },
    8: {
        "title": "Hisobotlar — BITO'ning kuchi",
        "theory": """📚 *8-KUN: HISOBOTLAR — BITO'NING KUCHI* ⚡

*Tadbirkorga asosiy gap:*
"Aka, siz hozir har kuni kechqurun qo'lda hisoblaysiz.
Bito'da shu tugmani bossangiz — hamma narsa tayyor."

*O'rganasiz:*
• Sotuv hisoboti
• Ombor qoldiq
• Mijoz/ta'minotchi qarzdorlik
• Foyda hisoboti
• Kassa hisoboti""",
        "tasks": [
            "Kunlik sotuv hisobotini oching",
            "Haftalik sotuv hisobotini tahlil qiling",
            "Ombor qoldiq hisobotini ko'ring",
            "Mijoz qarzdorlik hisobotini oching",
            "Ta'minotchi qarzdorlik hisobotini oching",
            "Foyda hisobotini ko'ring",
            "Kassa hisobotini tekshiring",
        ],
        "homework": "Foyda hisoboti + Ombor qoldiq hisoboti screenshot'ini yuboring va qisqa tushuntiring",
        "test_question": "Tadbirkor «bugun qancha sof foyda qildim» deb so'rasa, qaysi hisobotni ochasiz?",
        "test_options": [
            "Sotuv hisoboti",
            "Kassa hisoboti",
            "PNL (Foyda/Zarar) hisoboti",
            "Ombor hisoboti"
        ],
        "test_correct": 2,
    },
    9: {
        "title": "Integratsiya va sozlamalar",
        "theory": """📚 *9-KUN: INTEGRATSIYA VA QO'SHIMCHA SOZLAMALAR*

*Bugun o'rganasiz:*
• Telegram bot sozlash (mijoz bot + ta'minotchi bot)
• Etiketka chiqarish
• Mahsulot import/eksport (Excel orqali)
• Chek sozlamalari

*Manba:* docs.bito.online/readme/integratsiyalar""",
        "tasks": [
            "Mijozlar uchun Telegram bot sozlang",
            "Ta'minotchi boti sozlang",
            "Mahsulot etiketkasini chiqaring",
            "Excel orqali mahsulot import qiling",
            "Chek dizaynini sozlang",
        ],
        "homework": "Telegram bot ishlayotgan screenshot va bitta import qilingan mahsulot screenshot'ini yuboring",
        "test_question": "Telegram bot integratsiyasi tadbirkorga qanday foyda beradi?",
        "test_options": [
            "Foyda bermaydi",
            "Mijozlar bot orqali qoldiq so'rashi va buyurtma berishi mumkin",
            "Faqat reklama uchun",
            "Soliq uchun kerak"
        ],
        "test_correct": 1,
    },
    10: {
        "title": "Biznes turlari",
        "theory": """📚 *10-KUN: BIZNES TURLARI — QAYSI BIZNESGA QANDAY SOZLASH*

| Biznes | Asosiy modullar | E'tibor |
|--------|----------------|---------|
| Mini market | POS + Ombor + Moliya | Tez sotuv |
| Ulgurji | Sotuv + CRM + Ombor | Qarz nazorat |
| Distributsiya | Sotuv + Logistika | Agent nazorat |
| Ishlab chiqarish | Ishlab ch. + Ombor | Tannarx |
| Xizmat | CRM + Moliya + HR | Mijoz, vaqt |""",
        "tasks": [
            "Mini market uchun to'liq sozlash simulyatsiyasi (40 daqiqa)",
            "Ulgurji savdo konfiguratsiyasini tushunish",
            "Distributsiya modelini o'rganish",
        ],
        "homework": "Mini market uchun noldan to tayyor sozlash — barcha qadamlar screenshot",
        "test_question": "Kafe/restoran uchun BITO'ning qaysi moduli eng muhim?",
        "test_options": [
            "Faqat kassa",
            "Ishlab chiqarish (retsept/kalkulyatsiya) + POS + Moliya",
            "Faqat HR",
            "Faqat CRM"
        ],
        "test_correct": 1,
    },
    11: {
        "title": "Ishlab chiqarish va Distributsiya",
        "theory": """📚 *11-KUN: ISHLAB CHIQARISH VA DISTRIBUTSIYA*

*Ishlab chiqarish:*
Xomashyo → Retsept/Texkarta → Tayyor mahsulot
BITO xomashyoni avtomat yechib oladi!

*Distributsiya:*
Agent → Zakaz → Yetkazib berish → Hisobot

*Manba:* docs.bito.online/readme/ishlab-chiqarish""",
        "tasks": [
            "Texkarta yarating (xomashyo + miqdor = tayyor mahsulot)",
            "Tayyor mahsulot ishlab chiqaring",
            "Agentlarga tashrif rejasi tuzing",
            "Agent orqali buyurtma oling",
            "Agent joylashuvini ko'ring",
        ],
        "homework": "Texkarta + tayyor mahsulot + agent zakazi screenshot'ini yuboring",
        "test_question": "Texkarta nima uchun kerak?",
        "test_options": [
            "Tovar ko'rinishi uchun",
            "1 ta tayyor mahsulot uchun nechta xomashyo ketishini belgilash — avtomatik yechish uchun",
            "Soliq uchun",
            "Xodimlar uchun"
        ],
        "test_correct": 1,
    },
    12: {
        "title": "3 minutlik demo tayyorlash",
        "theory": """📚 *12-KUN: 3 MINUTLIK DEMO TAYYORLASH* 🎯

Bu kursning eng muhim natijasi!

*DEMO SKRIPTI:*

🎬 *Ochilish:*
"Aka/opa, keling 3 minutda ko'rsataman — shu telefondan butun biznesingizni boshqarasiz."

1️⃣ *Sotuv (30 soniya):*
POS → barkod → sotuv → chek
"10 soniyada sotuv qildik va hamma narsa yozildi."

2️⃣ *Qoldiq (30 soniya):*
Ombor → qoldiq
"Bozorga ketmasdan bilasiz."

3️⃣ *Hisobot (30 soniya):*
Sotuv hisoboti → foyda
"Bugungi foyda — bitta tugma."

🎬 *Yopish:*
"Shu narsalarni hozir qo'lda qilasiz — Bito'da avtomatik. O'rnatish 1-2 kun."

*Topshiriq: VIDEO yozib yuboring!*""",
        "tasks": [
            "Demo skriptini yodlang",
            "3 marta mashq qiling (oynada yoki juftlikda)",
            "3 minutlik video yozib yuboring — AI baholaydi!",
        ],
        "homework": "3 minutlik demo video yuboring. AI 10 ballik tizimda baholaydi.",
        "test_question": "Demo ochilishida birinchi nima aytiladi?",
        "test_options": [
            "Narxni aytasiz",
            "'Keling 3 minutda ko'rsataman — telefondan butun biznesni boshqarasiz'",
            "Dastur haqida batafsil gapirasiz",
            "Tadbirkordan savol so'raysiz"
        ],
        "test_correct": 1,
    },
    13: {
        "title": "Qiymat taklifi — tadbirkor tilida",
        "theory": """📚 *13-KUN: QIYMAT TAKLIFI — TADBIRKOR TILIDA*

*Tadbirkor muammosi → Bito yechimi:*

❌ "Qoldiqni bilmayman"
✅ Ombor real-time → Yo'qotish kamayadi

❌ "Kim qancha qarz — esimda yo'q"
✅ CRM qarzdorlik → Pul qaytadi

❌ "Xodim o'g'irlayaptimi"
✅ Kassa sessiya + hisobot → Nazorat

❌ "Qaysi mahsulot yaxshi sotiladi"
✅ Sotuv hisoboti → To'g'ri xarid

*Mashq: Juftlikda — biri tadbirkor, biri integrator*""",
        "tasks": [
            "Har bir muammoni o'z so'zingiz bilan aytish mashqi",
            "5 ta e'tirozga javob bering (yozma)",
            "Juftlikda 5 daqiqa suhbat o'tkazing",
        ],
        "homework": "5 ta e'tirozga o'z so'zingiz bilan javob yozing — AI baholaydi!",
        "test_question": "Tadbirkor 'Qimmat ekan' desa, qanday javob berasiz?",
        "test_options": [
            "Narxni tushirasiz",
            "Chegirma berasiz",
            "'O'g'rilik va kamomaddan qancha yo'qotyapsiz? BITO 1 oyda o'zini oqlaydi' — deyasiz",
            "Gapni o'zgartirasiz"
        ],
        "test_correct": 2,
    },
    14: {
        "title": "YAKUNIY IMTIHON",
        "theory": """📚 *14-KUN: YAKUNIY IMTIHON* 🏆

Bugun hamma narsa hal bo'ladi!

*3 qism:*

📝 *1. Texnik test* (30 savol, 45 daqiqa)
O'tish mezoni: 70%+

🛠 *2. Amaliy test* (0 dan do'kon sozlash, 45 daqiqa)
Barcha qadamlar bajarilishi shart

🎬 *3. Demo test* (3 daqiqa video)
Baho: 7/10+

*O'tgan → BITO SERTIFIKATLANGAN INTEGRATOR*
*O'tmagan → 3 kun qo'shimcha mashq*""",
        "tasks": [
            "Texnik test (30 savol)",
            "Amaliy test (0 dan sozlash)",
            "Demo video (final)",
        ],
        "homework": "Barcha testlardan o'ting — sertifikat olasiz!",
        "test_question": None,  # Maxsus imtihon
        "test_options": [],
        "test_correct": None,
    },
}

# ── KEYBOARDS ───────────────────────────────────────────────────────────
def main_menu_kb():
    kb = [
        [InlineKeyboardButton("📚 Bugungi dars", callback_data="today")],
        [InlineKeyboardButton("📊 Mening progressim", callback_data="progress")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("❓ Yordam", callback_data="help")],
    ]
    return InlineKeyboardMarkup(kb)

def day_menu_kb(day_num):
    kb = [
        [InlineKeyboardButton("📖 Nazariya o'qish", callback_data=f"theory_{day_num}")],
        [InlineKeyboardButton("✅ Topshiriqlar ro'yxati", callback_data=f"tasks_{day_num}")],
        [InlineKeyboardButton("📤 Uy vazifasini yuborish", callback_data=f"submit_{day_num}")],
        [InlineKeyboardButton("🧠 Test topshirish", callback_data=f"test_{day_num}")],
        [InlineKeyboardButton("◀️ Bosh menu", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(kb)

# ── AI BAHOLASH ──────────────────────────────────────────────────────────
async def ai_evaluate(submission: str, day: int, task_type: str) -> dict:
    day_info = DAYS.get(day, {})
    
    prompt = f"""Sen BITO Academy'ning AI baholovchisisan. O'zbek tilida javob ber.

Kun: {day} — {day_info.get('title', '')}
Topshiriq turi: {task_type}
O'quvchi javobi/tavsifi: {submission}

Baholash mezonlari:
- Texnik to'g'rilik (0-4 ball)
- Tushunish chuqurligi (0-3 ball)  
- Amaliy qo'llash (0-3 ball)

Javob faqat JSON formatda:
{{
  "score": 7,
  "max": 10,
  "texnik": "...",
  "tushunish": "...",
  "amaliy": "...",
  "umumiy": "O'quvchiga rag'batlantiruvchi, aniq va foydali fikr (2-3 gap)",
  "yaxshilash": "Keyingi safar nima qilish kerak (1-2 gap)"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        # JSON ni tozalash
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return {
            "score": 7, "max": 10,
            "umumiy": "Yaxshi topshirdingiz! Davom eting.",
            "yaxshilash": "Har bir modulni amalda qo'llang."
        }

async def ai_demo_evaluate(text_description: str) -> dict:
    prompt = f"""Sen BITO Academy demo baholovchisisisan. O'zbek tilida javob ber.

O'quvchi o'z demo taqdimotini shunday tavsif qildi:
{text_description}

Demo baholash mezonlari (har biri 0-2 ball):
1. Ochilish (diqqat jalb qilish)
2. Sotuv ko'rsatish (10 soniyada)
3. Qoldiq ko'rsatish
4. Hisobot ko'rsatish
5. Yopish (keyingi qadam)

Faqat JSON:
{{
  "score": 8,
  "max": 10,
  "ochilish": "baho va fikr",
  "sotuv": "baho va fikr",
  "qoldiq": "baho va fikr", 
  "hisobot": "baho va fikr",
  "yopish": "baho va fikr",
  "umumiy": "Umumiy baho va motivatsiya (2-3 gap)",
  "passed": true
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"score": 7, "max": 10, "umumiy": "Yaxshi demo!", "passed": True}

# ── HANDLERS ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    u = get_user(uid)
    
    update_user(uid, {"name": user.full_name})
    
    if u["status"] == "new":
        await update.message.reply_text(
            f"👋 Salom, *{user.first_name}!*\n\n"
            "🎓 *BITO Academy 3.0* ga xush kelibsiz!\n\n"
            "Bu yerda 14 kunda *BITO Sertifikatlangan Integrator* bo'lasiz.\n\n"
            "Avval kichik kirish testidan o'tishingiz kerak. Tayyor bo'lsangiz bosing! 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Kirish testini boshlash", callback_data="start_entry")
            ]])
        )
    elif u["status"] == "training":
        await update.message.reply_text(
            f"Qaytib keldingiz, *{user.first_name}!* 💪\n\n"
            f"📅 Hozirgi kun: *{u['current_day']}-kun*\n"
            f"🔥 Streak: *{u['streak']} kun*",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    elif u["status"] == "certified":
        await update.message.reply_text(
            f"🏆 Siz allaqachon *BITO Sertifikatlangan Integrator*siz!\n\n"
            "Partner yo'lida davom eting!",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    else:
        await update.message.reply_text(
            "Xush kelibsiz! Testni tugallang.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Davom etish", callback_data="start_entry")
            ]])
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ── ENTRY TEST ──
    if data == "start_entry":
        update_user(uid, {"status": "entry_test", "entry_q": 0, "entry_score": 0})
        await show_entry_question(query, 0)

    elif data.startswith("eq_"):
        parts = data.split("_")
        q_idx = int(parts[1])
        ans_idx = int(parts[2])
        u = get_user(uid)
        
        q = ENTRY_QUESTIONS[q_idx]
        score = u.get("entry_score", 0)
        
        if q["correct"] is not None and ans_idx == q["correct"]:
            score += q["weight"]
        elif q["correct"] is None:
            score += 1  # Info savol, hamma javob qabul
        
        if q_idx + 1 < len(ENTRY_QUESTIONS):
            update_user(uid, {"entry_score": score})
            await show_entry_question(query, q_idx + 1)
        else:
            # Test tugadi
            max_score = sum(q["weight"] for q in ENTRY_QUESTIONS)
            percent = (score / max_score) * 100
            
            if percent >= 50:
                update_user(uid, {
                    "status": "training",
                    "entry_score": score,
                    "current_day": 1,
                    "streak": 0
                })
                await query.edit_message_text(
                    f"🎉 *Tabriklaymiz! Kirish testidan o'tdingiz!*\n\n"
                    f"📊 Ball: *{score}/{max_score}* ({percent:.0f}%)\n\n"
                    "✅ Siz 14 kunlik kursga qabul qilindingiz!\n\n"
                    "Endi har kuni darsga kirib, topshiriqlarni bajaring.\n"
                    "Har kun streak'ingiz oshib boradi! 🔥",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 1-kunni boshlash", callback_data="today")
                    ]])
                )
            else:
                update_user(uid, {"status": "failed_entry", "entry_score": score})
                await query.edit_message_text(
                    f"❌ *Afsuski, kirish testidan o'ta olmadingiz.*\n\n"
                    f"Ball: {score}/{max_score} ({percent:.0f}%)\n"
                    "O'tish uchun 50% kerak edi.\n\n"
                    "💡 Tavsiya: Smartfon bilan ko'proq ishlang va qayta urinib ko'ring.\n\n"
                    "3 kundan keyin qayta topshirishingiz mumkin.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Qayta urinish (3 kundan keyin)", callback_data="retry_entry")
                    ]])
                )

    elif data == "today":
        u = get_user(uid)
        if u["status"] != "training":
            await query.edit_message_text("Avval kirish testidan o'ting!")
            return
        day = u["current_day"]
        day_info = DAYS.get(day, {})
        await query.edit_message_text(
            f"📅 *{day}-KUN: {day_info.get('title', '').upper()}*\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=day_menu_kb(day)
        )

    elif data.startswith("theory_"):
        day = int(data.split("_")[1])
        day_info = DAYS.get(day, {})
        await query.edit_message_text(
            day_info.get("theory", "Nazariya topilmadi."),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Orqaga", callback_data=f"day_{day}")
            ]])
        )

    elif data.startswith("tasks_"):
        day = int(data.split("_")[1])
        day_info = DAYS.get(day, {})
        tasks_text = "\n".join([f"☐ {t}" for t in day_info.get("tasks", [])])
        await query.edit_message_text(
            f"✅ *{day}-KUN TOPSHIRIQLARI:*\n\n{tasks_text}\n\n"
            f"📝 *Uy vazifasi:*\n{day_info.get('homework', '')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 Yuborish", callback_data=f"submit_{day}"),
                InlineKeyboardButton("◀️ Orqaga", callback_data=f"day_{day}")
            ]])
        )

    elif data.startswith("submit_"):
        day = int(data.split("_")[1])
        context.user_data["waiting_submit"] = day
        await query.edit_message_text(
            f"📤 *{day}-kun uy vazifasini yuboring*\n\n"
            "Screenshot tavsifini yozing yoki nima qilganingizni batafsil yozing.\n"
            "AI sizning javobingizni baholaydi! 🤖\n\n"
            "_(Masalan: '20 ta mahsulot kiritdim, 3 kategoriya yaratdim, barkod bilan qidirdim va rasm qo'shdim')_",
            parse_mode="Markdown"
        )

    elif data.startswith("test_"):
        day = int(data.split("_")[1])
        day_info = DAYS.get(day, {})
        
        if day == 14:
            await show_final_exam(query, uid)
            return
            
        if day_info.get("test_question"):
            context.user_data["test_day"] = day
            opts = day_info["test_options"]
            kb = [[InlineKeyboardButton(f"{i+1}. {o}", callback_data=f"ans_{day}_{i}")]
                  for i, o in enumerate(opts)]
            await query.edit_message_text(
                f"🧠 *{day}-KUN TESTI:*\n\n{day_info['test_question']}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    elif data.startswith("ans_"):
        parts = data.split("_")
        day = int(parts[1])
        ans = int(parts[2])
        day_info = DAYS.get(day, {})
        correct = day_info.get("test_correct")
        u = get_user(uid)
        
        if ans == correct:
            # To'g'ri javob — kunni yakunlash
            completed = u.get("completed_days", [])
            if day not in completed:
                completed.append(day)
            
            next_day = day + 1
            streak = u.get("streak", 0) + 1
            score = u.get("total_score", 0) + 10
            
            update_user(uid, {
                "completed_days": completed,
                "current_day": min(next_day, 14),
                "streak": streak,
                "total_score": score,
                f"day_{day}_done": True
            })
            
            msg = (
                f"✅ *To'g'ri javob!*\n\n"
                f"🔥 Streak: *{streak} kun*\n"
                f"⭐ Jami ball: *{score}*\n\n"
            )
            if next_day <= 14:
                msg += f"🎯 *{next_day}-kun tayyor!*"
                kb = [[InlineKeyboardButton(f"▶️ {next_day}-kunga o'tish", callback_data="today")],
                      [InlineKeyboardButton("🏠 Bosh menu", callback_data="menu")]]
            else:
                msg += "🏆 *Barcha kunlar tugadi! Yakuniy imtihonga tayyor bo'ling!*"
                kb = [[InlineKeyboardButton("🏆 Yakuniy imtihon", callback_data="test_14")],
                      [InlineKeyboardButton("🏠 Bosh menu", callback_data="menu")]]
            
            await query.edit_message_text(msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb))
        else:
            correct_text = day_info["test_options"][correct]
            await query.edit_message_text(
                f"❌ *Noto'g'ri javob.*\n\n"
                f"To'g'ri javob: *{correct_text}*\n\n"
                "Nazariyani qayta o'qib, yana urinib ko'ring.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Qayta urinish", callback_data=f"test_{day}"),
                    InlineKeyboardButton("📖 Nazariya", callback_data=f"theory_{day}")
                ]])
            )

    elif data == "progress":
        u = get_user(uid)
        completed = len(u.get("completed_days", []))
        total = 14
        bar = "🟦" * completed + "⬜" * (total - completed)
        
        await query.edit_message_text(
            f"📊 *SIZNING PROGRESSINGIZ*\n\n"
            f"👤 {u.get('name', 'Foydalanuvchi')}\n\n"
            f"📅 Joriy kun: *{u.get('current_day', 1)}/14*\n"
            f"✅ Tugallangan: *{completed}/14*\n"
            f"🔥 Streak: *{u.get('streak', 0)} kun*\n"
            f"⭐ Ball: *{u.get('total_score', 0)}*\n\n"
            f"```\n{bar}\n```\n"
            f"📈 {completed/total*100:.0f}% tugallandi",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Orqaga", callback_data="menu")
            ]])
        )

    elif data == "leaderboard":
        db = load_db()
        users = [(v.get("name", "?"), v.get("total_score", 0), v.get("streak", 0))
                 for v in db.values() if v.get("status") in ["training", "certified"]]
        users.sort(key=lambda x: x[1], reverse=True)
        
        text = "🏆 *TOP INTEGRATORLAR*\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, score, streak) in enumerate(users[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} {name} — ⭐{score} 🔥{streak}\n"
        
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Orqaga", callback_data="menu")
            ]]))

    elif data == "menu":
        await query.edit_message_text(
            "🎓 *BITO Academy 3.0*\nNima qilmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

    elif data.startswith("day_"):
        day = int(data.split("_")[1])
        day_info = DAYS.get(day, {})
        await query.edit_message_text(
            f"📅 *{day}-KUN: {day_info.get('title', '').upper()}*",
            parse_mode="Markdown",
            reply_markup=day_menu_kb(day)
        )

    elif data == "help":
        await query.edit_message_text(
            "❓ *YORDAM*\n\n"
            "📚 Har kuni:\n"
            "1. Nazariyani o'qing\n"
            "2. Topshiriqlarni bajaring\n"
            "3. Uy vazifasini yuboring\n"
            "4. Testdan o'ting\n\n"
            "🔥 Streak uchun har kuni kiring!\n\n"
            "📞 Muammo bo'lsa: @bito_support",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Orqaga", callback_data="menu")
            ]])
        )

async def show_entry_question(query, q_idx):
    q = ENTRY_QUESTIONS[q_idx]
    kb = [[InlineKeyboardButton(opt, callback_data=f"eq_{q_idx}_{i}")]
          for i, opt in enumerate(q["options"])]
    
    await query.edit_message_text(
        f"📝 *Kirish testi — {q_idx+1}/{len(ENTRY_QUESTIONS)}*\n\n"
        f"{q['q']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_final_exam(query, uid):
    await query.edit_message_text(
        "🏆 *YAKUNIY IMTIHON*\n\n"
        "3 qism:\n"
        "1️⃣ Texnik test (30 savol)\n"
        "2️⃣ Amaliy test (0 dan sozlash)\n"
        "3️⃣ Demo video\n\n"
        "Tayyor bo'lsangiz demo videongizni yuboring!\n"
        "Video tavsifini yozib yuboring — AI baholaydi.",
        parse_mode="Markdown"
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    u = get_user(uid)

    # Uy vazifasi yuborilgan
    if context.user_data.get("waiting_submit"):
        day = context.user_data.pop("waiting_submit")
        
        await update.message.reply_text("🤖 AI baholayapti... bir soniya sabr qiling...")
        
        result = await ai_evaluate(text, day, "homework")
        score = result.get("score", 7)
        max_s = result.get("max", 10)
        
        stars = "⭐" * score + "☆" * (max_s - score)
        
        msg = (
            f"📊 *AI BAHOLASH NATIJASI — {day}-kun*\n\n"
            f"{stars}\n"
            f"*Ball: {score}/{max_s}*\n\n"
            f"💬 *Fikr:*\n{result.get('umumiy', '')}\n\n"
            f"💡 *Yaxshilash:*\n{result.get('yaxshilash', '')}"
        )
        
        # Ballni qo'shish
        total = u.get("total_score", 0) + score
        update_user(uid, {"total_score": total, f"hw_{day}_score": score})
        
        kb = [[InlineKeyboardButton("🧠 Testga o'tish", callback_data=f"test_{day}")],
              [InlineKeyboardButton("🏠 Bosh menu", callback_data="menu")]]
        
        await update.message.reply_text(msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb))
        return

    # Default
    if u["status"] == "training":
        await update.message.reply_text(
            "Quyidagi menyu orqali davom eting 👇",
            reply_markup=main_menu_kb()
        )
    elif u["status"] == "new":
        await update.message.reply_text(
            "Avval kirish testini boshlang!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Boshlash", callback_data="start_entry")
            ]])
        )

# ── ADMIN COMMANDS ───────────────────────────────────────────────────────
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    db = load_db()
    total = len(db)
    new = sum(1 for u in db.values() if u.get("status") == "new")
    entry = sum(1 for u in db.values() if u.get("status") == "entry_test")
    training = sum(1 for u in db.values() if u.get("status") == "training")
    certified = sum(1 for u in db.values() if u.get("status") == "certified")
    failed = sum(1 for u in db.values() if u.get("status") == "failed_entry")
    
    await update.message.reply_text(
        f"📊 *ADMIN STATISTIKA*\n\n"
        f"👥 Jami foydalanuvchilar: *{total}*\n"
        f"🆕 Yangi: *{new}*\n"
        f"📝 Test jarayonida: *{entry}*\n"
        f"📚 O'qiyapti: *{training}*\n"
        f"🏆 Sertifikatlangan: *{certified}*\n"
        f"❌ Testdan o'tmagan: *{failed}*",
        parse_mode="Markdown"
    )


async def open_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mini App ni ochish"""
    # GitHub Pages URL
    MINIAPP_URL = "https://tulavov.github.io/bito-academy-bot/miniapp"
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🎓 BITO Academy ochish",
            web_app={"url": MINIAPP_URL}
        )
    ]])
    await update.message.reply_text(
        "👆 Tugmani bosib BITO Academy ni oching!",
        reply_markup=kb
    )

# ── MAIN ─────────────────────────────────────────────────────────────────
def main():
    print("🤖 BITO Academy Bot ishga tushmoqda...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("app", open_app))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30,
        close_loop=False
    )

if __name__ == "__main__":
    main()
