import os
from pathlib import Path
from flask import Flask

if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('TECOS_DB_PATH', '/tmp/tecos.db')
else:
    os.environ.setdefault('TECOS_DB_PATH', str(Path(__file__).resolve().parent / 'tecos.db'))

from database import init_db
from rotas import register_routes

app = Flask(__name__, static_folder='static')
app.secret_key = 'tecoss-secret-key'

init_db()
register_routes(app)


if __name__ == '__main__':
    app.run(debug=True)
