# Krok 1: Wybierz oficjalny, lekki obraz Pythona jako bazę
FROM python:3.11-slim

# Krok 2: Ustaw zmienne środowiskowe dla optymalizacji Pythona w Dockerze
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Krok 3: Ustaw katalog roboczy wewnątrz kontenera
WORKDIR /app

# Krok 4: Skopiuj plik z zależnościami i zainstaluj je
# Kopiujemy go osobno, aby Docker mógł wykorzystać cache, jeśli zależności się nie zmienią
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Krok 5: Skopiuj resztę kodu aplikacji do katalogu roboczego
COPY . .

# Krok 6: Wystaw port, na którym będzie działać serwer wewnątrz kontenera
EXPOSE 5000

# Krok 7: Zdefiniuj komendę, która uruchomi aplikację za pomocą produkcyjnego serwera Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]