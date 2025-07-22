from app import create_app

app = create_app()

if __name__ == '__main__':
    # Dodaj host='0.0.0.0'
    app.run(host='0.0.0.0', debug=True)