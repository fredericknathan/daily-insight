import yfinance as yf
from datetime import datetime

tickers = ['^GSPC', '^N225', '^HSI', '^KS11', '^JKSE', '^STI']
for t in tickers:
    news = yf.Ticker(t).news
    print(f'\n--- {t} ---')
    for n in news[:3]:
        c = n.get('content', {})
        pub = c.get('pubDate')
        if pub:
            dt = datetime.strptime(pub.split('T')[0] + ' ' + pub.split('T')[1][:8], '%Y-%m-%d %H:%M:%S')
            age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
            print(f'{age_hours:.1f} hours ago - {c.get("title")}')
