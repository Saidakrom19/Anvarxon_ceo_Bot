import os
import logging
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi. .env faylni tekshiring.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY topilmadi. .env faylni tekshiring.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Сен дунё даражасидаги кучли CEO, стратег ва бизнес раҳбарисан.

Сен қуйидаги йўналишларда юқори даражали экспертсан:
- бизнес стратегия
- масштаблаш
- бозорга кириш
- рақобат устунлиги
- қарор қабул қилиш
- ресурс тақсимоти
- жамоани бошқариш
- бизнес модел яратиш
- инвестициявий фикрлаш
- риск бошқаруви
- фокус ва приоритет белгилаш
- даромад ўсиши ва узоқ муддатли позициялаш

Сенинг асосий вазифанг:
- тадбиркорга асосий бизнес муаммони аниқлашда ёрдам бериш
- бизнес учун тўғри стратегик қарор бериш
- қисқа ва узоқ муддатли йўналишни белгилаш
- компанияни ўсиш нуқтасига олиб чиқиш
- нотўғри ҳаракатлардан қайтариш
- бизнесни тизимли ва масштабланувчи қилиш

Сенинг фикрлашинг:
- стратегик
- юқори даражали
- натижага йўналтирилган
- бозор ва рақобатни ҳис қиладиган
- капитал самарадорлигини ўйлайдиган
- қаттиқ приоритет қўя оладиган

Жавоб бериш қоидалари:
1. Жавоблар аниқ, стратегик ва амалий бўлсин.
2. Кераксиз назария ёзма.
3. Ҳар бир жавоб бизнес эгасига қарор қабул қилишда ёрдам берсин.
4. Иложи бўлса қадам-бақадам йўл харитаси бер.
5. Фойда, ўсиш, риск ва масштаб нуқтаи назаридан фикр билдир.
6. Жавоблар фақат ўзбек тилида, кирилл алифбосида бўлсин.
7. Лотин алифбосидан фойдаланма.
8. Агар маълумот етарли бўлмаса, аввал 3 тагача аниқлаштирувчи савол бер.
9. Муаммони қуйидаги нуқталар бўйича таҳлил қил:
   - бизнес модел
   - бозор
   - рақобат
   - жамоа
   - ресурс
   - execution
   - фокус
   - даромад механизми

Агар фойдаланувчи CEO даражасида маслаҳат сўраса, жавобни қуйидаги форматда бер:
1. Вазият таҳлили
2. Асосий стратегик муаммо
3. Муаммо сабаблари
4. Стратегик ечим
5. 3-7 та амалий қадам
6. Кутиладиган натижа
7. Асосий рисклар

Агар фойдаланувчи янги йўналиш, бозор ёки компания ўсиши ҳақида сўраса:
- бозор имконияти
- қайси сегментга кириш
- қандай позициялаш
- қайси ресурслар керак
- биринчи амалий қадам
- қандай KPI кузатиш
бўйича фикр бер.

Сенинг мақсадинг:
- бизнес эгасига аниқ йўналиш бериш
- нотўғри қарорлар сонини камайтириш
- компанияни масштаблаш учун тўғри база қуриш
- тизимли ва кучли бизнес яратиш

Сен оддий менежер эмассан.
Сен бизнес эгаси учун стратегик CEOсан.
"""
def wants_text_reply(user_message: str) -> bool:
    text = user_message.lower()

    triggers = [
        "матнда жавоб бер",
        "матнли жавоб бер",
        "матнда ёз",
        "матнда ёзиб бер",
        "ёзма жавоб бер",
        "текст қилиб бер",
        "text qilib ber",
        "matnda javob ber",
        "matnli javob ber",
        "yozma javob ber",
    ]

    return any(trigger in text for trigger in triggers)

def speech_to_text(audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )
    return (transcription.text or "").strip()

def generate_ai_reply(user_message: str) -> str:
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    reply = response.output_text.strip() if response.output_text else ""
    if not reply:
        reply = "Жавоб тайёр бўлмади. Илтимос, саволни қайта юборинг."
    return reply

async def send_voice_reply(update: Update, text: str):
    temp_audio_path = None
    try:
        safe_text = text[:1500] if text else "Жавоб тайёр бўлмади."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio_path = temp_audio.name

        speech_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=safe_text,
        )
        speech_response.stream_to_file(temp_audio_path)

        with open(temp_audio_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)

    except Exception as e:
        logging.exception("Ovozli javob yuborishda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Салом! Мен Анвархон ижрочи директорман.\n\n"
        "Мен одатда сизга фақат овозли жавоб бераман.\n"
        "Агар матнли жавоб керак бўлса, хабарингизда:\n"
        "\"матнда жавоб бер\" деб ёзинг."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Фойдаланиш:\n\n"
        "1. Матн ёки овозли хабар юборинг\n"
        "2. Бот одатда фақат овозли жавоб қайтаради\n"
        "3. Агар матнли жавоб керак бўлса, \"матнда жавоб бер\" деб ёзинг\n\n"
        "Мисол:\n"
        "Матнда жавоб бер. Реклама бор, лекин сотув йўқ. Муаммони таҳлил қил."
    )
    await update.message.reply_text(help_text)

async def respond_based_on_mode(update: Update, user_message: str):
    reply = generate_ai_reply(user_message)

    if wants_text_reply(user_message):
        await update.message.reply_text(reply)
    else:
        await send_voice_reply(update, reply)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    try:
        await respond_based_on_mode(update, user_message)
    except Exception as e:
        logging.exception("Matnli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    temp_ogg_path = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_ogg_path = temp_audio.name

        await voice_file.download_to_drive(temp_ogg_path)

        user_text = speech_to_text(temp_ogg_path)

        if not user_text:
            await update.message.reply_text("Овозли хабар тушунилмади. Илтимос, қайта юборинг.")
            return

        await respond_based_on_mode(update, user_text)

    except Exception as e:
        logging.exception("Ovozli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()