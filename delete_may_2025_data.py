from app import create_app, db
from app.models import Transaction # Zaimportuj model Transaction
from sqlalchemy import extract, and_
from datetime import datetime

# Utwórz kontekst aplikacji, aby móc korzystać z SQLAlchemy
app = create_app()

def delete_transactions_for_month_year(year, month):
    """
    Usuwa wszystkie transakcje (przychody i wydatki) dla podanego roku i miesiąca.
    """
    with app.app_context():
        try:
            # Znajdź transakcje do usunięcia
            transactions_to_delete = Transaction.query.filter(
                and_(
                    extract('year', Transaction.date) == year,
                    extract('month', Transaction.date) == month
                )
            ).all()

            if not transactions_to_delete:
                print(f"Nie znaleziono żadnych transakcji dla {month:02d}-{year}.")
                return

            num_transactions = len(transactions_to_delete)
            print(f"Znaleziono {num_transactions} transakcji dla {month:02d}-{year}, które zostaną usunięte.")

            # Potwierdzenie od użytkownika
            confirm = input(f"Czy na pewno chcesz usunąć {num_transactions} transakcji z {month:02d}-{year}? (tak/nie): ")
            if confirm.lower() != 'tak':
                print("Anulowano usuwanie danych.")
                return

            # Usuń znalezione transakcje
            for transaction in transactions_to_delete:
                db.session.delete(transaction)
            
            db.session.commit()
            print(f"Pomyślnie usunięto {num_transactions} transakcji z {month:02d}-{year}.")

        except Exception as e:
            db.session.rollback()
            print(f"Wystąpił błąd podczas usuwania danych: {e}")

if __name__ == '__main__':
    target_year = 2025
    target_month = 3 # Maj

    print(f"--- Skrypt usuwania danych transakcji dla {target_month:02d}-{target_year} ---")
    delete_transactions_for_month_year(target_year, target_month)
    print("--- Zakończono działanie skryptu ---")