from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, Blueprint
from flask_login import login_user, logout_user, login_required, current_user
import os
from app import User
from app import db
from app.services import suggest_category_gemini, get_monthly_summary_gemini, get_yearly_summary_gemini
from app.models import Transaction, Category, Account, Portfolio, AssetCategory, Asset, AssetValueHistory, PortfolioSnapshot
from datetime import datetime, date, timedelta 
from sqlalchemy import extract, func
from sqlalchemy import desc
import json
import pytz
import pandas as pd
import uuid
from threading import Thread
from app.models import ImportTask, TempTransaction
import time

main_bp = Blueprint('main', __name__)

PERSON_TOMEK = "Tomek"
PERSON_TOCKA = "Toćka"
PERSON_WSPOLNE = "Wspólne"

ACCOUNT_NAME_TOMEK = "Tomek Prywatne"
ACCOUNT_NAME_TOCKA = "Toćka Prywatne"
ACCOUNT_NAME_WSPOLNE = "Wspólne Revolut"

POLAND_TZ = pytz.timezone('Europe/Warsaw')

tasks_in_progress = {}

CATEGORY_COLORS_PALETTE = [
    'rgba(255, 99, 132, 0.85)',  # Różowy/Czerwony
    'rgba(54, 162, 235, 0.85)',  # Niebieski
    'rgba(255, 206, 86, 0.85)',  # Żółty
    'rgba(75, 192, 192, 0.85)',  # Turkusowy/Teal
    'rgba(153, 102, 255, 0.85)', # Fioletowy
    'rgba(255, 159, 64, 0.85)',  # Pomarańczowy
    'rgba(76, 175, 80, 0.85)',   # Zielony
    'rgba(201, 203, 207, 0.85)', # Szary
    'rgba(230, 126, 34, 0.85)',  # Ciemny Pomarańczowy (Carrot)
    'rgba(46, 204, 113, 0.85)',  # Szmaragdowy
    'rgba(142, 68, 173, 0.85)',  # Ciemny Fiolet (Wisteria)
    'rgba(241, 196, 15, 0.85)',  # Słonecznikowy Żółty
    'rgba(26, 188, 156, 0.85)',  # Turkusowy
    'rgba(231, 76, 60, 0.85)',   # Ciemny Czerwony (Alizarin)
    'rgba(52, 73, 94, 0.85)',    # Ciemny Niebiesko-Szary (Wet Asphalt)
    'rgba(127, 140, 141, 0.85)', # Szary (Asbestos)
    'rgba(0, 184, 148, 0.85)',   # Mint
    'rgba(253, 203, 110, 0.85)', # Orange Yellow
    'rgba(9, 132, 227, 0.85)',   # Peter River Blue
    'rgba(211, 84, 0, 0.85)'     # Pumpkin
]

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        app_user = os.environ.get('APP_USER')
        app_password = os.environ.get('APP_PASSWORD')

        # Proste porównanie haseł (dla tego przypadku wystarczy)
        # W prawdziwej aplikacji z wieloma użytkownikami hasła byłyby haszowane
        if username == app_user and password == app_password:
            user = User.get(username)
            login_user(user) # "Zapamiętaj" użytkownika w sesji
            flash('Zalogowano pomyślnie!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Nieprawidłowy login lub hasło.', 'danger')

    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Wylogowano pomyślnie.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/', methods=['GET'])
