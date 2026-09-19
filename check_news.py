import yfinance as yf
import time

tickers = ['^GSPC', '^N225', '^HSI', '^KS11', '^JKSE', '^STI']
for t in tickers:
    news = yf.Ticker(t).news
    print(f'\n--- {t} ---')
    if not news:
        print('No news')
        continue
    for n in news[:3]:
        pub = n.get('providerPublishTime')
        if pub:
            age_hours = (time.time() - pub) / 3600
            print(f'{age_hours:.1f} hours ago - {n.get("title")}')
