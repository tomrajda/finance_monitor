from app import create_app, db
from app.models import Category, Account, Transaction
from datetime import date, timedelta, datetime
import random
from sqlalchemy import extract
import calendar # <<< DODAJ TEN IMPORT


app = create_app()

def seed_data():
    with app.app_context():
        # Jeśli już są transakcje, nie dodawaj ponownie (chyba że chcesz resetować za każdym razem)
        # Aby resetować, odkomentuj poniższe linie:
        # print("Czyszczenie istniejących transakcji...")
        # Transaction.query.delete()
        # db.session.commit()
        
        if Transaction.query.first():
            print("Dane transakcji już istnieją. Pomijam dodawanie przykładowych danych.")
            return

        # Pobierz lub utwórz konta
        accounts_map = {}
        account_names = ["Tomek Prywatne", "Toćka Prywatne", "Wspólne Revolut"]
        for name in account_names:
            acc = Account.query.filter_by(name=name).first()
            if not acc: # Na wszelki wypadek, gdyby __init__ nie utworzył
                acc = Account(name=name)
                db.session.add(acc)
            accounts_map[name] = acc
        db.session.commit() # Zapisz nowe konta, jeśli były dodane

        # Pobierz lub utwórz kategorie
        categories_map = {}
        # Nazwa kategorii : is_shared_expense
        category_data = {
            "Living (Wspólne)": True, "Rachunki (Wspólne)": True,
            "Jedzenie": False, "Transport": False, "Rozrywka": False,
            "Zdrowie": False, "Ubrania": False, "Inne": False,
            "Przychód Ogólny": False # Kategoria dla typu przychodu, nieużywana dla flagi is_shared_expense
        }
        for name, is_shared in category_data.items():
            cat = Category.query.filter_by(name=name).first()
            if not cat:
                cat = Category(name=name, is_shared_expense=is_shared)
                db.session.add(cat)
            categories_map[name] = cat
        db.session.commit() # Zapisz nowe kategorie

        # Upewnijmy się, że mamy wszystkie potrzebne obiekty
        required_accounts = ["Tomek Prywatne", "Toćka Prywatne", "Wspólne Revolut"]
        required_categories = ["Living (Wspólne)", "Rachunki (Wspólne)", "Jedzenie", "Transport", "Rozrywka"]
        
        for acc_name in required_accounts:
            if acc_name not in accounts_map or not accounts_map[acc_name].id: # Sprawdź też ID po commit
                accounts_map[acc_name] = Account.query.filter_by(name=acc_name).first() # Spróbuj pobrać ponownie
                if not accounts_map[acc_name]:
                    print(f"Krytyczny błąd: Nie udało się uzyskać konta {acc_name}")
                    return
        for cat_name in required_categories:
            if cat_name not in categories_map or not categories_map[cat_name].id:
                categories_map[cat_name] = Category.query.filter_by(name=cat_name).first()
                if not categories_map[cat_name]:
                    print(f"Krytyczny błąd: Nie udało się uzyskać kategorii {cat_name}")
                    return
        
        transactions_to_add = []
        today = date.today()
        PERSON_TOMEK = "Tomek"
        PERSON_TOCKA = "Toćka"
        PERSON_WSPOLNE = "Wspólne"

        # Generowanie danych dla ostatnich N miesięcy + bieżący
        num_months_past = 3 

        for i in range(num_months_past, -1, -1): # Od 3 miesięcy temu do bieżącego (0)
            # Określ rok i miesiąc
            current_loop_date = today - timedelta(days=i * 30) # Przybliżenie miesiąca
            month = current_loop_date.month
            year = current_loop_date.year

            # Sprawdź, czy już są dane dla tego miesiąca/roku, aby uniknąć duplikatów, jeśli skrypt jest uruchamiany wielokrotnie
            # Ta część jest opcjonalna, jeśli czyścimy dane na początku
            # existing_for_month = Transaction.query.filter(extract('year', Transaction.date) == year, extract('month', Transaction.date) == month).first()
            # if existing_for_month:
            #     print(f"Dane dla {year}-{month:02d} już istnieją, pomijam.")
            #     continue
            
            print(f"Generowanie danych dla {year}-{month:02d}...")

            # Przychody
            transactions_to_add.append(Transaction(description=f"Wypłata {calendar.month_name[month]}", amount=random.uniform(4800, 5500), date=date(year, month, 10), is_income=True, account_id=accounts_map["Tomek Prywatne"].id, person=PERSON_TOMEK))
            transactions_to_add.append(Transaction(description=f"Wypłata {calendar.month_name[month]}", amount=random.uniform(4300, 4900), date=date(year, month, 10), is_income=True, account_id=accounts_map["Toćka Prywatne"].id, person=PERSON_TOCKA))
            if random.random() < 0.2: # Dodatkowy mniejszy przychód
                 transactions_to_add.append(Transaction(description=f"Bonus {calendar.month_name[month]}", amount=random.uniform(200, 800), date=date(year, month, 15), is_income=True, account_id=random.choice([accounts_map["Tomek Prywatne"].id, accounts_map["Toćka Prywatne"].id]), person=random.choice([PERSON_TOMEK, PERSON_TOCKA])))


            # Wydatki wspólne
            transactions_to_add.append(Transaction(description=f"Living {calendar.month_name[month]}", amount=random.uniform(1000, 1500), date=date(year, month, 5), category_id=categories_map["Living (Wspólne)"].id, account_id=accounts_map["Wspólne Revolut"].id, person=PERSON_WSPOLNE))
            transactions_to_add.append(Transaction(description=f"Rachunki {calendar.month_name[month]}", amount=random.uniform(300, 600), date=date(year, month, 15), category_id=categories_map["Rachunki (Wspólne)"].id, account_id=accounts_map["Wspólne Revolut"].id, person=PERSON_WSPOLNE))

            # Wydatki prywatne Tomka
            for _ in range(random.randint(3, 6)): # 3-6 wydatków prywatnych
                cat_name = random.choice(["Jedzenie", "Transport", "Rozrywka", "Zdrowie", "Ubrania", "Inne"])
                # Upewnij się, że kategoria nie jest 'wspólna' dla wydatku prywatnego
                while categories_map[cat_name].is_shared_expense:
                     cat_name = random.choice(["Jedzenie", "Transport", "Rozrywka", "Zdrowie", "Ubrania", "Inne"])
                
                transactions_to_add.append(Transaction(
                    description=f"{cat_name} - Tomek {random.choice(['zakup', 'usługa', 'bilet'])}", 
                    amount=round(random.uniform(20, 250), 2), 
                    date=date(year, month, random.randint(1, 28)), 
                    category_id=categories_map[cat_name].id, 
                    account_id=accounts_map["Tomek Prywatne"].id, 
                    person=PERSON_TOMEK))

            # Wydatki prywatne Toćki
            for _ in range(random.randint(3, 6)):
                cat_name = random.choice(["Jedzenie", "Transport", "Rozrywka", "Zdrowie", "Ubrania", "Inne"])
                while categories_map[cat_name].is_shared_expense:
                     cat_name = random.choice(["Jedzenie", "Transport", "Rozrywka", "Zdrowie", "Ubrania", "Inne"])

                transactions_to_add.append(Transaction(
                    description=f"{cat_name} - Toćka {random.choice(['kosmetyki', 'książka', 'wyjście'])}", 
                    amount=round(random.uniform(20, 200), 2), 
                    date=date(year, month, random.randint(1, 28)), 
                    category_id=categories_map[cat_name].id, 
                    account_id=accounts_map["Toćka Prywatne"].id, 
                    person=PERSON_TOCKA))
        
        try:
            if transactions_to_add:
                db.session.bulk_save_objects(transactions_to_add)
                db.session.commit()
                print(f"Dodano {len(transactions_to_add)} przykładowych transakcji.")
            else:
                print("Nie dodano nowych transakcji (możliwe, że dane już istniały dla wszystkich okresów).")
        except Exception as e:
            db.session.rollback()
            print(f"Błąd podczas dodawania danych: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    seed_data()