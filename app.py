import os
from flask import Flask
from database import init_db
from rotas import register_routes

app = Flask(__name__)
app.secret_key = 'tecoss-secret-key'

init_db()
register_routes(app)


if __name__ == '__main__':
    app.run(debug=True)
