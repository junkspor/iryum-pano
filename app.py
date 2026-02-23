import streamlit as st
import requests
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import json
import os
from typing import Any, Dict, Optional

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

# --- 3. VERİ ÇEKME MOTORU (HAREM ALTIN) ---
# Streamlit Cloud'da websocket/socket.io bağlantıları sık sık bloklanabildiği için,
# Harem'in web panelinin kullandığı AJAX endpoint'lerini HTTP POST ile çekiyoruz.
# (X-Requested-With header'ı önemli.)

def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s == "-":
        return None
    # 7.431,05 gibi TR formatlarını da temizle
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return None


@st.cache_data(ttl=110, show_spinner=False)
def harem_anlik_fiyatlar() -> Dict[str, Optional[float]]:
    session = requests.Session()
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.haremaltin.com/",
    }
    payload = "dil_kodu=tr"

    def post_json(url: str) -> Dict[str, Any]:
        r = session.post(url, data=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()

    # Not: Harem tarafında altınlar ve dövizler ayrı endpoint'lerden gelebiliyor.
    altin = post_json("https://www.haremaltin.com/dashboard/ajax/altin")
    doviz = post_json("https://www.haremaltin.com/dashboard/ajax/doviz")

    altin_data = altin.get("data", altin)
    doviz_data = doviz.get("data", doviz)

    # Harem ekranındaki ana kalemler için olası kodlar:
    # - HAS ALTIN: ALTIN (bazı yerlerde HAS)
    # - ONS: ONS
    # - USD: USDTRY
    # - USD/KG: USDKG
    def pick_satis(d: Dict[str, Any], *keys: str) -> Optional[float]:
        for k in keys:
            if k in d and isinstance(d[k], dict):
                if "satis" in d[k]:
                    val = _to_float(d[k].get("satis"))
                    if val is not None:
                        return val
            # bazı implementasyonlarda direkt string/float olabilir
            if k in d and not isinstance(d[k], dict):
                val = _to_float(d.get(k))
                if val is not None:
                    return val
        return None

    has_satis = pick_satis(altin_data, "ALTIN", "HAS", "HASALTIN")
    ons_satis = pick_satis(altin_data, "ONS")
    usdkg_satis = pick_satis(altin_data, "USDKG", "USD/KG", "USD_KG")
    usdtry_satis = pick_satis(doviz_data, "USDTRY", "USD")

    return {
        "has_satis": has_satis,
        "ons_satis": ons_satis,
        "usdtry_satis": usdtry_satis,
        "usdkg_satis": usdkg_satis,
    }


f = harem_anlik_fiyatlar()
ons = f.get("ons_satis")
dolar = f.get("usdtry_satis")
canli_teorik_has = f.get("has_satis")
altinkg_usd = f.get("usdkg_satis")

if (ons is None) or (dolar is None) or (canli_teorik_has is None):
    st.error(
        "Harem Altın'dan fiyatlar çekilemedi. "
        "(Endpoint değişmiş/engellenmiş olabilir.)"
    )
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
usdkg_txt = f" | ALTIN KG/USD: {altinkg_usd:,.2f} $" if altinkg_usd is not None else ""
st.markdown(
    f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺{usdkg_txt} | Saat: {saat}</div>",
    unsafe_allow_html=True,
)