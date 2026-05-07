from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)

# СЮДА ВСТАВЬ СВОЮ ССЫЛКУ ИЗ SUPABASE (замени password на свой пароль)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.postgresql://postgres:[1210892254225]@db.vpwxwkpwstnhyagmufsh.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ (ТАБЛИЦЫ) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    balance = db.Column(db.Float, default=1000.0)

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    trend = db.Column(db.Float, default=0.0)

# Создаем таблицы в облаке
with app.app_context():
    db.create_all()

# --- ЛОГИКА ---
def update_prices():
    coins = Coin.query.all()
    for coin in coins:
        noise = random.uniform(-0.03, 0.03)
        coin.price = round(coin.price * (1 + coin.trend + noise), 2)
        if coin.price < 0.01: coin.price = 0.01
        if random.random() < 0.1:
            coin.trend = random.uniform(-0.02, 0.02)
    db.session.commit()

# --- СТРАНИЦЫ ---
@app.route('/admin')
def admin_panel():
    update_prices()
    coins = Coin.query.all()
    users = User.query.all()
    
    html = '''
    <h1>Крипто-Админка (Cloud DB)</h1>
    <h3>Валюты</h3>
    <table border="1">
        <tr><th>Название</th><th>Цена</th></tr>
        {% for coin in coins %}
        <tr><td>{{ coin.name }}</td><td>${{ coin.price }}</td></tr>
        {% endfor %}
    </table>
    <form action="/admin/add_coin" method="post">
        Имя: <input name="name"> Цена: <input name="price" type="number" step="0.01"> <input type="submit" value="Создать монету">
    </form>
    <h3>Юзеры</h3>
    <ul>
        {% for user in users %}
        <li>{{ user.username }} - ${{ user.balance }}</li>
        {% endfor %}
    </ul>
    <form action="/admin/add_user" method="post">
        Имя: <input name="user"> <input type="submit" value="Создать юзера">
    </form>
    '''
    return render_template_string(html, coins=coins, users=users)

@app.route('/admin/add_coin', methods=['POST'])
def add_coin():
    name = request.form.get('name')
    price = float(request.form.get('price'))
    new_coin = Coin(name=name, price=price)
    db.session.add(new_coin)
    db.session.commit()
    return "Монета добавлена! <a href='/admin'>Назад</a>"

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    name = request.form.get('user')
    new_user = User(username=name)
    db.session.add(new_user)
    db.session.commit()
    return "Юзер добавлен! <a href='/admin'>Назад</a>"

@app.route('/')
def index():
    return "Сервер с облачной базой готов. <a href='/admin'>Перейти в админку</a>"

if __name__ == '__main__':
    app.run()
