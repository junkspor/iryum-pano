import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# ==============================================================
# 💎 1. ADIM: PATRONUN HAS (24 AYAR) REFERANS ALANI 💎
# ==============================================================

# Sabah tabelayı ayarlarken ekrandaki veya baz aldığınız HAS fiyatını buraya yazın:
REFERANS_HAS = 7350.0 

# Dükkanın baz fiyatlarını buraya yazın. Format: [ALIŞ, SATIŞ]
FIYAT_LISTESI = {
    "24 AYAR (HAS)":  [0, 7350.00],
    "22 AYAR SATIŞ":  [0, 7300.00],
    "14 AYAR":        [0, 6900.00],
    "22 AYAR ALIŞ":   [6350.00, 0],
    "BEŞLİ":          [237500.00, 250000.00],
    "TAM (ATA)":      [47500.00, 50000.00],
    "YARIM":          [23100.00, 24400.00],
    "ÇEYREK":         [11550.00, 12200.00],
    "GRAM (HAS)":     [7100.00, 7500.00]
}
# ==============================================================

# --- 2. SAYFA AYARLARI VE OTOMATİK YENİLEME ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- 3. AGRESİF REKLAM GİZLEYİCİ CSS ---
st.markdown("""
<style>
    footer {visibility: hidden !important; display: none !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    div[class*="viewerBadge"] {display: none !important; opacity: 0 !important; visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0) !important;}
    .stApp { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .header-container { display: flex; justify-content: flex-end; align-items: center; background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .header-text { color: #ffffff; font-size: clamp(14px, 3vw, 28px); font-weight: bold; text-align: center; width: 100%; }
    .row-wrapper { display: flex; align-items: baseline; padding: 10px 0; border-bottom: 1px solid #333; }
    .product-name { flex: 1.2; font-size: clamp(14px, 3.2vw, 36px); font-weight: bold; color: #ffffff; white-space: nowrap; }
    .price-container { flex: 1; display: flex; justify-content: flex-end; align-items: baseline; }
    .price-buy { font-size: clamp(18px, 4.5vw, 55px); font-weight: bold; color: #2ecc71; font-family: 'Courier New', monospace; text-align: right; }
    .price-sell { font-size: clamp(20px, 5.5vw, 70px); font-weight: 900; color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 0, 0.5); margin-left: 10px; }
    .hidden { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ ÇEKME FONKSİYONLARI ---
def turkiye_saati_al():
    tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(tz).strftime('%H:%M:%S')

def canli_ons_al():
    try:
        return yf.Ticker("GC=F").history(period="1d", interval="1m")['Close'].iloc[-1]
    except:
        return None

def canli_dolar_al():
    try:
        return yf.Ticker("TRY=X").history(period="1d", interval="1m")['Close'].iloc[-1]
    except:
        return None

# --- 5. YÖNETİCİ PANELİ ---
st.sidebar.header("💎 İRYUM YÖNETİCİ")
s_adj = st.sidebar.slider("Satış Fiyatlarına Ekle/Çıkar (TL)", -500.0, 500.0, 0.0, step=1.0)
a_adj = st.sidebar.slider("Alış Fiyatlarına Ekle/Çıkar (TL)", -500.0, 500.0, 0.0, step=1.0)

# --- 6. EKRANA ÇİZİM ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.2, 1, 1])
with c2: st.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
with c3: st.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

ons = canli_ons_al()
dolar = canli_dolar_al()
if ons and dolar:
    # Kuyumcu Formülü: (Ons / 31.1034768) * Dolar
    canli_has = (ons / 31.1034768) * dolar
    degisim_orani = canli_has / REFERANS_HAS 
    
    for isim, degerler in FIYAT_LISTESI.items():
        ref_a = degerler[0]
        ref_s = degerler[1]
        
        g_a = (ref_a * degisim_orani) + a_adj if ref_a > 0 else 0
        g_s = (ref_s * degisim_orani) + s_adj if ref_s > 0 else 0
        
        a_h = f'<span class="price-buy">{g_a:,.2f}</span>' if g_a > 0 else '<span class="price-buy hidden">----</span>'
        s_h = f'<span class="price-sell">{g_s:,.2f}</span>' if g_s > 0 else '<span class="price-sell hidden">----</span>'
        
        html = f'<div class="row-wrapper"><div class="product-name">{isim}</div><div class="price-container">{a_h}</div><div class="price-container">{s_h}</div></div>'
        st.markdown(html, unsafe_allow_html=True)

    # Alt Bilgi Alanı: Hem ONS, Hem Dolar Hem de CANLI HAS eklendi
    st.markdown(f"""
        <div style='text-align: center; color: #555; margin-top: 25px;'>
            ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺ | CANLI HAS: <span style='color:#fff;'>{canli_has:,.2f} ₺</span> | Saat: {turkiye_saati_al()}
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("Borsa verisi çekilemedi. İnternet bağlantısını kontrol edin.")