@login_required
def index():
    today = date.today()
    last_day_of_prev_month = today.replace(day=1) - timedelta(days=1)
    default_year_for_details = last_day_of_prev_month.year
    default_month_for_details = last_day_of_prev_month.month

    selected_year_for_details = request.args.get('year', default=default_year_for_details, type=int)
    selected_month_for_details = request.args.get('month', default=default_month_for_details, type=int)

    income_tomek = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, Transaction.person == PERSON_TOMEK, extract('year', Transaction.date) == selected_year_for_details, extract('month', Transaction.date) == selected_month_for_details).scalar() or 0.0
    income_tocka = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, Transaction.person == PERSON_TOCKA, extract('year', Transaction.date) == selected_year_for_details, extract('month', Transaction.date) == selected_month_for_details).scalar() or 0.0
    total_income_selected_month = income_tomek + income_tocka
    all_expenses_query_selected_month = Transaction.query.filter(Transaction.is_income == False, extract('year', Transaction.date) == selected_year_for_details, extract('month', Transaction.date) == selected_month_for_details)
    total_expenses_raw_selected_month = all_expenses_query_selected_month.with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    shared_categories = Category.query.filter_by(is_shared_expense=True).all()
    shared_category_ids = [cat.id for cat in shared_categories]
    shared_expenses_total_amount_selected_month = 0
    if shared_category_ids:
        shared_expenses_total_amount_selected_month = all_expenses_query_selected_month.filter(Transaction.category_id.in_(shared_category_ids)).with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    individual_share_of_shared_expenses_selected_month = shared_expenses_total_amount_selected_month / 2
    private_expenses_tomek_selected_month = all_expenses_query_selected_month.filter(Transaction.person == PERSON_TOMEK, Transaction.category_id.notin_(shared_category_ids)).with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    private_expenses_tocka_selected_month = all_expenses_query_selected_month.filter(Transaction.person == PERSON_TOCKA, Transaction.category_id.notin_(shared_category_ids)).with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    total_expenses_tomek_selected_month = private_expenses_tomek_selected_month + individual_share_of_shared_expenses_selected_month
    total_expenses_tocka_selected_month = private_expenses_tocka_selected_month + individual_share_of_shared_expenses_selected_month
    savings_total_selected_month = total_income_selected_month - total_expenses_raw_selected_month
    savings_tomek_selected_month = income_tomek - total_expenses_tomek_selected_month
    savings_tocka_selected_month = income_tocka - total_expenses_tocka_selected_month
    expenses_by_category_overall_q = db.session.query(Category.name, func.sum(Transaction.amount)).join(Category, Transaction.category_id == Category.id).filter(Transaction.is_income == False, extract('year', Transaction.date) == selected_year_for_details, extract('month', Transaction.date) == selected_month_for_details).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()
    expenses_by_category_overall_dict = {cat: amount for cat, amount in expenses_by_category_overall_q}
    expenses_tomek_by_category_dict = {}
    private_tomek_cat_q = all_expenses_query_selected_month.filter(Transaction.person == PERSON_TOMEK, Transaction.category_id.notin_(shared_category_ids)).join(Category).group_by(Category.name).with_entities(Category.name, func.sum(Transaction.amount)).all()
    for cat_name, amount in private_tomek_cat_q: expenses_tomek_by_category_dict[cat_name] = expenses_tomek_by_category_dict.get(cat_name, 0) + amount
    for cat in shared_categories:
        amount_shared_cat_tomek = all_expenses_query_selected_month.filter(Transaction.category_id == cat.id).with_entities(func.sum(Transaction.amount)).scalar() or 0.0
        if amount_shared_cat_tomek > 0: expenses_tomek_by_category_dict[f"{cat.name} (udział)"] = expenses_tomek_by_category_dict.get(f"{cat.name} (udział)", 0) + (amount_shared_cat_tomek / 2)
    expenses_tocka_by_category_dict = {}
    private_tocka_cat_q = all_expenses_query_selected_month.filter(Transaction.person == PERSON_TOCKA, Transaction.category_id.notin_(shared_category_ids)).join(Category).group_by(Category.name).with_entities(Category.name, func.sum(Transaction.amount)).all()
    for cat_name, amount in private_tocka_cat_q: expenses_tocka_by_category_dict[cat_name] = expenses_tocka_by_category_dict.get(cat_name, 0) + amount
    for cat in shared_categories:
        amount_shared_cat_tocka = all_expenses_query_selected_month.filter(Transaction.category_id == cat.id).with_entities(func.sum(Transaction.amount)).scalar() or 0.0
        if amount_shared_cat_tocka > 0: expenses_tocka_by_category_dict[f"{cat.name} (udział)"] = expenses_tocka_by_category_dict.get(f"{cat.name} (udział)", 0) + (amount_shared_cat_tocka / 2)
    transactions_selected_month = Transaction.query.filter(extract('year', Transaction.date) == selected_year_for_details, extract('month', Transaction.date) == selected_month_for_details).order_by(Transaction.date.desc()).all()
    years_for_dropdown_query = db.session.query(extract('year', Transaction.date)).distinct().all()
    years_for_dropdown = sorted(list(set(r[0] for r in years_for_dropdown_query if r[0] is not None)))
    if not years_for_dropdown: years_for_dropdown = [today.year]
    if today.year not in years_for_dropdown: years_for_dropdown.append(today.year)
    if default_year_for_details not in years_for_dropdown: years_for_dropdown.append(default_year_for_details)
    years_for_dropdown = sorted(list(set(years_for_dropdown)))
    months_list_for_dropdown = [(1, "styczeń"), (2, "luty"), (3, "marzec"), (4, "kwiecień"), (5, "maj"), (6, "czerwiec"), (7, "lipiec"), (8, "sierpień"), (9, "wrzesień"), (10, "październik"), (11, "listopad"), (12, "grudzień")]
    current_month_name_for_details = dict(months_list_for_dropdown).get(selected_month_for_details, "nieznany miesiąc")
    
    ytd_label_year = selected_year_for_details
    total_income_ytd_couple = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12)).scalar() or 0.0
    total_expenses_raw_ytd_couple = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12)).scalar() or 0.0
    savings_ytd_total_couple = total_income_ytd_couple - total_expenses_raw_ytd_couple
    months_for_avg_ytd = selected_month_for_details if ytd_label_year == today.year else 12
    average_monthly_expenses_ytd_couple = total_expenses_raw_ytd_couple / months_for_avg_ytd if months_for_avg_ytd > 0 else 0
    income_ytd_tomek = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, Transaction.person == PERSON_TOMEK, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12)).scalar() or 0.0
    income_ytd_tocka = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, Transaction.person == PERSON_TOCKA, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12)).scalar() or 0.0
    shared_expenses_total_ytd = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12), Transaction.category_id.in_(shared_category_ids)).scalar() or 0.0
    individual_share_of_shared_expenses_ytd = shared_expenses_total_ytd / 2
    private_expenses_ytd_tomek = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, Transaction.person == PERSON_TOMEK, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12), Transaction.category_id.notin_(shared_category_ids)).scalar() or 0.0
    total_expenses_ytd_tomek = private_expenses_ytd_tomek + individual_share_of_shared_expenses_ytd
    savings_ytd_tomek = income_ytd_tomek - total_expenses_ytd_tomek
    private_expenses_ytd_tocka = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, Transaction.person == PERSON_TOCKA, extract('year', Transaction.date) == ytd_label_year, extract('month', Transaction.date) <= (selected_month_for_details if ytd_label_year == today.year else 12), Transaction.category_id.notin_(shared_category_ids)).scalar() or 0.0
    total_expenses_ytd_tocka = private_expenses_ytd_tocka + individual_share_of_shared_expenses_ytd
    savings_ytd_tocka = income_ytd_tocka - total_expenses_ytd_tocka

    monthly_trends_data = {"labels": [], "incomes": [], "expenses": []}
    polskie_miesiace_abbr = ["", "sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
    year_for_trends_chart = selected_year_for_details
    last_month_for_trends_display = 0
    if year_for_trends_chart == today.year:
        last_month_for_trends_display = today.month -1 
        if last_month_for_trends_display == 0 : last_month_for_trends_display = 0
    elif year_for_trends_chart < today.year: last_month_for_trends_display = 12
    else: last_month_for_trends_display = 0
    for month_num in range(1, last_month_for_trends_display + 1):
        month_label = polskie_miesiace_abbr[month_num]
        monthly_trends_data["labels"].append(f"{month_label} '{str(year_for_trends_chart)[-2:]}")
        month_income_trend = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, extract('year', Transaction.date) == year_for_trends_chart, extract('month', Transaction.date) == month_num).scalar() or 0.0
        monthly_trends_data["incomes"].append(month_income_trend)
        month_expense_trend = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, extract('year', Transaction.date) == year_for_trends_chart, extract('month', Transaction.date) == month_num).scalar() or 0.0
        monthly_trends_data["expenses"].append(month_expense_trend)
    
    all_db_categories_for_colors = Category.query.order_by(Category.id).all() # Zmieniono nazwę zmiennej
    category_color_map = {}
    all_possible_chart_labels = set()
    for cat_obj in all_db_categories_for_colors: # Użyto nowej nazwy
        if cat_obj.name.lower() != "przychód ogólny": # Porównanie z małą literą
            all_possible_chart_labels.add(cat_obj.name)
            if cat_obj.is_shared_expense:
                all_possible_chart_labels.add(f"{cat_obj.name} (udział)")
    sorted_chart_labels = sorted(list(all_possible_chart_labels))
    for i, label_name in enumerate(sorted_chart_labels):
        category_color_map[label_name] = CATEGORY_COLORS_PALETTE[i % len(CATEGORY_COLORS_PALETTE)]

    return render_template('index.html',
                           transactions=transactions_selected_month,
                           income_tomek=income_tomek,
                           income_tocka=income_tocka,
                           total_income=total_income_selected_month,
                           private_expenses_tomek=private_expenses_tomek_selected_month,
                           tomek_share_of_shared_expenses=individual_share_of_shared_expenses_selected_month,
                           total_expenses_tomek=total_expenses_tomek_selected_month,
                           savings_tomek=savings_tomek_selected_month,
                           private_expenses_tocka=private_expenses_tocka_selected_month,
                           tocka_share_of_shared_expenses=individual_share_of_shared_expenses_selected_month,
                           total_expenses_tocka=total_expenses_tocka_selected_month,
                           savings_tocka=savings_tocka_selected_month,
                           total_expenses_raw=total_expenses_raw_selected_month,
                           savings_total_month=savings_total_selected_month,
                           year_to_date_label=ytd_label_year,
                           total_income_ytd_couple=total_income_ytd_couple,
                           total_expenses_raw_ytd_couple=total_expenses_raw_ytd_couple,
                           savings_ytd_total_couple=savings_ytd_total_couple,
                           average_monthly_expenses_ytd_couple=average_monthly_expenses_ytd_couple,
                           savings_ytd_tomek=savings_ytd_tomek,
                           savings_ytd_tocka=savings_ytd_tocka,
                           expenses_by_category_overall_dict=expenses_by_category_overall_dict,
                           expenses_tomek_by_category_dict=expenses_tomek_by_category_dict,
                           expenses_tocka_by_category_dict=expenses_tocka_by_category_dict,
                           selected_year=selected_year_for_details,
                           selected_month=selected_month_for_details,
                           years=years_for_dropdown,
                           months=months_list_for_dropdown,
                           current_month_name=current_month_name_for_details,
                           PERSON_TOMEK=PERSON_TOMEK,
                           PERSON_TOCKA=PERSON_TOCKA,
                           monthly_trends_data=monthly_trends_data,
                           category_color_map=category_color_map
                           )

