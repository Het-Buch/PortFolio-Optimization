# 📈 Agentic AI for Smart Portfolio Management
### *A Fusion of ML and Nature-Inspired Algorithms*

> An intelligent, end-to-end portfolio optimization system that combines **machine learning**, **nature-inspired metaheuristic algorithms**, and **Agentic AI** to deliver real-time, personalized investment recommendations — built by Heli Hathi & Het Buch. The system fetches 15 years of historical stock data from Yahoo Finance (Nifty50 & Sensex), engineers 25 technical indicators via TA-Lib, trains and compares 25 ML regression models using PyCaret, optimizes portfolio weights using PSO, GWO, and Bat Algorithm, analyses market sentiment from financial news, and uses two LangChain + Groq-powered autonomous agents — a Market Research Agent and a Portfolio Optimization Agent — to generate detailed, explainable rebalancing reports; all of this is wrapped in a Streamlit + Flask web-app with Firebase backend for secure user authentication, portfolio storage, and a manager dashboard.

---

## 🗂️ Table of Contents

- [✨ Features](#-features)
- [🧩 Modules](#-modules)
- [🛠️ Tech Stack](#%EF%B8%8F-tech-stack)
- [📁 Folder Structure](#-folder-structure)
- [⚙️ Setup & Installation](#%EF%B8%8F-setup--installation)
- [🔥 Firebase Setup](#-firebase-setup)
- [▶️ Running the App](#%EF%B8%8F-running-the-app)
- [👥 Team](#-team)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 **Real-Time Data** | Fetches live & historical stock data via yFinance |
| 🤖 **ML Price Prediction** | Compares 25 regression models; selects best via PyCaret |
| 🧠 **Agentic AI** | Two autonomous agents for market research & portfolio optimization |
| 🐺 **Nature-Inspired Optimization** | PSO, GWO, Bat Algorithm — individual, hybrid & ensemble |
| 📰 **Sentiment Analysis** | Scrapes Moneycontrol & Livemint; scores with VADER NLP |
| 📋 **Detailed Reports** | Explainable rebalancing reports with risk/return justifications |
| 🔐 **Secure Auth** | Firebase Authentication with role-based access (Investor / Manager) |
| 🌐 **Web App** | Interactive Streamlit + Flask app, deployed on Streamlit Cloud |

---

## 🧩 Modules

### 1. 📥 Data Collection
Fetches **15 years** of OHLCV stock data (Jan 2010 → present) for **Nifty50 + Sensex** companies using `yFinance`. Financial news is scraped in real-time from Moneycontrol and Livemint via `BeautifulSoup`.

### 2. ⚙️ Data Preprocessing & Feature Engineering
Raw OHLCV data is enriched with **25 technical indicators** using `TA-Lib`:
- Moving averages (SMA 10/30, EMA 10/30)
- Momentum indicators (RSI, MACD)
- Volatility bands (Bollinger Bands)
- Lag features (Close_lag_1 to Close_lag_5)
- Cyclical time encodings (sin/cos of day & month)
- Stationarity checks via ADF Test

### 3. 📈 Stock Price Prediction (ML Models)
`PyCaret` is used to simultaneously train and rank **25 ML regression algorithms**. Top performers (XGBoost, LightGBM, Gradient Boosting, Ridge Regression) are rebuilt with `Scikit-learn` and fine-tuned using `Optuna`. **Ridge Regression** achieved the lowest prediction error post-tuning.

### 4. 🌿 Portfolio Optimization (Nature-Inspired)
Three nature-inspired algorithms optimize portfolio weight allocation by maximizing the **Sharpe Ratio** while minimizing risk:
- **PSO** — Particle Swarm Optimization *(best balanced results)*
- **GWO** — Grey Wolf Optimization
- **BAT** — Bat Algorithm
- Hybrid & Ensemble combinations (PSO→GWO, GWO→BAT, PSO+GWO, All Ensemble)

### 5. 🤖 Agentic AI
Two intelligent agents powered by **LangChain + Groq**:
- **Market Research Agent** — Continuously analyses real-time market conditions, news, sector trends, and risk factors
- **Portfolio Optimization Agent** — Validates weight changes, explains rebalancing logic, and generates structured reports

### 6. 💬 Sentiment Analysis
Financial news headlines are scored as **Positive / Negative / Neutral** using the `VADER` sentiment model. Sentiment scores are fed into the optimization pipeline to bias allocation decisions.

### 7. 🗄️ Database (Firebase)
Firebase Realtime Database stores three collections — `users`, `stocks`, and `purchases` — in JSON format. Firebase Authentication handles secure login, registration, and role-based access control.

### 8. 🌐 Web Application (Streamlit + Flask)
A fully interactive multi-page app covering:
- Landing Page → Login / Register / Manager Login
- User Home → Portfolio Overview, Buy/Sell/Edit Stocks
- Optimization Page → Run algorithms, view pie charts & performance metrics
- Report Generation → Detailed AI-generated portfolio analysis
- Manager Dashboard → User management, stock listing, analytics

---

## 🛠️ Tech Stack

### 🐍 Core Language
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)

### 🤖 Machine Learning & Data
| Library | Purpose |
|---|---|
| `PyCaret` | Auto-training & comparing 25 ML models |
| `Scikit-learn` | Model rebuilding, preprocessing, evaluation |
| `XGBoost` / `LightGBM` | Gradient boosting regressors |
| `Optuna` | Hyperparameter tuning |
| `Pandas` / `NumPy` | Data manipulation & numerical computing |
| `yFinance` | Real-time & historical stock data |
| `TA-Lib` / `ta` | Technical indicator generation |
| `Statsmodels` | ADF stationarity testing |

### 🌿 Optimization & AI
| Library | Purpose |
|---|---|
| `SciPy` | Mathematical optimization utilities |
| `LangChain` | Agentic AI orchestration & LLM chaining |
| `Groq` | High-speed LLM inference for agents |
| `duckduckgo-search` | Web search tool for agents |

### 💬 NLP & Sentiment
| Library | Purpose |
|---|---|
| `vaderSentiment` | Rule-based sentiment scoring |
| `BeautifulSoup4` | News scraping from financial websites |
| `Requests` | HTTP requests for data fetching |

### 🌐 Web & Backend
| Library | Purpose |
|---|---|
| `Streamlit` | Interactive frontend web application |
| `Flask` | Lightweight backend API server |
| `firebase-admin` | Firebase database & authentication |

### 📊 Visualization
| Library | Purpose |
|---|---|
| `Matplotlib` | Static performance charts |
| `Plotly` *(optional)* | Interactive portfolio visualizations |

---

## 📁 Folder Structure

```
portfolio-optimization/
│
├── main.py                          # 🚀 App entry point
├── requirements.txt                 # 📦 Python dependencies
├── portfolio-optimization-...-firebase-adminsdk-....json  # 🔑 Firebase credentials
│
├── data/
│   └── india_pincodes.csv           # 📍 Pincode lookup for registration
│
├── database/                        # 🗄️ Firebase CRUD operations
│   ├── connection.py                # Firebase connection setup
│   ├── curd.py                      # Create / Read / Update / Delete
│   ├── login_user.py                # User login logic
│   ├── manager_login.py             # Manager login logic
│   ├── manager_operation.py         # Manager-specific DB operations
│   └── register_user.py             # User registration logic
│
├── frontend/                        # 🎨 Streamlit UI pages
│   ├── landing.py                   # Landing / welcome page
│   ├── login.py                     # User login page
│   ├── register.py                  # User registration page
│   ├── home.py                      # User home / portfolio overview
│   ├── buy.py                       # Buy stocks page
│   ├── edit_stock.py                # Edit user holdings
│   ├── optimize.py                  # Portfolio optimization page
│   ├── profile.py                   # User profile page
│   ├── manager_login.py             # Manager login page
│   ├── manger_home.py               # Manager dashboard
│   ├── add_stock.py                 # Add new stock (manager)
│   ├── show_stock.py                # View all stocks (manager)
│   ├── show_users.py                # View all users (manager)
│   ├── edit_stock_manager.py        # Edit stock details (manager)
│   └── cleaned_top_companies.csv    # Company list for dropdowns
│
├── ml/                              # 🤖 ML, AI & optimization logic
│   ├── train.py                     # Model training pipeline (PyCaret + Scikit-learn)
│   ├── model.py                     # Model loading & prediction
│   ├── optimization.py              # PSO, GWO, BAT algorithms
│   ├── agentic.py                   # LangChain agent definitions
│   ├── market_agents.py             # Market Research Agent logic
│   ├── sentiment.py                 # VADER sentiment scoring
│   ├── news.py                      # News scraping via BeautifulSoup
│   ├── visualization.py             # Charts & performance plots
│   ├── report.md                    # Sample generated report
│   └── .env                         # 🔐 API keys (Groq, etc.)
│
├── services/                        # 🔧 Shared service utilities
│   ├── cache.py                     # Data caching helpers
│   └── stock_services.py            # Stock price fetching service
│
└── utils/
    └── navigation.py                # Streamlit page navigation helper
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python **3.10+**
- A Firebase project (see [Firebase Setup](#-firebase-setup) below)
- A **Groq API key** (free at [console.groq.com](https://console.groq.com))

### Step 1 — Clone the Repository
```bash
git clone https://github.com/your-username/portfolio-optimization.git
cd portfolio-optimization
```

### Step 2 — Create a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

> ⚠️ **TA-Lib Note:** TA-Lib requires a compiled C library. Install it separately before `pip install ta-lib`:
> - **Windows:** Download the `.whl` from [here](https://github.com/cgohlke/talib-build/releases) and run `pip install TA_Lib-*.whl`
> - **macOS:** `brew install ta-lib`
> - **Linux:** `sudo apt-get install libta-lib-dev`

### Step 4 — Configure Environment Variables

Create a `.env` file inside the `ml/` folder:
```env
GROQ_API_KEY=your_groq_api_key_here
```

Create a `.env` file inside the `database/` folder (if needed for any additional secrets):
```env
# Add any additional keys here
```

### Step 5 — Add Firebase Credentials
Place your Firebase Admin SDK JSON file in the project root and ensure the filename matches the reference in `database/connection.py`. See [Firebase Setup](#-firebase-setup) for how to generate this file.

---

## 🔥 Firebase Setup

### Step 1 — Create a Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add project"** → enter a project name → click **Continue**
3. Disable Google Analytics (optional) → click **Create Project**

### Step 2 — Enable Realtime Database
1. In the left sidebar, click **Build → Realtime Database**
2. Click **"Create Database"**
3. Choose your region (e.g., `us-central1`)
4. Start in **Test mode** for development (you can add rules later)

### Step 3 — Create Collections Structure
Your database should have three top-level nodes:
```
/
├── users/
├── stocks/
└── purchases/
```
These are created automatically when the app first writes data.

### Step 4 — Enable Authentication
1. In the left sidebar, click **Build → Authentication**
2. Click **"Get Started"**
3. Under **Sign-in method**, enable **Email/Password**

### Step 5 — Generate Admin SDK Credentials
1. Click the ⚙️ **gear icon** → **Project Settings**
2. Go to the **Service Accounts** tab
3. Click **"Generate new private key"** → **Generate Key**
4. A JSON file will download — rename it and place it in the project root:
   ```
   portfolio-optimization-<project-id>-firebase-adminsdk-<key>.json
   ```

### Step 6 — Update `connection.py`
Open `database/connection.py` and ensure the credential path matches your file:
```python
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("portfolio-optimization-<your-key>.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://<your-project-id>-default-rtdb.firebaseio.com/'
})
```

### Step 7 — Set Database Rules (Production)
In Firebase Console → Realtime Database → **Rules**, replace with:
```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    },
    "stocks": {
      ".read": "auth != null",
      ".write": "auth != null"
    },
    "purchases": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    }
  }
}
```

---

## ▶️ Running the App

```bash
# Make sure your virtual environment is activated
streamlit run main.py
```

The app will open at **http://localhost:8501**

### Default Access
| Role | How to Access |
|---|---|
| 👤 **New User** | Click "Register" on the landing page |
| 🔑 **Existing User** | Click "Login" with your credentials |
| 🛠️ **Manager** | Click "Manager" and use manager credentials |

---

## 👥 Team

| Name | Enrollment No. | Contributions |
|---|---|---|
| **Heli Hathi** | 92100103341 | Conceptualization, diagrams, database design, optimization algorithms, Agentic AI & sentiment analysis, backend |
| **Het Buch** | 92100103196 | Literature review, methodology, wireframes, frontend web-app, backend |

**Guide:** Prof. Ravikumar R. Natarajan, Assistant Professor, Dept. of Computer Engineering  
**Institution:** Marwadi University, Rajkot — Faculty of Technology (2024–25)

---

> ⚠️ **Disclaimer:** This system provides AI-generated investment insights for educational purposes only. It does not guarantee financial returns and does not execute trades automatically. Always consult a certified financial advisor before making investment decisions.
