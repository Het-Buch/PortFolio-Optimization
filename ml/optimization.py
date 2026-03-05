import numpy as np
import pandas as pd
from scipy.optimize import minimize
import json
from ml.train import train_models
from ml.news import filter_data
from ml.visualization import create_portfolio_charts
from ml.agentic import analyze_portfolio
from services.cache import cached_prediction
from services.stock_services import fetch_stock_data
import time

# from train import train_models
# from news import filter_data
# from visualization import create_portfolio_charts
# from agentic import analyze_portfolio
# from market_agents import analyze_portfolio_with_market_data

# Static portfolio data
portfolio_data = {
    "user": "Het Buch and Heli Hathi",
    "portfolio": [
        {
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "stocks_owned": 10
        },
        {
            "company": "Tesla Inc.",
            "ticker": "TSLA",
            "stocks_owned": 5
        },
        {
            "company": "Microsoft Corporation",
            "ticker": "MSFT",
            "stocks_owned": 8
        },
        {
            "company": "Amazon.com Inc.",
            "ticker": "AMZN",
            "stocks_owned": 12
        },
        {
            "company": "NVIDIA Corporation",
            "ticker": "NVDA",
            "stocks_owned": 6
        }
    ]
}

def calculate_portfolio_metrics(weights, returns, cov_matrix):
    """Calculate portfolio return and risk."""
    portfolio_return = np.sum(returns * weights)
    portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return portfolio_return, portfolio_risk

def objective_function(weights, returns, cov_matrix, risk_free_rate=0.02):
    """Calculate Sharpe ratio (negative for minimization)."""
    portfolio_return, portfolio_risk = calculate_portfolio_metrics(weights, returns, cov_matrix)
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk
    return -sharpe_ratio

def calculate_initial_weights(portfolio_data):
    """Calculate initial weights based on number of stocks owned."""
    total_stocks = sum(company['stocks_owned'] for company in portfolio_data['portfolio'])
    return {
        company['company']: company['stocks_owned'] / total_stocks
        for company in portfolio_data['portfolio']
    }

def optimize_portfolio(portfolio_data, show_charts=True, use_ai_analysis=True, use_market_agents=True):
    """Optimize portfolio using PSO."""
    # Extract data
    # print(portfolio_data)
    companies = portfolio_data['portfolio']
    # companies = portfolio_data
    
    n_assets = len(companies)
    
    # Get predicted prices and sentiment scores
    returns_data = []
    sentiment_scores = []
    valid_companies = []

    print("Processing companies...")

    for company in companies:

        ticker = company["ticker"].upper()
        if not ticker.endswith(".NS"):
            ticker = ticker + ".NS"
        print(f"\nProcessing {company['company']} ({ticker})")
        price_data = cached_prediction(ticker, company["company"])
        time.sleep(1)

        if price_data and "Predicted Price" in price_data:

            predicted_price = float(price_data["Predicted Price"])
            returns_data.append(predicted_price)
            valid_companies.append(company)

            print(f"Predicted price: {predicted_price}")

        else:
            fallback_quote = fetch_stock_data(ticker)
            fallback_price = float((fallback_quote or {}).get(ticker, (fallback_quote or {}).get("price", 0)) or 0)

            if fallback_price > 0:
                returns_data.append(fallback_price)
                valid_companies.append(company)
                print(f"Using fallback live price: {fallback_price}")
            else:
                print(f"Skipping {company['company']} - prediction failed")

        news_data = filter_data(company['company'])
        sentiment_scores.append(news_data.get("sentiment", 0))
    companies = valid_companies
    n_assets = len(companies)

    if n_assets == 0:
        print("No valid companies available for optimization.")
        return None, None

    # Convert to numpy arrays
    returns = np.array(returns_data, dtype=float)
    sentiments = np.array(sentiment_scores[:n_assets], dtype=float)
    
    # Calculate covariance matrix (using historical data)
    # For simplicity, we'll use a diagonal matrix with variances based on sentiment
    cov_matrix = np.diag(np.abs(sentiments) + 0.1)  # Add small constant to avoid singular matrix
    
    # Constraints
    constraints = (
        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # weights sum to 1
        {'type': 'ineq', 'fun': lambda x: x}  # weights >= 0
    )
    
    # Initial guess (equal weights)
    initial_weights = np.array([1/n_assets] * n_assets)
    
    print("\nOptimizing portfolio weights...")
    # Optimize
    result = minimize(
        objective_function,
        initial_weights,
        args=(returns, cov_matrix),
        method='SLSQP',
        constraints=constraints
    )
    
    # Calculate final metrics
    final_return, final_risk = calculate_portfolio_metrics(result.x, returns, cov_matrix)
    
    # Prepare output
    optimized_weights = {
        'portfolio_weights': {
            company['company']: float(weight)
            for company, weight in zip(companies, result.x)
        },
        'portfolio_metrics': {
            'expected_return': float(final_return),
            'portfolio_risk': float(final_risk),
            'sharpe_ratio': float(-result.fun)
        }
    }
    
    # Create visualization if requested
    fig = None
    if show_charts:
        fig = create_portfolio_charts(portfolio_data, optimized_weights)
    
    # Calculate initial weights
    initial_weights = calculate_initial_weights(portfolio_data)
    
    # Get AI analysis if requested
    if use_ai_analysis:
        print("\nGenerating AI analysis of portfolio changes...")
        ai_report = analyze_portfolio(portfolio_data, optimized_weights, initial_weights)
        optimized_weights['ai_analysis'] = ai_report


    
    # Get market-aware analysis if requested
    if use_market_agents:
        try:
            from ml.market_agents import analyze_portfolio_with_market_data

            print("\nGenerating market-aware analysis with specialized agents...")
            market_analysis = analyze_portfolio_with_market_data(
                portfolio_data,
                optimized_weights,
                initial_weights
            )
            optimized_weights['market_analysis'] = market_analysis
        except Exception as e:
            print(f"Skipping market-agent analysis: {e}")
            optimized_weights['market_analysis'] = {
                "status": "skipped",
                "reason": str(e)
            }
    
    return optimized_weights,fig

def main():
    """Run portfolio optimization with static data."""
    print("Starting portfolio optimization...")
    print(f"User: {portfolio_data['user']}")
    print("\nPortfolio:")
    for company in portfolio_data['portfolio']:
        print(f"- {company['company']} ({company['ticker']}): {company['stocks_owned']} shares")
    
    # Set show_charts to False to disable visualization
    # Set use_ai_analysis to False to disable AI analysis
    # Set use_market_agents to False to disable market-aware analysis
    result,fig = optimize_portfolio(
        portfolio_data, 
        show_charts=True, 
        use_ai_analysis=True,
        use_market_agents=True
    )
    
    print("\nOptimization Results:")
    print("\nPortfolio Weights:")
    for company, weight in result['portfolio_weights'].items():
        print(f"- {company}: {weight:.2%}")
    
    print("\nPortfolio Metrics:")
    print(f"- Expected Return: {result['portfolio_metrics']['expected_return']:.2%}")
    print(f"- Portfolio Risk: {result['portfolio_metrics']['portfolio_risk']:.2%}")
    print(f"- Sharpe Ratio: {result['portfolio_metrics']['sharpe_ratio']:.2f}")

if __name__ == '__main__':
    main() 