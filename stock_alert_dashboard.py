import streamlit as st
from datetime import datetime, timedelta
import requests
import statistics
import os

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# -------- Settings -------- #
WATCHLIST = ['NVDA', 'LCID', 'TSLA', 'AMD', 'AAPL']
BULLISH_KEYWORDS = ['partnered', 'contract', 'buyout', 'acquisition', 'approval']

# -------- Alpaca Client -------- #
alpaca_client = StockHistoricalDataClient(
    os.getenv("ALPACA_KEY"),
    os.getenv("ALPACA_SECRET")
)

# -------- Market Data from Alpaca -------- #
def get_real_market_data(symbol):
    try:
        end = datetime.now()
        start = end - timedelta(days=14)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end
        )
        bars = alpaca_client.get_stock_bars(request).df

        if bars.empty or symbol not in bars.index.get_level_values(0):
            return None, []

        stock_data = bars.loc[symbol]
        current_volume = stock_data.iloc[-1]['volume']
        past_volumes = stock_data['volume'].tolist()[:-1]
        return current_volume, past_volumes

    except Exception as e:
        return None, []

# -------- Unusual Volume Detector -------- #
def is_unusual_volume(current_volume, historical_volumes):
    if not historical_volumes:
        return False
    avg_vol = statistics.mean(historical_volumes)
    return current_volume > avg_vol * 5

# -------- News Scan -------- #
def get_news_headlines(symbol):
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return ["NEWSAPI_KEY not set in environment"]
    url = f"https://newsapi.org/v2/everything?q={symbol}&sortBy=publishedAt&apiKey={api_key}"
    try:
        res = requests.get(url)
        articles = res.json().get("articles", [])
        return [a["title"] for a in articles[:5]]
    except:
        return ["Error fetching news"]

def is_bullish_news(headlines):
    return any(any(word in headline.lower() for word in BULLISH_KEYWORDS) for headline in headlines)

# -------- Streamlit Dashboard -------- #
st.set_page_config(page_title="Stock Jump Alerts", layout="wide")
st.title("🚨 Stock Jump Detector Dashboard")

for symbol in WATCHLIST:
    st.subheader(f"{symbol}")

    current_vol, past_vols = get_real_market_data(symbol)
    if not past_vols:
        st.warning(f"⚠️ No volume data found for {symbol}.")
        continue

    tweet_count = "N/A (snscrape not supported)"
    headlines = get_news_headlines(symbol)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current Volume", f"{current_vol:,}")
        st.metric("Average Volume", f"{int(statistics.mean(past_vols)):,}")
        if is_unusual_volume(current_vol, past_vols):
            st.success("Unusual Volume Detected")

    with col2:
        st.metric("Tweets (last hour)", tweet_count)
        # if tweet_count > 100:
        #     st.warning("High Twitter Activity")

    with col3:
        st.write("Latest Headlines:")
        for h in headlines:
            st.write(f"• {h}")
        if is_bullish_news(headlines):
            st.info("Bullish News Detected")

    st.markdown("---")
