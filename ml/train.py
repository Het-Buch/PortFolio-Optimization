import yfinance as yf
import pandas as pd
import numpy as np
import logging
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
from sklearn.linear_model import Ridge
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Calculate dynamic date range
today = datetime.today().date()
end_date = today - timedelta(days=1)  # Yesterday
start_date = today - timedelta(days=15 * 365)  # Approximately 15 years ago
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# Feature Engineering Functions
def add_technical_indicators(data):
    """Add technical indicators to the stock data."""
    data['SMA_10'] = data['Close'].rolling(window=10).mean()
    data['SMA_30'] = data['Close'].rolling(window=30).mean()
    data['EMA_10'] = data['Close'].ewm(span=10, adjust=False).mean()
    data['EMA_30'] = data['Close'].ewm(span=30, adjust=False).mean()
    data['Return'] = data['Close'].pct_change()
    data['Volatility'] = data['Return'].rolling(window=10).std()
    data['RSI'] = RSIIndicator(data['Close']).rsi()
    data['MACD'] = MACD(data['Close']).macd()
    bb = BollingerBands(data['Close'])
    data['BB_High'] = bb.bollinger_hband()
    data['BB_Low'] = bb.bollinger_lband()
    return data

def create_lag_features(data, lags=5):
    """Create lag features for the 'Close' price."""
    for lag in range(1, lags + 1):
        data[f'Close_lag_{lag}'] = data['Close'].shift(lag)
    return data

def encode_time_features(data):
    """Encode time-based features using sine and cosine transformations."""
    data.index = pd.to_datetime(data.index)
    data['Day_sin'] = np.sin(2 * np.pi * data.index.day / 31)
    data['Day_cos'] = np.cos(2 * np.pi * data.index.day / 31)
    data['Month_sin'] = np.sin(2 * np.pi * data.index.month / 12)
    data['Month_cos'] = np.cos(2 * np.pi * data.index.month / 12)
    return data

def preprocess_data(data):
    """Preprocess the data by adding features, shifting indicators, and handling missing values."""
    data = add_technical_indicators(data)
    
    # Shift indicators to use only past data
    indicators = ['SMA_10', 'SMA_30', 'EMA_10', 'EMA_30', 'RSI', 'MACD', 'BB_High', 'BB_Low', 'Volatility', 'Return']
    for ind in indicators:
        data[f'{ind}_lag1'] = data[ind].shift(1)
    data.drop(columns=indicators, inplace=True)
    
    # Create lag features for 'Close'
    data = create_lag_features(data, lags=5)
    
    # Encode time features
    data = encode_time_features(data)
    
    # Set index to Date if available
    if 'Date' in data.columns:
        data.set_index("Date", inplace=True)
    data.index = pd.to_datetime(data.index)
    
    # Drop rows with NaN values
    data.dropna(inplace=True)
    return data

def get_stock_data(ticker, start_date=start_date_str, end_date=end_date_str):
    """Fetch stock data from Yahoo Finance."""
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        logging.warning(f"Data not available for ticker: {ticker}")
        return None
    data.reset_index(inplace=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    return preprocess_data(data)

def train_models(ticker, company_name):
    """Train a Ridge model and predict today's price using yesterday's features."""
    logging.info(f"Processing {company_name} ({ticker})...")
    data = get_stock_data(ticker)
    if data is None or len(data) < 2:
        logging.warning(f"Not enough data for {ticker}")
        return None
    
    # Prepare features and target
    X = data.drop('Close', axis=1)
    y = data['Close']
    
    # Use all data except the last row for training
    X_train = X.iloc[:-1]
    y_train = y.iloc[:-1]
    X_test = X.iloc[-1:]  # Yesterday's features
    
    # Train Ridge model
    ridge_model = Ridge(
        alpha=1.0,
        fit_intercept=True,
        copy_X=True,
        max_iter=None,
        positive=False,
        solver='auto',
        tol=0.0001
    )
    ridge_model.fit(X_train, y_train)
    
    # Predict today's price
    predicted_price = ridge_model.predict(X_test)[0]
    
    return {
        "Company Name": company_name,
        "Ticker": ticker,
        "Predicted Price": predicted_price
    }

def main():
    """Process companies from CSV and save predicted prices."""
    input_file = 'top 80 compines with ticker.csv'  # Adjust to your input file name
    output_file = "ridge_predicted_15y_prices.csv"
    results_list = []
    
    # Read company data
    df = pd.read_csv(input_file)
    
    # Process each company
    for _, row in df.iterrows():
        ticker = row['Ticker'] + ".NS"  # Append .NS for NSE stocks
        result = train_models(ticker, row['Company Name'])
        if result is not None:
            results_list.append(result)
    
    # Save results to CSV
    results_df = pd.DataFrame(results_list)
    results_df.to_csv(output_file, index=False)
    logging.info("All results saved successfully!")

if __name__ == "__main__":
    main()