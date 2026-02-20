import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import json
import os
import requests

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
    .form-urun-baslik { color: #aaa; margin-top: 15px; margin-bottom: -15px; font-size: 16px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 3. AKILLI VERİ ÇEKME MOTORU (BULUT ENGELİNİ AŞAN YAPI) ---
def gercek_piyasa_verisi_al():
    # Streamlit bulut sunucularını gizlemek için sahte tarayıcı (Chrome) kimliği
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # 1. HEDEF: TRUNCGIL API (Kapalıçarşı verisini bulut sunucularına kapatmayan sağlam sistem)
    try:
        r = requests.get("https://finans.truncgil.com/today.json", headers=headers, timeout=5)
        veri = r.json()
        ons = float(veri['ONS']['Satış'].replace('.', '').replace(',', '.'))
        usd = float(veri['USD']['Satış'].replace('.', '').replace(',', '.'))
        return ons, usd, "Kapalıçarşı (Serbest Piyasa)"
    except:
        pass
        
    # 2. HEDEF: HAREM ALTIN (Eğer Cloudflare o an sahte kimliğe izin verirse)
    try:
        r = requests.get("https://www.haremaltin.com/dashboard/ajax/doviz", headers=headers, timeout=5)
        veri = r.json()['data']
        return float(veri['ONS']['satis']), float(veri['USDTRY']['satis']), "Harem Altın"
    except:
        pass

    # 3. HEDEF: GENELPARA
    try:
        r = requests.get("https://api.genelpara.com/embed/para.json", headers=headers, timeout=5)
        veri = r.json()
        return float(veri['ONS']['satis']), float(veri['USD']['satis']), "GenelPara"
    except:
        pass
        
    # 4. HEDEF: YAHOO (Uluslararası Yedek)
    try:
        ons_y = yf.Ticker("GC=F").history(period="1d", interval="1m")['Close'].iloc[-1]
        dolar_y = yf.Ticker("TRY=X").history(period="1d", interval="1m")['Close'].iloc[-1]
        return float(ons_y), float(dolar_y), "Uluslararası Spot (Yedek)"
    except:
        return None, None, "Bağlantı Koptu"

ons, dolar, veri_kaynagi = gercek_piyasa_verisi_al()
# --- 4. KALICI HAFIZA (JSON) SİSTEMİ ---
DOSYA_ADI = "fiyat_hafizasi.json"
varsayilan_veriler = {
    'kayitli_teorik_has': 0.0,
    'g_24': 0.0, 'g_22_s': 0.0, 'g_14': 0.0, 'g_22_a': 0.0,
    'g_besli_a': 0.0, 'g_besli_s': 0.0, 'g_tam_a': 0.0, 'g_tam_s': 0.0,
    'g_yarim_a': 0.0, 'g_yarim_s': 0.0, 'g_ceyrek_a': 0.0, 'g_ceyrek_s': 0.0,
    'g_gram_a': 0.0, 'g_gram_s': 0.0
}

if os.path.exists(DOSYA_ADI):
    try:
        with open(DOSYA_ADI, "r") as dosya:
            kalici_hafiza = json.load(dosya)
    except: kalici_hafiza = varsayilan_veriler
else: kalici_hafiza = varsayilan_veriler

for anahtar, deger in kalici_hafiza.items():
    if anahtar not in st.session_state:
        st.session_state[anahtar] = deger

# --- ÖLÜMSÜZLÜK MODU (ÇÖKMEYİ ENGELLE) ---
if not ons or not dolar:
    if st.session_state.kayitli_teorik_has > 0:
        st.warning("⚠️ Borsa siteleri güvenlik duvarını açtı. Sistem çökmek yerine son girdiğiniz oranlarla çalışmaya devam ediyor!")
        canli_teorik_has = st.session_state.kayitli_teorik_has
        ons = 0.0
        dolar = 0.0
        veri_kaynagi = "ÇEVRİMDIŞI HAFIZA KORUMASI"
    else:
        st.error("Hiçbir borsaya bağlanılamadı ve hafızada fiyat yok. İnterneti kontrol edin.")
        st.stop()
else:
    canli_teorik_has = (ons / 31.1034768) * dolar

# --- 5. BAŞLIK VE FİYAT GİRİŞ FORMU ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

exp = st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN TIKLAYIN ⚙️", expanded=True)
frm = exp.form(key="fiyat_formu")

frm.markdown("### 1. Tek Fiyatlı Ürünler")
c1, c2 = frm.columns(2)
y_24 = c1.number_input("24 Ayar (HAS)", value=float(st.session_state.g_24), step=10.0)
y_22_s = c1.number_input("22 Ayar (SATIŞ)", value=float(st.session_state.g_22_s), step=10.0)
y_14 = c2.number_input("14 Ayar", value=float(st.session_state.g_14), step=10.0)
y_22_a = c2.number_input("22 Ayar (ALIŞ)", value=float(st.session_state.g_22_a), step=10.0)

frm.markdown("### 2. Sarrafiye Grubu (Alış - Satış)")
frm.markdown('<p class="form-urun-baslik">BEŞLİ</p>', unsafe_allow_html=True)
c_b1, c_b2 = frm.columns(2)
y_besli_a = c_b1.number_input("Alış (Beşli)", value=float(st.session_state.g_besli_a), step=10.0)
y_besli_s = c_b2.number_input("Satış (Beşli)", value=float(st.session_state.g_besli_s), step=10.0)

frm.markdown('<p class="form-urun-baslik">TAM (ATA)</p>', unsafe_allow_html=True)
c_t1, c_t2 = frm.columns(2)
y_tam_a = c_t1.number_input("Alış (Tam)", value=float(st.session_state.g_tam_a), step=10.0)
y_tam_s = c_t2.number_input("Satış (Tam)", value=float(st.session_state.g_tam_s), step=10.0)

frm.markdown('<p class="form-urun-baslik">YARIM</p>', unsafe_allow_html=True)
c_y1, c_y2 = frm.columns(2)
y_yarim_a = c_y1.number_input("Alış (Yarım)", value=float(st.session_state.g_yarim_a), step=10.0)
y_yarim_s = c_y2.number_input("Satış (Yarım)", value=float(st.session_state.g_yarim_s), step=10.0)

frm.markdown('<p class="form-urun-baslik">ÇEYREK</p>', unsafe_allow_html=True)
c_c1, c_c2 = frm.columns(2)
y_ceyrek_a = c_c1.number_input("Alış (Çeyrek)", value=float(st.session_state.g_ceyrek_a), step=10.0)
y_ceyrek_s = c_c2.number_input("Satış (Çeyrek)", value=float(st.session_state.g_ceyrek_s), step=10.0)

frm.markdown('<p class="form-urun-baslik">GRAM (HAS)</p>', unsafe_allow_html=True)
c_g1, c_g2 = frm.columns(2)
y_gram_a = c_g1.number_input("Alış (Gram)", value=float(st.session_state.g_gram_a), step=10.0)
y_gram_s = c_g2.number_input("Satış (Gram)", value=float(st.session_state.g_gram_s), step=10.0)

frm.markdown("<br>", unsafe_allow_html=True)
buton = frm.form_submit_button(label="✅ RAKAMLARI SİSTEME İŞLE VE GÜNCELLE")

if buton:
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

    yeni_kayit_verisi = {
        'kayitli_teorik_has': st.session_state.kayitli_teorik_has, 
        'g_24': y_24, 'g_22_s': y_22_s, 'g_14': y_14, 'g_22_a': y_22_a,
        'g_besli_a': y_besli_a, 'g_besli_s': y_besli_s, 'g_tam_a': y_tam_a, 'g_tam_s': y_tam_s,
        'g_yarim_a': y_yarim_a, 'g_yarim_s': y_yarim_s, 'g_ceyrek_a': y_ceyrek_a, 'g_ceyrek_s': y_ceyrek_s,
        'g_gram_a': y_gram_a, 'g_gram_s': y_gram_s
    }
    try:
        with open(DOSYA_ADI, "w") as dosya:
            json.dump(yeni_kayit_verisi, dosya)
    except:
        pass

# --- 6. HESAPLAMA VE TABLO BASIMI ---
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

# Alt bilgiye sadeleştirilmiş USD Satış ve Kaynak bilgisi
st.markdown(f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD (Satış): {dolar:,.4f} ₺ | Saat: {saat} | Kaynak: {veri_kaynagi}</div>", unsafe_allow_html=True)