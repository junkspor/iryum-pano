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

# --- 3. HAFIZA ---
DOSYA_ADI = "fiyat_hafizasi.json"
varsayilan = {'son_ons': 0.0, 'son_usd': 0.0, 'kayitli_teorik_has': 0.0, 'g_24': 0.0, 'g_22_s': 0.0, 'g_14': 0.0, 'g_22_a': 0.0, 'g_besli_a': 0.0, 'g_besli_s': 0.0, 'g_tam_a': 0.0, 'g_tam_s': 0.0, 'g_yarim_a': 0.0, 'g_yarim_s': 0.0, 'g_ceyrek_a': 0.0, 'g_ceyrek_s': 0.0, 'g_gram_a': 0.0, 'g_gram_s': 0.0}

try:
    with open(DOSYA_ADI, "r") as dosya:
        kalici_hafiza = json.load(dosya)
except:
    kalici_hafiza = varsayilan

for k, v in varsayilan.items():
    if k not in st.session_state:
        st.session_state[k] = kalici_hafiza.get(k, v)

# --- 4. DOĞRUDAN YAHOO API MOTORU (ASLA ÇÖKMEZ) ---
def veri_getir():
    ons_val, usd_val = 0.0, 0.0
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. YÖNTEM: Yahoo'nun Kendi Gizli Veri Damarı (En Sağlamı)
    try:
        r_ons = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X", headers=headers, timeout=5)
        ons_val = float(r_ons.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        
        r_usd = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/TRY=X", headers=headers, timeout=5)
        usd_val = float(r_usd.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        return ons_val, usd_val
    except: pass

    # 2. YÖNTEM: Yfinance Kütüphanesi (Yedek - Hafta Sonu Korumalı)
    try:
        ons_val = float(yf.Ticker("XAUUSD=X").history(period="5d")['Close'].dropna().iloc[-1])
        usd_val = float(yf.Ticker("TRY=X").history(period="5d")['Close'].dropna().iloc[-1])
    except: pass
        
    return ons_val, usd_val

ons, dolar = veri_getir()

# Eğer iki yöntem de anlık koparsa, eski hafızayı kullan
if ons == 0.0 or dolar == 0.0:
    ons = st.session_state.get('son_ons', 0.0)
    dolar = st.session_state.get('son_usd', 0.0)

# Ekranda uyarı ver ama SAKIN sistemi kilitleme! (st.stop söküldü)
if ons == 0.0 or dolar == 0.0:
    st.error("⚠️ Yahoo Finance sunucularına şu an erişilemiyor. Lütfen paneli birazdan yenileyin. (Formu kullanmaya devam edebilirsiniz)")
st.session_state.update({'son_ons': ons, 'son_usd': dolar})
canli_teorik_has = (ons / 31.1034768) * dolar if (ons > 0 and dolar > 0) else 0.0

# --- 5. EKRAN VE GİRİŞ FORMU ---
st.markdown("<h1 style='text-align: center; color: #00ff00; font-size: clamp(25px, 6vw, 55px); margin-bottom: 10px;'>🪙 İRYUM CANLI PANO 🪙</h1>", unsafe_allow_html=True)

exp = st.expander("⚙️ FİYATLARI GİRMEK VE GÜNCELLEMEK İÇİN TIKLAYIN ⚙️", expanded=True)
frm = exp.form(key="fiyat_formu")

frm.markdown("### 1. Tek Fiyatlı Ürünler")
c1, c2 = frm.columns(2)
y_24 = c1.number_input("24 Ayar (HAS)", value=float(st.session_state.get('g_24', 0.0)), step=10.0)
y_22_s = c1.number_input("22 Ayar (SATIŞ)", value=float(st.session_state.get('g_22_s', 0.0)), step=10.0)
y_14 = c2.number_input("14 Ayar", value=float(st.session_state.get('g_14', 0.0)), step=10.0)
y_22_a = c2.number_input("22 Ayar (ALIŞ)", value=float(st.session_state.get('g_22_a', 0.0)), step=10.0)

frm.markdown("### 2. Sarrafiye Grubu (Alış - Satış)")
frm.markdown('<p class="form-urun-baslik">BEŞLİ</p>', unsafe_allow_html=True)
cb1, cb2 = frm.columns(2)
y_besli_a = cb1.number_input("Alış (Beşli)", value=float(st.session_state.get('g_besli_a', 0.0)), step=10.0)
y_besli_s = cb2.number_input("Satış (Beşli)", value=float(st.session_state.get('g_besli_s', 0.0)), step=10.0)

frm.markdown('<p class="form-urun-baslik">TAM (ATA)</p>', unsafe_allow_html=True)
ct1, ct2 = frm.columns(2)
y_tam_a = ct1.number_input("Alış (Tam)", value=float(st.session_state.get('g_tam_a', 0.0)), step=10.0)
y_tam_s = ct2.number_input("Satış (Tam)", value=float(st.session_state.get('g_tam_s', 0.0)), step=10.0)

frm.markdown('<p class="form-urun-baslik">YARIM</p>', unsafe_allow_html=True)
cy1, cy2 = frm.columns(2)
y_yarim_a = cy1.number_input("Alış (Yarım)", value=float(st.session_state.get('g_yarim_a', 0.0)), step=10.0)
y_yarim_s = cy2.number_input("Satış (Yarım)", value=float(st.session_state.get('g_yarim_s', 0.0)), step=10.0)

frm.markdown('<p class="form-urun-baslik">ÇEYREK</p>', unsafe_allow_html=True)
cc1, cc2 = frm.columns(2)
y_ceyrek_a = cc1.number_input("Alış (Çeyrek)", value=float(st.session_state.get('g_ceyrek_a', 0.0)), step=10.0)
y_ceyrek_s = cc2.number_input("Satış (Çeyrek)", value=float(st.session_state.get('g_ceyrek_s', 0.0)), step=10.0)

frm.markdown('<p class="form-urun-baslik">GRAM (HAS)</p>', unsafe_allow_html=True)
cg1, cg2 = frm.columns(2)
y_gram_a = cg1.number_input("Alış (Gram)", value=float(st.session_state.get('g_gram_a', 0.0)), step=10.0)
y_gram_s = cg2.number_input("Satış (Gram)", value=float(st.session_state.get('g_gram_s', 0.0)), step=10.0)

frm.markdown("<br>", unsafe_allow_html=True)
buton = frm.form_submit_button(label="✅ RAKAMLARI SİSTEME İŞLE VE GÜNCELLE")

if buton:
    veri_paketi = {'kayitli_teorik_has': canli_teorik_has, 'g_24': y_24, 'g_22_s': y_22_s, 'g_14': y_14, 'g_22_a': y_22_a, 'g_besli_a': y_besli_a, 'g_besli_s': y_besli_s, 'g_tam_a': y_tam_a, 'g_tam_s': y_tam_s, 'g_yarim_a': y_yarim_a, 'g_yarim_s': y_yarim_s, 'g_ceyrek_a': y_ceyrek_a, 'g_ceyrek_s': y_ceyrek_s, 'g_gram_a': y_gram_a, 'g_gram_s': y_gram_s, 'son_ons': ons, 'son_usd': dolar}
    st.session_state.update(veri_paketi)
    try:
        with open(DOSYA_ADI, "w") as dosya:
            json.dump(veri_paketi, dosya)
    except: pass

oran = canli_teorik_has / st.session_state.get('kayitli_teorik_has', 1.0) if st.session_state.get('kayitli_teorik_has', 0.0) > 0 else 1.0

ch1, ch2, ch3 = st.columns([1.2, 1, 1])
ch2.markdown('<div class="header-container"><div class="header-text">ALIŞ</div></div>', unsafe_allow_html=True)
ch3.markdown('<div class="header-container"><div class="header-text">SATIŞ</div></div>', unsafe_allow_html=True)

urunler = [
    ("24 AYAR (HAS)", 0.0, st.session_state.get('g_24', 0.0)),
    ("22 AYAR SATIŞ", 0.0, st.session_state.get('g_22_s', 0.0)),
("14 AYAR", 0.0, st.session_state.get('g_14', 0.0)),
    ("22 AYAR ALIŞ", st.session_state.get('g_22_a', 0.0), 0.0),
    ("BEŞLİ", st.session_state.get('g_besli_a', 0.0), st.session_state.get('g_besli_s', 0.0)),
    ("TAM (ATA)", st.session_state.get('g_tam_a', 0.0), st.session_state.get('g_tam_s', 0.0)),
    ("YARIM", st.session_state.get('g_yarim_a', 0.0), st.session_state.get('g_yarim_s', 0.0)),
    ("ÇEYREK", st.session_state.get('g_ceyrek_a', 0.0), st.session_state.get('g_ceyrek_s', 0.0)),
    ("GRAM (HAS)", st.session_state.get('g_gram_a', 0.0), st.session_state.get('g_gram_s', 0.0))
]

html_satirlar = "".join([f'<div class="row-wrapper"><div class="product-name">{i}</div><div class="price-container">{"<span class=\'price-buy\'>" + f"{a*oran:,.2f}" + "</span>" if a>0 else "<span class=\'price-buy hidden\'>----</span>"}</div><div class="price-container">{"<span class=\'price-sell\'>" + f"{s*oran:,.2f}" + "</span>" if s>0 else "<span class=\'price-sell hidden\'>----</span>"}</div></div>' for i, a, s in urunler])

st.markdown(html_satirlar, unsafe_allow_html=True)

saat = datetime.now(pytz.timezone('Europe/Istanbul')).strftime('%H:%M:%S')
st.markdown(f"<div style='text-align: center; color: #555; margin-top: 25px;'>ONS: {ons:,.2f} $ | USD: {dolar:,.4f} ₺ | Saat: {saat} | Kaynak: Yahoo Spot</div>", unsafe_allow_html=True)