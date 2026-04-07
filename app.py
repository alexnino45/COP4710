from flask import Flask

from config import DEBUG, SECRET_KEY
from routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    register_blueprints(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=DEBUG)
