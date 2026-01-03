# 🐻🍑 Finance Monitor

A comprehensive personal finance and investment tracking application built with **Flask**, designed for joint and individual financial monitoring, featuring **AI-powered category suggestion** and a robust **portfolio management system**.

This project provides a detailed overview of joint and private finances for a couple ("Tomek" and "Toćka"), calculating savings, shared expenses, and investment performance (including post-tax profits).

---

## ✨ Key Features

* **Dual Tracking Logic:** Detailed calculation of individual vs. shared expenses and savings tailored for two people.
* **AI-Powered Categorization:** Integrates with the **Gemini API** to suggest appropriate categories for new transactions based on their descriptions.
* **Financial Summaries (AI-Generated):** Uses the Gemini API to generate natural language summaries and insights into monthly and yearly financial performance.
* **Advanced CSV Import:** A multi-step import feature using **Pandas** to process bank statements, allowing users to verify AI-suggested categories before committing transactions to the database.
* **Investment Portfolio Management:**
    * Track various assets and portfolios.
    * Calculate **Profit/Loss (P&L)**, including the effect of the Polish Capital Gains Tax (Podatek Belki – 19%).
    * Monitor target vs. current asset allocation.
* **Web Stack:** Built using Python **Flask** and **SQLAlchemy** (ORM).
* **Containerized Deployment:** Ready-to-go setup using **Docker** and **Gunicorn**.

---

## 🚀 Quick Start (Dockerized)

The easiest way to get the application running is by using Docker Compose.

### 1. Prerequisites

* Docker and Docker Compose installed.
* A `.env` file created in the root directory (see Step 2).

### 2. Configuration (`.env` file)

You must create a file named **`.env`** in the project root directory (the same location as `docker-compose.yml`) and populate it with the required environment variables.

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask application secret key. | `your_long_random_secret_key` |
| `DATABASE_URL` | SQLAlchemy connection string (e.g., for PostgreSQL or SQLite). | `sqlite:///instance/finance.db` |
| `GEMINI_API_KEY` | **Crucial for AI features!** Get this from Google AI Studio. | `AIzaSy...your...key...12345` |
| `APP_USER` | Admin username for Flask-Login. | `tomek` |
| `APP_PASSWORD` | Admin password for Flask-Login. | `securepassword123` |

### 3. Build and Run

Run the following command in the project root directory:

```bash
docker-compose up --build