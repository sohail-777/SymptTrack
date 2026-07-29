# app.py — SymptTrack application entry point
from flask import Flask
from flask_cors import CORS

from config import Config
from db import init_pool
from ml.diagnosis_model import start_background_load
from utils.json_provider import SymptTrackJSONProvider

from routes.pages import pages_bp
from routes.auth import auth_bp
from routes.patient import patient_bp
from routes.admin import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.json_provider_class = SymptTrackJSONProvider
    app.json = SymptTrackJSONProvider(app)

    CORS(app, supports_credentials=True)

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Something went wrong on our end. Please try again."}, 500

    return app


app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  🏥  SymptTrack — Health Journal & ML Diagnosis Assistant")
    print("=" * 60)
    init_pool()
    start_background_load()  # loads the CORe ML model in the background
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
