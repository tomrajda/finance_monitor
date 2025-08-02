# Krok 1: Wybierz oficjalny, lekki obraz Pythona jako bazę
FROM python:3.11-slim

# Krok 2: Ustaw zmienne środowiskowe
ENV PYTHONUNBUFFERED 1

# Krok 3: Ustaw katalog roboczy wewnątrz kontenera
WORKDIR /app

# Krok 4: Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Krok 5: Skopiuj resztę kodu aplikacji do katalogu roboczego
COPY . .

# Krok 6: Wystaw port, na którym nasłuchuje aplikacja wewnątrz kontenera
EXPOSE 5000

# Krok 7: Zdefiniuj komendę, która uruchomi aplikację za pomocą Gunicorna
# ZMIANA TUTAJ: Dodano --timeout 120, aby zwiększyć limit czasu do 120 sekund
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "run:app"]