import os

from flask import Flask, app, render_template
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from app.conversores.full_convert import full_convert_bp


load_dotenv()

def create_app():
    app = Flask(__name__,static_folder="static", template_folder="templates")

    app.secret_key = os.getenv('SECRET_KEY', '')

    registry_routes(app)

    return app

def registry_routes(app):
    app.register_blueprint(full_convert_bp)
