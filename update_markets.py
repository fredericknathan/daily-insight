import yaml

with open('src/config/markets.yaml', 'r') as f:
    config = yaml.safe_load(f)

for m in config['countries']:
    if 'pplx_ticker' in m:
        del m['pplx_ticker']
    m['news_query'] = f"{m['name']} stock market"

with open('src/config/markets.yaml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
