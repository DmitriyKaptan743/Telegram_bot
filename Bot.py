import os
import telebot
from flask import Flask, request
import logging
import random
import json

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен з Environment Variables
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    logger.error("API_TOKEN не знайдено в змінних середовища!")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Flask для вебхука
app = Flask(__name__)

# Локальна база користувачів {user_id: {"username": ..., "points": ...}}
users = {}

# Нагороди
REWARD_THRESHOLDS = {
    10: "🥉 Бронзова нагорода!",
    25: "🥈 Срібна нагорода!",
    50: "🥇 Золота нагорода!",
    100: "🏆 Платинова нагорода!"
}

def add_points(user_id, username, points_to_add):
    """Додає бали користувачу у локальну базу"""
    user = users.get(user_id, {"username": username, "points": 0})
    user["points"] += points_to_add
    user["username"] = username
    users[user_id] = user
    logger.info(f"Користувач {username} ({user_id}) отримав {points_to_add} балів. Загалом: {user['points']}")
    return user["points"]

def get_user_points(user_id):
    """Отримує бали користувача"""
    return users.get(user_id, {}).get("points", 0)

def check_rewards(points):
    """Перевіряє нагороди"""
    rewards = []
    for threshold, reward in REWARD_THRESHOLDS.items():
        if points == threshold:
            rewards.append(reward)
    return rewards

# ======================
# Хендлери команд
# ======================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        logger.info(f"Отримано команду /start від користувача {message.from_user.id}")
        welcome_text = ("Вітаю! 🤖\n\n"
                        "Напиши 'Привіт' і отримуй бали.\n"
                        "Перевір баланс командою /score.\n\n"
                        "Удачі! 🍀")
        bot.reply_to(message, welcome_text)
    except Exception as e:
        logger.error(f"Помилка в send_welcome: {e}")

@bot.message_handler(commands=['score'])
def send_score(message):
    try:
        user_id = message.from_user.id
        points = get_user_points(user_id)
        username = message.from_user.username or message.from_user.first_name
        score_text = f"👤 {username}\n💰 У вас {points} балів."
        bot.reply_to(message, score_text)
    except Exception as e:
        logger.error(f"Помилка в send_score: {e}")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def count_hello(message):
    try:
        text = message.text if message.text else ""
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name

        logger.info(f"Отримано повідомлення від {username} ({user_id}): {text[:50]}...")

        # Підрахунок слова "привіт" (та інші варіанти)
        text_lower = text.lower()
        greetings = ["привіт", "привет", "hello", "hi", "hey"]
        count = sum(text_lower.count(g) for g in greetings)

        if count > 0:
            points = add_points(user_id, username, count)
            rewards = check_rewards(points)

            reply = f"🎉 Ви отримали {count} бал(ів)!\n💰 Загалом у вас {points} балів."
            if rewards:
                reply += "\n\n🏅 " + "\n🏅 ".join(rewards)

            bot.reply_to(message, reply)
        else:
            responses = [
                "Цікаво! Напишіть 'Привіт', щоб отримати бали! 😊",
                "Я розумію! Але бали дають тільки за 'Привіт' 🤖",
                "Дякую за повідомлення! Спробуйте написати 'Привіт' 👋"
            ]
            bot.reply_to(message, random.choice(responses))

    except Exception as e:
        logger.error(f"Помилка в count_hello: {e}")

# ======================
# Flask routes
# ======================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        logger.info(f"Отримано webhook: {json_str[:200]}...")

        update = telebot.types.Update.de_json(json.loads(json_str))
        bot.process_new_updates([update])

        logger.info("Webhook успішно оброблено")
        return "OK", 200
    except Exception as e:
        logger.error(f"Помилка в webhook: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    return "🤖 Telegram Bot is running! 🚀", 200

@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "healthy", "bot_token": "configured" if API_TOKEN else "missing"}, 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        webhook_url = f"https://{request.host}/{API_TOKEN}"
        result = bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook встановлено: {webhook_url}")
        return f"Webhook set: {result}", 200
    except Exception as e:
        logger.error(f"Помилка встановлення webhook: {e}")
        return f"Error: {e}", 500

if __name__ == "__main__":
    print("🚀 BOT SCRIPT STARTED")
    logger.info(f"API_TOKEN налаштовано: {'Так' if API_TOKEN else 'Ні'}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