@main_bp.route('/rok', methods=['GET'])
@login_required
def yearly_summary():
    today = date.today()
    
    years_with_data_query = db.session.query(extract('year', Transaction.date)).distinct().all()
    years_with_data = sorted([r[0] for r in years_with_data_query if r[0] is not None], reverse=True)
    
    if not years_with_data:
        years_with_data = [today.year]

    selected_year = request.args.get('year', default=years_with_data[0], type=int)

    # Obliczenia danych rocznych (Przychody, Wydatki, Oszczędności)
    total_income_ytd = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.is_income == True, 
        extract('year', Transaction.date) == selected_year
    ).scalar() or 0.0
    
    total_expenses_ytd = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.is_income == False, 
        extract('year', Transaction.date) == selected_year
    ).scalar() or 0.0
    
    total_savings_ytd = total_income_ytd - total_expenses_ytd

    # Dane dla wykresu
    expenses_ytd_q = db.session.query(
        Category.name, 
        func.sum(Transaction.amount)
    ).join(Category).filter(
        Transaction.is_income == False, 
        extract('year', Transaction.date) == selected_year
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all() # Sortowanie malejąco
    
    # ZMIANA: Przygotuj dane jako dwie osobne, posortowane listy
    expenses_ytd_chart_data = {
        "labels": [item[0] for item in expenses_ytd_q],
        "data": [item[1] for item in expenses_ytd_q]
    }

    return render_template('yearly_summary.html',
                           selected_year=selected_year,
                           years_with_data=years_with_data,
                           total_income_ytd=total_income_ytd,
                           total_expenses_ytd=total_expenses_ytd,
                           total_savings_ytd=total_savings_ytd,
                           # Przekazujemy nową, posortowaną strukturę danych
                           expenses_ytd_chart_data=expenses_ytd_chart_data
                           )

@main_bp.route('/api/get_yearly_summary', methods=['GET'])
@login_required
def api_get_yearly_summary():
    if not current_app.config.get('GEMINI_API_KEY'):
        return jsonify({'error': 'Klucz API Gemini nie jest skonfigurowany.'}), 500

    year = request.args.get('year', type=int)
    if not year:
        return jsonify({'error': 'Rok jest wymagany.'}), 400
    
    # 1. Oblicz dane ogólne
    total_income_ytd = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == True, extract('year', Transaction.date) == year).scalar() or 0.0
    total_expenses_ytd = db.session.query(func.sum(Transaction.amount)).filter(Transaction.is_income == False, extract('year', Transaction.date) == year).scalar() or 0.0
    total_savings_ytd = total_income_ytd - total_expenses_ytd
    savings_rate_ytd = (total_savings_ytd / total_income_ytd * 100) if total_income_ytd > 0 else 0
    num_months_with_data = db.session.query(func.count(func.distinct(extract('month', Transaction.date)))).filter(extract('year', Transaction.date) == year, Transaction.amount > 0).scalar() or 1
    avg_monthly_savings = total_savings_ytd / num_months_with_data

    # 2. Znajdź top 3 kategorie
    top_cats_q = db.session.query(Category.name, func.sum(Transaction.amount)).join(Category).filter(
        Transaction.is_income == False, extract('year', Transaction.date) == year
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(3).all()
    top_categories = {cat: amount for cat, amount in top_cats_q}

    # 3. Znajdź najlepszy i najgorszy miesiąc
    # POPRAWIONA SKŁADNIA ZAPYTANIA
    monthly_summary_q = db.session.query(
        extract('month', Transaction.date).label('month'),
        func.sum(db.case((Transaction.is_income == True, Transaction.amount), else_=0)).label('income'),
        func.sum(db.case((Transaction.is_income == False, Transaction.amount), else_=0)).label('expense')
    ).filter(
        extract('year', Transaction.date) == year
    ).group_by('month').all()
    
    monthly_savings = []
    # Wynik zapytania będzie teraz (miesiąc, suma_przychodów, suma_wydatków)
    for month_decimal, income, expense in monthly_summary_q:
        income = income or 0.0
        expense = expense or 0.0
        monthly_savings.append({"month": int(month_decimal), "savings": income - expense})
    
    best_month = max(monthly_savings, key=lambda x: x['savings']) if monthly_savings else {}
    worst_month = min(monthly_savings, key=lambda x: x['savings']) if monthly_savings else {}
    
    polskie_miesiace = ["", "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
    best_month_data = {"name": polskie_miesiace[best_month.get("month", 0)], "savings": best_month.get("savings", 0.0)}
    worst_month_data = {"name": polskie_miesiace[worst_month.get("month", 0)], "savings": worst_month.get("savings", 0.0)}

    # 4. Wywołaj Gemini
    summary_text = get_yearly_summary_gemini(
        selected_year=year,
        total_income_ytd=total_income_ytd,
        total_expenses_ytd=total_expenses_ytd,
        total_savings_ytd=total_savings_ytd,
        avg_monthly_savings=avg_monthly_savings,
        savings_rate_ytd=savings_rate_ytd,
        top_categories=top_categories,
        best_month=best_month_data,
        worst_month=worst_month_data
    )
    
    # Używamy jsonify, które automatycznie konwertuje na JSON. Zastąpienie \n na <br> jest zbędne, jeśli frontend sam to robi.
    # Ale dla pewności zostawmy, jeśli frontend oczekuje gotowego HTML.
    return jsonify({'summary_html': summary_text.replace('\n', '<br>')})

@main_bp.route('/api/get_gemini_summary', methods=['GET'])
@login_required
def api_get_gemini_summary():
    if not current_app.config.get('GEMINI_API_KEY'):
        return jsonify({'error': 'Klucz API Gemini nie jest skonfigurowany.', 'summary_html': '<p class="text-danger">Błąd: Klucz API Gemini nie jest skonfigurowany.</p>'}), 500

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'error': 'Rok i miesiąc są wymagane.', 'summary_html': '<p class="text-warning">Błąd: Nie podano roku lub miesiąca.</p>'}), 400

    month_income_total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.is_income == True,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).scalar() or 0.0
    month_expenses_total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.is_income == False,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).scalar() or 0.0
    month_savings = month_income_total - month_expenses_total
    expenses_by_cat_q = db.session.query(
        Category.name, func.sum(Transaction.amount)
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.is_income == False,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).group_by(Category.name).all()
    expenses_by_category_dict = {cat: amount for cat, amount in expenses_by_cat_q}
    months_list = [ (1, "Styczeń"), (2, "Luty"), (3, "Marzec"), (4, "Kwiecień"), (5, "Maj"), (6, "Czerwiec"), (7, "Lipiec"), (8, "Sierpień"), (9, "Wrzesień"), (10, "Październik"), (11, "Listopad"), (12, "Grudzień") ]
    month_name_pl = dict(months_list).get(month, "Nieznany Miesiąc")
    summary_text = get_monthly_summary_gemini(
        month_name=month_name_pl, year=year, income_total=month_income_total,
        expenses_total=month_expenses_total, savings=month_savings,
        expenses_by_category=expenses_by_category_dict
    )
    summary_html = summary_text.replace('\n', '<br>')
    return jsonify({'summary_html': summary_html})

