import os
import telebot
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

# Токен з Environment Variables (Render -> Environment)
API_TOKEN = os.getenv("API_TOKEN")

bot = telebot.TeleBot(API_TOKEN)

# Firebase
cred = credentials.Certificate("telegram-c480f-firebase-adminsdk-fbsvc-71cde196d0.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://telegram-c480f-default-rtdb.firebaseio.com/'
})

# Flask для вебхука
app = Flask(__name__)

REWARD_THRESHOLDS = {
    10: "🥉 Бронзова нагорода!",
    25: "🥈 Срібна нагорода!",
    50: "🥇 Золота нагорода!",
    100: "🏆 Платинова нагорода!"
}

def add_points(user_id, username, points_to_add):
    ref = db.reference(f'users/{user_id}')
    user_data = ref.get()
    if user_data:
        new_points = user_data.get('points', 0) + points_to_add
        ref.update({'points': new_points, 'username': username})
    else:
        new_points = points_to_add
        ref.set({'username': username, 'points': new_points})
    return new_points

def check_rewards(points):
    rewards = []
    for threshold, reward in REWARD_THRESHOLDS.items():
        if points == threshold:
            rewards.append(reward)
    return rewards

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Вітаю! Напиши 'Привіт' і отримуй бали. Перевір баланc командою /score.")

@bot.message_handler(commands=['score'])
def send_score(message):
    user_id = message.from_user.id
    ref = db.reference(f'users/{user_id}')
    user_data = ref.get()
    points = user_data.get('points', 0) if user_data else 0
    bot.reply_to(message, f"У вас {points} балів.")

@bot.message_handler(func=lambda message: True)
def count_hello(message):
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    count = text.lower().count("привіт")
    if count > 0:
        points = add_points(user_id, username, count)
        rewards = check_rewards(points)
        reply = f"Ви отримали {count} бал(ів)! Загалом у вас {points} балів."
        if rewards:
            reply += "\n" + "\n".join(rewards)
        bot.reply_to(message, reply)

# ======================
# Flask routes
# ======================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "!", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200


if __name__ == "__main__":
    # Для локального тесту
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
