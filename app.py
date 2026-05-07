import os
import random
from flask import Flask, request, render_template_string, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- ТВОЯ БАЗА SUPABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.vpwxwkpwstnhyagmufsh:1210892254225@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False, default="1234")
    balance = db.Column(db.Float, default=1000.0)

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    change = db.Column(db.Float, default=0.0)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    coin_name = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()

# --- АДМИНКА (ДЛЯ ТЕБЯ) ---
@app.route('/')
@app.route('/admin')
def admin():
    users = User.query.all()
    coins = Coin.query.all()
    return render_template_string('''
        <body style="background:#121212; color:white; font-family:sans-serif; padding:20px;">
            <h1>Управление Биржей</h1>
            <div style="display:flex; gap:20px;">
                <div style="background:#1e1e1e; padding:20px; border-radius:10px;">
                    <h2>Добавить монету</h2>
                    <form action="/add_coin" method="post">
                        <input name="name" placeholder="Название (BTC)" required><br><br>
                        <input name="price" type="number" step="0.01" placeholder="Цена" required><br><br>
                        <button type="submit">Добавить</button>
                    </form>
                </div>
                <div style="background:#1e1e1e; padding:20px; border-radius:10px;">
                    <h2>Пользователи</h2>
                    {% for u in users %}
                        <p>{{ u.username }} | Пароль: {{ u.password }} | Баланс: ${{ u.balance }}</p>
                    {% endfor %}
                </div>
            </div>
        </body>
    ''', users=users, coins=coins)

@app.route('/add_coin', methods=['POST'])
def add_coin():
    name = request.form.get('name').upper()
    price = float(request.form.get('price'))
    db.session.add(Coin(name=name, price=price))
    db.session.commit()
    return redirect('/')

# --- API ДЛЯ МОБИЛЬНОГО ПРИЛОЖЕНИЯ ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(username=data.get('login'), password=data.get('pass')).first()
    if user:
        return jsonify({"status": "ok", "id": user.id, "balance": user.balance})
    return jsonify({"status": "error"}), 401

@app.route('/api/get_market', methods=['GET'])
def get_market():
    # Имитация живого рынка: меняем цены при каждом запросе
    for c in Coin.query.all():
        old = c.price
        c.price = round(c.price * (1 + random.uniform(-0.03, 0.03)), 2)
        c.change = round(c.price - old, 2)
    db.session.commit()
    coins = [{"id": c.id, "name": c.name, "price": c.price, "change": c.change} for c in Coin.query.all()]
    return jsonify(coins)

@app.route('/api/trade', methods=['POST'])
def trade():
    data = request.json
    user = User.query.get(data.get('user_id'))
    coin = Coin.query.get(data.get('coin_id'))
    action = data.get('action')
    
    port = Portfolio.query.filter_by(user_id=user.id, coin_name=coin.name).first()
    if not port:
        port = Portfolio(user_id=user.id, coin_name=coin.name, amount=0)
        db.session.add(port)

    if action == 'buy' and user.balance >= coin.price:
        user.balance -= coin.price
        port.amount += 1
    elif action == 'sell' and port.amount >= 1:
        user.balance += coin.price
        port.amount -= 1
    else:
        return jsonify({"status": "fail", "msg": "Ошибка баланса или активов"})
    
    db.session.commit()
    return jsonify({"status": "ok", "new_balance": user.balance})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