@main_bp.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    categories_all = Category.query.order_by(Category.name).all()
    accounts_db = Account.query.order_by(Account.name).all()
    accounts_map = {acc.name: acc.id for acc in accounts_db}

    # Zaktualizowane emoji
    account_buttons_data = [
        {"name": ACCOUNT_NAME_TOMEK, "emoji": "🐻", "id": accounts_map.get(ACCOUNT_NAME_TOMEK)},
        {"name": ACCOUNT_NAME_TOCKA, "emoji": "🍑", "id": accounts_map.get(ACCOUNT_NAME_TOCKA)},
        {"name": ACCOUNT_NAME_WSPOLNE, "emoji": "🐻🍑", "id": accounts_map.get(ACCOUNT_NAME_WSPOLNE)},
    ]
    account_buttons_data = [acc for acc in account_buttons_data if acc["id"] is not None]

    person_buttons_data = [
        {"value": PERSON_TOMEK, "emoji": "🐻", "text": PERSON_TOMEK},
        {"value": PERSON_TOCKA, "emoji": "🍑", "text": PERSON_TOCKA},
    ]

    if request.method == 'POST':
        # ... (cała logika POST - BEZ ZMIAN w stosunku do ostatniej działającej wersji) ...
        # Skopiuj tutaj pełną logikę bloku if request.method == 'POST' z poprzedniej odpowiedzi
        transaction_type = request.form.get('transaction_type')
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')
        description_for_db = request.form.get('description', '').strip()
        category_id_str = request.form.get('category_id')
        new_category_name_from_form = request.form.get('new_category_name', '').strip().capitalize()
        selected_account_id = request.form.get('selected_account_id')
        final_person_for_transaction = None
        errors = []; amount = 0.0; transaction_date = None
        if not amount_str: errors.append("Kwota jest wymagana.")
        else:
            try: amount = float(amount_str)
            except ValueError: errors.append("Nieprawidłowy format kwoty.")
        if not date_str: errors.append("Data jest wymagana.")
        else:
            try: transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError: errors.append("Nieprawidłowy format daty.")
        account_id = None; selected_account_obj = None
        if selected_account_id and selected_account_id.isdigit():
            account_id = int(selected_account_id)
            selected_account_obj = Account.query.get(account_id)
            if not selected_account_obj: errors.append("Wybrane konto jest nieprawidłowe.")
        else: errors.append("Konto jest wymagane.")
        category_id = None
        if not errors:
            if transaction_type == 'expense':
                final_person_for_transaction = request.form.get('selected_expense_person')
                if selected_account_obj and selected_account_obj.name == ACCOUNT_NAME_WSPOLNE:
                    final_person_for_transaction = PERSON_WSPOLNE
                    if category_id_str and category_id_str.isdigit():
                        category_id = int(category_id_str)
                        chosen_cat_obj = Category.query.get(category_id)
                        if not chosen_cat_obj or not chosen_cat_obj.is_shared_expense: errors.append("Dla konta wspólnego wybierz kategorię wspólną.")
                    elif not category_id_str: errors.append("Wybierz kategorię dla wydatku z konta wspólnego.")
                else: 
                    if not final_person_for_transaction: errors.append("Określ, czyj to wydatek.")
                if category_id_str == 'new_category' and new_category_name_from_form:
                    existing_category = Category.query.filter(func.lower(Category.name) == func.lower(new_category_name_from_form)).first()
                    if existing_category: category_id = existing_category.id; flash(f"Kategoria '{new_category_name_from_form}' już istnieje.", "info")
                    else:
                        new_cat_obj = Category(name=new_category_name_from_form, is_shared_expense=False)
                        db.session.add(new_cat_obj)
                        try: db.session.flush(); category_id = new_cat_obj.id
                        except Exception as e: db.session.rollback(); errors.append(f"Błąd dodawania kategorii: {e}")
                elif category_id_str and category_id_str.isdigit(): category_id = int(category_id_str)
                if not category_id and transaction_type == 'expense' : errors.append("Kategoria jest wymagana dla wydatku.")
            elif transaction_type == 'income':
                description_for_db = request.form.get('description_income', '').strip()
                final_person_for_transaction = request.form.get('selected_income_person')
                if not final_person_for_transaction: errors.append("Określ, dla kogo jest przychód.")
                category_id = None
        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('add_transaction.html', categories=categories_all, account_buttons_data=account_buttons_data, person_buttons_data=person_buttons_data, today_date=date.today().strftime('%Y-%m-%d'), form_data=request.form, PERSON_TOMEK=PERSON_TOMEK, PERSON_TOCKA=PERSON_TOCKA, ACCOUNT_NAME_TOMEK=ACCOUNT_NAME_TOMEK, ACCOUNT_NAME_TOCKA=ACCOUNT_NAME_TOCKA, ACCOUNT_NAME_WSPOLNE=ACCOUNT_NAME_WSPOLNE)
        new_transaction_obj = Transaction(amount=amount, date=transaction_date, description=description_for_db, is_income=(transaction_type == 'income'), category_id=category_id, account_id=account_id, person=final_person_for_transaction)
        db.session.add(new_transaction_obj)
        try:
            db.session.commit()
            flash_message = f'{("Wydatek", "Przychód")[transaction_type == "income"]} "{description_for_db or "bez opisu"}" ({amount:.2f} PLN) dodany pomyślnie!'
            if category_id_str == 'new_category' and new_category_name_from_form and not errors: flash_message += f" Nowa kategoria '{new_category_name_from_form}' została utworzona."
            flash(flash_message, 'success')
            return redirect(url_for('main.add_transaction')) 
        except Exception as e:
            db.session.rollback(); flash(f'Błąd zapisywania: {e}', 'danger')
            return render_template('add_transaction.html', categories=categories_all, account_buttons_data=account_buttons_data, person_buttons_data=person_buttons_data, today_date=date.today().strftime('%Y-%m-%d'), form_data=request.form, PERSON_TOMEK=PERSON_TOMEK, PERSON_TOCKA=PERSON_TOCKA, ACCOUNT_NAME_TOMEK=ACCOUNT_NAME_TOMEK, ACCOUNT_NAME_TOCKA=ACCOUNT_NAME_TOCKA, ACCOUNT_NAME_WSPOLNE=ACCOUNT_NAME_WSPOLNE)

    return render_template('add_transaction.html',
                           categories=categories_all,
                           account_buttons_data=account_buttons_data,
                           person_buttons_data=person_buttons_data,
                           today_date=date.today().strftime('%Y-%m-%d'),
                           form_data={}, 
                           PERSON_TOMEK=PERSON_TOMEK,
                           PERSON_TOCKA=PERSON_TOCKA,
                           # Dodajemy nazwy kont do kontekstu, aby JS mógł ich używać
                           ACCOUNT_NAME_TOMEK=ACCOUNT_NAME_TOMEK,
                           ACCOUNT_NAME_TOCKA=ACCOUNT_NAME_TOCKA,
                           ACCOUNT_NAME_WSPOLNE=ACCOUNT_NAME_WSPOLNE
                           )

