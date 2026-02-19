import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide")
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- 2. REKLAM GİZLEYİCİ CSS ---
st.markdown("""
<style>
    footer {visibility: hidden !important; display: none !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0) !important;}
    .stApp { background-color: #000000; }
    
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

# --- 3. HAFIZA (TÜM KUTULAR BAŞLANGIÇTA TAMAMEN BOŞTUR) ---
if 'ref_has' not in st.session_state: st.session_state.ref_has = None
if 'g_24' not in st.session_state: st.session_state.g_24 = None
if 'g_22_s' not in st.session_state: st.session_state.g_22_s = None
if 'g_14' not in st.session_state: st.session_state.g_14 = None
if 'g_22_a' not in st.session_state: st.session_state.g_22_a = None
if 'g_besli_a' not in st.session_state: st.session_state.g_besli_a = None
if 'g_besli_s' not in st.session_state: st.session_state.g_besli_s = None
if 'g_tam_a' not in st.session_state: st.session_state.g_tam_a = None
if 'g_tam_s' not in st.session_state: st.session_state.g_tam_s = None
if 'g_yarim_a' not in st.session_state: st.session_state.g_yarim_a = None
if 'g_yarim_s' not in st.session_state: st.session_state.g_yarim_s = None
if 'g_ceyrek_a' not in st.session_state: st.session_state.g_ceyrek_a = None
if 'g_ceyrek_s' not in st.session_state: st.session_state.g_ceyrek_s = None
if 'g_gram_a' not in st.session_state: st.session_state.g_gram_a = None
if 'g_gram_s' not in st.session_state: st.session_state.g_gram_s = None
if 'a_adj' not in st.session_state: st.session_state.a_adj = 0.0
if 's_adj' not in st.session_state: st.session_state.s_adj = 0.0

# --- 4. BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

# --- 5. FİYAT GİRİŞ PANELİ (AÇILDIĞINDA BOMBOŞ GELECEK) ---
with st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN BURAYA TIKLAYIN ⚙️", expanded=True):
    with st.form(key="fiyat_formu"):
        st.markdown("### 1. Referans Has Fiyatı")
        y_ref = st.number_input("O ANKİ HAS FİYATI:", value=st.session_state.ref_has, step=10.0, placeholder="Örn: 7350.00")
        
        st.markdown("### 2. Tek Fiyatlı Ürünler")
        col1, col2 = st.columns(2)
        with col1:
            y_24 = st.number_input("24 Ayar (Sadece Satış)", value=st.session_state.g_24, step=10.0, placeholder="Örn: 7350.00")
y_22_s = st.number_input("22 Ayar (SATIŞ)", value=st.session_state.g_22_s, step=10.0, placeholder="Örn: 7300.00")
        with col2:
            y_14 = st.number_input("14 Ayar (Sadece Satış)", value=st.session_state.g_14, step=10.0, placeholder="Örn: 6900.00")
            y_22_a = st.number_input("22 Ayar (ALIŞ)", value=st.session_state.g_22_a, step=10.0, placeholder="Örn: 6400.00")
            
        st.markdown("### 3. Çift Fiyatlı Ürünler (Alış - Satış)")
        col3, col4 = st.columns(2)
        with col3:
            y_besli_a = st.number_input("Beşli (Alış)", value=st.session_state.g_besli_a, step=10.0, placeholder="Örn: 240000.00")
            y_tam_a = st.number_input("Tam (Alış)", value=st.session_state.g_tam_a, step=10.0, placeholder="Örn: 48000.00")
            y_yarim_a = st.number_input("Yarım (Alış)", value=st.session_state.g_yarim_a, step=10.0, placeholder="Örn: 23300.00")
            y_ceyrek_a = st.number_input("Çeyrek (Alış)", value=st.session_state.g_ceyrek_a, step=10.0, placeholder="Örn: 11650.00")
            y_gram_a = st.number_input("Gram (Alış)", value=st.session_state.g_gram_a, step=10.0, placeholder="Örn: 7150.00")
        with col4:
            y_besli_s = st.number_input("Beşli (Satış)", value=st.session_state.g_besli_s, step=10.0, placeholder="Örn: 251500.00")
            y_tam_s = st.number_input("Tam (Satış)", value=st.session_state.g_tam_s, step=10.0, placeholder="Örn: 50300.00")
            y_yarim_s = st.number_input("Yarım (Satış)", value=st.session_state.g_yarim_s, step=10.0, placeholder="Örn: 24500.00")
            y_ceyrek_s = st.number_input("Çeyrek (Satış)", value=st.session_state.g_ceyrek_s, step=10.0, placeholder="Örn: 12250.00")
            y_gram_s = st.number_input("Gram (Satış)", value=st.session_state.g_gram_s, step=10.0, placeholder="Örn: 7550.00")

        st.markdown("### 4. Hızlı Makas Ayarı (Zorunlu Değil)")
        y_a_adj = st.slider("Tüm Alışlara Ekle/Çıkar", -500.0, 500.0, float(st.session_state.a_adj), step=1.0)
        y_s_adj = st.slider("Tüm Satışlara Ekle/Çıkar", -500.0, 500.0, float(st.session_state.s_adj), step=1.0)

        submit_button = st.form_submit_button(label="✅ RAKAMLARI SİSTEME İŞLE VE GÜNCELLE")

        if submit_button:
            st.session_state.ref_has = y_ref
            st.session_state.g_24 = y_24
            st.session_state.g_22_s = y_22_s
            st.session_state.g_14 = y_14
            st.session_state.g_22_a = y_22_a
            st.session_state.g_besli_a = y_besli_a
            st.session_state.g_besli_s = y_besli_s
            st.session_state.g_tam_a = y_tam_a
            st.session_state.g_tam_s = y_tam_s
            st.session_state.g_yarim_a = y_yarim_a
            st.session_state.g_yarim_s = y_yarim_s
            st.session_state.g_ceyrek_a = y_ceyrek_a
            st.session_state.g_ceyrek_s = y_ceyrek_s
            st.session_state.g_gram_a = y_gram_a
            st.session_state.g_gram_s = y_gram_s
            st.session_state.a_adj = y_a_adj
            st.session_state.s_adj = y_s_adj

# Sistem boş (None) değerleri görünce hata vermesin diye hepsini 0.0 kabul ettiriyoruz
v_ref = st.session_state.ref_has or 0.0
fiyat_sozlugu = {
    "24 AYAR (HAS)":  [0.0, st.session_state.g_24 or 0.0],
    "22 AYAR SATIŞ":  [0.0, st.session_state.g_22_s or 0.0],
    "14 AYAR":        [0.0, st.session_state.g_14 or 0.0],
    "22 AYAR ALIŞ":   [st.session_state.g_22_a or 0.0, 0.0],
    "BEŞLİ":          [st.session_state.g_besli_a or 0.0, st.session_state.g_besli_s or 0.0],
    "TAM (ATA)":      [st.session_state.g_tam_a or 0.0, st.session_state.g_tam_s or 0.0],
    "YARIM":          [st.session_state.g_yarim_a or 0.0, st.session_state.g_yarim_s or 0.0],
    "ÇEYREK":         [st.session_state.g_ceyrek_a or 0.0, st.session_state.g_ceyrek_s or 0.0],
    "GRAM (HAS)":     [st.session_state.g_gram_a or 0.0, st.session_state.g_gram_s or 0.0]
}
# --- 6. TABLO BAŞLIKLARI ---
c1, c2, c3 = st.columns([1.2, 1, 1])
with c2: st.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
with c3: st.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

# --- 7. VERİ ÇEKME VE HESAPLAMA ---
def turkiye_saati_al():
    tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(tz).strftime('%H:%M:%S')

def canli_ons_al():
    try: return yf.Ticker("GC=F").history(period="1d", interval="1m")['Close'].iloc[-1]
    except: return None

def canli_dolar_al():
    try: return yf.Ticker("TRY=X").history(period="1d", interval="1m")['Close'].iloc[-1]
    except: return None

ons = canli_ons_al()
dolar = canli_dolar_al()

if ons and dolar:
    canli_has = (ons / 31.1034768) * dolar
    degisim_orani = canli_has / v_ref if v_ref > 0 else 1
    
    for isim, degerler in fiyat_sozlugu.items():
        ref_a = degerler[0]
        ref_s = degerler[1]
        
        g_a = (ref_a * degisim_orani) + st.session_state.a_adj if ref_a > 0 else 0
        g_s = (ref_s * degisim_orani) + st.session_state.s_adj if ref_s > 0 else 0
        
        # Eğer rakam girilmemişse (0.0 ise) ekranda yatay çizgi göster
        a_h = f'<span class="price-buy">{g_a:,.2f}</span>' if g_a > 0 else '<span class="price-buy hidden">----</span>'
        s_h = f'<span class="price-sell">{g_s:,.2f}</span>' if g_s > 0 else '<span class="price-sell hidden">----</span>'
        
        html = f'<div class="row-wrapper"><div class="product-name">{isim}</div><div class="price-container">{a_h}</div><div class="price-container">{s_h}</div></div>'
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺ | Saat: {turkiye_saati_al()}</div>", unsafe_allow_html=True)
else:
    st.error("Borsa verisi çekilemedi. İnternet bağlantısını kontrol edin.")