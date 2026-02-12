import streamlit as st
import yfinance as yf
import time
from streamlit_autorefresh import st_autorefresh

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide")

# 2 Dakikada bir (120000 ms) sayfayı zorla yenileme
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- GELİŞMİŞ TASARIM (TABLET UYUMLU VE YEŞİL) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; }
    
    /* Yan Panel (Sidebar) Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #333;
    }
    .stSidebar [data-testid="stMarkdownContainer"] p {
        color: #00ff00;
        font-weight: bold;
    }

    /* Tablo Tasarımı */
    .header-text { 
        color: #ffffff; 
        font-size: clamp(20px, 4vw, 35px); 
        font-weight: bold; 
        text-align: right; 
        background-color: #222; 
        padding: 10px; 
        border-radius: 5px; 
    }
    
    .product-name { 
        font-size: clamp(18px, 3.5vw, 40px); 
        font-weight: bold; 
        color: #ffffff; 
        text-align: left; 
        padding-top: 15px;
        white-space: nowrap; /* Kaymayı önler */
    }
    
    .price-buy { 
        font-size: clamp(25px, 5vw, 60px); 
        font-weight: bold; 
        color: #2ecc71; 
        text-align: right; 
        font-family: 'Courier New', monospace; 
        white-space: nowrap; 
    }
    
    .price-sell { 
        font-size: clamp(30px, 6vw, 75px); 
        font-weight: 900; 
        color: #00ff00; 
        text-align: right; 
        font-family: 'Courier New', monospace; 
        text-shadow: 0 0 15px #00ff00; 
        white-space: nowrap; 
    }
    
    hr { border-color: #444; margin: 8px 0; }
    
    /* Sütunlar arası boşluğu daralt */
    [data-testid="column"] {
        padding: 0 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SOL PANEL (MAKAS VE DÜZELTME) ---
st.sidebar.header("💎 İryum Yönetici")
st.sidebar.markdown("---")

st.sidebar.subheader("📈 Satış Fiyatları")
satis_adjust = st.sidebar.slider("Tüm Satışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)

st.sidebar.subheader("📉 Alış Fiyatları")
alis_adjust = st.sidebar.slider("Tüm Alışları Artır/Azalt (TL)", -500.0, 500.0, 0.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.write("Bu ayarlar Ons değişimine ek olarak fiyatları manuel güncellemenizi sağlar.")

# --- VERİ ÇEKME (CANLI ONS) ---
def canlı_ons_al():
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d", interval="1m")
        return data['Close'].iloc[-1]
    except:
        return None

canlı_ons = canlı_ons_al()

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: 50px; margin-bottom: 20px;'>İRYUM CANLI PANO</h1>", unsafe_allow_html=True)

# --- TABLO BAŞLIKLARI ---
c1, c2, c3 = st.columns([3.5, 3, 3.5])
with c2: st.markdown('<div class="header-text">ALIŞ</div>', unsafe_allow_html=True)
with c3: st.markdown('<div class="header-text">SATIŞ</div>', unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

if canlı_ons:
    # 20:30 REFERANS HESABI
    ref_ons = 4970.0
    değişim = canlı_ons / ref_ons

    def satir_yaz(isim, ref_alis, ref_satis):
        # Borsa değişimi + Sizin sol panelden yaptığınız manuel ayar
        g_alis = (ref_alis * değişim) + alis_adjust if ref_alis > 0 else 0
        g_satis = (ref_satis * değişim) + satis_adjust if ref_satis > 0 else 0
        
        col1, col2, col3 = st.columns([3.5, 3, 3.5])
        col1.markdown(f'<div class="product-name">{isim}</div>', unsafe_allow_html=True)
        # ALIŞ
        col2.markdown(f'<div class="price-buy">{"----" if g_alis == 0 else f"{g_alis:,.2f}"}</div>', unsafe_allow_html=True)
        # SATIŞ
        col3.markdown(f'<div class="price-sell">{"----" if g_satis == 0 else f"{g_satis:,.2f}"}</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

# --- LİSTE (İstediğiniz Format) ---
    satir_yaz("24 AYAR (HAS)", 0, 7350.00)
    satir_yaz("22 AYAR SATIŞ", 0, 7300.00)
    satir_yaz("14 AYAR", 0, 6900.00)
    satir_yaz("22 AYAR ALIŞ", 6350.00, 0)
    satir_yaz("BEŞLİ", 237500.00, 250000.00)
    satir_yaz("TAM (ATA)", 47500.00, 50000.00)
    satir_yaz("YARIM", 23100.00, 24400.00)
    satir_yaz("ÇEYREK", 11550.00, 12200.00)
    satir_yaz("GRAM (HAS)", 7100.00, 7500.00)

    # Bilgilendirme
    st.markdown(f"""
        <div style='text-align: center; color: #555; font-size: 18px; margin-top: 20px;'>
            ONS: {canlı_ons:,.2f} $ | Son Güncelleme: {time.strftime('%H:%M:%S')}
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("Piyasa verisi çekilemedi. Lütfen bağlantıyı kontrol edin.")