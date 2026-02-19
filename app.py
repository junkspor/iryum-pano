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

# --- 3. VERİ ÇEKME MOTORU ---
def veri_getir(sembol):
    try:
        return yf.Ticker(sembol).history(period="1d", interval="1m")['Close'].iloc[-1]
    except:
        return None

ons = veri_getir("GC=F")
dolar = veri_getir("TRY=X")

if not ons or not dolar:
    st.error("Borsa verisi çekilemedi. İnternet bağlantısını kontrol edin.")
    st.stop()

# Uluslararası formüle göre teorik Has
canli_teorik_has = (ons / 31.1034768) * dolar

# --- 4. HAFIZA KURULUMU ---
def hafiza_kur(degisken, baslangic=0.0):
    if degisken not in st.session_state:
        st.session_state[degisken] = baslangic

# Sistemin arka planda baz alacağı teorik fiyat kilidi
hafiza_kur('kayitli_teorik_has', canli_teorik_has)

hafiza_kur('g_24')
hafiza_kur('g_22_s')
hafiza_kur('g_14')
hafiza_kur('g_22_a')
hafiza_kur('g_besli_a')
hafiza_kur('g_besli_s')
hafiza_kur('g_tam_a')
hafiza_kur('g_tam_s')
hafiza_kur('g_yarim_a')
hafiza_kur('g_yarim_s')
hafiza_kur('g_ceyrek_a')
hafiza_kur('g_ceyrek_s')
hafiza_kur('g_gram_a')
hafiza_kur('g_gram_s')

# --- 5. BAŞLIK VE FİYAT GİRİŞ FORMU ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

exp = st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN BURAYA TIKLAYIN ⚙️", expanded=True)
frm = exp.form(key="fiyat_formu")

frm.markdown("### 1. Ürünlerin İlk Fiyatları")
c1, c2 = frm.columns(2)
y_24 = c1.number_input("24 Ayar (HAS)", value=float(st.session_state.g_24), step=10.0)
y_22_s = c1.number_input("22 Ayar (SATIŞ)", value=float(st.session_state.g_22_s), step=10.0)
y_14 = c2.number_input("14 Ayar", value=float(st.session_state.g_14), step=10.0)
y_22_a = c2.number_input("22 Ayar (ALIŞ)", value=float(st.session_state.g_22_a), step=10.0)

frm.markdown("### 2. Sarrafiye Grubu (Alış - Satış)")
c3, c4 = frm.columns(2)
y_besli_a = c3.number_input("Beşli (Alış)", value=float(st.session_state.g_besli_a), step=10.0)
y_tam_a = c3.number_input("Tam (Alış)", value=float(st.session_state.g_tam_a), step=10.0)
y_yarim_a = c3.number_input("Yarım (Alış)", value=float(st.session_state.g_yarim_a), step=10.0)
y_ceyrek_a = c3.number_input("Çeyrek (Alış)", value=float(st.session_state.g_ceyrek_a), step=10.0)
y_gram_a = c3.number_input("Gram (Alış)", value=float(st.session_state.g_gram_a), step=10.0)

y_besli_s = c4.number_input("Beşli (Satış)", value=float(st.session_state.g_besli_s), step=10.0)
y_tam_s = c4.number_input("Tam (Satış)", value=float(st.session_state.g_tam_s), step=10.0)
y_yarim_s = c4.number_input("Yarım (Satış)", value=float(st.session_state.g_yarim_s), step=10.0)
y_ceyrek_s = c4.number_input("Çeyrek (Satış)", value=float(st.session_state.g_ceyrek_s), step=10.0)
y_gram_s = c4.number_input("Gram (Satış)", value=float(st.session_state.g_gram_s), step=10.0)

buton = frm.form_submit_button(label="✅ RAKAMLARI SİSTEME İŞLE VE GÜNCELLE")

if buton:
    # SİHİRLİ DOKUNUŞ: Butona basıldığı anki teorik fiyatı hafızaya kilitliyoruz.
    st.session_state.kayitli_teorik_has = canli_teorik_has
    
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

# --- 6. HESAPLAMA VE TABLO BASIMI ---

# Oran = Şu anki küresel fiyat / Bizim kaydettiğimiz andaki küresel fiyat
oran = canli_teorik_has / st.session_state.kayitli_teorik_has if st.session_state.kayitli_teorik_has > 0 else 1.0

c1_h, c2_h, c3_h = st.columns([1.2, 1, 1])
c2_h.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
c3_h.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

def satir_bas(isim, a_fiyat, s_fiyat):
    a_fiyat = a_fiyat or 0.0
    s_fiyat = s_fiyat or 0.0
    
    g_a = (a_fiyat * oran) if a_fiyat > 0 else 0
    g_s = (s_fiyat * oran) if s_fiyat > 0 else 0
    
    a_html = f'<span class="price-buy">{g_a:,.2f}</span>' if g_a > 0 else '<span class="price-buy hidden">----</span>'
    s_html = f'<span class="price-sell">{g_s:,.2f}</span>' if g_s > 0 else '<span class="price-sell hidden">----</span>'
        
    div_satir = f'<div class="row-wrapper"><div class="product-name">{isim}</div><div class="price-container">{a_html}</div><div class="price-container">{s_html}</div></div>'
    st.markdown(div_satir, unsafe_allow_html=True)

satir_bas("24 AYAR (HAS)", 0.0, st.session_state.g_24)
satir_bas("22 AYAR SATIŞ", 0.0, st.session_state.g_22_s)
satir_bas("14 AYAR", 0.0, st.session_state.g_14)
satir_bas("22 AYAR ALIŞ", st.session_state.g_22_a, 0.0)
satir_bas("BEŞLİ", st.session_state.g_besli_a, st.session_state.g_besli_s)
satir_bas("TAM (ATA)", st.session_state.g_tam_a, st.session_state.g_tam_s)
satir_bas("YARIM", st.session_state.g_yarim_a, st.session_state.g_yarim_s)
satir_bas("ÇEYREK", st.session_state.g_ceyrek_a, st.session_state.g_ceyrek_s)
satir_bas("GRAM (HAS)", st.session_state.g_gram_a, st.session_state.g_gram_s)

saat = datetime.now(pytz.timezone('Europe/Istanbul')).strftime('%H:%M:%S')
st.markdown(f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺ | Saat: {saat}</div>", unsafe_allow_html=True)