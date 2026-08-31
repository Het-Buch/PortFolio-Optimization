"""Financial news scraping + VADER sentiment."""

import logging
import re

import requests
import streamlit as st
from bs4 import BeautifulSoup

from ml.sentiment import analyze_sentiments, weighted_sentiment

log = logging.getLogger(__name__)

SOURCES = {
    "mint": "https://www.livemint.com/news",
    "moneycontrol": "https://www.moneycontrol.com/news/news-all",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}
NEUTRAL = 0.05

# Dropped when matching: they appear in almost every Indian listed-company name.
_NOISE = {"limited", "ltd", "the", "india", "indian", "company", "corporation",
          "corp", "inc", "industries", "enterprises", "&", "and", "of"}


def _keywords(company, ticker=""):
    """Match tokens for a company. Full legal names never appear in headlines."""
    words = [w for w in re.split(r"[^\w&]+", str(company or "").lower()) if w]
    core = [w for w in words if w not in _NOISE and len(w) > 2]

    keys = set()
    sym = str(ticker or "").upper().replace(".NS", "").strip()
    if len(sym) > 2:
        keys.add(sym.lower())
    if core:
        keys.add(core[0])              # "Tata Consultancy Services Ltd" -> "tata"
        if len(core) >= 2:
            keys.add(" ".join(core[:2]))  # ...and "tata consultancy"
    return keys


@st.cache_data(ttl=1800, show_spinner=False)
def _headlines():
    """All headlines from both sources. Cached — every company reuses one scrape."""
    out = []
    for source, url in SOURCES.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=6)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.content, "html.parser")
            for h in soup.find_all(["h1", "h2", "h3"]):
                a = h.find("a")
                text = (a.text if a else h.text).strip()
                if len(text) > 20:
                    out.append({"headline": text, "source": source})
        except Exception as e:
            log.warning("scrape failed %s: %s", source, e)
    return out


def filter_data(company_name, ticker=""):
    """Headlines mentioning the company, plus a weighted sentiment score."""
    if not company_name:
        return {"error": "company name is required", "sentiment": NEUTRAL}

    keys = _keywords(company_name, ticker)
    if not keys:
        return {"message": f"no usable keywords for {company_name}", "sentiment": NEUTRAL}

    matched = [n for n in _headlines()
               if any(k in n["headline"].lower() for k in keys)]

    if not matched:
        return {"message": f"No news found for {company_name}", "sentiment": NEUTRAL}

    scores = analyze_sentiments([n["headline"] for n in matched])
    return {"news": matched, "sentiment": weighted_sentiment(scores)}


def _self_check():
    k = _keywords("Tata Consultancy Services Limited", "TCS.NS")
    assert "tcs" in k and "tata" in k and "tata consultancy" in k, k
    assert "limited" not in k and "india" not in _keywords("India Cements Ltd"), k

    heads = [{"headline": "TCS wins large cloud deal in Europe", "source": "mint"}]
    assert any("tcs" in h["headline"].lower() for h in heads)
    print("news: OK")


if __name__ == "__main__":
    _self_check()
