import os
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, LLMSingleActionAgent
from langchain_core.prompts import StringPromptTemplate
from langchain.chains import LLMChain
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.chat_models import init_chat_model
from langchain.schema import AgentAction, AgentFinish
from typing import List, Union, Dict
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class MarketResearchAgent:
    """Agent responsible for gathering market information and news."""
    
    def __init__(self):
        self.search = DuckDuckGoSearchRun()
        self.llm = init_chat_model("llama3-8b-8192", model_provider="groq")
        
        self.tools = [
            Tool(
                name="Search",
                func=self.search.run,
                description="Useful for searching current market information, news, and trends"
            )
        ]
        
        # Remove memory initialization as ConversationBufferMemory is unavailable

    def research_market(self, company_name: str) -> Dict:
        """Research market conditions for a specific company."""
        prompt = f"""Research the current market conditions, recent news, and trends for {company_name}.
        Focus on:
        1. Recent market performance
        2. Industry trends
        3. Key news and developments
        4. Market sentiment
        5. Risk factors
        
        Provide a comprehensive analysis with sources."""
        
        try:
            response = self.llm.invoke(prompt)
            # Extract content from AIMessage
            response_content = response.content if hasattr(response, 'content') else str(response)
            return {
                "company": company_name,
                "research": response_content,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error in market research for {company_name}: {str(e)}")
            return None

class PortfolioValidationAgent:
    """Agent responsible for validating portfolio recommendations."""
    
    def __init__(self):
        self.llm = init_chat_model("llama3-8b-8192", model_provider="groq")
        
    def validate_portfolio(self, 
                         portfolio_data: Dict,
                         optimized_weights: Dict,
                         initial_weights: Dict,
                         market_research: Dict) -> Dict:
        """Validate portfolio recommendations against market research."""
        
        # Create a simplified version of the data to reduce token count
        simplified_portfolio = {
            "companies": [company["company"] for company in portfolio_data.get("portfolio", [])]
        }
        
        # Create a simplified version of market research
        simplified_research = {}
        for company, data in market_research.items():
            if data and "research" in data:
                # Truncate research to first 500 characters to reduce token count
                simplified_research[company] = data["research"][:500] + "..." if len(data["research"]) > 500 else data["research"]
        
        prompt = f"""Analyze and validate the following portfolio optimization results against current market conditions:

Portfolio Companies:
{', '.join(simplified_portfolio.get("companies", []))}

Initial Weights:
{json.dumps(initial_weights, indent=2)}

Optimized Weights:
{json.dumps(optimized_weights, indent=2)}

Market Research Summary:
{json.dumps(simplified_research, indent=2)}

Please provide:
1. Validation of portfolio changes against market conditions
2. Analysis of alignment with current market trends
3. Risk assessment based on market research
4. Recommendations for adjustments if needed
5. Confidence score for the optimization (0-100)

Format your response with clear sections and use tables where appropriate."""
        
        try:
            validation = self.llm.invoke(prompt)
            # Extract content from AIMessage
            validation_content = validation.content if hasattr(validation, 'content') else str(validation)
            return {
                "validation": validation_content,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error in portfolio validation: {str(e)}")
            return None

class MarketInsightAgent:
    """Agent responsible for analyzing market insights and trends."""
    
    def __init__(self):
        self.llm = init_chat_model("llama3-8b-8192", model_provider="groq")
        
    def analyze_market_insights(self, market_research: Dict) -> Dict:
        """Analyze market insights and identify key trends."""
        
        # Create a simplified version of market research
        simplified_research = {}
        for company, data in market_research.items():
            if data and "research" in data:
                # Truncate research to first 300 characters to reduce token count
                simplified_research[company] = data["research"][:300] + "..." if len(data["research"]) > 300 else data["research"]
        
        prompt = f"""Analyze the following market research and provide key insights:

Market Research Summary:
{json.dumps(simplified_research, indent=2)}

Please provide:
1. Key market trends and patterns
2. Potential opportunities and risks
3. Market sentiment analysis
4. Industry-specific insights
5. Recommendations for portfolio positioning

Format your response with clear sections and use tables where appropriate."""
        
        try:
            insights = self.llm.invoke(prompt)
            # Extract content from AIMessage
            insights_content = insights.content if hasattr(insights, 'content') else str(insights)
            return {
                "insights": insights_content,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error in market insight analysis: {str(e)}")
            return None

def analyze_portfolio_with_market_data(portfolio_data: Dict, 
                                     optimized_weights: Dict, 
                                     initial_weights: Dict) -> Dict:
    """Main function to analyze portfolio using multiple specialized agents."""
    
    try:
        # Initialize agents
        market_researcher = MarketResearchAgent()
        portfolio_validator = PortfolioValidationAgent()
        market_insight_analyzer = MarketInsightAgent()
        
        # Gather market research for each company
        market_research = {}
        for company in portfolio_data['portfolio']:
            company_name = company['company']
            research = market_researcher.research_market(company_name)
            if research:
                market_research[company_name] = research
        
        # Analyze market insights
        market_insights = market_insight_analyzer.analyze_market_insights(market_research)
        
        # Validate portfolio
        portfolio_validation = portfolio_validator.validate_portfolio(
            portfolio_data,
            optimized_weights,
            initial_weights,
            market_research
        )
        
        # Combine all analyses
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_research": market_research,
            "market_insights": market_insights,
            "portfolio_validation": portfolio_validation
        }
        
        # Print the report in a formatted way
        print("\n=== Enhanced Portfolio Analysis Report ===")
        print(f"Generated on: {report['timestamp']}")
        
        print("\nMarket Research:")
        for company, research in market_research.items():
            print(f"\n{company}:")
            print(research['research'])
        
        print("\nMarket Insights:")
        print(market_insights['insights'])
        
        print("\nPortfolio Validation:")
        print(portfolio_validation['validation'])
        
        return report
        
    except Exception as e:
        print(f"Error in enhanced portfolio analysis: {str(e)}")
        return None