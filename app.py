import re
import time
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Yahoo fallback (en son çare)
import yfinance as yf

# -----------------------
# AYARLAR
# -----------------------
REFRESH_SEC = 120  # 2 dk
OZ_TO_GR = 31.1034768

# Senin verdiğin örneklerden çıkan Harem'e yakınlaştırma çarpanı
HAREM_HAS_K = 1.0313

st.set_page_config(page_title="İryum Pano", layout="wide")
st.title("İryum Pano — Harem'e Yakın HAS (USD: kur.doviz | ONS: altin.doviz)")
st.caption("2 dakikada 1 güncellenir. Kaynaklar bloklanırsa Yahoo/yfinance en son çare devreye girer.")

# 2 dakikada bir rerun
st_autorefresh(interval=REFRESH_SEC * 1000, key="auto_refresh")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
})

def tr_to_float(s: str) -> float:
    # "5.167,9" -> 5167.9  |  "43,8381" -> 43.8381  |  "170.900" -> 170900
    return float(s.replace(".", "").replace(",", "."))

def safe_get(url: str, timeout=15) -> str:
    r = SESSION.get(url, timeout=timeout)
    # burada raise_for_status YOK: uygulama çökmesin
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} @ {url}")
    return r.text

def ons_sell_altindoviz() -> float:
    html = safe_get("https://altin.doviz.com/ons")
    # Sayfada genelde: "Alış / Satış $5.148,85 /  $5.149,41"
    m = re.search(r"Alış\s*/\s*Satış\s*\$?\s*([0-9\.\,]+)\s*/\s*\$?\s*([0-9\.\,]+)", html)
    if not m:
        raise RuntimeError("ONS Alış/Satış bulunamadı (altin.doviz.com HTML değişmiş olabilir).")
    return tr_to_float(m.group(2))  # SATIŞ

def usdtry_sell_kurdoviz() -> float:
    html = safe_get("https://kur.doviz.com/serbest-piyasa/amerikan-dolari")
    # Sayfada genelde: "Alış / Satış 43,8123 / 43,8381" gibi bir satır var.
    m = re.search(r"Alış\s*/\s*Satış\s*([0-9\.\,]+)\s*/\s*([0-9\.\,]+)", html)
    if not m:
        raise RuntimeError("USD Alış/Satış bulunamadı (kur.doviz.com HTML değişmiş olabilir).")
    return tr_to_float(m.group(2))  # SATIŞ

def yf_last_price(ticker: str) -> float:
    s = yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].dropna()
    if s.empty:
        raise RuntimeError(f"yfinance boş döndü: {ticker}")
    return float(s.iloc[-1])

def ons_sell_yahoo_last_resort() -> tuple[float, str]:
    # 1) spot'e en yakın: XAUUSD=X
    try:
        return yf_last_price("XAUUSD=X"), "yfinance: XAUUSD=X"
    except Exception:
        pass
    # 2) en son: futures (spot değil): GC=F
    return yf_last_price("GC=F"), "yfinance: GC=F (futures)"

@st.cache_data(ttl=110)
def fetch_prices():
    notes = []
    # ONS
    try:
        ons = ons_sell_altindoviz()
        ons_src = "altin.doviz.com"
    except Exception as e:
        notes.append(f"ONS altin.doviz alınamadı: {e}")
        ons, ons_src = ons_sell_yahoo_last_resort()

    # USDTRY
    try:
        usd = usdtry_sell_kurdoviz()
        usd_src = "kur.doviz.com"
    except Exception as e:
        notes.append(f"USD kur.doviz alınamadı: {e}")
        # En son çare: USDTRY=X
        try:
            usd = yf_last_price("USDTRY=X")
            usd_src = "yfinance: USDTRY=X"
        except Exception as e2:
            usd = 0.0
            usd_src = "USD bulunamadı"
            notes.append(f"USD yfinance da alınamadı: {e2}")

    return {
        "ons_sell": ons,
        "usdtry_sell": usd,
        "ons_src": ons_src,
        "usd_src": usd_src,
        "notes": notes,
        "ts": time.time(),
    }

data = fetch_prices()

# HAS hesabı (Harem'e yakın)
ons_sell = data["ons_sell"]
usd_sell = data["usdtry_sell"]

if usd_sell <= 0:
    st.error("USD alınamadı. HAS hesaplanamıyor. (Kaynaklar bloklanmış olabilir.)")
else:
    has_teorik = (ons_sell / OZ_TO_GR) * usd_sell
    has_harem_yakin = has_teorik * HAREM_HAS_K

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ONS Satış (USD/oz)", f"{ons_sell:,.2f}")
    c2.metric("USD Satış (TRY)", f"{usd_sell:,.4f}")
    c3.metric("HAS (teorik TL/gr)", f"{has_teorik:,.2f}")
    c4.metric("HAS (Harem'e yakın TL/gr)", f"{has_harem_yakin:,.2f}")

st.caption(f"Kaynaklar: ONS={data['ons_src']} | USD={data['usd_src']} | K={HAREM_HAS_K}")
st.caption(f"Son güncelleme: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['ts']))}")

if data["notes"]:
    st.warning(" / ".join(data["notes"]))