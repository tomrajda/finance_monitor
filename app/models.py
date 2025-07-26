from datetime import datetime, date
from app import db
from sqlalchemy.orm import validates

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_shared_expense = db.Column(db.Boolean, default=False) 
    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    transactions = db.relationship('Transaction', backref='account', lazy=True)

    def __repr__(self):
        return f'<Account {self.name}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    is_income = db.Column(db.Boolean, default=False)
    
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    person = db.Column(db.String(50), nullable=False) 

    def __repr__(self):
        type_ = "Przychód" if self.is_income else "Wydatek"
        return f'<{type_} {self.amount} - {self.description or "Brak opisu"}>'

# --- NOWE MODELE DLA PORTFELA INWESTYCYJNEGO ---

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # Np. "Portfel Długoterminowy", "Portfel Ryzykowny T&M"
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship('Asset', backref='portfolio', lazy='dynamic', cascade="all, delete-orphan")

    # Modelowe alokacje (przechowywane jako JSON string lub osobna tabela)
    # Dla uproszczenia na razie jako JSON string
    # np. {"Akcje PL": 0.4, "Obligacje USA": 0.3, "Gotówka": 0.3}
    # Gdzie kluczem jest nazwa AssetCategory.name
    target_allocation = db.Column(db.Text, nullable=True) # Przechowuje JSON string

    def __repr__(self):
        return f'<Portfolio {self.name}>'

class AssetCategory(db.Model):
    __tablename__ = 'asset_category' # Jawna nazwa tabeli, aby uniknąć konfliktu z 'Category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # Np. Akcje PL, Obligacje Skarbowe, ETF Świat, Gotówka, PPK, Nieruchomości
    assets = db.relationship('Asset', backref='asset_category_ref', lazy=True) # Zmieniona nazwa backref

    def __repr__(self):
        return f'<AssetCategory {self.name}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) # Np. "Akcje KGHM", "Obligacje Skarbowe EDO0332", "Fundusz PKO Akcji Plus"
    ticker = db.Column(db.String(20), nullable=True, index=True) # Opcjonalny ticker giełdowy
    current_value = db.Column(db.Float, nullable=False, default=0.0) # Aktualna wartość całego aktywa
    quantity = db.Column(db.Float, nullable=True) # Ilość jednostek/akcji (jeśli dotyczy)
    purchase_price_per_unit = db.Column(db.Float, nullable=True) # Cena zakupu za jednostkę (jeśli dotyczy)
    currency = db.Column(db.String(10), nullable=False, default="PLN") # Waluta aktywa
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    asset_category_id = db.Column(db.Integer, db.ForeignKey('asset_category.id'), nullable=False)
    
    # Relacja do historii wartości (opcjonalne na tym etapie, ale dobre na przyszłość)
    value_history = db.relationship('AssetValueHistory', backref='asset', lazy='dynamic', cascade="all, delete-orphan")

    @validates('current_value')
    def validate_current_value(self, key, value):
        if value < 0:
            raise ValueError("Wartość aktywa nie może być ujemna.")
        return value

    def __repr__(self):
        return f'<Asset {self.name} - Value: {self.current_value} {self.currency}>'

class AssetValueHistory(db.Model): # Do śledzenia zmian wartości aktywów w czasie
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    value = db.Column(db.Float, nullable=False) # Wartość aktywa w danym dniu

    def __repr__(self):
        return f'<AssetValueHistory AssetID: {self.asset_id} - Date: {self.date} - Value: {self.value}>'

class PortfolioSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True) # Data i czas snapshotu
    total_value = db.Column(db.Float, nullable=False) # Całkowita wartość portfela w momencie snapshotu
    currency = db.Column(db.String(10), nullable=False, default="PLN") # Waluta portfela

    # Relacja zwrotna, jeśli potrzebna
    portfolio_ref = db.relationship('Portfolio', backref=db.backref('snapshots', lazy='dynamic', cascade="all, delete-orphan"))


    def __repr__(self):
        return f'<PortfolioSnapshot PortfolioID: {self.portfolio_id} - Time: {self.timestamp} - Value: {self.total_value} {self.currency}>'

class SavingsGoal(db.Model):
    year = db.Column(db.Integer, primary_key=True) # Jeden cel na rok
    goal_total = db.Column(db.Float, nullable=True)
    goal_tomek = db.Column(db.Float, nullable=True)
    goal_tocka = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<SavingsGoal {self.year}: Total={self.goal_total}>'