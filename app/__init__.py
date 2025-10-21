from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
from datetime import datetime
from flask_login import LoginManager, UserMixin

db = SQLAlchemy()
login_manager = LoginManager()

# NOWA "FAŁSZYWA" KLASA UŻYTKOWNIKA (nie jest modelem SQLAlchemy)
class User(UserMixin):
    def __init__(self, id):
        self.id = id

    @staticmethod
    def get(user_id):
        # W naszym przypadku mamy tylko jednego użytkownika z ID 'admin'
        if user_id == os.environ.get('APP_USER'):
            return User(user_id)
        return None

# Funkcja ładowania użytkownika wymagana przez Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    login_manager.init_app(app) # Inicjalizacja Flask-Login
    login_manager.login_view = 'main.login' # Przekieruj niezalogowanych na stronę logowania
    login_manager.login_message = "zaloguj się, aby uzyskać dostęp."
    login_manager.login_message_category = "info"

    from app.routes import main_bp # Upewnij się, że import jest tutaj
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.utcnow().year}

    with app.app_context():
        from app import models # Importuj modele w kontekście aplikacji
        db.create_all()

        account_names = {
            "Tomek Prywatne": "Tomek Prywatne",
            "Toćka Prywatne": "Toćka Prywatne",
            "Wspólne Revolut": "Wspólne Revolut"
        }
        if models.Account.query.count() < len(account_names):
            for key, name in account_names.items():
                if not models.Account.query.filter_by(name=name).first():
                    db.session.add(models.Account(name=name))
            db.session.commit()
            print("Domyślne konta dodane/zaktualizowane.")

        shared_categories_data = {
            "Living (Wspólne)": True,
            "Rachunki (Wspólne)": True,
        }
        for cat_name, is_shared in shared_categories_data.items():
            category = models.Category.query.filter_by(name=cat_name).first()
            if not category:
                category = models.Category(name=cat_name, is_shared_expense=is_shared)
                db.session.add(category)
            elif category.is_shared_expense != is_shared:
                category.is_shared_expense = is_shared
        db.session.commit()
        print("Domyślne kategorie wspólne dodane/zaktualizowane.")
        
        default_categories_data = {
            "Jedzenie": False, "Transport": False, "Rozrywka": False, 
            "Zdrowie": False, "Ubrania": False, "Przychód Ogólny": False,
            "Inne": False
        }
        for cat_name, is_shared in default_categories_data.items():
            if not models.Category.query.filter_by(name=cat_name).first():
                db.session.add(models.Category(name=cat_name, is_shared_expense=is_shared))
        db.session.commit()
        print("Domyślne kategorie osobiste dodane (jeśli brakowało).")

    return app