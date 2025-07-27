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
    
    # Oblicz stopę oszczędności jako procent przychodów
    savings_rate = (savings / income_total * 100) if income_total > 0 else 0
    
    # Przygotuj listę wydatków
    expenses_str = "\n".join([f"- {cat}: {amount:.2f} PLN" for cat, amount in expenses_by_category.items()])

    # --- NOWY, ROZBUDOWANY PROMPT ---
    prompt = f"""
    Jesteś doświadczonym, empatycznym doradcą finansowym z Polski. Twoim zadaniem jest analiza miesięcznego budżetu pary i przedstawienie go w sposób ciekawy, motywujący i osadzony w polskich realiach.
    
    Oto dane finansowe pary za {month_name} {year}:
    - Przychody łączne: {income_total:.2f} PLN
    - Wydatki łączne: {expenses_total:.2f} PLN
    - Oszczędności (Przychody - Wydatki): {savings:.2f} PLN
    - Stopa oszczędności: {savings_rate:.1f}% przychodów

    Oto rozkład ich wydatków według kategorii:
    {expenses_str if expenses_str else "- Brak wydatków w tym miesiącu."}
    
    Wykonaj następujące zadania w języku polskim, używając przyjaznego i wspierającego tonu. Używaj formatowania Markdown (nagłówki, pogrubienia, listy), aby odpowiedź była czytelna.

    **Zadanie 1: Tytuł i Krótkie Podsumowanie**
    Stwórz chwytliwy, pozytywny tytuł dla tego miesiąca, np. "Świetny Miesiąc Oszczędzania!" albo "Inwestycja w Siebie!".
    Następnie, w 2-3 zdaniach, podsumuj ogólną kondycję finansową pary w tym miesiącu. Skup się na relacji między przychodami a wydatkami.

    **Zadanie 2: Analiza w Kontekście Polskich Realiów**
    Porównaj ich stopę oszczędności z ogólnymi zaleceniami i statystykami dla Polski.
    - Wspomnij, że eksperci finansowi często zalecają oszczędzanie 10-20% miesięcznych dochodów.
    - Możesz dodać kontekst, że według różnych badań (np. Głównego Urzędu Statystycznego), stopa oszczędności gospodarstw domowych w Polsce waha się, ale osiągnięcie poziomu 10% jest już dobrym wynikiem.
    - Skomentuj, jak para wypada na tym tle. Jeśli ich wynik jest świetny, pochwal ich. Jeśli jest niski, zmotywuj do poprawy, bez krytykowania.

    **Zadanie 3: Analiza Kategorii Wydatków**
    Przeanalizuj listę wydatków. Zidentyfikuj jedną lub dwie kategorie, które wyróżniają się najbardziej (pozytywnie lub negatywnie).
    - Jeśli jakaś kategoria, np. "Rozrywka" lub "Jedzenie", stanowi duży procent wydatków, delikatnie na to zwróć uwagę. Zaproponuj refleksję, np. "Warto zauważyć, że wydatki na [kategoria] były w tym miesiącu znaczące. Czy przyniosły Wam dużo radości i były tego warte?".
    - Jeśli wydatki na "życie" (np. "Living", "Rachunki") są wysokie, możesz to skomentować jako stały, ważny element budżetu.
    - Nie krytykuj, ale zachęcaj do świadomego wydawania pieniędzy.

    **Zadanie 4: Konkretne i Kreatywne Porady**
    Daj 2-3 konkretne, praktyczne i lekko kreatywne porady na przyszłość, dopasowane do ich sytuacji.
    - Jeśli mają nadwyżkę: "Świetna robota! Zastanówcie się, co zrobić z tą nadwyżką. Może to dobry moment na nadpłatę małego kredytu, zasilenie 'poduszki finansowej' lub zainwestowanie małej kwoty w [coś, co pasuje do ich wydatków, np. kurs, jeśli wydają na edukację]?"
    - Jeśli mają deficyt lub niskie oszczędności: "Każdy ma czasem trudniejszy miesiąc. Może w przyszłym miesiącu spróbujecie wyzwania 'tydzień bez wydatków na jedzenie na mieście' albo przeanalizujecie subskrypcje, z których rzadko korzystacie? Małe kroki potrafią zdziałać cuda!"
    - Zawsze zakończ pozytywnym, motywującym akcentem.
    """
    # --- KONIEC PROMPTU ---

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Błąd Gemini (podsumowanie): {e}")
        return "### Błąd Generowania Podsumowania\n\nNie udało się wygenerować podsumowania z powodu błędu. Spróbuj ponownie później."
    
