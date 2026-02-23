import streamlit as st
import yfinance as yf  # fallback only
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import json
import os
import time

import socketio
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

# --- 3. VERİ ÇEKME MOTORU (Harem Altın) ---
# Bu pano, Harem ekranıyla aynı kalması için ONS / USD / HAS değerlerini Harem'in canlı yayınından alır.
# Not: Yayın formatı zamanla değişebilir; bu yüzden payload esnek şekilde parse ediliyor.

def _to_float_tr(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        # 7.520,66 -> 7520.66 ; 170.900 -> 170900
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return None

def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for vv in obj.values():
            yield from _walk(vv)
    elif isinstance(obj, list):
        for it in obj:
            yield from _walk(it)

def _extract_code_buy_sell(d):
    # Harem payload'larında farklı alan adları gelebiliyor; olası anahtarları dene
    if not isinstance(d, dict):
        return None
    code = d.get("code") or d.get("symbol") or d.get("s") or d.get("k") or d.get("KOD")
    if isinstance(code, str):
        code_u = code.strip().upper()
    else:
        return None

    buy = d.get("alis") or d.get("buy") or d.get("bid") or d.get("b") or d.get("ALIS")
    sell = d.get("satis") or d.get("sell") or d.get("ask") or d.get("a") or d.get("SATIS")

    buy_f = _to_float_tr(buy)
    sell_f = _to_float_tr(sell)

    if buy_f is None and sell_f is None:
        return None
    return code_u, buy_f, sell_f

@st.cache_data(ttl=30)  # 2 dakikada bir yenilemede fazlasıyla yeterli; gereksiz bağlantıyı azaltır
def harem_anlik_fiyatlar(timeout_sec: float = 4.0):
    wanted = {"HAS", "ONS", "USD", "USDTRY", "DOLAR"}
    captured = {}

    sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)

    def on_any(event, data=None):
        payload = data
        for node in _walk(payload):
            parsed = _extract_code_buy_sell(node)
            if not parsed:
                continue
            code, buy_f, sell_f = parsed
            if code in wanted:
                captured[code] = {"buy": buy_f, "sell": sell_f, "event": event}

    # python-socketio: '*' catch-all handler
    sio.on("*", on_any)

    sio.connect("https://socketweb.haremaltin.com", transports=["polling", "websocket"])

    t0 = time.time()
    def _has_ons():
        return "ONS" in captured and (captured["ONS"].get("sell") is not None)
    def _has_usd():
        for k in ("USDTRY", "USD", "DOLAR"):
            if k in captured and captured[k].get("sell") is not None:
                return True
        return False
    def _has_has():
        return "HAS" in captured and (captured["HAS"].get("sell") is not None)

    while time.time() - t0 < timeout_sec and not (_has_ons() and _has_usd() and _has_has()):
        sio.sleep(0.1)

    try:
        sio.disconnect()
    except Exception:
        pass

    return captured

# Harem'den çek
f = harem_anlik_fiyatlar()

ons = (f.get("ONS") or {}).get("sell")
dolar = (f.get("USDTRY") or f.get("USD") or f.get("DOLAR") or {}).get("sell")
canli_teorik_has = (f.get("HAS") or {}).get("sell")

if ons is None or dolar is None or canli_teorik_has is None:
    st.error("Harem verisi çekilemedi (ONS / USD / HAS). İnternet bağlantısını kontrol edin veya biraz sonra tekrar deneyin.")
    st.stop()

# --- 4. KALICI HAFIZA (JSON) SİSTEMİ ---
DOSYA_ADI = "fiyat_hafizasi.json"

varsayilan_veriler = {
    'kayitli_teorik_has': 0.0, 'g_24': 0.0, 'g_22_s': 0.0, 'g_14': 0.0, 'g_22_a': 0.0,
    'g_besli_a': 0.0, 'g_besli_s': 0.0, 'g_tam_a': 0.0, 'g_tam_s': 0.0,
    'g_yarim_a': 0.0, 'g_yarim_s': 0.0, 'g_ceyrek_a': 0.0, 'g_ceyrek_s': 0.0,
    'g_gram_a': 0.0, 'g_gram_s': 0.0
}

# Sayfa her açıldığında dosyadan son kaydedilen rakamları oku
if os.path.exists(DOSYA_ADI):
    try:
        with open(DOSYA_ADI, "r") as dosya:
            kalici_hafiza = json.load(dosya)
    except:
        kalici_hafiza = varsayilan_veriler
else:
    kalici_hafiza = varsayilan_veriler

# Okunan verileri sistemin anlık hafızasına yükle
for anahtar, deger in kalici_hafiza.items():
    if anahtar not in st.session_state:
        st.session_state[anahtar] = deger

# --- 5. BAŞLIK VE FİYAT GİRİŞ FORMU ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

exp = st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN BURAYA TIKLAYIN ⚙️", expanded=True)
frm = exp.form(key="fiyat_formu")

frm.markdown("### 1. Tek Fiyatlı Ürünler")
y_24 = frm.number_input("24 Ayar (HAS)", value=float(st.session_state.g_24), step=10.0)
y_22_s = frm.number_input("22 Ayar (SATIŞ)", value=float(st.session_state.g_22_s), step=10.0)
y_14 = frm.number_input("14 Ayar", value=float(st.session_state.g_14), step=10.0)
y_22_a = frm.number_input("22 Ayar (ALIŞ)", value=float(st.session_state.g_22_a), step=10.0)

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
    # 1. Anlık hafızayı güncelle
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

    # 2. Asla Silinmesin Diye JSON DOSYASINA YAZ (Kalıcı Kayıt)
    yeni_kayit_verisi = {
        'kayitli_teorik_has': canli_teorik_has, 'g_24': y_24, 'g_22_s': y_22_s, 'g_14': y_14, 'g_22_a': y_22_a,
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
st.markdown(f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺ | Saat: {saat}</div>", unsafe_allow_html=True)