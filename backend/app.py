from flask import Flask
from flask_cors import CORS
from routes.weather import weather_bp
from routes.health import health_bp
from routes.feedback import feedback_bp

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.register_blueprint(weather_bp,  url_prefix="/api/weather")
    app.register_blueprint(health_bp,   url_prefix="/api")
    app.register_blueprint(feedback_bp, url_prefix="/api")
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

'''

Add to Render environment variables:
```
FEEDBACK_ADMIN_SECRET = choose_a_secret_password

'''