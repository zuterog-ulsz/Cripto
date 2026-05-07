from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)

# Исправленная ссылка (проверь свой пароль внутри скобок, скобки [] убери)
# Пример: 'postgresql://postgres:пароль@db.vpwxwkpwstnhyagmufsh.supabase.co:5432/postgres'
# Обрати внимание на порт 6543 и добавление ?sslmode=require в конце
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1210892254225@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    balance = db.Column(db.Float, default=1000.0)

class Coin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    trend = db.Column(db.Float, default=0.0)
    last_change = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()

# --- ЛОГИКА ОБНОВЛЕНИЯ КУРСОВ ---
def update_prices():
    coins = Coin.query.all()
    for coin in coins:
        old_price = coin.price
        # Рыночный шум + тренд
        volatility = random.uniform(-0.04, 0.04) 
        coin.price = round(coin.price * (1 + coin.trend + volatility), 2)
        
        if coin.price < 0.01: coin.price = 0.01
        
        coin.last_change = round(coin.price - old_price, 2)
        
        # Шанс смены тренда
        if random.random() < 0.15:
            coin.trend = random.uniform(-0.03, 0.03)
    db.session.commit()

# --- СТИЛЬНЫЙ ИНТЕРФЕЙС (HTML/CSS) ---
ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        body { 
            background: radial-gradient(circle at top, #1a1f3c, #0d0f1a); 
            color: white; font-family: 'Inter', sans-serif; margin: 0; padding: 40px;
        }
        .container { max-width: 1000px; margin: auto; }
        h1 { color: #4facfe; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; }
        
        .card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }
        .card { 
            background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 25px; border-radius: 15px; backdrop-filter: blur(10px);
        }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { text-align: left; color: #888; font-size: 12px; text-transform: uppercase; padding: 10px; }
        td { padding: 12px 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
        
        .price-up { color: #00ff88; }
        .price-down { color: #ff4b5c; }
        
        input { 
            background: #161b33; border: 1px solid #30363d; color: white; 
            padding: 10px; border-radius: 8px; margin-right: 10px; outline: none;
        }
        input:focus { border-color: #4facfe; }
        
        .btn { 
            background: linear-gradient(45deg, #00f2fe 0%, #4facfe 100%);
            border: none; color: white; padding: 10px 20px; border-radius: 8px;
            cursor: pointer; font-weight: 600; transition: 0.3s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4); }
        
        .badge { background: #4facfe; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Dashboard <span style="color:white; opacity:0.3; font-weight:200;">| Crypto Server</span></h1>
        
        <div class="card-grid">
            <!-- КРИПТОВАЛЮТЫ -->
            <div class="card">
                <h3>Активные коины <span class="badge">{{ coins|length }}</span></h3>
                <table>
                    <tr><th>Название</th><th>Цена</th><th>Изм.</th></tr>
                    {% for coin in coins %}
                    <tr>
                        <td><b>{{ coin.name }}</b></td>
                        <td>${{ "{:,.2f}".format(coin.price) }}</td>
                        <td class="{{ 'price-up' if coin.last_change >= 0 else 'price-down' }}">
                            {{ "+" if coin.last_change > 0 }}{{ coin.last_change }}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                <br>
                <form action="/admin/add_coin" method="post">
                    <input name="name" placeholder="Имя (напр. TON)" required>
                    <input name="price" type="number" step="0.01" placeholder="Цена" required>
                    <button class="btn" type="submit">Создать</button>
                </form>
            </div>

            <!-- ПОЛЬЗОВАТЕЛИ -->
            <div class="card">
                <h3>Трейдеры <span class="badge">{{ users|length }}</span></h3>
                <table>
                    <tr><th>Логин</th><th>Баланс</th></tr>
                    {% for user in users %}
                    <tr>
                        <td>{{ user.username }}</td>
                        <td><span class="price-up">$ {{ "{:,.2f}".format(user.balance) }}</span></td>
                    </tr>
                    {% endfor %}
                </table>
                <br>
                <form action="/admin/add_user" method="post">
                    <input name="user" placeholder="Имя игрока" required>
                    <button class="btn" type="submit">Добавить</button>
                </form>
            </div>
        </div>
        
        <p style="text-align:center; opacity:0.5;">Данные сохраняются в Supabase Cloud 24/7</p>
    </div>
</body>
</html>
'''

# --- МАРШРУТЫ ---
@app.route('/admin')
def admin_panel():
    update_prices()
    coins = Coin.query.all()
    users = User.query.all()
    return render_template_string(ADMIN_HTML, coins=coins, users=users)

@app.route('/admin/add_coin', methods=['POST'])
def add_coin():
    try:
        name = request.form.get('name').upper()
        price = float(request.form.get('price'))
        new_coin = Coin(name=name, price=price)
        db.session.add(new_coin)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    try:
        name = request.form.get('user')
        new_user = User(username=name)
        db.session.add(new_user)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('admin_panel'))

@app.route('/')
def index():
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run()
