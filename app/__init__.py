from flask import Flask
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__, template_folder='templates')
    CORS(app)
    app.config.from_object(Config)

    from app import routes
    app.register_blueprint(routes.bp)

    return app

