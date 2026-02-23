import streamlit as st
import requests
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import json
import os
from typing import Any, Dict, Optional, Tuple

# --- 1) SAYFA AYARLARI ---
st.set_page_config(page_title="İryum Canlı Pano", layout="wide")
# 2 dakikada bir yenile
st_autorefresh(interval=120000, key="fiyat_sayaci")

# --- 2) REKLAM GİZLEYİCİ CSS ---
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

# --- 3) KALICI HAFIZA (JSON) ---
DOSYA_ADI = "fiyat_hafizasi.json"

# Hem kullanıcı girdileri, hem de "son başarılı referans fiyatlar" burada dursun.
varsayilan_veriler = {
    # Kullanıcı girişleri
    "kayitli_teorik_has": 0.0,
    "g_24": 0.0, "g_22_s": 0.0, "g_14": 0.0, "g_22_a": 0.0,
    "g_besli_a": 0.0, "g_besli_s": 0.0, "g_tam_a": 0.0, "g_tam_s": 0.0,
    "g_yarim_a": 0.0, "g_yarim_s": 0.0, "g_ceyrek_a": 0.0, "g_ceyrek_s": 0.0,
    "g_gram_a": 0.0, "g_gram_s": 0.0,
    "altinkg_usd_satis": 0.0,

    # Referans fiyatlar (son başarılı çekim)
    "last_usdtry_satis": 0.0,
    "last_has_satis": 0.0,
    "last_harem_ons_satis": 0.0,
    "last_oanda_ons_satis": 0.0,
}

