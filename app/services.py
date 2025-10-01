import google.generativeai as genai
from app.models import Category
from app import db
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash') # Lub gemini-pro

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
    
    savings_rate = (savings / income_total * 100) if income_total > 0 else 0
    expenses_str = "\n".join([f"- {cat}: {amount:.2f} PLN" for cat, amount in expenses_by_category.items()])

    prompt = f"""
    Jesteś doświadczonym, empatycznym analitykiem finansowym i coachem z Polski. Twoim zadaniem jest analiza miesięcznego budżetu pary T&M i przedstawienie go w sposób ciekawy, motywujący i osadzony w polskich realiach, z dużą ilością danych i ciekawostek.
    
    Oto dane finansowe pary za {month_name} {year}:
    - Przychody łączne: {income_total:.2f} PLN
    - Wydatki łączne: {expenses_total:.2f} PLN
    - Oszczędności: {savings:.2f} PLN
    - Stopa oszczędności: {savings_rate:.1f}% przychodów

    Oto rozkład ich wydatków według kategorii:
    {expenses_str if expenses_str else "- Brak wydatków w tym miesiącu."}
    
    Wykonaj następujące zadania w języku polskim, używając przyjaznego i wspierającego tonu. Używaj formatowania Markdown (nagłówki, pogrubienia, listy, cytaty blokowe dla ciekawostek).

    **Zadanie 1: Tytuł i Kluczowe Wskaźniki**
    Stwórz chwytliwy, pozytywny tytuł dla tego miesiąca, np. "Finansowy Sprint w {month_name}!" albo "Miesiąc Mądrych Decyzji!".
    Następnie, w 2-3 zdaniach, podsumuj ogólną kondycję finansową. Podkreśl najważniejszą liczbę miesiąca – kwotę oszczędności lub stopę oszczędności.

    **Zadanie 2: Analiza Stopy Oszczędności w Kontekście**
    Szczegółowo przeanalizuj ich stopę oszczędności ({savings_rate:.1f}%).
    - Porównaj ją z ogólnymi zaleceniami dla Polski (10-20% dochodów).
    - **Dodaj ciekawostkę statystyczną:** Wspomnij o danych, np. "Według danych GUS/Eurostat, stopa oszczędności gospodarstw domowych w Polsce w ostatnich latach oscylowała w okolicach 5-10%. Wasz wynik ({savings_rate:.1f}%) plasuje Was [znacznie powyżej/blisko/poniżej] średniej krajowej. To świetny punkt odniesienia!".
    - Podkreśl, co oznacza ich wynik w praktyce. Oblicz, ile mogliby zaoszczędzić w ciągu roku, utrzymując ten poziom: ({savings:.2f} PLN * 12 miesięcy = {savings * 12:.2f} PLN).

    **Zadanie 3: Głębsza Analiza Wydatków**
    Zidentyfikuj 2-3 najważniejsze kategorie wydatków i skomentuj je, podając konkretne liczby i procenty.
    - Oblicz, jaki procent **wszystkich wydatków** stanowiły 1-2 największe kategorie. Np. "Warto zauważyć, że wydatki na [kategoria 1] ({expenses_by_category.get('Kategoria 1', 0):.2f} PLN) stanowiły aż { (expenses_by_category.get('Kategoria 1', 0) / expenses_total * 100) if expenses_total > 0 else 0:.0f}% Waszych miesięcznych kosztów."
    - **Dodaj ciekawostkę finansową:** Jeśli największą kategorią jest "Jedzenie", możesz dodać: "> **Ciekawostka:** Przeciętne polskie gospodarstwo domowe wydaje na żywność i napoje bezalkoholowe około 25-30% swojego budżetu. Jak Wasze wydatki w tej kategorii mają się do tej średniej?". Jeśli "Transport", wspomnij o rosnących cenach paliw. Jeśli "Rozrywka", pochwal za inwestowanie w dobre samopoczucie.

    **Zadanie 4: Konkretne, "Numbryczne" Porady**
    Daj 2 praktyczne porady oparte na liczbach.
    - Jeśli oszczędności są dobre: "Świetna robota! Wasze {savings:.2f} PLN to solidny wkład. Proponuję strategię '50/30/20', gdzie 50% idzie na potrzeby, 30% na przyjemności, a 20% na oszczędności i inwestycje. Wasz wynik jest [blisko/daleko] od tego modelu. Może warto [coś zrobić], aby się do niego zbliżyć?".
    - Jeśli oszczędności są niskie: "Każdy miesiąc jest inny. Spróbujcie w przyszłym miesiącu 'zasady 1%'. Polega ona na próbie zmniejszenia wydatków w jednej dużej kategorii (np. Jedzenie) tylko o 1%, co dałoby Wam dodatkowe {expenses_by_category.get('Jedzenie', 0) * 0.01:.2f} PLN oszczędności. To mały krok, który buduje świetny nawyk!".

    Zawsze zakończ raport pozytywnym, motywującym akcentem, podsumowując największy sukces finansowy tego miesiąca.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Błąd Gemini (podsumowanie): {e}")
        return "### Błąd Generowania Podsumowania\n\nNie udało się wygenerować podsumowania z powodu błędu. Spróbuj ponownie później."
    
def get_yearly_summary_gemini(
    selected_year: int, total_income_ytd: float, total_expenses_ytd: float,
    total_savings_ytd: float, avg_monthly_savings: float, savings_rate_ytd: float,
    top_categories: dict, best_month: dict, worst_month: dict
) -> str:
    """Generuje roczny raport finansowy i strategiczne porady używając Gemini."""
    
    top_categories_str = "\n".join([f"- {cat}: {amount:.2f} PLN (średnio {(amount/12):.2f} PLN/mies.)" for cat, amount in top_categories.items()])
    best_month_name = best_month.get("name", "Brak danych")
    best_month_savings = best_month.get("savings", 0.0)
    worst_month_name = worst_month.get("name", "Brak danych")
    worst_month_savings = worst_month.get("savings", 0.0)

    prompt = f"""
    Jesteś czołowym analitykiem finansowym i coachem specjalizującym się w długoterminowych strategiach dla par. Twoim zadaniem jest stworzenie kompleksowego, rocznego raportu finansowego dla pary T&M na podstawie poniższych danych za rok {selected_year}. Używaj języka polskiego, formatowania Markdown (nagłówki, pogrubienia, listy, cytaty), a ton ma być profesjonalny, ale jednocześnie motywujący i pełen ciekawych spostrzeżeń.

    **Dane Roczne T&M za {selected_year}:**
    - Całkowity przychód roczny: {total_income_ytd:.2f} PLN
    - Całkowite wydatki roczne: {total_expenses_ytd:.2f} PLN
    - **Całkowite oszczędności roczne: {total_savings_ytd:.2f} PLN**
    - Średnie miesięczne oszczędności: {avg_monthly_savings:.2f} PLN
    - **Roczna stopa oszczędności: {savings_rate_ytd:.1f}%**

    **Kluczowe obserwacje:**
    - Kategorie z największymi wydatkami w roku (i średnia miesięczna):
    {top_categories_str}
    - Najlepszy miesiąc pod względem oszczędności: {best_month_name} ({best_month_savings:.2f} PLN)
    - Najtrudniejszy miesiąc pod względem oszczędności: {worst_month_name} ({worst_month_savings:.2f} PLN)

    **Zadania do wykonania w raporcie:**

    1.  **Tytuł Raportu:** Stwórz inspirujący tytuł, np. "**Wasz Finansowy Rok {selected_year}: Analiza, Osiągnięcia i Mapa Drogowa na Przyszłość**".

    2.  **Podsumowanie Ogólne ("Executive Summary"):**
        W 2-3 zdaniach podsumuj rok. Skup się na kluczowej metryce – rocznej stopie oszczędności. Porównaj ją z zalecanymi w Polsce 10-20% i skomentuj wynik.
        **Dodaj ciekawostkę:** "> **Kontekst:** Osiągnięcie rocznej stopy oszczędności na poziomie {savings_rate_ytd:.1f}% oznacza, że efektywnie pracowaliście 'na siebie' przez około {(savings_rate_ytd / 100 * 12):.1f} miesiąca w roku! Każdy punkt procentowy to dodatkowe dni wolności finansowej."

    3.  **Głęboka Analiza Roczna ("Deep Dive"):**
        *   **Struktura Wydatków:** Skomentuj top 3 kategorie. Oblicz, jaki procent **całkowitych rocznych wydatków** stanowi suma tych trzech kategorii. Np. "Wasze top 3 kategorie pochłonęły łącznie [suma] PLN, co stanowi [procent]% wszystkich rocznych kosztów. To pokazuje, co jest dla Was priorytetem."
        *   **Zmienność i Stabilność:** Porównaj najlepszy i najtrudniejszy miesiąc. Różnica w oszczędnościach między nimi wyniosła **{best_month_savings - worst_month_savings:.2f} PLN**. Co to mówi o stabilności Waszych finansów? Czy były to jednorazowe zdarzenia (premie, duże zakupy), czy powtarzalny schemat?
        *   **Siła Procentu Składanego:** Oblicz, co by się stało z Waszymi rocznymi oszczędnościami ({total_savings_ytd:.2f} PLN) po 10 latach, zakładając skromne, średnie oprocentowanie 7% rocznie (uwzględniając procent składany). Użyj wzoru: Kwota * (1 + 0.07)^10. Podaj wynik jako inspirującą liczbę. Np. "> **Potęga Czasu:** Gdybyście zainwestowali tegoroczne oszczędności, przy średnim rocznym zwrocie 7%, po 10 latach ta kwota urosłaby do około **{(total_savings_ytd * (1.07**10)):.2f} PLN**! To pokazuje, jak potężny jest procent składany."

    4.  **Strategiczne Rekomendacje na {selected_year + 1}:**
        *   **Cel Oszczędnościowy SMART:** Bazując na średnich miesięcznych oszczędnościach, zaproponuj konkretny cel roczny. Np. "Jeśli uda Wam się zwiększyć średnie miesięczne oszczędności o zaledwie 10% (do {(avg_monthly_savings * 1.1):.2f} PLN), w przyszłym roku zaoszczędzicie łącznie **{(avg_monthly_savings * 1.1 * 12):.2f} PLN**."
        *   **"Audyt Kategorii":** Zaproponuj, aby w nowym roku przyjrzeli się jednej kategorii z top 3 wydatków i spróbowali zoptymalizować ją o 5-10%, nie rezygnując z jakości życia. Oblicz, ile dałoby to dodatkowych oszczędności w skali roku.

    Zakończ raport gratulacjami za podjęty wysiłek i motywującym akcentem na przyszłość.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Błąd Gemini (podsumowanie roczne): {e}")
        return "### Błąd Generowania Raportu\n\nNie udało się wygenerować rocznego podsumowania z powodu błędu. Spróbuj ponownie później."