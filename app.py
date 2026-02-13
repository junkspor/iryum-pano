import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide")

# 2 Dakikada bir yenileme (120000 ms)
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- 2. TÜRKİYE SAATİ FONKSİYONU ---
def turkiye_saati_al():
    tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(tz).strftime('%H:%M:%S')

# --- 3. REKLAM TEMİZLİĞİ VE TABELA CSS ---
st.markdown("""
<style>
    /* Reklamları ve Streamlit yazılarını mobilde dahi kökten sil */
    footer {visibility: hidden !important; display: none !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    [data-testid="stStatusWidget"] {display:none !important;}
    
    /* Mobildeki "Hosted with Streamlit" rozetini kazı */
    div[class^="viewerBadge_container"], 
    div[class*="viewerBadge_container"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Üst menü (sağdaki üç nokta) gizle ama ok işaretine (panel) dokunma */
    #MainMenu {visibility: hidden !important;}
    [data-testid="stHeader"] {background: transparent !important;}

    /* Genel Arka Plan */
    .stApp { background-color: #000000; }
    
    /* Yan Panel (Yönetici) */
    [data-testid="stSidebar"] { 
        background-color: #111111; 
        border-right: 1px solid #333; 
    }

    /* Tablo Tasarımı */
    .header-container { display: flex; justify-content: flex-end; align-items: center; background-color: #222; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .header-text { color: #ffffff; font-size: clamp(14px, 3vw, 28px); font-weight: bold; text-align: center; width: 100%; }
    .row-wrapper { display: flex; align-items: baseline; padding: 10px 0; border-bottom: 1px solid #333; }
    .product-name { flex: 1.2; font-size: clamp(14px, 3.2vw, 36px); font-weight: bold; color: #ffffff; white-space: nowrap; }
    .price-container { flex: 1; display: flex; justify-content: flex-end; align-items: baseline; }
    .price-buy { font-size: clamp(18px, 4.5vw, 55px); font-weight: bold; color: #2ecc71; font-family: 'Courier New', monospace; }
    .price-sell { font-size: clamp(20px, 5.5vw, 70px); font-weight: 900; color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 0, 0.5); margin-left: 10px; }
    .hidden { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 4. YÖNETİCİ PANELİ (SOLDAKİ OK) ---
st.sidebar.header("💎 İRYUM YÖNETİCİ")
st.sidebar.markdown("---")
s_adj = st.sidebar.slider("Satışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)
a_adj = st.sidebar.slider("Alışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)

# --- 5. VERİ ÇEKME ---
def canlı_ons_al():
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d", interval="1m")
        return data['Close'].iloc[-1]
    except:
        return None

canlı_ons = canlı_ons_al()

# --- 6. BAŞLIK VE TABLO MANTIĞI ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px);'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

col_h1, col_h2, col_h3 = st.columns([1.2, 1, 1])
with col_h2: st.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
with col_h3: st.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

# !!! DİKKAT: Buradan sonraki her satır 4 boşluk içerdedir (Hizalama Burasıdır)
if canlı_ons:
    r_ons = 4970.0
    deg = canlı_ons / r_ons

    def satir(isim, ref_a, ref_s):
        g_a = (ref_a * deg) + a_adj if ref_a > 0 else 0
g_s = (ref_s * deg) + s_adj if ref_s > 0 else 0
        a_h = f'<span class="price-buy">{g_a:,.2f}</span>' if g_a > 0 else '<span class="price-buy hidden">----</span>'
        s_h = f'<span class="price-sell">{g_s:,.2f}</span>' if g_s > 0 else '<span class="price-sell hidden">----</span>'
        st.markdown(f'<div class="row-wrapper"><div class="product-name">{isim}</div><div class="price-container">{a_h}</div><div class="price-container">{s_h}</div></div>', unsafe_allow_html=True)

    # ÜRÜN LİSTESİ
    satir("24 AYAR (HAS)", 0, 7350.00)
    satir("22 AYAR SATIŞ", 0, 7300.00)
    satir("14 AYAR", 0, 6900.00)
    satir("22 AYAR ALIŞ", 6350.00, 0)
    satir("BEŞLİ", 237500.00, 250000.00)
    satir("TAM (ATA)", 47500.00, 50000.00)
    satir("YARIM", 23100.00, 24400.00)
    satir("ÇEYREK", 11550.00, 12200.00)
    satir("GRAM (HAS)", 7100.00, 7500.00)

    # ALT BİLGİ
    st.markdown(f"<div style='text-align: center; color: #555; font-size: 16px; margin-top: 25px;'>ONS: {canlı_ons:,.2f} $ | Güncelleme: {turkiye_saati_al()} (TSİ)</div>", unsafe_allow_html=True)
else:
    st.error("Piyasa verisi çekilemedi.")