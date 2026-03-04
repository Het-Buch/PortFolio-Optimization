import os
from groq import Groq
from ml.news import filter_data
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PortfolioAgent:
    def __init__(self):
        """Initialize the Portfolio Agent with Groq API client."""
        # Initialize Groq client using the latest version
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables. Please check your .env file.")
        
        # Initialize without any additional arguments
        self.client = Groq(api_key=api_key)
        
    def analyze_portfolio_changes(self, portfolio_data, optimized_weights, initial_weights):
        """Analyze and explain portfolio changes using Groq."""
        # Prepare the analysis prompt
        prompt = self._create_analysis_prompt(portfolio_data, optimized_weights, initial_weights)
        
        try:
            # Get analysis from Groq using llama-3.1-8b-instant model
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert financial analyst specializing in portfolio optimization. 
                        Your task is to analyze portfolio changes and explain them in clear, professional terms.
                        Consider market conditions, company performance, and risk factors in your analysis.
                        Use tables to display the data when appropriate."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=2048
            )
            
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error in Groq API call: {str(e)}")
            return "Unable to generate analysis due to API error. Please check your API key and try again."
    
    def _create_analysis_prompt(self, portfolio_data, optimized_weights, initial_weights):
        """Create a detailed prompt for portfolio analysis."""
        prompt = f"""Please analyze the following portfolio optimization results and provide a detailed explanation:

Portfolio Details:
{json.dumps(portfolio_data, indent=2)}

Initial Weights:
{json.dumps(initial_weights, indent=2)}

Optimized Weights:
{json.dumps(optimized_weights, indent=2)}

Please provide:
1. A summary of major changes in portfolio allocation
2. Explanation of why these changes were recommended
3. Analysis of risk and return implications
4. Market context and validation of recommendations
5. Potential risks or concerns to consider

Current Date: {datetime.now().strftime('%Y-%m-%d')}

Please format your response with clear sections and use tables where appropriate to display data."""
        return prompt
    
    def validate_recommendations(self, company_name, optimized_weight, initial_weight):
        """Validate recommendations for a specific company using news and sentiment."""
        # Get news and sentiment data
        news_data = filter_data(company_name)
        
        # Create validation prompt
        prompt = f"""Validate the following portfolio recommendation:

Company: {company_name}
Initial Weight: {initial_weight:.1%}
Recommended Weight: {optimized_weight:.1%}
Change: {(optimized_weight - initial_weight):.1%}

Recent News and Sentiment:
{json.dumps(news_data, indent=2)}

Please analyze:
1. Whether the recommended change aligns with current market conditions
2. How recent news and sentiment support or contradict the recommendation
3. Potential risks or opportunities to consider
4. Whether the change seems reasonable given the company's current position

Provide a concise validation of this specific recommendation. Use tables to display data where appropriate."""
        
        try:
            # Get validation from Groq
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst validating portfolio recommendations based on current market conditions and news. Use tables to display data where appropriate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=2048
            )
            
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error in Groq API call for {company_name}: {str(e)}")
            return f"Unable to validate {company_name} due to API error."
    
    def generate_portfolio_report(self, portfolio_data, optimized_weights, initial_weights):
        """Generate a comprehensive portfolio analysis report."""
        # Get overall analysis
        overall_analysis = self.analyze_portfolio_changes(
            portfolio_data, optimized_weights, initial_weights
        )
        
        # Get company-specific validations
        company_validations = {}
        for company in portfolio_data['portfolio']:
            company_name = company['company']
            initial_weight = initial_weights[company_name]
            optimized_weight = optimized_weights['portfolio_weights'][company_name]
            
            validation = self.validate_recommendations(
                company_name, optimized_weight, initial_weight
            )
            company_validations[company_name] = validation
        
        # Combine all analyses
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_analysis": overall_analysis,
            "company_specific_analysis": company_validations,
            "portfolio_metrics": optimized_weights['portfolio_metrics']
        }
        
        return report

def analyze_portfolio(portfolio_data, optimized_weights, initial_weights):
    """Main function to analyze portfolio using the AI agent."""
    try:
        agent = PortfolioAgent()
        report = agent.generate_portfolio_report(
            portfolio_data, optimized_weights, initial_weights
        )
        
        # Print the report in a formatted way
        print("\n=== Portfolio Analysis Report ===")
        print(f"Generated on: {report['timestamp']}")
        print("\nOverall Analysis:")
        print(report['overall_analysis'])
        
        print("\nCompany-Specific Analysis:")
        for company, analysis in report['company_specific_analysis'].items():
            print(f"\n{company}:")
            print(analysis)
        
        print("\nPortfolio Metrics:")
        for metric, value in report['portfolio_metrics'].items():
            print(f"{metric}: {value}")
        
        return report
    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
        print("Please check your .env file and ensure GROQ_API_KEY is set correctly.")
        return None