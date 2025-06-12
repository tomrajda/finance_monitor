@echo off
echo Uruchamianie srodowiska wirtualnego...
call .\venv\Scripts\activate.bat

echo Uruchamianie aplikacji Flask...
:: Uruchom serwer Flask w tle, aby skrypt mógł kontynuować
:: i otworzyć przeglądarkę. Użyjemy 'start ""' aby uruchomić w nowym oknie
:: bez czekania na zakończenie.
start "Flask Server" /B python run.py

:: Małe opóźnienie, aby dać serwerowi Flask chwilę na uruchomienie
echo Oczekiwanie na start serwera (3 sekundy)...
timeout /t 3 /nobreak > nul

echo Otwieranie aplikacji w przegladarce...
start http://127.0.0.1:5000

echo.
echo Serwer Flask dziala w tle.
echo Aby zatrzymac serwer, zamknij okno konsoli, ktore uruchomilo 'python run.py'
echo (moze byc zminimalizowane lub ukryte), lub uzyj Ctrl+C w tym oknie, jesli
echo serwer nie uruchomil sie poprawnie w tle.
echo.

:: Ta konsola pozostanie otwarta, aby można było zobaczyć komunikaty.
:: Możesz ją zamknąć. Zamknięcie tej konsoli NIE zatrzyma serwera Flask,
:: jeśli uruchomił się poprawnie z 'start /B'.
pause