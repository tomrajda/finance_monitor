from app import create_app

app = create_app()

# Ten blok jest używany tylko przy uruchamianiu skryptu bezpośrednio (np. przez 'python run.py')
if __name__ == '__main__':
    # Używamy host='0.0.0.0' aby aplikacja była dostępna w Twojej sieci lokalnej,
    # tak jak to robi Docker.
    # Używamy debug=True dla wygodnego developmentu (automatyczne przeładowanie, debugger).
    app.run(host='0.0.0.0', port=5000, debug=True)