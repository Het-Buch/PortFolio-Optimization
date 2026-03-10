import matplotlib.pyplot as plt
import numpy as np


def _display_name(value):
    return str(value or "").replace(".NS", "").strip()

def create_portfolio_charts(portfolio_data, optimized_weights, show_charts=True):
    """
    Create pie charts comparing before and after portfolio weights.
    
    Args:
        portfolio_data: Original portfolio data with stocks_owned
        optimized_weights: Optimized weights from the optimization process
        show_charts: Boolean flag to control whether to show charts
    """
    if not show_charts:
        return
    
    # Calculate initial weights based on portfolio value (fallback to quantity).
    total_value = sum(float(company.get('position_value', 0) or 0) for company in portfolio_data['portfolio'])
    if total_value > 0:
        initial_weights = {
            company['company']: float(company.get('position_value', 0) or 0) / total_value
            for company in portfolio_data['portfolio']
        }
    else:
        total_stocks = sum(company['stocks_owned'] for company in portfolio_data['portfolio'])
        if total_stocks <= 0:
            return None
        initial_weights = {
            company['company']: company['stocks_owned'] / total_stocks
            for company in portfolio_data['portfolio']
        }
    
    # Prepare data for plotting
    companies = list(initial_weights.keys())
    display_companies = [_display_name(c) for c in companies]
    initial_values = list(initial_weights.values())
    optimized_values = [float(optimized_weights['portfolio_weights'].get(company, 0) or 0) for company in companies]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot initial portfolio
    ax1.pie(initial_values, labels=display_companies, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Initial Portfolio Weights\n(Based on Portfolio Value)')
    
    # Plot optimized portfolio
    ax2.pie(optimized_values, labels=display_companies, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Optimized Portfolio Weights\n(Based on ML Model)')
    
    # Add portfolio metrics as text
    metrics = optimized_weights['portfolio_metrics']
    metrics_text = f"Expected Return: {metrics['expected_return']:.2%}\n"
    metrics_text += f"Portfolio Risk: {metrics['portfolio_risk']:.2%}\n"
    metrics_text += f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}"
    
    plt.figtext(0.5, -0.1, metrics_text, ha='center', va='center', fontsize=10)
    
    # Adjust layout to prevent text overlap
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('portfolio_comparison.png', bbox_inches='tight', dpi=300)
    print("\nPortfolio comparison charts have been saved as 'portfolio_comparison.png'")
    
    # Print detailed comparison
    print("\nDetailed Portfolio Comparison:")
    print("\nCompany\t\tInitial Weight\tOptimized Weight\tChange")
    print("-" * 60)
    for company in companies:
        initial = initial_weights[company]
        optimized = optimized_weights['portfolio_weights'][company]
        change = optimized - initial
        company_label = _display_name(company)
        print(f"{company_label[:15]:<15} {initial:>10.1%} {optimized:>15.1%} {change:>10.1%}") 

    return fig