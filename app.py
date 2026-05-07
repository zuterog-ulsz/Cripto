import telebot
from telebot import types
from flask import Flask, request, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import random
import threading
import io
import matplotlib
matplotlib.use('Agg') # Режим без графического окна (для сервера)
import matplotlib.pyplot as plt

app = Flask(__name__)

# --- НАСТРОЙКИ БАЗЫ И БОТА ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.vpwxwkpwstnhyagmufsh:1210892254225@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

TOKEN = '8761993990:AAG60aP6hT7U_FrcDBrv6KqiYvMckGgqO0s'

db = SQLAlchemy(app)
bot = telebot.TeleBot(TOKEN)

active_sessions = {}
login_process = {}

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False, default="1234")
    balance = db.Column(db.Float, default=1000.0)

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    trend = db.Column(db.Float, default=0.0)
    last_change = db.Column(db.Float, default=0.0)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    coin_name = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN password VARCHAR(80) DEFAULT \'1234\';'))
        db.session.commit()
    except:
        db.session.rollback()

# --- ЛОГИКА ИЗМЕНЕНИЯ КУРСОВ ---
def update_prices():
    coins = Coin.query.all()
    for coin in coins:
        old_price = coin.price
        volatility = random.uniform(-0.05, 0.05) 
        coin.price = round(coin.price * (1 + coin.trend + volatility), 2)
        if coin.price < 0.01: coin.price = 0.01
        coin.last_change = round(coin.price - old_price, 2)
        if random.random() < 0.15:
            coin.trend = random.uniform(-0.03, 0.03)
    db.session.commit()

# --- ФУНКЦИЯ РИСОВАНИЯ ГРАФИКА ---
def generate_chart(coin_name, current_price):
    # Генерируем 30 случайных точек истории для красоты (заканчиваются текущей ценой)
    prices = [current_price]
    for _ in range(30):
        prices.insert(0, prices[0] * (1 + random.uniform(-0.04, 0.04)))
    
    plt.figure(figsize=(8, 4))
    plt.plot(prices, marker='', color='#00f2fe', linewidth=2.5)
    plt.title(f"График {coin_name} (Текущая цена: ${current_price:,.2f})", color='white', fontsize=14)
    plt.gca().set_facecolor('#1e293b')
    plt.gcf().patch.set_facecolor('#0f172a')
    plt.tick_params(colors='white')
    plt.grid(color='#334155', linestyle='--', linewidth=0.5)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

