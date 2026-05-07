import os
import random
from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# --- НАСТРОЙКИ ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.vpwxwkpwstnhyagmufsh:1210892254225@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False, default="1234")
    balance = db.Column(db.Float, default=1000.0)

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    last_change = db.Column(db.Float, default=0.0)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    coin_name = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()

# --- ЛОГИКА ---
def update_prices():
    coins = Coin.query.all()
    for coin in coins:
        old_price = coin.price
        change = random.uniform(-0.05, 0.05)
        coin.price = round(coin.price * (1 + change), 2)
        if coin.price < 0.01: coin.price = 0.01
        coin.last_change = round(coin.price - old_price, 2)
    db.session.commit()

# --- ADMIN PANEL ---
ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Crypto Admin</title><style>
    body { background: #0f172a; color: white; font-family: sans-serif; padding: 20px; }
    .card { background: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; border-bottom: 1px solid #334155; text-align: left; }
    input { background: #0f172a; color: white; border: 1px solid #38bdf8; padding: 5px; margin: 5px 0; }
    button { background: #38bdf8; border: none; padding: 10px; border-radius: 5px; cursor: pointer; }
</style></head>
<body>
    <h1>Crypto Dashboard</h1>
    <div class="card">
        <h2>Монеты</h2>
        <table>
            <tr><th>Название</th><th>Цена</th><th>Изменение</th></tr>
            {% for coin in coins %}
            <tr><td>{{ coin.name }}</td><td>${{ coin.price }}</td><td>{{ coin.last_change }}</td></tr>
            {% endfor %}
        </table>
        <form action="/admin/add_coin" method="post">
            <input name="name" placeholder="BTC" required>
            <input name="price" type="number" step="0.01" placeholder="50000" required>
            <button type="submit">Добавить монету</button>
        </form>
    </div>
    <div class="card">
        <h2>Пользователи</h2>
        <table>
            <tr><th>Логин</th><th>Баланс</th></tr>
            {% for user in users %}
            <tr><td>{{ user.username }}</td><td>${{ user.balance }}</td></tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
@app.route('/admin')
def admin():
    update_prices()
    return render_template_string(ADMIN_HTML, coins=Coin.query.all(), users=User.query.all())

@app.route('/admin/add_coin', methods=['POST'])
def add_coin():
    db.session.add(Coin(name=request.form.get('name').upper(), price=float(request.form.get('price'))))
    db.session.commit()
    return redirect('/admin')

# --- API ДЛЯ ПРИЛОЖЕНИЯ ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(username=data.get('username'), password=data.get('password')).first()
    if user:
        return jsonify({"status": "ok", "user_id": user.id, "username": user.username, "balance": user.balance})
    return jsonify({"status": "error", "message": "Ошибка входа"}), 401

@app.route('/api/data', methods=['GET'])
def get_data():
    user_id = request.args.get('user_id')
    update_prices()
    user = User.query.get(user_id)
    coins = Coin.query.all()
    portfolio = Portfolio.query.filter_by(user_id=user_id).all()
    return jsonify({
        "balance": user.balance,
        "coins": [{"id": c.id, "name": c.name, "price": c.price, "change": c.last_change} for c in coins],
        "portfolio": [{"name": p.coin_name, "amount": p.amount} for p in portfolio]
    })

@app.route('/api/trade', methods=['POST'])
def trade():
    data = request.json
    user = User.query.get(data.get('user_id'))
    coin = Coin.query.get(data.get('coin_id'))
    action = data.get('action') # 'buy' или 'sell'
    
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
        return jsonify({"status": "error", "message": "Недостаточно средств/монет"})
    
    db.session.commit()
    return jsonify({"status": "ok", "balance": user.balance})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
