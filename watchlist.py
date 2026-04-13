# वॉचलिस्ट को 5 कैटेगरी में बाँटा गया है जैसा आपने माँगा था
WATCHLIST_GROUPS = {
    "Market Indices": {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "FIN NIFTY": "NIFTY_FIN_SERVICE.NS",
        "SENSEX": "^BSESN",
        "MIDCAP NIFTY": "NIFTY_MID_SELECT.NS",
        "INDIA VIX": "^INDIAVIX"
    },
    "Crypto Hub": {
        "BITCOIN": "BTC-USD",
        "ETHEREUM": "ETH-USD",
        "SOLANA": "SOL-USD",
        "XRP": "XRP-USD",
        "PAX GOLD": "PAXG-USD"
    },
    "Market Sectors": {
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY FMCG": "^CNXFMCG"
    },
    "Favorites": {
        "RELIANCE": "RELIANCE.NS",
        "HDFC BANK": "HDFCBANK.NS",
        "TCS": "TCS.NS",
        "ICICI BANK": "ICICIBANK.NS",
        "INFY": "INFY.NS"
    },
    "Global Market": {
        "GIFT NIFTY": "GIFTY.NS",
        "S&P 500": "^GSPC",
        "GOLD": "GC=F",
        "CRUDE OIL": "CL=F",
        "US TECH 100": "^IXIC"
    }
}

# सेक्टर हीटमैप के लिए मुख्य स्टॉक्स (यह चेक करने के लिए कि सेक्टर कैसा है)
SECTOR_COMPONENTS = {
    "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "AUTO": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS"],
    "PHARMA": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "APOLLOHOSP.NS"],
    "ENERGY": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS"]
}

def get_ticker_by_name(name):
    """वॉचलिस्ट में नाम से टिकर खोजने के लिए"""
    for group in WATCHLIST_GROUPS.values():
        if name in group:
            return group[name]
    return None

def get_all_symbols():
    """सर्च फंक्शन के लिए सभी सिम्बल्स की एक लिस्ट"""
    all_syms = []
    for group in WATCHLIST_GROUPS.values():
        all_syms.extend(list(group.keys()))
    return all_syms

