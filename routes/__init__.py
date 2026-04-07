from routes.books import books_bp
from routes.lists import lists_bp
from routes.pages import pages_bp
from routes.stats import stats_bp
from routes.users import users_bp

def register_blueprints(app):
    app.register_blueprint(pages_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(lists_bp)
    app.register_blueprint(stats_bp)