def _load_persistent() -> Dict[str, Any]:
    if os.path.exists(DOSYA_ADI):
        try:
            with open(DOSYA_ADI, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return {**varsayilan_veriler, **d}
        except Exception:
            pass
    return dict(varsayilan_veriler)

def _save_persistent(d: Dict[str, Any]) -> None:
    try:
        with open(DOSYA_ADI, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception:
        pass

kalici_hafiza = _load_persistent()

# Session'a yükle (varsa koru)
for k, v in kalici_hafiza.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- 4) HAREM'DEN USD & HAS (SATIŞ) ÇEKME ---
def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s == "-":
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def _pick_satis(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in d and isinstance(d[k], dict):
            if "satis" in d[k]:
                val = _to_float(d[k].get("satis"))
                if val is not None:
                    return val
        if k in d and not isinstance(d[k], dict):
            val = _to_float(d.get(k))
            if val is not None:
                return val
    return None

@st.cache_data(ttl=110, show_spinner=False)
def harem_anlik_fiyatlar() -> Dict[str, Optional[float]]:
    session = requests.Session()

    # Bazı durumlarda WAF daha az takılsın diye önce ana sayfaya bir GET atalım (cookie alır)
    try:
        session.get("https://www.haremaltin.com/", timeout=10, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
    except Exception:
        pass

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.haremaltin.com/",
        "Origin": "https://www.haremaltin.com",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    payload = "dil_kodu=tr"

    def post_json(url: str) -> Dict[str, Any]:
        try:
            r = session.post(url, data=payload, headers=headers, timeout=15)
            if r.status_code != 200:
                return {}
            return r.json()
        except Exception:
            return {}

    altin = post_json("https://www.haremaltin.com/dashboard/ajax/altin")
    doviz = post_json("https://www.haremaltin.com/dashboard/ajax/doviz")

    altin_data = altin.get("data", altin) if isinstance(altin, dict) else {}
    doviz_data = doviz.get("data", doviz) if isinstance(doviz, dict) else {}

    has_satis = _pick_satis(altin_data, "ALTIN", "HAS", "HASALTIN")
    ons_satis = _pick_satis(altin_data, "ONS")
    usdtry_satis = _pick_satis(doviz_data, "USDTRY", "USD")

    return {"has_satis": has_satis, "ons_satis": ons_satis, "usdtry_satis": usdtry_satis}

# --- 5) OANDA'DAN ONS (SATIŞ/ASK) ---
def oanda_ons_satis() -> Tuple[Optional[float], Optional[str]]:
    """(price, reason) döner."""
    token = st.secrets.get("OANDA_TOKEN")
    account_id = st.secrets.get("OANDA_ACCOUNT_ID")
    if not token or not account_id:
        return None, "OANDA secrets eksik (OANDA_TOKEN / OANDA_ACCOUNT_ID)."

    env = (st.secrets.get("OANDA_ENV", "practice") or "practice").strip().lower()
    base = "https://api-fxtrade.oanda.com" if env == "live" else "https://api-fxpractice.oanda.com"
    url = f"{base}/v3/accounts/{account_id}/pricing"

    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"instruments": "XAU_USD"}, timeout=15)
        if r.status_code != 200:
            return None, f"OANDA HTTP {r.status_code}"
        data = r.json()
        prices = data.get("prices") or []
        if not prices:
            return None, "OANDA prices boş"
        asks = prices[0].get("asks") or []
        if not asks:
            return None, "OANDA asks boş"
        return float(asks[0].get("price")), None
    except Exception as e:
        return None, "OANDA istek hatası"

# --- 6) REFERANS FİYATLARI SEÇ (ONS=OANDA, USD+HAS=HAREM) ---
harem = harem_anlik_fiyatlar()

# USD & HAS (Harem satış) — başarısız olursa son kayıtlı değerleri kullan.
dolar = harem.get("usdtry_satis") or float(st.session_state.get("last_usdtry_satis", 0.0) or 0.0) or None
canli_teorik_has = harem.get("has_satis") or float(st.session_state.get("last_has_satis", 0.0) or 0.0) or None

# ONS: OANDA öncelikli; olmazsa Harem; o da olmazsa son kayıtlı
oanda_ons, oanda_reason = oanda_ons_satis()
ons = oanda_ons or harem.get("ons_satis") or float(st.session_state.get("last_oanda_ons_satis", 0.0) or 0.0) or float(st.session_state.get("last_harem_ons_satis", 0.0) or 0.0) or None

# Referanslar geldiyse kalıcı kaydet (bir sonraki blokta erişim var)
if harem.get("usdtry_satis"):
    st.session_state["last_usdtry_satis"] = float(harem["usdtry_satis"])
if harem.get("has_satis"):
    st.session_state["last_has_satis"] = float(harem["has_satis"])
if harem.get("ons_satis"):
    st.session_state["last_harem_ons_satis"] = float(harem["ons_satis"])
if oanda_ons:
    st.session_state["last_oanda_ons_satis"] = float(oanda_ons)

# Kalıcı dosyaya da yaz (sessiz)
kalici_hafiza = _load_persistent()
for k in ["last_usdtry_satis", "last_has_satis", "last_harem_ons_satis", "last_oanda_ons_satis",
          "kayitli_teorik_has", "g_24", "g_22_s", "g_14", "g_22_a",
          "g_besli_a", "g_besli_s", "g_tam_a", "g_tam_s",
          "g_yarim_a", "g_yarim_s", "g_ceyrek_a", "g_ceyrek_s",
          "g_gram_a", "g_gram_s", "altinkg_usd_satis"]:
    if k in st.session_state:
        kalici_hafiza[k] = st.session_state[k]
_save_persistent(kalici_hafiza)

# Kullanıcıyı yormadan sadece uyarı (çöktürme yok)
if dolar is None or canli_teorik_has is None:
    st.warning("Harem'den USD/HAS şu an çekilemedi. Son kayıtlı değerler kullanılıyor.")
if ons is None:
    msg = "ONS fiyatı alınamadı. Son kayıtlı değer yoksa 0 gösterilecek."
    if oanda_reason:
        msg += f" ({oanda_reason})"
    st.warning(msg)
    ons = 0.0
if dolar is None:
    dolar = 0.0
if canli_teorik_has is None:
    canli_teorik_has = 0.0

# --- 7) BAŞLIK VE FİYAT GİRİŞ FORMU ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

exp = st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN BURAYA TIKLAYIN ⚙️", expanded=True)
frm = exp.form(key="fiyat_formu")

# USDKG satış değerini manuel gir (Harem ekranındaki USD KG Satış)
y_altinkg = frm.number_input("ALTIN KG/USD (Satış) [Manuel]", value=float(st.session_state.get("altinkg_usd_satis", 0.0)), step=10.0)

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
    # kayıtlı teorik has = o anki Harem HAS satış (yoksa 0 kalır)
    st.session_state.kayitli_teorik_has = float(canli_teorik_has or 0.0)
    st.session_state.altinkg_usd_satis = float(y_altinkg or 0.0)

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

    # JSON'a yaz
    kalici = _load_persistent()
    for k in [
        "kayitli_teorik_has", "g_24", "g_22_s", "g_14", "g_22_a",
        "g_besli_a", "g_besli_s", "g_tam_a", "g_tam_s",
        "g_yarim_a", "g_yarim_s", "g_ceyrek_a", "g_ceyrek_s",
        "g_gram_a", "g_gram_s", "altinkg_usd_satis",
        "last_usdtry_satis", "last_has_satis", "last_harem_ons_satis", "last_oanda_ons_satis",
    ]:
        kalici[k] = st.session_state.get(k, varsayilan_veriler.get(k, 0.0))
    _save_persistent(kalici)

# --- 8) HESAPLAMA VE TABLO ---
kayitli = float(st.session_state.get("kayitli_teorik_has", 0.0) or 0.0)
oran = (float(canli_teorik_has) / kayitli) if kayitli > 0 else 1.0

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
altinkg_usd = float(st.session_state.get("altinkg_usd_satis", 0.0) or 0.0)
usdkg_txt = f" | ALTIN KG/USD: {altinkg_usd:,.2f} $" if altinkg_usd > 0 else ""

st.markdown(
    f"<div style='text-align: center; color: #555; margin-top: 25px;'>"
    f"ONS: {float(ons):,.2f} $ | USD: {float(dolar):,.4f} ₺{usdkg_txt} | Saat: {saat}"
    f"</div>",
    unsafe_allow_html=True,
)
