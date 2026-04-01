import os
import re
import logging
import tempfile
from io import BytesIO
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

CONTROLLER_BOT_USERNAME = os.getenv("CONTROLLER_BOT_USERNAME", "Lazizxon_controller_Bot").lstrip("@")
CEO_BOT_USERNAME = os.getenv("CEO_BOT_USERNAME", "Anvarxon_ceo_Bot").lstrip("@")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY topilmadi")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY topilmadi")
if not VOICE_ID:
    raise ValueError("VOICE_ID topilmadi")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

TEAM_CONTEXT = """
Жамоа таркиби:

1. Анвархон — @Anvarxon_ceo_Bot — CEO, стратегия, қарор қабул қилиш, бизнес йўналиши, приоритет, масштаблаш
2. Умаржон — @Umarjon_Marketolog_bot — маркетинг, бренд, реклама, лид генерация, позициялаш
3. Ғайратжон — @Gayrat_Finance_Bot — молия, cash flow, харажат, фойда, нарх, маржа
4. Исломжон — @Islomjon_Rop_Bot — РОП, сотув бўлими раҳбари, сотув тизими, скрипт, конверсия, closing
5. Махмуджон — @Maxmudjon_hr_Bot — HR, найм, жамоа, мотивация, ходимлар самарадорлиги
6. Расулжон — @Rasuljon_lawyer_Bot — юрист, шартнома, ҳуқуқий ҳимоя, юридик рисклар
7. Муродхон — @Murodxon_tax_Bot — солиқ, легал оптимизация, солиқ режалаштириш
8. Бехрузбек — @Behruz_creative_Bot — креатив директор, визуал ғоя, контент, реклама концепцияси
9. Улуғбек — @Ulugbek_innovator_Bot — инновация, янги ғоя, MVP, автоматизация
10. Ахли илм домла — @Domla_sharia_Bot — шаръий масалалар, ҳалол-ҳаром, шариатга мувофиқлик
11. Лазизхон — @Lazizxon_controller_Bot — назорат, тақсимлаш, дедлайн, сифат текшируви, раҳбар ва жамоа ўртасида кўприк
"""

CEO_PROMPT = f"""
Сен Анвархон исмли AI CEOсан.

Сенинг ролиң:
- стратегия бериш
- бизнес бўйича асосий қарорларни шакллантириш
- устуворликларни белгилаш
- компания учун тўғри йўналишни кўрсатиш
- бизнес мақсадига мос ечим бериш
- раҳбар даражасида фикрлаш

Сенинг ишлаш қоидаң:
- сен раҳбар билан тўғридан-тўғри ишламайсан
- сен фақат Назоратчи орқали ишлайсан
- Назоратчи йўналтирмаган вазифага жавоб бермайсан
- сен мутахассисларга тўғридан-тўғри вазифа бермайсан
- сен ўз жавобингни Назоратчига тақдим қиласан
- сендан кейин бажариш жараёнини Назоратчи бошқаради

Ички бошқарув тартиби:
Раҳбар → Назоратчи → Сен
Сен → Назоратчи → Раҳбар

Назоратчи:
Лазизхон — @{CONTROLLER_BOT_USERNAME}

Сен қуйидагиларни қилмайсан:
- микроменежмент
- операцион назорат
- дедлайн қувиш
- тўғридан-тўғри ижрочи билан ишлаш

Бу ишлар Назоратчига тегишли.

Сенинг фикрлашинг:
- стратегик
- аниқ
- бизнес мантиғига асосланган
- натижага қаратилган
- приоритетни яхши ажратадиган

Жавоб бериш қоидалари:
- жавоблар фақат ўзбек тилида, кирилл алифбосида бўлсин
- жавоблар қисқа, кучли ва стратегик бўлсин
- кераксиз назария ёзма
- CEO сифатида қарор ва йўналиш бер
- агар маълумот етарли бўлмаса, 3 тагача аниқлаштирувчи савол бер
- сен раҳбарга эмас, Назоратчига жавоб бераётгандек ёз

Жавоб формати:
1. CEO таҳлили
2. Асосий қарор
3. Стратегик йўналиш
4. 3-5 амалий қадам
5. Эҳтимолий рисклар

Қўшимча контекст:
{TEAM_CONTEXT}
"""

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def message_mentions_bot(text: str, bot_username: str) -> bool:
    if not text:
        return False
    return f"@{bot_username.lower()}" in text.lower()

def should_ceo_reply(update: Update) -> bool:
    if not update.message:
        return False

    txt = update.message.text or update.message.caption or ""
    from_username = (update.effective_user.username or "").lower()

    if from_username == CONTROLLER_BOT_USERNAME.lower() and message_mentions_bot(txt, CEO_BOT_USERNAME):
        return True

    if from_username == CONTROLLER_BOT_USERNAME.lower() and update.message.reply_to_message:
        reply_from = update.message.reply_to_message.from_user
        if reply_from and (reply_from.username or "").lower() == CEO_BOT_USERNAME.lower():
            return True

    return False

def extract_task_from_controller_message(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace(f"@{CEO_BOT_USERNAME}", "").strip()
    return cleaned

def speech_to_text(audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )
    return (transcription.text or "").strip()

def elevenlabs_text_to_speech(text: str) -> BytesIO:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    data = {
        "text": text[:2500],
        "model_id": "eleven_multilingual_v2",
    }

    response = requests.post(url, json=data, headers=headers, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs xatolik: {response.status_code} | {response.text}")

    audio = BytesIO(response.content)
    audio.name = "voice.mp3"
    audio.seek(0)
    return audio

async def send_voice_reply(update: Update, text: str):
    try:
        audio_file = elevenlabs_text_to_speech(text)
        await update.message.reply_voice(voice=audio_file)
    except Exception as e:
        logger.exception("CEO ElevenLabs ovozli javob xatosi")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

def generate_ceo_reply(user_message: str) -> str:
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": CEO_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    reply = response.output_text.strip() if response.output_text else ""
    if not reply:
        reply = "CEO жавоби тайёр бўлмади."
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Салом. Мен Анвархон CEO ботман.\n"
        "Мен фақат Назоратчи орқали келган вазифаларга стратегик жавоб бераман."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Ишлаш тартиби:\n"
        f"1. Раҳбар тўғридан-тўғри менга вазифа бермайди\n"
        f"2. Назоратчи @{CONTROLLER_BOT_USERNAME} мени йўналтиради\n"
        f"3. Мен CEO сифатида стратегия ва қарор бўйича жавоб бераман\n"
        f"4. Ижро ва назоратни Назоратчи давом эттиради"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not should_ceo_reply(update):
        return

    try:
        task_text = extract_task_from_controller_message(normalize_text(update.message.text))
        reply = generate_ceo_reply(task_text)

        await update.message.reply_text(reply)
        await send_voice_reply(update, reply)

    except Exception as e:
        logger.exception("CEO text error")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return
    if not should_ceo_reply(update):
        return

    temp_ogg_path: Optional[str] = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_ogg_path = temp_audio.name

        await voice_file.download_to_drive(temp_ogg_path)

        user_text = speech_to_text(temp_ogg_path)

        if not user_text:
            await update.message.reply_text("Овозли вазифа тушунилмади.")
            return

        reply = generate_ceo_reply(user_text)

        await update.message.reply_text(reply)
        await send_voice_reply(update, reply)

    except Exception as e:
        logger.exception("CEO voice error")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("CEO bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()