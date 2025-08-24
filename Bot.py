import os
import telebot
import firebase_admin
from firebase_admin import credentials, db
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

# Firebase ініціалізація з перевіркою помилок
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("telegram-c480f-firebase-adminsdk-fbsvc-71cde196d0.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://telegram-c480f-default-rtdb.firebaseio.com/'
        })
        logger.info("Firebase успішно ініціалізовано")
    else:
        logger.info("Firebase вже було ініціалізовано")
except Exception as e:
    logger.error(f"Помилка ініціалізації Firebase: {e}")
    firebase_admin = None

# Flask для вебхука
app = Flask(__name__)

REWARD_THRESHOLDS = {
    10: "🥉 Бронзова нагорода!",
    25: "🥈 Срібна нагорода!",
    50: "🥇 Золота нагорода!",
    100: "🏆 Платинова нагорода!"
}

def add_points(user_id, username, points_to_add):
    """Додає бали користувачу в базу даних"""
    try:
        if not firebase_admin or not firebase_admin._apps:
            logger.warning("Firebase не доступний, використовуємо локальне збереження")
            return points_to_add

        ref = db.reference(f'users/{user_id}')
        user_data = ref.get()
        if user_data:
            new_points = user_data.get('points', 0) + points_to_add
            ref.update({'points': new_points, 'username': username})
        else:
            new_points = points_to_add
            ref.set({'username': username, 'points': new_points})

        logger.info(f"Користувач {username} ({user_id}) отримав {points_to_add} балів. Загалом: {new_points}")
        return new_points
    except Exception as e:
        logger.error(f"Помилка при додаванні балів: {e}")
        return points_to_add

def get_user_points(user_id):
    """Отримує бали користувача з бази даних"""
    try:
        if not firebase_admin or not firebase_admin._apps:
            logger.warning("Firebase не доступний")
            return 0

        ref = db.reference(f'users/{user_id}')
        user_data = ref.get()
        points = user_data.get('points', 0) if user_data else 0
        return points
    except Exception as e:
        logger.error(f"Помилка при отриманні балів: {e}")
        return 0

def check_rewards(points):
    """Перевіряє, чи заслуговує користувач на нагороду"""
    rewards = []
    for threshold, reward in REWARD_THRESHOLDS.items():
        if points == threshold:
            rewards.append(reward)
    return rewards

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обробник команди /start"""
    try:
        logger.info(f"Отримано команду /start від користувача {message.from_user.id}")
        welcome_text = ("Вітаю! 🤖\n\n"
                        "Напиши 'Привіт' і отримуй бали.\n"
                        "Перевір баланс командою /score.\n\n"
                        "Удачі! 🍀")
        bot.reply_to(message, welcome_text)
        logger.info(f"Надіслано привітання користувачу {message.from_user.id}")
    except Exception as e:
        logger.error(f"Помилка в send_welcome: {e}")
        try:
            bot.reply_to(message, "Виникла помилка, але я працюю! Спробуйте ще раз.")
        except Exception as ex:
            logger.error("Не вдалося відправити повідомлення про помилку")

@bot.message_handler(commands=['score'])
def send_score(message):
    """Обробник команди /score"""
    try:
        user_id = message.from_user.id
        logger.info(f"Запит балансу від користувача {user_id}")

        points = get_user_points(user_id)
        username = message.from_user.username or message.from_user.first_name

        score_text = f"👤 {username}\n💰 У вас {points} балів."
        bot.reply_to(message, score_text)
        logger.info(f"Надіслано баланс користувачу {user_id}: {points} балів")
    except Exception as e:
        logger.error(f"Помилка в send_score: {e}")
        try:
            bot.reply_to(message, "Помилка при отриманні балансу. Спробуйте пізніше.")
        except Exception as ex:
            logger.error("Не вдалося відправити повідомлення про помилку")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def count_hello(message):
    """Обробник всіх текстових повідомлень"""
    try:
        text = message.text if message.text else ""
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name

        logger.info(f"Отримано повідомлення від {username} ({user_id}): {text[:50]}...")

        # Підрахунок слова "привіт" (різні варіанти)
        text_lower = text.lower()
        greetings = ["привіт", "привет", "hello", "hi", "hey"]
        count = 0
        for greeting in greetings:
            count += text_lower.count(greeting)

        if count > 0:
            points = add_points(user_id, username, count)
            rewards = check_rewards(points)

            reply = f"🎉 Ви отримали {count} бал(ів)!\n💰 Загалом у вас {points} балів."

            if rewards:
                reply += "\n\n🏅 " + "\n🏅 ".join(rewards)

            bot.reply_to(message, reply)
            logger.info(f"Користувач {username} отримав {count} балів")
        else:
            responses = [
                "Цікаво! Напишіть 'Привіт', щоб отримати бали! 😊",
                "Я розумію! Але бали дають тільки за 'Привіт' 🤖",
                "Дякую за повідомлення! Спробуйте написати 'Привіт' 👋"
            ]
            bot.reply_to(message, random.choice(responses))

    except Exception as e:
        logger.error(f"Помилка в count_hello: {e}")
        try:
            bot.reply_to(message, "Щось пішло не так, але я все ще тут! 🤖")
        except Exception as ex:
            logger.error("Не вдалося відправити повідомлення про помилку")

# ======================
# Flask routes
# ======================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    """Обробник вебхука від Telegram"""
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
    """Головна сторінка для перевірки статусу"""
    return "🤖 Telegram Bot is running! 🚀", 200

@app.route("/health", methods=["GET"])
def health_check():
    """Перевірка здоров'я сервісу"""
    return {"status": "healthy", "bot_token": "configured" if API_TOKEN else "missing"}, 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Встановлення вебхука (для налагодження)"""
    try:
        webhook_url = f"https://{request.host}/{API_TOKEN}"
        result = bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook встановлено: {webhook_url}")
        return f"Webhook set: {result}", 200
    except Exception as e:
        logger.error(f"Помилка встановлення webhook: {e}")
        return f"Error: {e}", 500

if __name__ == "__main__":
    logger.info("Запуск Telegram бота...")
    logger.info(f"API_TOKEN налаштовано: {'Так' if API_TOKEN else 'Ні'}")

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Запуск сервера на порту {port}")

    app.run(host="0.0.0.0", port=port, debug=False)
