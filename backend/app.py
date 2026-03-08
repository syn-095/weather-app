from flask import Flask
from flask_cors import CORS
from routes.weather import weather_bp
from routes.health import health_bp
from routes.feedback import feedback_bp
from routes.admin import admin_bp
from routes.analytics import analytics_bp
from routes.ground_truth import gt_bp
from routes.elevation import elevation_bp

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.register_blueprint(weather_bp,    url_prefix="/api/weather")
    app.register_blueprint(health_bp,     url_prefix="/api")
    app.register_blueprint(feedback_bp,   url_prefix="/api")
    app.register_blueprint(admin_bp,      url_prefix="/api")
    app.register_blueprint(analytics_bp,  url_prefix="/api")
    app.register_blueprint(gt_bp,         url_prefix="/api")
    app.register_blueprint(elevation_bp,  url_prefix="/api")
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)