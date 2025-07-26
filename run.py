from app import create_app

app = create_app()

# Ten blok if __name__ ... jest teraz używany tylko do lokalnego developmentu bez Dockera.
# Gunicorn bezpośrednio używa obiektu 'app'.
if __name__ == '__main__':
    app.run(debug=True)