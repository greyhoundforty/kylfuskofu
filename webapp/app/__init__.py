from flask import Flask
from .config import Config
import traceback
import sys


def create_app():
    try:
        app = Flask(__name__, template_folder="../templates", static_folder="../static")

        app.config.from_object(Config)

        # Import logger after Flask app is created
        from .logger import logger

        logger.debug("Initializing Flask application")

        from .database import init_app

        init_app(app)

        with app.app_context():
            from .routes import routes

            app.register_blueprint(routes)
            logger.debug("Registered routes blueprint")

        return app

    except Exception as e:
        print(f"Error during app initialization: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
