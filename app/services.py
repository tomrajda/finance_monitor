import google.generativeai as genai
from app.models import Category
from app import db
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash') # Lub gemini-pro

def suggest_category_gemini(description: str) -> tuple[str, bool]:
    """
    Sugeruje kategorię wydatku na podstawie opisu, używając Gemini.
    Zwraca krotkę: (nazwa_kategorii, czy_jest_nowa_i_nie_istnieje_w_bazie)
    """
    if not description:
        return "Nieokreślona", False

    existing_categories_db = Category.query.all()
    existing_categories_names = [cat.name for cat in existing_categories_db]

    prompt = f"""
    Jesteś asystentem kategoryzacji wydatków. Na podstawie poniższego opisu wydatku, zasugeruj najbardziej odpowiednią kategorię.
    Opis wydatku: "{description}"

    Dostępne kategorie, których możesz użyć, jeśli pasują: {', '.join(existing_categories_names) if existing_categories_names else 'Brak zdefiniowanych kategorii.'}

    Jeśli opis pasuje do jednej z istniejących kategorii, użyj jej nazwy.
    Jeśli żadna z istniejących kategorii idealnie nie pasuje, zaproponuj NOWĄ, zwięzłą nazwę kategorii (1-3 słowa).
    Odpowiedz TYLKO nazwą kategorii (istniejącą lub nową). Nie dodawaj żadnych wyjaśnień. Nazwa powinna być w języku polskim.
    Przykład dla nowej:
    Opis: "Bilet na pociąg do Krakowa"
    Odpowiedź: "Podróże Pociągiem"
    """
    try:
        response = model.generate_content(prompt)
        suggested_category_name = response.text.strip()

        if not suggested_category_name:
            return "Nieokreślona", False

        suggested_category_name = suggested_category_name.capitalize()
        
        category_obj = Category.query.filter(db.func.lower(Category.name) == db.func.lower(suggested_category_name)).first()
        
        if category_obj:
            return category_obj.name, False 
        else:
            return suggested_category_name, True 
            
    except Exception as e:
        print(f"Błąd Gemini (sugestia kategorii): {e}")
        return "Nieokreślona", False

def get_monthly_summary_gemini(month_name: str, year: int, income_total: float, expenses_total: float, savings: float, expenses_by_category: dict) -> str:
    """Generuje podsumowanie miesiąca i porady finansowe używając Gemini."""
    
    expenses_str = "\n".join([f"- {cat}: {amount:.2f} PLN" for cat, amount in expenses_by_category.items()])

    prompt = f"""
    Jesteś doradcą finansowym. Przeanalizuj następujące dane finansowe za {month_name} {year} w języku polskim:
    Przychody łączne: {income_total:.2f} PLN
    Wydatki łączne: {expenses_total:.2f} PLN
    Oszczędności (Przychody - Wydatki): {savings:.2f} PLN

    Wydatki według kategorii:
    {expenses_str if expenses_str else "- Brak wydatków w tym miesiącu."}

    Zadania:
    1. Napisz krótkie, przyjazne podsumowanie sytuacji finansowej w tym miesiącu (2-3 zdania).
    2. Przedstaw 2-3 konkretne, praktyczne porady finansowe lub obserwacje na podstawie tych danych.
       - Jeśli oszczędności są dobre, pochwal i zasugeruj, jak utrzymać ten stan lub co można zrobić z nadwyżką.
       - Jeśli wydatki w jakiejś kategorii są wysokie, delikatnie na to zwróć uwagę i zaproponuj refleksję lub optymalizację.
       - Jeśli oszczędności są niskie lub ujemne, zaproponuj kroki zaradcze.
    3. Używaj języka polskiego. Bądź motywujący i wspierający.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Błąd Gemini (podsumowanie): {e}")
        return "Nie udało się wygenerować podsumowania z powodu błędu."