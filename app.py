import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide")

# 2 Dakikada bir yenileme
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- TÜRKİYE SAATİ ---
def turkiye_saati_al():
    tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(tz).strftime('%H:%M:%S')

# --- GELİŞMİŞ CSS (TAM HİZALAMA VE TABLET UYUMU) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; }
    
    /* Yan Panel */
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    
    /* Başlık Alanı */
    .header-container {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        background-color: #222;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .header-text {
        color: #ffffff;
        font-size: clamp(16px, 3vw, 28px);
        font-weight: bold;
        text-align: center;
        width: 100%;
    }

    /* Ürün ve Fiyat Konteynırı */
    .row-wrapper {
        display: flex;
        align-items: baseline; /* Rakamları taban çizgisinde hizalar */
        padding: 10px 0;
        border-bottom: 1px solid #333;
    }
    
    .product-name {
        flex: 1.2; /* İsim alanı */
        font-size: clamp(16px, 3.2vw, 36px);
        font-weight: bold;
        color: #ffffff;
        white-space: nowrap;
    }
    
    .price-container {
        flex: 1; /* Fiyat alanı */
        display: flex;
        justify-content: flex-end;
        align-items: baseline;
    }

    .price-buy {
        font-size: clamp(22px, 4.5vw, 55px);
        font-weight: bold;
        color: #2ecc71;
        font-family: 'Courier New', monospace;
        text-align: right;
        line-height: 1; /* Kaymayı önlemek için sabit satır yüksekliği */
    }
    
    .price-sell {
        font-size: clamp(26px, 5.5vw, 70px);
        font-weight: 900;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        text-align: right;
        text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        line-height: 1;
        margin-left: 10px;
    }

    /* Gizleme ve Çizgi Ayarı */
    .hidden { visibility: hidden; }
    hr { display: none; } /* Kendi satır yapımızı kurduğumuz için standart çizgiyi gizliyoruz */
</style>
""", unsafe_allow_html=True)

# --- YAN PANEL ---
st.sidebar.header("💎 İryum Yönetici")
satis_adjust = st.sidebar.slider("Satışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)
alis_adjust = st.sidebar.slider("Alışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)

# --- VERİ ÇEKME ---
def canlı_ons_al():
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d", interval="1m")
        return data['Close'].iloc[-1]
    except:
        return None

canlı_ons = canlı_ons_al()

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(30px, 6vw, 55px); margin-bottom: 10px;'>İRYUM CANLI PANO</h1>", unsafe_allow_html=True)

# --- TABLO BAŞLIKLARI ---
h_col1, h_col2, h_col3 = st.columns([1.2, 1, 1])
with h_col2: st.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
with h_col3: st.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

if canlı_ons:
    ref_ons = 4970.0
    değişim = canlı_ons / ref_ons

    def satir_yaz(isim, ref_alis, ref_satis):
        g_alis = (ref_alis * değişim) + alis_adjust if ref_alis > 0 else 0
        g_satis = (ref_satis * değişim) + satis_adjust if ref_satis > 0 else 0
        
        # HTML yapısını tek bir blokta basıyoruz ki CSS tam hükmedebilsin
alis_html = f'<span class="price-buy">{g_alis:,.2f}</span>' if g_alis > 0 else '<span class="price-buy hidden">----</span>'
               
        st.markdown(f"""
            <div class="row-wrapper">
                <div class="product-name">{isim}</div>
                <div class="price-container">{alis_html}</div>
                <div class="price-container">{satis_html}</div>
            </div>
        """, unsafe_allow_html=True)

    # --- LİSTE ---
    satir_yaz("24 AYAR (HAS)", 0, 7350.00)
    satir_yaz("22 AYAR SATIŞ", 0, 7300.00)
    satir_yaz("14 AYAR", 0, 6900.00)
    satir_yaz("22 AYAR ALIŞ", 6350.00, 0)
    satir_yaz("BEŞLİ", 237500.00, 250000.00)
    satir_yaz("TAM (ATA)", 47500.00, 50000.00)
    satir_yaz("YARIM", 23100.00, 24400.00)
    satir_yaz("ÇEYREK", 11550.00, 12200.00)
    satir_yaz("GRAM (HAS)", 7100.00, 7500.00)

    # Alt Bilgi
    st.markdown(f"""
        <div style='text-align: center; color: #555; font-size: 18px; margin-top: 25px;'>
            ONS: {canlı_ons:,.2f} $ | Güncelleme: {turkiye_saati_al()} (TSİ)
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("Piyasa verisi çekilemedi.")