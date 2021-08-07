# Welcome to crypto gain or crypto pain!
Provides a frontend user interface for querying the past 24hrs of data on cryptocurrency trading pairs from binance. The data is fetched through binance's API and is hosted on a local sqlite database generated/updated on app startup. It shows price changes for trading pairs and indicates winners and losers in the past 24hrs (+/- 5% price change). Data is sortable and can be filtered by user input.

## Instructions
After cloning/forking the repo, install the dependencies:
`pip install -r requirements.txt`
To inititate the app:
```powershell
uvicorn main:app
```
Click url link displayed in terminal or open browser at http://127.0.0.1:8000 to view searchable table.

Credit to Jonas Earendel for the original JavaScript and CSS which I adapted for the sort feature: https://github.com/tofsjonas/sortable.