# --- СУПЕР ИНТЕРФЕЙС АДМИНА ---
ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Admin Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #e2e8f0; font-family: 'Montserrat', sans-serif; padding: 30px; margin: 0; }
        .header { text-align: center; margin-bottom: 40px; }
        h1 { color: #38bdf8; font-weight: 900; font-size: 2.5em; text-shadow: 0 0 20px rgba(56, 189, 248, 0.3); margin:0;}
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { color: #f8fafc; border-bottom: 2px solid #334155; padding-bottom: 10px; margin-top:0; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th { text-align: left; color: #94a3b8; padding: 10px; border-bottom: 1px solid #334155; }
        td { padding: 12px 10px; border-bottom: 1px solid #334155; font-weight: bold; }
        .up { color: #4ade80; } .down { color: #f87171; }
        input { background: #0f172a; border: 1px solid #38bdf8; color: white; padding: 10px; border-radius: 8px; margin-bottom: 10px; width: calc(100% - 24px); outline: none;}
        button { background: #38bdf8; color: #0f172a; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.2s;}
        button:hover { background: #7dd3fc; transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="header"><h1>CRIPTO ADMIN DASHBOARD</h1><p>Управление биржей и пользователями</p></div>
    <div class="grid">
        <div class="card">
            <h2>💰 Валюты</h2>
            <table>
                <tr><th>Название</th><th>Цена</th><th>Изменение</th></tr>
                {% for coin in coins %}
                <tr><td>{{ coin.name }}</td><td>${{ "{:,.2f}".format(coin.price) }}</td>
                <td class="{{ 'up' if coin.last_change >= 0 else 'down' }}">{{ "+" if coin.last_change > 0 }}{{ coin.last_change }}</td></tr>
                {% endfor %}
            </table>
            <form action="/admin/add_coin" method="post">
                <input name="name" placeholder="Символ монеты (напр. BTC)" required>
                <input name="price" type="number" step="0.01" placeholder="Начальная цена" required>
                <button type="submit">+ Добавить монету</button>
            </form>
        </div>
        <div class="card">
            <h2>👥 Пользователи</h2>
            <table>
                <tr><th>Логин</th><th>Пароль</th><th>Баланс</th></tr>
                {% for user in users %}
                <tr><td>{{ user.username }}</td><td style="color:#94a3b8; font-size: 0.8em;">{{ user.password }}</td><td class="up">${{ "{:,.2f}".format(user.balance) }}</td></tr>
                {% endfor %}
            </table>
            <form action="/admin/add_user" method="post">
                <input name="user" placeholder="Логин (без пробелов)" required>
                <input name="password" placeholder="Пароль" required>
                <button type="submit">+ Создать аккаунт</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

@app.route('/admin')
def admin_panel():
    update_prices()
    return render_template_string(ADMIN_HTML, coins=Coin.query.all(), users=User.query.all())

@app.route('/admin/add_coin', methods=['POST'])
def add_coin():
    db.session.add(Coin(name=request.form.get('name').upper(), price=float(request.form.get('price'))))
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    db.session.add(User(username=request.form.get('user'), password=request.form.get('password')))
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/')
def index():
    return redirect(url_for('admin_panel'))

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💰 Баланс", "💼 Портфель", "📈 Курсы", "📊 Графики", "🛒 Купить", "📉 Продать", "⚙️ Настройки", "🚪 Выйти")
    return markup

@bot.message_handler(commands=['start'])
def bot_start(message):
    msg = bot.send_message(message.chat.id, "Привет! Добро пожаловать на биржу 🚀\n\nВведите ваш **Логин**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_username)

def process_username(message):
    login_process[message.chat.id] = {'username': message.text}
    msg = bot.send_message(message.chat.id, "Отлично! Теперь введите **Пароль**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_password)

def process_password(message):
    username = login_process[message.chat.id].get('username')
    password = message.text
    
    with app.app_context():
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            active_sessions[message.chat.id] = user.id
            bot.send_message(message.chat.id, f"✅ Вход выполнен!\nДобро пожаловать, {username}!", reply_markup=get_main_menu())
        else:
            bot.send_message(message.chat.id, "❌ Неверный логин или пароль.\nНажмите /start чтобы попробовать снова.")

@bot.message_handler(func=lambda message: True)
def main_logic(message):
    if message.chat.id not in active_sessions:
        bot.send_message(message.chat.id, "Сначала войдите в аккаунт! Нажмите /start")
        return

    with app.app_context():
        user = User.query.get(active_sessions[message.chat.id])
        
        if message.text == "🚪 Выйти":
            del active_sessions[message.chat.id]
            bot.send_message(message.chat.id, "Вы вышли из аккаунта. /start", reply_markup=types.ReplyKeyboardRemove())
            
        elif message.text == "💰 Баланс":
            bot.send_message(message.chat.id, f"💵 Твой баланс: **${user.balance:,.2f}**", parse_mode="Markdown")
            
        elif message.text == "📈 Курсы":
            update_prices()
            coins = Coin.query.all()
            text_prices = "📊 **Текущие курсы на бирже:**\n\n"
            for c in coins:
                icon = "🟢" if c.last_change >= 0 else "🔴"
                text_prices += f"{icon} {c.name}: `${c.price:,.2f}`\n"
            bot.send_message(message.chat.id, text_prices, parse_mode="Markdown")
            
        elif message.text == "💼 Портфель":
            portfolio = Portfolio.query.filter_by(user_id=user.id).all()
            if not portfolio:
                bot.send_message(message.chat.id, "Твой портфель пока пуст.")
                return
            text_port = "💼 **Твои активы:**\n\n"
            for p in portfolio:
                if p.amount > 0:
                    text_port += f"▫️ {p.coin_name}: {p.amount} шт.\n"
            bot.send_message(message.chat.id, text_port, parse_mode="Markdown")

        elif message.text == "🛒 Купить":
            coins = Coin.query.all()
            markup = types.InlineKeyboardMarkup()
            for c in coins:
                markup.add(types.InlineKeyboardButton(text=f"Купить {c.name} (${c.price:,.2f})", callback_data=f"buy_{c.id}"))
            bot.send_message(message.chat.id, "Выберите валюту для покупки (1 шт):", reply_markup=markup)

        elif message.text == "📉 Продать":
            portfolio = Portfolio.query.filter_by(user_id=user.id).all()
            markup = types.InlineKeyboardMarkup()
            has_coins = False
            for p in portfolio:
                if p.amount > 0:
                    has_coins = True
                    current_coin = Coin.query.filter_by(name=p.coin_name).first()
                    markup.add(types.InlineKeyboardButton(text=f"Продать {p.coin_name} (${current_coin.price:,.2f})", callback_data=f"sell_{current_coin.id}"))
            
            if has_coins:
                bot.send_message(message.chat.id, "Что продаем? (1 шт):", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, "У вас нет валюты для продажи!")

        # --- НОВЫЕ КНОПКИ ---
        elif message.text == "📊 Графики":
            coins = Coin.query.all()
            markup = types.InlineKeyboardMarkup()
            for c in coins:
                markup.add(types.InlineKeyboardButton(text=f"График {c.name}", callback_data=f"graph_{c.id}"))
            bot.send_message(message.chat.id, "Выберите монету, чтобы посмотреть график:", reply_markup=markup)
            
        elif message.text == "⚙️ Настройки":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="Изменить Логин", callback_data="settings_login"))
            markup.add(types.InlineKeyboardButton(text="Изменить Пароль", callback_data="settings_password"))
            bot.send_message(message.chat.id, "⚙️ **Настройки аккаунта**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def process_callback(call):
    with app.app_context():
        user_id = active_sessions.get(call.message.chat.id)
        if not user_id:
            return bot.answer_callback_query(call.id, "Сначала войдите в аккаунт!")
        user = User.query.get(user_id)

        # ТОРГОВЛЯ
        if call.data.startswith('buy_') or call.data.startswith('sell_'):
            action, coin_id = call.data.split('_')
            coin = Coin.query.get(int(coin_id))

            if action == "buy":
                if user.balance >= coin.price:
                    user.balance -= coin.price
                    port = Portfolio.query.filter_by(user_id=user.id, coin_name=coin.name).first()
                    if port:
                        port.amount += 1
                    else:
                        db.session.add(Portfolio(user_id=user.id, coin_name=coin.name, amount=1))
                    db.session.commit()
                    bot.answer_callback_query(call.id, f"✅ Куплено 1 {coin.name}!")
                    bot.edit_message_text(f"✅ Успешно куплен {coin.name}.\nВаш баланс: ${user.balance:,.2f}", call.message.chat.id, call.message.message_id)
                else:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")

            elif action == "sell":
                port = Portfolio.query.filter_by(user_id=user.id, coin_name=coin.name).first()
                if port and port.amount > 0:
                    port.amount -= 1
                    user.balance += coin.price
                    db.session.commit()
                    bot.answer_callback_query(call.id, f"✅ Продано 1 {coin.name}!")
                    bot.edit_message_text(f"✅ Успешно продан {coin.name}.\nВаш баланс: ${user.balance:,.2f}", call.message.chat.id, call.message.message_id)
                else:
                    bot.answer_callback_query(call.id, "❌ У вас нет этой валюты!")

        # ГРАФИКИ
        elif call.data.startswith('graph_'):
            bot.answer_callback_query(call.id, "Генерирую график...")
            coin_id = int(call.data.split('_')[1])
            coin = Coin.query.get(coin_id)
            img = generate_chart(coin.name, coin.price)
            bot.send_photo(call.message.chat.id, img)

        # НАСТРОЙКИ
        elif call.data == "settings_login":
            msg = bot.send_message(call.message.chat.id, "Введите новый логин:")
            bot.register_next_step_handler(msg, update_login, user.id)
        elif call.data == "settings_password":
            msg = bot.send_message(call.message.chat.id, "Введите новый пароль:")
            bot.register_next_step_handler(msg, update_password, user.id)

def update_login(message, user_id):
    with app.app_context():
        new_username = message.text
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            bot.send_message(message.chat.id, "❌ Этот логин уже занят!")
        else:
            user = User.query.get(user_id)
            user.username = new_username
            db.session.commit()
            bot.send_message(message.chat.id, f"✅ Логин успешно изменен на: {new_username}")

def update_password(message, user_id):
    with app.app_context():
        user = User.query.get(user_id)
        user.password = message.text
        db.session.commit()
        bot.send_message(message.chat.id, "✅ Пароль успешно изменен!")

def run_bot():
    print("--- БОТ ЗАПУСКАЕТСЯ ЧЕРЕЗ ПЛАНЕР ---")
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"--- КРИТИЧЕСКАЯ ОШИБКА БОТА: {e} ---")

# --- ИСПРАВЛЕННЫЙ ЗАПУСК БОТА ДЛЯ FLASK 3.x ---
bot_started = False

@app.before_request
def activate_job():
    global bot_started
    if not bot_started:
        thread = threading.Thread(target=run_bot, daemon=True)
        thread.start()
        bot_started = True

# Тестовая страница, чтобы "разбудить" бота
@app.route('/init')
def init_bot():
    return "Бот просыпается... Проверь логи через 10 секунд."

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