@main_bp.route('/transaction/delete/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    # Znajdź transakcję w głównej tabeli
    transaction_to_delete = Transaction.query.get(transaction_id)
    
    if transaction_to_delete:
        try:
            db.session.delete(transaction_to_delete)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Transakcja została usunięta.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Błąd bazy danych: {e}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Nie znaleziono transakcji o podanym ID.'}), 404

@main_bp.route('/api/suggest_category', methods=['POST'])
@login_required
def api_suggest_category():
    if not current_app.config.get('GEMINI_API_KEY'): return jsonify({'error': 'Gemini API key not configured'}), 500
    data = request.get_json(); description = data.get('description')
    if not description: return jsonify({'error': 'Opis jest wymagany do sugestii.'}), 400
    suggested_name, is_new_suggestion = suggest_category_gemini(description)
    if suggested_name and suggested_name != "Nieokreślona":
        if not is_new_suggestion: 
            category_obj = Category.query.filter(func.lower(Category.name) == func.lower(suggested_name)).first()
            if category_obj: return jsonify({'category_id': category_obj.id, 'category_name': category_obj.name, 'is_new_suggestion': False})
            else: return jsonify({'error': f"Błąd: sugerowana istniejaca kategoria '{suggested_name}' nie znaleziona."}), 500
        else: return jsonify({'category_id': None, 'category_name': suggested_name, 'is_new_suggestion': True})
    else: return jsonify({'error': 'Nie udało się zasugerować kategorii przez AI.'}), 500

@main_bp.route('/manage_categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if request.method == 'POST':
        category_name = request.form.get('category_name', '').strip().capitalize()
        is_shared = True if request.form.get('is_shared_expense') == 'on' else False
        if category_name:
            if Category.query.filter(func.lower(Category.name) == func.lower(category_name)).first(): flash('Kategoria o tej nazwie już istnieje.', 'warning')
            else:
                db.session.add(Category(name=category_name, is_shared_expense=is_shared)); db.session.commit(); flash(f'Kategoria "{category_name}" dodana.', 'success')
        else: flash('Nazwa kategorii nie może być pusta.', 'warning')
        return redirect(url_for('main.manage_categories'))
    return render_template('manage_categories.html', categories=Category.query.order_by(Category.name).all())

@main_bp.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category_to_delete = Category.query.get_or_404(category_id)
    if category_to_delete.transactions: flash(f'Kategoria "{category_to_delete.name}" jest używana i nie może być usunięta.', 'warning')
    else: db.session.delete(category_to_delete); db.session.commit(); flash(f'Kategoria "{category_to_delete.name}" usunięta.', 'success')
    return redirect(url_for('main.manage_categories'))

@main_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_transactions():
    if request.method == 'POST':
        # Logika uploadu pliku (opisana dalej)
        pass
    return render_template('import.html')

@main_bp.route('/import/start', methods=['POST'])
@login_required
def start_import():
    if 'csv_file' not in request.files:
        flash('Nie wybrano pliku.', 'danger')
        return redirect(url_for('main.add_transaction'))
    
    file = request.files['csv_file']
    bank_name = request.form.get('bank_name')

    if file.filename == '':
        flash('Nie wybrano pliku.', 'danger')
        return redirect(url_for('main.add_transaction'))

    if file and file.filename.endswith('.csv'):
        task_id = str(uuid.uuid4())
        
        # Zapisz plik tymczasowo (w produkcji lepiej użyć chmury, np. S3, ale na Render to zadziała)
        filepath = os.path.join(current_app.instance_path, f"{task_id}.csv")
        file.save(filepath)

        # Stwórz zadanie w bazie danych
        new_task = ImportTask(id=task_id, status='PENDING')
        db.session.add(new_task)
        db.session.commit()
        
        # Uruchom przetwarzanie w osobnym wątku
        thread = Thread(target=process_csv_task, args=(current_app._get_current_object(), task_id, filepath, bank_name))
        thread.daemon = True
        thread.start()

        # Przekieruj użytkownika na stronę śledzenia postępu
        return redirect(url_for('main.import_progress', task_id=task_id))

    flash('Nieprawidłowy format pliku. Proszę wybrać plik .csv.', 'warning')
    return redirect(url_for('main.add_transaction'))

@main_bp.route('/import/progress/<task_id>')
@login_required
def import_progress(task_id):
    task = ImportTask.query.get(task_id)
    if not task:
        return "Nie znaleziono zadania.", 404
    return render_template('import_progress.html', task=task)

@main_bp.route('/import/status/<task_id>')
@login_required
def import_status(task_id):
    task = ImportTask.query.get(task_id)
    if not task:
        return jsonify({'status': 'NOT_FOUND'}), 404
    
    return jsonify({
        'status': task.status,
        'progress': task.progress,
        'total_rows': task.total_rows,
        'summary': json.loads(task.summary) if task.summary else None,
        'error_message': task.error_message
    })

def process_csv_task(app, task_id, filepath, bank_name):
    with app.app_context():
        task = ImportTask.query.get(task_id)
        if not task: return

        try:
            task.status = 'PROCESSING'
            db.session.commit()

            df = pd.read_csv(filepath, encoding='cp1250', sep=',')
            df.columns = df.columns.str.strip()

            required_cols = {'Data transakcji', 'Dane transakcji', 'Tytuł', 'Kwota transakcji (waluta rachunku)'}
            if not required_cols.issubset(df.columns):
                raise ValueError(f"Brak wymaganych kolumn w pliku CSV. Wymagane: {required_cols}. Znaleziono: {set(df.columns)}")

            df.dropna(subset=['Data transakcji', 'Kwota transakcji (waluta rachunku)'], inplace=True)
            df = df[pd.to_datetime(df['Data transakcji'], format='%m/%d/%Y', errors='coerce').notna()]
            if df.empty: raise ValueError("Plik CSV nie zawiera prawidłowych wierszy z transakcjami.")
            
            df = df.rename(columns={
                'Data transakcji': 'date',
                'Kwota transakcji (waluta rachunku)': 'amount'
            })
            df['full_description'] = df['Dane transakcji'].fillna('') + ' ' + df['Tytuł'].fillna('')
            df['full_description'] = df['full_description'].str.strip()
            
            if df['amount'].dtype == 'object':
                 df['amount'] = df['amount'].str.replace(',', '.', regex=False).astype(float)
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y').dt.date

            task.total_rows = len(df)
            db.session.commit()
            
            all_categories = [c.name for c in Category.query.filter_by(is_shared_expense=False).all()]
            temp_transactions_to_add = []

            for index, row in df.iterrows():

                time.sleep(6.1)

                amount = row['amount']
                description = row['full_description']
                
                ai_input_description = f"Transakcja bankowa: {description}"
                suggested_category, _ = suggest_category_gemini(ai_input_description)
                
                temp_tx = TempTransaction(
                    task_id=task_id, raw_data=row.to_json(),
                    transaction_type='INCOME' if amount > 0 else 'EXPENSE',
                    amount=abs(amount), description=description, date=row['date'],
                    suggested_category_name=suggested_category,
                    status='PENDING_VERIFICATION' # Wszystkie trafiają do weryfikacji
                )
                temp_transactions_to_add.append(temp_tx)

                task.progress = len(temp_transactions_to_add)
                if len(temp_transactions_to_add) % 2 == 0: db.session.commit()
            
            db.session.bulk_save_objects(temp_transactions_to_add)
            task.status = 'VERIFICATION' # Zawsze przechodzimy do weryfikacji
            db.session.commit()

        except Exception as e:
            print(f"Błąd w zadaniu {task_id}: {e}")
            task.status = 'FAILED'; task.error_message = str(e)
            db.session.commit()
        finally:
            if os.path.exists(filepath): os.remove(filepath)

@main_bp.route('/import/verify/<task_id>', methods=['GET', 'POST'])
@login_required
def verify_import(task_id):
    task = ImportTask.query.get_or_404(task_id)
    
    if request.method == 'POST':
        form_data = request.form
        
        # Pobierz konto i osobę dla CAŁEGO importu
        account_id_for_import = form_data.get('import_account_id')
        person_for_import = form_data.get('import_person')

        if not account_id_for_import or not person_for_import:
            flash("Musisz wybrać konto i osobę dla całego importu.", "danger")
            # Przekieruj z powrotem, aby użytkownik mógł to naprawić
            return redirect(url_for('main.verify_import', task_id=task_id))

        transactions_to_finalize = TempTransaction.query.filter_by(task_id=task_id).all()
        newly_created_categories = {}
        new_transactions_to_add = []
        
        for tx in transactions_to_finalize:
            prefix = f'tx-{tx.id}-'
            category_choice = form_data.get(f'{prefix}category')
            
            final_category_id = None
            if category_choice == 'new_category':
                new_cat_name = form_data.get(f'{prefix}new_category_name', '').strip().capitalize()
                if new_cat_name:
                    category = Category.query.filter(func.lower(Category.name) == func.lower(new_cat_name)).first()
                    if not category:
                        category = Category(name=new_cat_name, is_shared_expense=False)
                        db.session.add(category)
                        db.session.flush()
                    final_category_id = category.id
            elif category_choice and category_choice.isdigit():
                final_category_id = int(category_choice)

            # Użyj danych z TempTransaction, ponieważ konto i osoba są już ustawione
            if tx.status == 'OK' and not final_category_id:
                category = Category.query.filter(func.lower(Category.name) == func.lower(tx.suggested_category_name)).first()
                if not category:
                    new_cat_name = tx.suggested_category_name
                    if "NOWA:" in new_cat_name.upper(): new_cat_name = new_cat_name.split(":", 1)[1].strip().capitalize()
                    category = Category(name=new_cat_name, is_shared_expense=False)
                    db.session.add(category)
                    db.session.flush()
                final_category_id = category.id

            if (tx.transaction_type == 'EXPENSE' and not final_category_id):
                continue # Pomiń wydatki bez kategorii

            new_trans = Transaction(
                amount=tx.amount, date=tx.date, description=tx.description,
                is_income=(tx.transaction_type == 'INCOME'),
                category_id=final_category_id,
                account_id=int(account_id_for_import), # Użyj wartości z góry formularza
                person=person_for_import              # Użyj wartości z góry formularza
            )
            new_transactions_to_add.append(new_trans)

        if new_transactions_to_add:
            db.session.add_all(new_transactions_to_add)
        
        task.status = 'COMPLETED'
        TempTransaction.query.filter_by(task_id=task_id).delete()
        db.session.commit()

        flash(f"Import zakończony! Dodano {len(new_transactions_to_add)} nowych transakcji.", "success")
        return redirect(url_for('main.index'))
    
    # --- LOGIKA GET ---
    
    all_transactions_for_task = TempTransaction.query.filter_by(task_id=task_id).order_by(TempTransaction.date).all()
    
    # Jeśli zadanie zostało przetworzone i nie ma nic do weryfikacji, przejdź do podsumowania/importu
    if not all_transactions_for_task and task.status == 'VERIFICATION':
         # Można by stworzyć osobną stronę podsumowania, na razie importujemy od razu
        return redirect(url_for('main.verify_import', task_id=task_id), code=307)
    
    categories = Category.query.order_by(Category.name).all()
    accounts = Account.query.all()

    for tx in all_transactions_for_task:
        tx.preselected_category_id = None
        tx.is_new_suggestion = False
        found_category = next((c for c in categories if c.name.lower() == tx.suggested_category_name.lower()), None)
        if found_category:
            tx.preselected_category_id = found_category.id
        elif tx.suggested_category_name not in ["Nieokreślona", "Inne"]:
             tx.is_new_suggestion = True

    return render_template('verify_import.html', 
                           task=task, 
                           transactions=all_transactions_for_task, 
                           categories=categories,
                           accounts=accounts,
                           PERSON_TOMEK=PERSON_TOMEK,
                           PERSON_TOCKA=PERSON_TOCKA
                           )

@main_bp.route('/import/delete_temp/<int:temp_tx_id>', methods=['DELETE'])
@login_required
def delete_temp_transaction(temp_tx_id):
    # Znajdź transakcję tymczasową w bazie
    tx_to_delete = TempTransaction.query.get(temp_tx_id)
    
    if tx_to_delete:
        try:
            db.session.delete(tx_to_delete)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Transakcja usunięta.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Błąd bazy danych: {e}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Nie znaleziono transakcji.'}), 404

@main_bp.route('/portfolio', methods=['GET'])
@login_required
def portfolio_index():
    portfolios = Portfolio.query.order_by(Portfolio.name).all()
    selected_portfolio_id = request.args.get('portfolio_id', type=int)
    selected_portfolio = None
    assets_list = []
    asset_categories = AssetCategory.query.order_by(AssetCategory.name).all()
    portfolio_summary_data = {}
    target_allocation_data = {}
    current_total_portfolio_value = 0 
    total_invested_amount = 0
    portfolio_snapshots_for_chart = {"labels": [], "values": []}
    portfolio_snapshots_list_for_table = []

    grand_total_all_portfolios_value = db.session.query(func.sum(Asset.current_value)).scalar() or 0.0

    if selected_portfolio_id:
        selected_portfolio = db.session.get(Portfolio, selected_portfolio_id)
        if selected_portfolio:
            assets_list = Asset.query.filter_by(portfolio_id=selected_portfolio.id).order_by(Asset.current_value.desc()).all()
            current_total_portfolio_value = 0 
            portfolio_summary_data = {} 
            for asset_item in assets_list:
                category_name = asset_item.asset_category_ref.name if asset_item.asset_category_ref else "Bez kategorii"
                portfolio_summary_data[category_name] = portfolio_summary_data.get(category_name, 0) + asset_item.current_value
                current_total_portfolio_value += asset_item.current_value
                if asset_item.invested_amount:
                    total_invested_amount += asset_item.invested_amount
            if selected_portfolio.target_allocation:
                try: target_allocation_data = json.loads(selected_portfolio.target_allocation)
                except json.JSONDecodeError: flash("Błąd w formacie modelowej alokacji.", "warning")
            
            all_snapshots_for_chart = PortfolioSnapshot.query.filter_by(portfolio_id=selected_portfolio.id).order_by(PortfolioSnapshot.timestamp.asc()).all()
            portfolio_snapshots_for_chart["labels"] = [] 
            portfolio_snapshots_for_chart["values"] = [] 
            for snapshot in all_snapshots_for_chart:
                timestamp_utc = snapshot.timestamp.replace(tzinfo=pytz.utc)
                timestamp_poland = timestamp_utc.astimezone(POLAND_TZ)
                portfolio_snapshots_for_chart["labels"].append(timestamp_poland.strftime("%Y-%m-%d %H:%M:%S")) 
                portfolio_snapshots_for_chart["values"].append(snapshot.total_value)
            portfolio_snapshots_list_for_table = PortfolioSnapshot.query.filter_by(portfolio_id=selected_portfolio.id).order_by(desc(PortfolioSnapshot.timestamp)).limit(10).all()
        else:
            if selected_portfolio_id: 
                flash(f"Nie znaleziono portfela o ID: {selected_portfolio_id}", "warning")

    profit_loss = current_total_portfolio_value - total_invested_amount
    profit_loss_percent = (profit_loss / total_invested_amount * 100) if total_invested_amount > 0 else 0

    # Oblicz zysk/stratę brutto (przed podatkiem)
    profit_loss_gross = current_total_portfolio_value - total_invested_amount
    profit_loss_gross_percent = (profit_loss_gross / total_invested_amount * 100) if total_invested_amount > 0 else 0

    # NOWA LOGIKA: Obliczanie podatku i zysku netto
    tax_rate = 0.19  # Stawka podatku Belki (19%)
    tax_to_pay = 0.0
    profit_loss_net = profit_loss_gross # Zysk netto domyślnie równy brutto

    if profit_loss_gross > 0:
        tax_to_pay = profit_loss_gross * tax_rate
        profit_loss_net = profit_loss_gross - tax_to_pay
    
    profit_loss_net_percent = (profit_loss_net / total_invested_amount * 100) if total_invested_amount > 0 else 0    

    return render_template('portfolio/index.html', 
                           portfolios=portfolios, 
                           selected_portfolio=selected_portfolio,
                           assets=assets_list, 
                           asset_categories=asset_categories,
                           portfolio_summary_data=portfolio_summary_data,
                           target_allocation_data=target_allocation_data,
                           total_portfolio_value=current_total_portfolio_value, 
                           grand_total_all_portfolios_value=grand_total_all_portfolios_value, 
                           portfolio_value_history_data=portfolio_snapshots_for_chart,
                           portfolio_snapshots_list=portfolio_snapshots_list_for_table,
                           total_invested_amount=total_invested_amount,
                           profit_loss_gross=profit_loss_gross,
                           profit_loss_gross_percent=profit_loss_gross_percent,
                           profit_loss=profit_loss,
                           profit_loss_percent=profit_loss_percent,
                           tax_to_pay=tax_to_pay,
                           profit_loss_net=profit_loss_net,
                           profit_loss_net_percent=profit_loss_net_percent,
                           ACCOUNT_NAME_TOMEK=ACCOUNT_NAME_TOMEK, 
                           ACCOUNT_NAME_TOCKA=ACCOUNT_NAME_TOCKA,
                           ACCOUNT_NAME_WSPOLNE=ACCOUNT_NAME_WSPOLNE,
                           PERSON_TOMEK=PERSON_TOMEK,
                           PERSON_TOCKA=PERSON_TOCKA
                           )

@main_bp.route('/portfolio/add', methods=['GET', 'POST'])
@login_required
def add_portfolio():
    # ... (kod funkcji bez zmian) ...
    asset_categories = AssetCategory.query.order_by(AssetCategory.name).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        target_alloc = {}; total_percentage = 0; valid_allocation = True
        for category in asset_categories:
            percentage_str = request.form.get(f'alloc_{category.id}')
            if percentage_str and percentage_str.strip() != "":
                try:
                    percentage = float(percentage_str)
                    if not (0 <= percentage <= 100): flash(f"Procent dla {category.name} musi być między 0-100.", "danger"); valid_allocation = False; break
                    target_alloc[category.name] = percentage; total_percentage += percentage
                except ValueError: flash(f"Nieprawidłowa wartość % dla {category.name}.", "danger"); valid_allocation = False; break
        if valid_allocation and target_alloc and abs(total_percentage - 100.0) > 0.01 : flash(f"Suma % alokacji musi być 100%, jest {total_percentage:.2f}%.", "warning"); valid_allocation = False
        if not name: flash('Nazwa portfela jest wymagana.', 'danger')
        elif Portfolio.query.filter_by(name=name).first(): flash('Portfel o tej nazwie już istnieje.', 'warning')
        elif not valid_allocation and target_alloc: pass
        else:
            target_allocation_json = json.dumps(target_alloc) if target_alloc else None
            new_portfolio = Portfolio(name=name, description=description, target_allocation=target_allocation_json)
            db.session.add(new_portfolio); db.session.commit()
            flash(f'Portfel "{name}" dodany.', 'success')
            return redirect(url_for('main.portfolio_index', portfolio_id=new_portfolio.id))
    return render_template('portfolio/add_portfolio.html', asset_categories=asset_categories)

@main_bp.route('/portfolio/<int:portfolio_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_portfolio(portfolio_id):
    # ... (kod funkcji bez zmian) ...
    portfolio_to_edit = Portfolio.query.get_or_404(portfolio_id)
    asset_categories = AssetCategory.query.order_by(AssetCategory.name).all()
    current_allocation = {}
    if portfolio_to_edit.target_allocation:
        try: current_allocation = json.loads(portfolio_to_edit.target_allocation)
        except json.JSONDecodeError: flash("Błąd odczytu alokacji.", "warning")

    if request.method == 'POST':
        portfolio_to_edit.name = request.form.get('name', portfolio_to_edit.name).strip()
        portfolio_to_edit.description = request.form.get('description', portfolio_to_edit.description).strip()
        target_alloc = {}; total_percentage = 0; valid_allocation = True
        for category in asset_categories:
            percentage_str = request.form.get(f'alloc_{category.id}')
            if percentage_str and percentage_str.strip() != "":
                try:
                    percentage = float(percentage_str)
                    if not (0 <= percentage <= 100): flash(f"% dla {category.name} musi być 0-100.", "danger"); valid_allocation = False; break
                    target_alloc[category.name] = percentage; total_percentage += percentage
                except ValueError: flash(f"Błędna wartość % dla {category.name}.", "danger"); valid_allocation = False; break
        if valid_allocation and target_alloc and abs(total_percentage - 100.0) > 0.01: flash(f"Suma % musi być 100%, jest {total_percentage:.2f}%.", "warning"); valid_allocation = False
        if not portfolio_to_edit.name: flash('Nazwa portfela jest wymagana.', 'danger')
        elif not valid_allocation and target_alloc: pass
        else:
            portfolio_to_edit.target_allocation = json.dumps(target_alloc) if target_alloc else None
            try:
                db.session.commit(); flash(f'Portfel "{portfolio_to_edit.name}" zaktualizowany.', 'success')
                return redirect(url_for('main.portfolio_index', portfolio_id=portfolio_to_edit.id))
            except Exception as e: db.session.rollback(); flash(f'Błąd aktualizacji: {e}', 'danger')
        current_allocation = target_alloc 
    return render_template('portfolio/edit_portfolio.html', portfolio=portfolio_to_edit, asset_categories=asset_categories, current_allocation=current_allocation)

@main_bp.route('/portfolio/<int:portfolio_id>/add_asset', methods=['POST'])
@login_required
def add_asset_to_portfolio(portfolio_id):
    # ... (kod funkcji bez zmian) ...
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    if request.method == 'POST':
        name = request.form.get('asset_name', '').strip()
        asset_category_id = request.form.get('asset_category_id', type=int)
        current_value_str = request.form.get('current_value')
        invested_amount = request.form.get('invested_amount')
        quantity_str = request.form.get('quantity')
        currency = request.form.get('currency', 'PLN').strip().upper()
        ticker = request.form.get('ticker', '').strip().upper() or None
        errors = []
        if not name: errors.append("Nazwa aktywa jest wymagana.")
        if not asset_category_id: errors.append("Kategoria aktywa jest wymagana.")
        current_value = 0.0
        if not current_value_str : errors.append("Aktualna wartość jest wymagana.")
        else:
            try: current_value = float(current_value_str)
            except ValueError: errors.append("Nieprawidłowy format wartości.")
            if current_value < 0 : errors.append("Wartość nie może być ujemna.")
        quantity = None
        if quantity_str and quantity_str.strip() != "":
            try: quantity = float(quantity_str)
            except ValueError: errors.append("Nieprawidłowy format ilości.")
        if errors:
            for error in errors: flash(error, 'danger')
        else:
            new_asset = Asset(
                name=name, 
                ticker=ticker, 
                current_value=current_value,
                invested_amount=float(invested_amount) if invested_amount else current_value,
                quantity=quantity, 
                currency=currency, 
                portfolio_id=portfolio.id, 
                asset_category_id=asset_category_id)
            db.session.add(new_asset)
            try:
                db.session.commit()
                history_entry = AssetValueHistory(asset_id=new_asset.id, value=new_asset.current_value, date=date.today())
                db.session.add(history_entry); db.session.commit()
                flash(f'Aktywo "{name}" dodane.', 'success')
            except Exception as e: db.session.rollback(); flash(f'Błąd dodawania aktywa: {e}', 'danger')
        return redirect(url_for('main.portfolio_index', portfolio_id=portfolio.id)) 
    return redirect(url_for('main.portfolio_index'))

@main_bp.route('/portfolio/asset/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    # ... (kod funkcji bez zmian, ale upewnij się, że przekazuje asset_value_history_entries) ...
    asset_to_edit = Asset.query.get_or_404(asset_id)
    portfolio_id_for_redirect = asset_to_edit.portfolio_id 
    asset_categories = AssetCategory.query.order_by(AssetCategory.name).all()
    asset_value_history_entries = asset_to_edit.value_history.order_by(desc(AssetValueHistory.date)).limit(10).all() # Ważne dla szablonu
    if request.method == 'POST':
        original_value = asset_to_edit.current_value
        invested_amount_str = request.form.get('invested_amount')
        asset_to_edit.name = request.form.get('asset_name', asset_to_edit.name).strip()
        asset_to_edit.asset_category_id = request.form.get('asset_category_id', asset_to_edit.asset_category_id, type=int)
        current_value_str = request.form.get('current_value')
        quantity_str = request.form.get('quantity')
        asset_to_edit.currency = request.form.get('currency', asset_to_edit.currency).strip().upper()
        asset_to_edit.ticker = request.form.get('ticker', asset_to_edit.ticker).strip().upper() or None
        errors = []
        if not asset_to_edit.name: errors.append("Nazwa aktywa jest wymagana.")
        new_current_value = asset_to_edit.current_value 
        if not current_value_str: errors.append("Aktualna wartość jest wymagana.")
        else:
            try: new_current_value = float(current_value_str)
            except ValueError: errors.append("Nieprawidłowy format wartości.")
            if new_current_value < 0: errors.append("Wartość nie może być ujemna.")
        new_quantity = asset_to_edit.quantity
        if quantity_str and quantity_str.strip() != "":
            try: new_quantity = float(quantity_str)
            except ValueError: errors.append("Nieprawidłowy format ilości.")
        elif not quantity_str or quantity_str.strip() == "": new_quantity = None
        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('portfolio/edit_asset.html', asset=asset_to_edit, asset_categories=asset_categories, asset_value_history_entries=asset_value_history_entries, form_data=request.form)
        else:
            asset_to_edit.current_value = new_current_value
    
            if invested_amount_str and invested_amount_str.strip() != "":
                try:
                    asset_to_edit.invested_amount = float(invested_amount_str)
                except ValueError:
                    errors.append("Nieprawidłowy format kwoty zainwestowanej.")
            else:
                # Jeśli pole jest puste, ustaw null lub wartość domyślną
                asset_to_edit.invested_amount = None # Ustawiamy na None (NULL w bazie)

            asset_to_edit.quantity = new_quantity
            asset_to_edit.last_updated = datetime.utcnow()
            if new_current_value != original_value:
                history_entry = AssetValueHistory(asset_id=asset_to_edit.id, value=asset_to_edit.current_value, date=date.today())
                db.session.add(history_entry)
            try:
                db.session.commit(); flash(f'Aktywo "{asset_to_edit.name}" zaktualizowane.', 'success')
                return redirect(url_for('main.portfolio_index', portfolio_id=portfolio_id_for_redirect))
            except Exception as e:
                db.session.rollback(); flash(f'Błąd aktualizacji: {e}', 'danger')
                return render_template('portfolio/edit_asset.html', asset=asset_to_edit, asset_categories=asset_categories, asset_value_history_entries=asset_value_history_entries, form_data=request.form)
    return render_template('portfolio/edit_asset.html', asset=asset_to_edit, asset_categories=asset_categories, asset_value_history_entries=asset_value_history_entries, form_data=None)

@main_bp.route('/portfolio/asset/<int:asset_id>/delete', methods=['POST'])
@login_required
def delete_asset(asset_id):
    # ... (kod funkcji bez zmian) ...
    asset_to_delete = Asset.query.get_or_404(asset_id)
    portfolio_id_redirect = asset_to_delete.portfolio_id
    asset_name = asset_to_delete.name
    db.session.delete(asset_to_delete)
    try:
        db.session.commit(); flash(f'Aktywo "{asset_name}" usunięte.', 'success')
    except Exception as e: db.session.rollback(); flash(f'Błąd usuwania: {e}', 'danger')
    return redirect(url_for('main.portfolio_index', portfolio_id=portfolio_id_redirect))

@main_bp.route('/portfolio/<int:portfolio_id>/add_snapshot', methods=['POST'])
@login_required
def add_portfolio_snapshot(portfolio_id):
    # ... (kod funkcji bez zmian) ...
    portfolio = db.session.get(Portfolio, portfolio_id) 
    if not portfolio:
        flash("Nie znaleziono portfela.", "danger")
        return redirect(url_for('main.portfolio_index'))
    current_total_value = 0
    assets_in_portfolio = Asset.query.filter_by(portfolio_id=portfolio.id).all()
    for asset_item in assets_in_portfolio:
        current_total_value += asset_item.current_value
    snapshot_currency = "PLN"
    new_snapshot = PortfolioSnapshot(portfolio_id=portfolio.id, total_value=current_total_value, currency=snapshot_currency, timestamp=datetime.utcnow())
    db.session.add(new_snapshot)
    try:
        db.session.commit()
        timestamp_poland = new_snapshot.timestamp.replace(tzinfo=pytz.utc).astimezone(POLAND_TZ)
        flash(f'Snapshot wartości portfela "{portfolio.name}" ({current_total_value:.2f} {snapshot_currency}) został dodany o {timestamp_poland.strftime("%Y-%m-%d %H:%M:%S")}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Wystąpił błąd podczas dodawania snapshotu: {e}', 'danger')
    return redirect(url_for('main.portfolio_index', portfolio_id=portfolio.id))

@main_bp.route('/portfolio/snapshot/<int:snapshot_id>/delete', methods=['POST'])
@login_required
def delete_portfolio_snapshot(snapshot_id):
    snapshot_to_delete = PortfolioSnapshot.query.get_or_404(snapshot_id) # Użyj PortfolioSnapshot
    portfolio_id_redirect = snapshot_to_delete.portfolio_id
    
    # Zapisz informacje o snapshocie przed usunięciem dla komunikatu flash
    snapshot_timestamp_utc = snapshot_to_delete.timestamp.replace(tzinfo=pytz.utc)
    snapshot_timestamp_poland = snapshot_timestamp_utc.astimezone(POLAND_TZ)
    entry_date_str = snapshot_timestamp_poland.strftime("%Y-%m-%d %H:%M:%S")

    db.session.delete(snapshot_to_delete)
    try:
        db.session.commit()
        flash(f'Snapshot wartości portfela z dnia {entry_date_str} został usunięty.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Wystąpił błąd podczas usuwania snapshotu: {e}', 'danger')
        
    return redirect(url_for('main.portfolio_index', portfolio_id=portfolio_id_redirect))

@main_bp.route('/portfolio/asset_value_history/<int:history_id>/delete', methods=['POST'])
@login_required
def delete_asset_value_history_entry(history_id):
    # Ta funkcja jest teraz dla indywidualnej historii aktywa, jeśli ją zachowujesz.
    # Jeśli historia jest tylko na poziomie portfela (PortfolioSnapshot), ta funkcja może nie być potrzebna
    # lub powinna odnosić się do usuwania snapshotu portfela.
    # W poprzedniej odpowiedzi, ta trasa była używana w `edit_asset.html`.
    # Teraz `delete_portfolio_snapshot` obsługuje usuwanie z listy na `portfolio_index.html`.
    # Upewnij się, do czego ta trasa ma służyć.
    history_entry = AssetValueHistory.query.get_or_404(history_id)
    asset_id_for_redirect = history_entry.asset_id 
    asset = Asset.query.get(asset_id_for_redirect) # Może być None, jeśli asset został usunięty
    portfolio_id_for_redirect = asset.portfolio_id if asset else None

    entry_date_str = history_entry.date.strftime("%Y-%m-%d")

    db.session.delete(history_entry)
    try:
        db.session.commit()
        flash(f'Wpis historii wartości aktywa z dnia {entry_date_str} został usunięty.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Wystąpił błąd podczas usuwania wpisu historii aktywa: {e}', 'danger')
    
    if asset: # Jeśli aktywo nadal istnieje, wróć do jego edycji
        return redirect(url_for('main.edit_asset', asset_id=asset.id))
    elif portfolio_id_for_redirect: # Jeśli nie, ale znamy portfel
         return redirect(url_for('main.portfolio_index', portfolio_id=portfolio_id_for_redirect))
    return redirect(url_for('main.portfolio_index')) # Domyślnie

@main_bp.route('/portfolio/manage_asset_categories', methods=['GET', 'POST'])
@login_required
def manage_asset_categories():
    if request.method == 'POST':
        name = request.form.get('category_name', '').strip().capitalize()
        if not name: flash("Nazwa kategorii aktywów nie może być pusta.", 'warning')
        elif AssetCategory.query.filter(func.lower(AssetCategory.name) == func.lower(name)).first(): flash("Kategoria o tej nazwie już istnieje.", 'warning')
        else:
            db.session.add(AssetCategory(name=name)); db.session.commit(); flash(f"Kategoria '{name}' dodana.", 'success')
        return redirect(url_for('main.manage_asset_categories'))
    return render_template('portfolio/manage_asset_categories.html', asset_categories=AssetCategory.query.order_by(AssetCategory.name).all())