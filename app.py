from flask import Flask, jsonify, request, render_template_string
import random
import sqlite3

app = Flask(__name__)

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, balance REAL)''')
    # Таблица валют
    cursor.execute('''CREATE TABLE IF NOT EXISTS coins 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, trend REAL)''')
    conn.commit()
    
    # Добавим начальные монеты, если их нет
    cursor.execute("SELECT count(*) FROM coins")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO coins (name, price, trend) VALUES ('Bitcoin', 50000.0, 0.01)")
        cursor.execute("INSERT INTO coins (name, price, trend) VALUES ('Ethereum', 3000.0, 0.005)")
        cursor.execute("INSERT INTO coins (name, price, trend) VALUES ('SisterCoin', 10.0, 0.1)")
    conn.commit()
    conn.close()

init_db()

# --- УМНЫЙ АЛГОРИТМ КУРСА ---
def update_prices():
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, price, trend FROM coins")
    coins = cursor.fetchall()
    
    for coin_id, price, trend in coins:
        # Случайное колебание + влияние тренда
        noise = random.uniform(-0.03, 0.03) 
        new_price = price * (1 + trend + noise)
        
        # Чтобы цена не стала отрицательной
        if new_price < 0.01: new_price = 0.01
        
        # Шанс смены тренда (чтобы рынок разворачивался)
        new_trend = trend
        if random.random() < 0.1: # 10% шанс изменения направления
            new_trend = random.uniform(-0.02, 0.02)
            
        cursor.execute("UPDATE coins SET price = ?, trend = ? WHERE id = ?", (round(new_price, 2), new_trend, coin_id))
    
    conn.commit()
    conn.close()

# --- СТРАНИЦЫ (ИНТЕРФЕЙС) ---

# Главная админка
@app.route('/admin')
def admin_panel():
    update_prices() # Обновляем курсы при каждом просмотре
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coins")
    coins = cursor.fetchall()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    
    # Простой HTML для управления
    html = '''
    <h1>Управление Крипто-Игрой</h1>
    <h2>Валюты</h2>
    <table border="1">
        <tr><th>ID</th><th>Название</th><th>Цена</th><th>Тренд</th></tr>
        {% for coin in coins %}
        <tr>
            <td>{{ coin[0] }}</td>
            <td>{{ coin[1] }}</td>
            <td>${{ coin[2] }}</td>
            <td>{{ coin[3] }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Создать новую валюту</h2>
    <form action="/admin/add_coin" method="post">
        Имя: <input type="text" name="name"> Цена: <input type="number" name="price">
        <input type="submit" value="Создать">
    </form>

    <h2>Пользователи</h2>
    <ul>
        {% for user in users %}
        <li>ID: {{ user[0] }} | <b>{{ user[1] }}</b> | Баланс: ${{ user[2] }}</li>
        {% endfor %}
    </ul>
    
    <h2>Создать аккаунт</h2>
    <form action="/admin/add_user" method="post">
        Логин: <input type="text" name="user"> Баланс: <input type="number" name="balance">
        <input type="submit" value="Добавить">
    </form>
    '''
    return render_template_string(html, coins=coins, users=users)

# Добавление монеты
@app.route('/admin/add_coin', methods=['POST'])
def add_coin():
    name = request.form.get('name')
    price = request.form.get('price')
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO coins (name, price, trend) VALUES (?, ?, 0)", (name, price))
    conn.commit()
    conn.close()
    return "Монета добавлена! <a href='/admin'>Назад</a>"

# Добавление юзера
@app.route('/admin/add_user', methods=['POST'])
def add_user():
    name = request.form.get('user')
    balance = request.form.get('balance')
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, balance) VALUES (?, ?)", (name, balance))
    conn.commit()
    conn.close()
    return "Юзер добавлен! <a href='/admin'>Назад</a>"

# API для будущего приложения (выдает цены в формате JSON)
@app.route('/api/prices')
def api_prices():
    update_prices()
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM coins")
    data = dict(cursor.fetchall())
    conn.close()
    return jsonify(data)

@app.route('/')
def index():
    return "Сервер работает. Админка тут: <a href='/admin'>/admin</a>"

if __name__ == '__main__':
    app.run()
