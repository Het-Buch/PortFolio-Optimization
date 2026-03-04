from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiments(news):
    """
    Apply VADER sentiment analysis on a list of news.
    Returns a list of sentiment score dictionaries.
    """
    analyzer = SentimentIntensityAnalyzer()
    sentiments = []
    for headline in news:
        score = analyzer.polarity_scores(headline)
        sentiments.append(score)
    return sentiments

def weighted_sentiment(sentiments, weights=None):
    """
    Compute a weighted average of the compound sentiment scores.
    If no weights are provided, use equal weighting.
    """
    if not sentiments:
        return 0
    if weights is None:
        weights = [1] * len(sentiments)
    total_weight = sum(weights)
    weighted_sum = sum([s['compound'] * w for s, w in zip(sentiments, weights)])
    return weighted_sum / total_weight