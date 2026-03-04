from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from ml.sentiment import analyze_sentiments, weighted_sentiment  # Import sentiment functions

app = Flask(__name__)

def get_mint():
    url = 'https://www.livemint.com/news'
    response = requests.get(url)    

    if response.status_code != 200:
        return {"error": "Failed to fetch the webpage"}
    
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    headlines = soup.find_all('h2')
    news_data = []
    i = 0

    for h2 in headlines:
        anchor = h2.find('a')
        if anchor:
            i = i + 1
            headline_text = anchor.text.strip()
            news_data.append({
                "No.": i,
                "headline": headline_text,
                "source": "mint"
            })
    return news_data

def get_money_control():
    url = 'https://www.moneycontrol.com/news/news-all'
    response = requests.get(url)

    if response.status_code != 200:
        return {"error": "Failed to fetch the webpage"}

    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    headlines = soup.find_all('h2')
    news_data = []
    i = 0

    for h2 in headlines:
        anchor = h2.find('a')
        if anchor:
            i = i + 1
            headline_text = anchor.text.strip()
            news_data.append({
                "No.": i,
                "headline": headline_text,
                "source": "moneycontrol"
            })
    return news_data

def filter_data(company_name):
    """Get filtered news and sentiment for a specific company."""
    if not company_name:
        return {'error': 'company name is required'}
    
    mint_data = get_mint()
    money_control_data = get_money_control()
    merged_data = mint_data + money_control_data
    
    filtered_news = [
        news for news in merged_data
        if company_name.lower() in news['headline'].lower()
    ]
    
    if filtered_news:
        # Extract headlines for sentiment analysis
        headlines = [news['headline'] for news in filtered_news]
        # Analyze sentiments of the headlines
        sentiments = analyze_sentiments(headlines)
        # Compute the weighted sentiment score (using equal weights by default)
        overall_sentiment = weighted_sentiment(sentiments)
        # Return both the filtered news and the sentiment score
        return {
            "news": filtered_news,
            "sentiment": overall_sentiment
        }
    else:
        # Return a message and neutral sentiment score if no news is found
        return {
            "message": f"No news found for {company_name}",
            "sentiment": 0.05  # Neutral sentiment score when no news is found
        }

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/get-news', methods=['GET'])
def get_news():
    company_name = request.args.get('company')
    return jsonify(filter_data(company_name))

if __name__ == '__main__':
    app.run(debug=True)