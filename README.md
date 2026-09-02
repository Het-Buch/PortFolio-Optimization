# 📈 Agentic AI for Smart Portfolio Management
### *A Fusion of ML and Nature-Inspired Algorithms*

> An intelligent, end-to-end portfolio optimization system that combines **machine learning**, **nature-inspired metaheuristic algorithms**, and **Agentic AI** to deliver real-time, personalized investment recommendations. The system fetches 15 years of historical stock data from Yahoo Finance (Nifty50 & Sensex), engineers technical indicators via the `ta` library, predicts prices with a tuned Ridge model, optimizes portfolio weights using PSO, GWO, and the Bat Algorithm, analyses market sentiment from financial news, and runs a **five-agent council** (Bull, Bear, Quant, Macro, Chair) on Groq tool-calling that queries live data before arguing the allocation — with a deterministic validator holding final authority over the numbers. All of it is wrapped in a Streamlit web-app with a Firebase backend for authentication, portfolio storage, and a manager dashboard.

---

## 🗂️ Table of Contents

- [✨ Features](#-features)
- [🧩 Modules](#-modules)
- [🛠️ Tech Stack](#%EF%B8%8F-tech-stack)
- [📁 Folder Structure](#-folder-structure)
- [⚙️ Setup & Installation](#%EF%B8%8F-setup--installation)
- [🔥 Firebase Setup](#-firebase-setup)
- [▶️ Running the App](#%EF%B8%8F-running-the-app)
- [🧪 Model Comparison & Tuning](#-model-comparison--tuning)
  
---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 **Real-Time Data** | Fetches live & historical stock data via yFinance |
| 🤖 **ML Price Prediction** | Ridge regression over 15y of engineered features |
| 🧠 **Agent Council** | 5 agents debate in parallel; every claim must cite a tool result |
| 🐺 **Nature-Inspired Optimization** | PSO, GWO, Bat — plus hybrids, ensemble, and an SLSQP baseline |
| 🧾 **Actionable Orders** | Whole-share BUY/SELL counts, not unactionable percentages |
| 🛡️ **Risk Metrics** | Ledoit-Wolf covariance, VaR, CVaR, max drawdown, Sortino, Calmar |
| 📰 **Sentiment Analysis** | Scrapes Moneycontrol & Livemint; scores with VADER NLP |
| 📋 **Detailed Reports** | Explainable rebalancing reports with risk/return justifications |
| 🔐 **Secure Auth** | Firebase Authentication with role-based access (Investor / Manager) |
| 🌐 **Web App** | Interactive Streamlit app, deployed on Streamlit Cloud |
| ⏱️ **Automation** | GitHub Actions cron: auto-sell on target, snapshots, price cache |

---

## 🧩 Modules

### 1. 📥 Data Collection
Fetches **15 years** of OHLCV stock data (Jan 2010 → present) for **Nifty50 + Sensex** companies using `yFinance`. Financial news is scraped in real-time from Moneycontrol and Livemint via `BeautifulSoup`.

### 2. ⚙️ Data Preprocessing & Feature Engineering
Raw OHLCV data is enriched with technical indicators using the `ta` library:
- Moving averages (SMA 10/30, EMA 10/30)
- Momentum indicators (RSI, MACD)
- Volatility bands (Bollinger Bands)
- Lag features (Close_lag_1 to Close_lag_5)
- Cyclical time encodings (sin/cos of day & month)

### 3. 📈 Stock Price Prediction (ML Models)
**Ridge Regression** (`Scikit-learn`, SVD solver) is trained per ticker on 15 years of engineered features and predicts the next close. Model selection across 25 candidates was carried out in the research notebooks; Ridge won on error and is what ships here.

### 4. 🌿 Portfolio Optimization (Nature-Inspired)
Seven optimizers maximize the **Sharpe Ratio** over a real annualized covariance matrix (Ledoit-Wolf shrinkage), subject to long-only weights and a 35% position cap:
- **PSO** — Particle Swarm Optimization
- **GWO** — Grey Wolf Optimization
- **BAT** — Bat Algorithm
- **SLSQP** — convex baseline, so the metaheuristics can be checked against a known optimum
- Hybrids & Ensemble (PSO→GWO, GWO→BAT, All Ensemble)

Because the position cap makes the objective non-smooth, the metaheuristics
measurably outperform SLSQP — which is the point of using them.

Output is converted to **whole-share orders**: NSE does not trade fractions, so
"33.3%" becomes "BUY 3".

### 5. 🤖 Agentic AI
Five agents on **Groq native tool-calling** (no LangChain):
- **Bull** — the constructive case: momentum, positive news, undervaluation
- **Bear** — the cautionary case: volatility, drawdown, concentration
- **Quant** — runs the optimizers and reports what the math says
- **Macro** — sector and index exposure
- **Chair** — synthesizes, names where the analysts disagreed, and how it resolved it

The four analysts run **in parallel** and each may call tools (`get_quote`,
`get_price_history`, `get_news_sentiment`, `run_optimizer`, `compare_algorithms`).
A claim with no supporting tool output is discarded.

**`council.validate()` is plain Python and holds final authority** — ±15% tilt cap,
35% position cap, non-negativity, normalization. The council reasons about the
allocation; the optimizer and the validator decide it. An LLM never emits a number
that moves money.

### 6. 💬 Sentiment Analysis
Financial news headlines are scored as **Positive / Negative / Neutral** using the `VADER` sentiment model. Sentiment scores are fed into the optimization pipeline to bias allocation decisions.

### 7. 🗄️ Database (Firebase)
Firebase Realtime Database stores `users`, `stocks`, `purchases`, `transactions`, plus `counters` (atomic ID generation), `sessions` (hashed tokens), `snapshots` and `price_cache`. Firebase Authentication handles login and registration; manager access is an **email allowlist**, and Google sign-in is available as an option.

### 8. 🌐 Web Application (Streamlit)
A fully interactive multi-page app covering:
- Landing Page → Login / Register (staff portal is a separate route, `/?manager=1`)
- User Home → Portfolio Overview, Buy/Sell/Edit Stocks
- Optimization Page → Run algorithms, view pie charts & performance metrics
- Report Generation → Detailed AI-generated portfolio analysis
- Manager Dashboard → KPIs, user growth, top holdings, recent activity

Sessions persist for 30 minutes across page refresh; the cookie carries only an
opaque token, with all state held server-side.

### 9. ⏱️ Automation
Streamlit Cloud has no scheduler, so a GitHub Actions cron runs after NSE close:
target-price auto-sell, daily portfolio snapshots, and a price cache that keeps the
interactive path off the rate limiter.

---

## 🛠️ Tech Stack

### 🐍 Core Language
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)

### 🤖 Machine Learning & Data
| Library | Purpose |
|---|---|
| `Scikit-learn` | Ridge regression, Ledoit-Wolf shrinkage covariance |
| `Pandas` / `NumPy` | Data manipulation; all optimizers are pure NumPy |
| `yFinance` | Batched historical & live market data |
| `ta` | Technical indicator generation |

### 🌿 Optimization & AI
| Library | Purpose |
|---|---|
| `SciPy` | SLSQP convex baseline |
| `Groq` | Native tool-calling; fast inference for the agent council |

PSO, GWO and the Bat Algorithm are implemented from scratch in NumPy
(`ml/optimizers.py`) — no metaheuristics library.

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
| `firebase-admin` | Firebase database & authentication |
| `Authlib` | Optional Google sign-in |
| `extra-streamlit-components` | Session cookies that survive refresh |

### 📊 Visualization
| Library | Purpose |
|---|---|
| `Matplotlib` | Allocation comparison charts |
| `Plotly` | Interactive sector breakdowns |

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
│   ├── auth.py                      # Identity resolution + manager allowlist
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
│   ├── login_manager.py             # Manager portal login (separate route)
│   ├── ui.py                        # Shared design system (palette, cards, charts)
│   ├── manger_home.py               # Manager dashboard
│   ├── add_stock.py                 # Add new stock (manager)
│   ├── sector_manager.py            # Sector wise portfolio distribution of all stocks add by manager
│   ├── sector_user.py               # Sector wise portfolio distribution of user portfolio
│   ├── show_stock.py                # View all stocks (manager)
│   ├── show_users.py                # View all users (manager)
│   ├── edit_stock_manager.py        # Edit stock details (manager)
│   └── cleaned_top_companies.csv    # Company list for dropdowns
│
├── ml/                              # 🤖 ML, AI & optimization logic
│   ├── optimizers.py                # PSO, GWO, BAT, hybrids, risk metrics (pure NumPy)
│   ├── optimization.py              # Entry point; weights → whole-share orders
│   ├── tools.py                     # Tool registry the agents call
│   ├── council.py                   # 5-agent debate + deterministic validator
│   ├── train.py                     # Ridge training pipeline
│   ├── sentiment.py                 # VADER sentiment scoring
│   ├── news.py                      # News scraping + relevance matching
│   ├── visualization.py             # Charts & performance plots
│   └── .env                         # 🔐 GROQ_API_KEY
│
├── services/                        # 🔧 Shared service utilities
│   ├── cache.py                     # Data caching helpers
│   └── stock_services.py            # Stock price fetching service
│
├── jobs/                            # ⏱️ Scheduled and offline work
│   ├── nightly.py                   # Auto-sell, snapshots, price cache
│   ├── seed_catalog.py              # One-shot catalog seed from CSV
│   └── model_comparison.py          # 25-model sweep + Optuna tuning (offline)
│
├── .github/workflows/nightly.yml    # Cron: weekdays 16:00 IST
├── .streamlit/config.toml           # Fast-start settings
│
└── utils/
    └── navigation.py                # Streamlit page navigation helper
```

Each module with non-trivial logic carries a self-check that needs no network and
no credentials:

```bash
python -m ml.optimizers      # all 7 algorithms + risk metrics
python -m ml.optimization    # weights + whole-share orders
python -m ml.tools           # registry/schema consistency
python -m ml.council         # validator bounds, stance parsing
python -m ml.news            # keyword extraction
python -m database.session   # token hashing
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

> All dependencies are pinned with both a floor and a ceiling. Leaving them open
> previously caused pip to spend hours backtracking through the dependency tree.

### Step 4 — Configure

Local development reads `.env`; deployment reads `st.secrets`; the scheduled job
reads GitHub Actions secrets. The same keys work in all three.

`ml/.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
```

`database/.env`:
```env
API_KEY=your_firebase_project_api_key_here
databaseURL=your_firebase_db_url
manager_emails=you@example.com,colleague@example.com
```

> `manager_emails` is an **allowlist** and replaces the old shared
> `manager_password`.

For Streamlit Cloud, put the same values plus the service-account JSON in
`.streamlit/secrets.toml` (gitignored) — the `[firebase]` table takes the JSON
field by field:

```toml
databaseURL    = "https://<project>-default-rtdb.firebaseio.com/"
manager_emails = "you@example.com"
GROQ_API_KEY   = "gsk_..."

[firebase]
type        = "service_account"
project_id  = "..."
private_key = "-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"
client_email = "..."
```

**Google sign-in (optional).** Add an `[auth]` block and the button appears;
omit it and email/password is used:

```toml
[auth]
redirect_uri  = "http://localhost:8501/oauth2callback"
cookie_secret = "any-long-random-string"

[auth.google]
client_id           = "...apps.googleusercontent.com"
client_secret       = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
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
```
/
├── users/          ├── counters/      # atomic ID generation
├── stocks/         ├── sessions/      # hashed session tokens
├── purchases/      ├── snapshots/     # nightly portfolio values
└── transactions/   └── price_cache/   # nightly closes
```
All are created automatically on first write.

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

### Step 6 — Seed the stock catalog
```bash
python -m jobs.seed_catalog
```
Validates every ticker in `ml/top 80 compines with ticker.csv` against live NSE
data and stores the resolved name and sector. Delisted or renamed symbols are
reported and skipped — no configuration edit is needed, `connection.py` finds the
credentials automatically.

### Step 7 — Set Database Rules (Production)
In Firebase Console → Realtime Database → **Rules**, replace with:
```json
{
  "rules": {
    ".read": false,
    ".write": false,
    "users":        { ".indexOn": ["personal/email"] },
    "purchases":    { ".indexOn": ["user_id", "stock_id"] },
    "transactions": { ".indexOn": ["user_id", "purchased_id"] },
    "sessions":     { ".indexOn": ["user_id"] },
    "stocks":       { ".indexOn": ["ticker", "is_deleted"] }
  }
}
```

**Why deny-all is correct here, not a mistake.** The app talks to the database
through the Firebase **Admin SDK**, which authenticates as a service account and
bypasses these rules entirely. The rules exist only to stop anyone who learns
your database URL from reading it directly over REST. `false` is exactly right;
loosening it to `auth != null` would grant access to any signed-in user of any
Firebase project.

**`.indexOn` is required regardless.** Index rules are *not* bypassed by the
Admin SDK. Without them `order_by_child(...).equal_to(...)` raises, and the app
falls back to downloading the whole table and filtering in Python — correct, but
it gets slower with every row added. With them, one user's purchases are fetched
server-side.

> Do **not** use the earlier `"$uid": {".read": "$uid === auth.uid"}` shape.
> Purchases are keyed by purchase ID (`26p0000001`) with `user_id` as a *field*,
> so a `$uid` match against the key never succeeds.

---

## ▶️ Running the App

```bash
# Make sure your virtual environment is activated
streamlit run main.py
```

The app will open at **http://localhost:8501**

### Full run order — start to finish

Steps 1–4 are one-time setup. Step 5 is the app. Steps 6–7 are the offline
research pipeline and are **not** needed to use the app.

| # | Step | Command | Notes |
|---|---|---|---|
| 1 | Install | `pip install -r requirements.txt` | |
| 2 | Configure | create `.env` — see [Step 4](#step-4--configure) | |
| 3 | Firebase credentials | drop the admin-SDK JSON in the project root | [Firebase Setup](#-firebase-setup) |
| 4 | Seed the catalog | `python -m jobs.seed_catalog` | one time; 49 NSE companies |
| 5 | **Run the app** | `streamlit run main.py` | http://localhost:8501 |
| 6 | Self-checks | `python -m ml.optimizers` | also `ml.optimization`, `ml.tools`, `ml.council`, `database.session` |
| 7 | Model comparison | `python -m jobs.model_comparison` | offline; see below |

Steps 6 and 7 need no Firebase and no credentials.

### Automation
Add `FIREBASE_CREDENTIALS` (the service-account JSON as one line) and
`DATABASE_URL` to **GitHub → Settings → Secrets → Actions**. Two workflows then
run on their own:

| Workflow | Schedule | Does |
|---|---|---|
| `nightly.yml` | weekdays **18:30 IST** (`0 13 * * 1-5`) | caches every catalog close, auto-sells on target, snapshots portfolio values |
| `model-comparison.yml` | Sundays **07:30 IST** (`0 2 * * 0`) | re-runs the 25-model sweep, uploads `results/` as a build artifact |

Both have `workflow_dispatch`, so you can trigger either from the **Actions** tab
without waiting for the schedule.

**18:30 IST is 3 hours after the 15:30 NSE close**, which gives Yahoo time to
settle the official close. The job also refuses to write unless the latest
session Yahoo reports actually *is* today — on a weekend, an NSE holiday, or an
unsettled feed it logs and exits, rather than stamping the previous session's
prices with today's date and double-counting a day in every user's history.

> ⚠️ GitHub's scheduler is best-effort and can run late under load. Neither job
> is time-critical, and both are safe to re-run.

### Default Access
| Role | How to Access |
|---|---|
| 👤 **New User** | Click "Register" on the landing page |
| 🔑 **Existing User** | Click "Login" with your credentials |
| 🛠️ **Manager** | Go to `/?manager=1` and sign in with an email listed in `manager_emails`. Password login needs a Firebase Auth account for that email; Google sign-in needs only the allowlist. |

---

## 🧪 Model Comparison & Tuning

An offline job that trains the 25 regression models listed in the report's
Table 3.3, tunes the best of them with Optuna, and writes every artifact to
`results/`. **It is never imported by the app** — running it is optional.

```bash
# quick pass, to gauge timing on your machine first
python -m jobs.model_comparison --tickers 3 --trials 10 --top 3

# full run
python -m jobs.model_comparison --tickers 8 --trials 40
```

| Flag | Default | Meaning |
|---|---|---|
| `--tickers` | `8` | how many NSE symbols to sample |
| `--trials` | `40` | Optuna trials per tuned model |
| `--top` | `5` | how many top models to tune |
| `--target` | `both` | `price`, `return`, or `both` |

### What it produces

| Path | Contents |
|---|---|
| `results/model_comparison_<target>.csv` | every model — RMSE, MAE, R², directional %, fold std |
| `results/model_comparison_<target>_tuned.csv` | post-Optuna scores and best params |
| `results/models/<target>/*.joblib` | each model refit on the full series |
| `results/predictions/<target>/*.csv` | per-fold out-of-sample predictions |
| `results/optuna/<target>.db` | resumable studies — interrupt and re-run safely |
| `results/datasets/<target>.csv` | the exact feature matrix used |
| `results/METHODOLOGY.md` | target, CV scheme, baseline, seeds, versions |
| `results/*.png` | ranking chart and before/after-tuning chart |

### Method

Walk-forward `TimeSeriesSplit(5)` — never a random split — seeded at 42, with
every model scored against a **naive baseline**: persistence (`tomorrow = today`)
for the price target, constant zero for the return target. A sub-1% RMSE
difference is reported as a tie, not a win.

Two targets are evaluated deliberately. On **price levels**, naive persistence
already scores R² ≈ 0.97, so every model clusters near the ceiling and the metric
cannot rank them — a high R² there reflects consecutive closes being similar, not
model skill. On **next-day returns**, the honest target for any directional
claim, results are reported as measured.

> **Note:** PyCaret is not used. Its pins (`numpy<1.27`, `pandas<2.2.0`,
> `scipy<=1.11.4`) have no Python 3.13 wheels and installing it would downgrade
> the whole stack. The models are built directly on scikit-learn, xgboost,
> lightgbm and catboost, and tuned with Optuna.

---

Live Demo - [Launch Portfolio Optimization App](https://portfolio-optimization-agentic-ai.streamlit.app/)

---
> ⚠️ **Disclaimer:** This system provides AI-generated investment insights for educational purposes only. It does not guarantee financial returns and does not execute trades automatically. Always consult a certified financial advisor before making investment decisions.