def get_yearly_summary_gemini(
    selected_year: int,
    total_income_ytd: float,
    total_expenses_ytd: float,
    total_savings_ytd: float,
    avg_monthly_savings: float,
    savings_rate_ytd: float,
    top_categories: dict,
    best_month: dict,
    worst_month: dict
) -> str:
    """Generuje roczny raport finansowy i strategiczne porady używając Gemini."""
    
    top_categories_str = "\n".join([f"- {cat}: {amount:.2f} PLN" for cat, amount in top_categories.items()])
    best_month_name = best_month.get("name", "Brak danych")
    best_month_savings = best_month.get("savings", 0.0)
    worst_month_name = worst_month.get("name", "Brak danych")
    worst_month_savings = worst_month.get("savings", 0.0)

    prompt = f"""
    Jesteś analitykiem finansowym i coachem specjalizującym się w długoterminowych strategiach dla par. Twoim zadaniem jest stworzenie rocznego raportu finansowego dla pary T&M na podstawie poniższych danych za rok {selected_year}. Używaj języka polskiego, formatowania Markdown (nagłówki, pogrubienia, listy), a ton ma być profesjonalny, ale jednocześnie motywujący i optymistyczny.

    **Dane Roczne:**
    - Całkowity przychód: {total_income_ytd:.2f} PLN
    - Całkowite wydatki: {total_expenses_ytd:.2f} PLN
    - Całkowite oszczędności: {total_savings_ytd:.2f} PLN
    - Średnie miesięczne oszczędności: {avg_monthly_savings:.2f} PLN
    - Roczna stopa oszczędności: {savings_rate_ytd:.1f}%

    **Kluczowe obserwacje:**
    - Kategorie z największymi wydatkami w roku:
    {top_categories_str}
    - Najlepszy miesiąc pod względem oszczędności: {best_month_name} ({best_month_savings:.2f} PLN)
    - Najtrudniejszy miesiąc pod względem oszczędności: {worst_month_name} ({worst_month_savings:.2f} PLN)

    **Zadania do wykonania:**

    1.  **Tytuł Raportu:** Stwórz inspirujący tytuł, np. "Wasz Finansowy Rok {selected_year}: Analiza i Krok w Przyszłość".

    2.  **Podsumowanie Ogólne ("Executive Summary"):** W 2-3 zdaniach podsumuj, jaki to był rok dla finansów pary. Skup się na kluczowej metryce – rocznej stopie oszczędności, porównując ją do zalecanych w Polsce 10-20%.

    3.  **Głęboka Analiza ("Deep Dive"):**
        *   **Nawyki Wydatkowe:** Skomentuj top 3 kategorie. Czy są one zgodne z celami i wartościami pary (np. "Duże wydatki na 'Podróże' pokazują, że cenicie sobie wspólne doświadczenia")? Czy któraś kategoria jest zaskoczeniem?
        *   **Zmienność w Czasie:** Porównaj najlepszy i najtrudniejszy miesiąc. Co mogło być przyczyną różnic? (np. "Widać, że {best_month_name} był świetny – być może to efekt premii lub niższych wydatków. Z kolei w {worst_month_name} mogły pojawić się nieplanowane koszty.").

    4.  **Strategiczne Rekomendacje na Następny Rok:**
        *   **Cel na {selected_year + 1}:** Bazując na średnich miesięcznych oszczędnościach, zaproponuj realistyczny, ale ambitny cel oszczędnościowy na kolejny rok.
        *   **"Jedna Zmiana":** Zaproponuj jedną, konkretną zmianę lub nawyk, który para mogłaby wprowadzić w nowym roku, aby poprawić swoje finanse (np. "Spróbujcie 'zasady 24 godzin' dla zakupów impulsywnych powyżej 200 zł" albo "Ustawcie automatyczny przelew na konto oszczędnościowe dzień po wypłacie").
    
    Zakończ raport motywującym i pozytywnym akcentem.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Błąd Gemini (podsumowanie roczne): {e}")
        return "### Błąd Generowania Raportu\n\nNie udało się wygenerować rocznego podsumowania z powodu błędu. Spróbuj ponownie później."