# BITO Academy Bot — O'rnatish Qo'llanmasi

## Bot nima qiladi?
- Kirish filtri (5 savol, 50% o'tish kerak)
- 14 kunlik kurs (har kun nazariya + topshiriqlar + test)
- AI baholash (Claude orqali uy vazifalari baholanadi)
- Progress tracking + streak
- Leaderboard
- Admin statistika

## Railway.app da joylash (BEPUL)

### 1. GitHub account oching
- github.com ga boring, ro'yxatdan o'ting

### 2. Yangi repository yarating
- "New repository" bosing
- Nom: `bito-academy-bot`
- Public tanlang
- Create bosing

### 3. Fayllarni yuklang
Bu papkadagi 4 ta faylni yuklang:
- bot.py
- requirements.txt
- Procfile
- README.md

### 4. Railway.app ga boring
- railway.app
- "Start a New Project" bosing
- "Deploy from GitHub repo" tanlang
- bito-academy-bot ni tanlang

### 5. Environment Variables qo'shing
Railway dashboard → Variables bo'limi:

| Kalit | Qiymat |
|-------|--------|
| BOT_TOKEN | (BotFather dan olgan token) |
| ANTHROPIC_KEY | (Claude API key) |
| ADMIN_ID | (Sizning Telegram ID'ingiz) |

### Telegram ID ni qanday bilaman?
@userinfobot ga yozing → u sizning ID'ingizni beradi

### Claude API key qayerdan?
console.anthropic.com → API Keys → Create Key

### 6. Deploy bosing
Railway avtomatik ishga tushiradi!

## Bot buyruqlari
- /start — Boshlash
- /stats — Admin statistika (faqat admin uchun)
