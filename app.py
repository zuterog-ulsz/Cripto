from flask import Flask, jsonify
import random

app = Flask(__name__)

# Начальные цены валют
stocks = {
    "Bitcoin": 50000.0,
    "Ethereum": 3000.0,
}

@app.route('/')
def home():
    return "Сервер крипто-игры запущен!"

@app.route('/prices')
def get_prices():
    # Каждый раз, когда мы запрашиваем цены, они немного меняются
    for coin in stocks:
        change = random.uniform(-0.05, 0.05) # цена меняется на +/- 5%
        stocks[coin] = round(stocks[coin] * (1 + change), 2)
    return jsonify(stocks)

if __name__ == '__main__':
    app.run()
