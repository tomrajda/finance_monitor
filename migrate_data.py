import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
import random # Importujemy bibliotekę do generowania losowych liczb

# --- KONFIGURACJA ---
# Wczytaj konfiguracje z plików .env.prod i .env.dev
config_prod = dotenv_values(".env.prod")
config_dev = dotenv_values(".env.dev")

# Baza źródłowa (skąd kopiujemy) to ZAWSZE produkcja
SOURCE_URI = config_prod.get('DATABASE_URL')
# Baza docelowa (gdzie wklejamy) to ZAWSZE deweloperska
TARGET_URI = config_dev.get('DATABASE_URL')

# Lista tabel do migracji w poprawnej kolejności zależności
TABLES_TO_MIGRATE = [
    'account', 'category', 'asset_category', 'savings_goal', 'portfolio',
    'asset', 'transaction', 'asset_value_history', 'portfolio_snapshot'
]

# Lista kolumn zawierających kwoty, które chcemy zanonimizować
# Dodaj tutaj wszystkie kolumny z kwotami z Twoich modeli
COLUMNS_TO_ANONYMIZE = [
    'amount', 'current_value', 'invested_amount', 'purchase_price_per_unit',
    'value', 'total_value', 'goal_total', 'goal_tomek', 'goal_tocka'
]
# --- KONIEC KONFIGURACJI ---


def anonymize_amount(value):
    """
    Funkcja, która "psuje" kwotę, zachowując jej rząd wielkości.
    Zmienia wartość o losowy procent od -20% do +20%.
    """
    if value is None or not isinstance(value, (int, float)) or value == 0:
        return value
    
    # Oblicz losowy modyfikator, np. 1.15, 0.92, 1.05
    modifier = 1 + random.uniform(-0.90, 0.90)
    
    new_value = value * modifier
    
    # Zaokrąglij do 2 miejsc po przecinku, aby wyglądało jak kwota
    return round(new_value, 2)


def migrate_database():
    """
    Kopiuje dane z bazy produkcyjnej do deweloperskiej, anonimizując kwoty.
    """
    if not SOURCE_URI or not TARGET_URI:
        print("BŁĄD: Upewnij się, że pliki .env.prod i .env.dev istnieją i zawierają DATABASE_URL!")
        return

    print("Łączenie z bazami danych...")
    try:
        source_engine = create_engine(SOURCE_URI)
        target_engine = create_engine(TARGET_URI)
        print("Połączono pomyślnie.")
    except Exception as e:
        print(f"Błąd podczas łączenia z bazą danych: {e}")
        return

    with target_engine.connect() as connection:
        tables_to_clear = reversed(TABLES_TO_MIGRATE)
        print("\n--- Czyszczenie istniejących danych w bazie deweloperskiej ---")
        for table_name in tables_to_clear:
            try:
                print(f"Czyszczenie tabeli '{table_name}'...")
                connection.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE;'))
                connection.commit()
            except Exception as e:
                print(f"OSTRZEŻENIE: Nie udało się wyczyścić tabeli '{table_name}' przez TRUNCATE. Próbuję DELETE. Błąd: {e}")
                connection.rollback() # Wycofaj transakcję, jeśli TRUNCATE się nie udało
                try:
                    connection.execute(text(f'DELETE FROM "{table_name}";'))
                    connection.commit()
                except Exception as e2:
                     print(f"!!! Błąd podczas czyszczenia tabeli '{table_name}': {e2}")
                     connection.rollback()
        
        for table_name in TABLES_TO_MIGRATE:
            print(f"\n--- Migracja tabeli: {table_name} ---")
            try:
                print(f"Odczytywanie danych z tabeli '{table_name}' w SQLite/Prod...")
                df = pd.read_sql_table(table_name, source_engine)
                print(f"Znaleziono {len(df)} wierszy.")

                if not df.empty:
                    # ANONIMIZACJA DANYCH
                    for col in COLUMNS_TO_ANONYMIZE:
                        if col in df.columns:
                            print(f" -> Anonimizacja kolumny '{col}'...")
                            df[col] = df[col].apply(anonymize_amount)
                    
                    print(f"Zapisywanie danych do tabeli '{table_name}' w PostgreSQL/Dev...")
                    df.to_sql(table_name, connection, if_exists='append', index=False)
                    print(f"Pomyślnie zmigrowano {len(df)} wierszy.")

                    if 'id' in df.columns:
                        max_id = df['id'].max()
                        sequence_name = f"{table_name}_id_seq"
                        print(f"Aktualizowanie sekwencji ID '{sequence_name}' do wartości {max_id}...")
                        try:
                            connection.execute(text(f"SELECT setval('{sequence_name}', {max_id}, true);"))
                            connection.commit()
                            print("Sekwencja zaktualizowana.")
                        except Exception as seq_e:
                            print(f"OSTRZEŻENIE: Nie udało się zaktualizować sekwencji '{sequence_name}'. Błąd: {seq_e}")
                else:
                    print(f"Tabela '{table_name}' jest pusta, pomijanie.")

            except Exception as e:
                print(f"!!! BŁĄD podczas migracji tabeli '{table_name}': {e}")
                print("!!! PRZERWANO MIGRACJĘ.")
                connection.rollback()
                return
    
    print("\n--- Migracja danych zakończona pomyślnie! ---")


if __name__ == '__main__':
    migrate_database()