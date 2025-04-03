# main.py
import os
import requests
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DB_ID"]
ADDRESS = "0x7C2D3d3C10C21d0c5BabE101Bf30aED822f227d6"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
POLYGONSCAN_API_KEY = os.environ["POLYGONSCAN_API_KEY"]


def get_eth_transactions():
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={ADDRESS}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    res = requests.get(url)
    return res.json().get("result", [])


def get_polygon_transactions():
    url = f"https://api.polygonscan.com/api?module=account&action=txlist&address={ADDRESS}&sort=desc&apikey={POLYGONSCAN_API_KEY}"
    res = requests.get(url)
    return res.json().get("result", [])


def get_eth_price():
    res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,polygon&vs_currencies=usd")
    return res.json()


def filter_outgoing(txns):
    return [tx for tx in txns if tx["from"].lower() == ADDRESS.lower() and int(tx["isError"]) == 0]


def send_to_notion(txn, network, prices):
    token = "ETH" if network == "Ethereum" else "MATIC"
    token_price = prices["ethereum" if token == "ETH" else "polygon"]["usd"]
    amount = int(txn["value"]) / (10 ** 18)
    fiat = amount * token_price
    date = datetime.fromtimestamp(int(txn["timeStamp"])).isoformat()

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Amount": {"number": amount},
            "Token": {"rich_text": [{"text": {"content": token}}]},
            "Fiat": {"number": fiat},
            "Fiat Currency": {"rich_text": [{"text": {"content": "USD"}}]},
            "Network": {"select": {"name": network}},
            "To Address": {"rich_text": [{"text": {"content": txn["to"]}}]},
            "Date": {"date": {"start": date}},
        },
    }
    requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)


def main():
    prices = get_eth_price()
    eth_txns = filter_outgoing(get_eth_transactions())[:3]
    polygon_txns = filter_outgoing(get_polygon_transactions())[:3]

    for txn in eth_txns:
        send_to_notion(txn, "Ethereum", prices)

    for txn in polygon_txns:
        send_to_notion(txn, "Polygon", prices)


if __name__ == "__main__":
    main()

# .github/workflows/main.yml
# This is the GitHub Actions workflow that runs the script hourly
name: Crypto to Notion Sync

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install requests

      - name: Run the script
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DB_ID: ${{ secrets.NOTION_DB_ID }}
          ETHERSCAN_API_KEY: ${{ secrets.ETHERSCAN_API_KEY }}
          POLYGONSCAN_API_KEY: ${{ secrets.POLYGONSCAN_API_KEY }}
        run: python main.py