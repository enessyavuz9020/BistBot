import yfinance as yf
import pandas_ta as ta
import requests
import datetime
import pytz
import pandas as pd
import sys

# --- AYARLAR ---
TELEGRAM_TOKEN = "8689264018:AAHPm5mzsa42K7q5SbNitYcJMLfTDr8Vh3I"
CHAT_ID = "1556530792"

# 📌 GENEL TARAMA LİSTESİ
GENEL_HISSELER = ["ALTINS1", "AEFES", "AGHOL", "AHGAZ", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALFAS", "ARCLK", "ASELS", "ASTOR", "BERA", "BIENY", "BIMAS", "BRMEN", "BRSAN", "CANTE", "CCOLA", "CEMAS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC", "ECZYT", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI", "EREGL", "EUPWR", "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GLYHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "IMASM", "IPEKE", "ISCTR", "ISDMR", "ISGYO", "ISMEN", "IZENR", "KCAER", "KCHOL", "KLSER", "KMPUR", "KONTR", "KONYA", "KOZAA", "KOZAL", "KRDMD", "KZBGY", "MAVI", "MGROS", "MIATK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "PNLSN", "QUAGR", "SAHOL", "SASA", "SDTTR", "SISE", "SKBNK", "SMRTG", "SOKM", "TABGD", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "YKBNK", "YYLGD", "ZOREN"]

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mesaj})

def telegram_son_komutu_al():
    # Telegram'daki son 24 saatlik okunmamış mesajları çeker
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("ok") and "result" in res:
            # Gelen mesajları en yeniden en eskiye doğru tarıyoruz
            for m in reversed(res["result"]):
                if "message" in m and "text" in m["message"]:
                    text = m["message"]["text"].upper()
                    # Eğer mesaj /TAKIP ile başlıyorsa
                    if text.startswith("/TAKIP"):
                        # Komutu temizleyip hisseleri listeye çeviriyoruz
                        hisseler = text.replace("/TAKIP", "").strip().split()
                        hisseler = [h.replace(",", "").strip() for h in hisseler if h.strip()]
                        return hisseler
    except:
        pass
    return []

def endeks_durumunu_analiz_et():
    try:
        endeks = yf.Ticker("XU100.IS")
        df = endeks.history(period="6mo")
        if df.empty: return "⚠️ BIST 100 verisi çekilemedi.\n", False
        
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        son_kapanis = df['Close'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        
        mesaj = f"📊 BIST 100 GÜNCEL: {son_kapanis:.2f}\n"
        if son_kapanis > sma_20 and son_kapanis > sma_50:
            mesaj += f"✅ YÖN YUKARI: Endeks güçlü, 20 ve 50 günlük ortalamaların üzerinde.\n"
            tehlike = False
        elif son_kapanis < sma_20 and son_kapanis > sma_50:
            mesaj += f"⚠️ DÜZELTME: Kısa vadede satıcılı (20G altı), ancak 50G ana destek çalışıyor.\n"
            tehlike = True
        else:
            mesaj += f"🚨 YÖN AŞAĞI: Endeks tüm destekleri kırmış durumda. Satış baskısı hakim.\n"
            tehlike = True
        return mesaj, tehlike
    except Exception as e:
        return f"⚠️ BIST 100 verisi anlık okunamadı.\n", False

def detayli_hisse_analizi(saf_kod, ozel_takip_mi=False):
    bugun = datetime.datetime.now()
    alti_ay_once = bugun - datetime.timedelta(days=200)
    url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseTekil?hisse={saf_kod}&startdate={alti_ay_once.strftime('%d-%m-%Y')}&enddate={bugun.strftime('%d-%m-%Y')}"
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        if 'value' not in res or not res['value']: return None
        
        df = pd.DataFrame(res['value'])[['HGDG_TARIH', 'HGDG_KAPANIS']]
        df.rename(columns={'HGDG_TARIH': 'Date', 'HGDG_KAPANIS': 'Close'}, inplace=True)
        df['Close'] = df['Close'].astype(float)
        
        if len(df) < 60: return None
        
        # Göstergeler
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=5, append=True)
        df.ta.ema(length=20, append=True)
        
        son_60 = df.tail(60)
        max_fiyat = son_60['Close'].max()
        min_fiyat = son_60['Close'].min()
        fark = max_fiyat - min_fiyat
        fib_618 = max_fiyat - (fark * 0.618)
        
        son = df.iloc[-1]
        onceki = df.iloc[-2]
        
        fiyat = son['Close']
        rsi = son['RSI_14']
        macd = son['MACD_12_26_9']
        sma20, sma50 = son['SMA_20'], son['SMA_50']
        ema5, ema20 = son['EMA_5'], son['EMA_20']
        
        # 1. ÖZEL TAKİP LİSTESİ RAPORU
        if ozel_takip_mi:
            durum = "Yükseliş Trendi" if fiyat > sma20 else ("Düşüş Trendi" if fiyat < sma50 else "Yatay/Düzeltme")
            return f"🔹 {saf_kod}: {fiyat:.2f} | RSI: {rsi:.1f} | Durum: {durum} | Güçlü Destek: {sma50:.2f}"
            
        # 2. FIRSATLAR (Sadece Genel Tarama İçin)
        firsat = None
        if abs(fiyat - fib_618) / fib_618 < 0.02 and rsi > 40:
            firsat = f"🟢 {saf_kod} (FIBO 0.618 DESTEĞİ) | Fiyat: {fiyat:.2f} | Altın Oran noktasına yakın, tepki verebilir."
        elif ema5 > ema20 and onceki['EMA_5'] <= onceki['EMA_20'] and rsi < 70:
            firsat = f"🚀 {saf_kod} (HIZLI MOMENTUM) | Fiyat: {fiyat:.2f} | 5 günlük ortalama, 20 günlüğü yukarı kesti!"
        elif rsi < 33:
            firsat = f"🛒 {saf_kod} (DİP NOKTASI) | Fiyat: {fiyat:.2f} | RSI ({rsi:.1f}) aşırı satım bölgesinde."

        # 3. RİSK RADARI
        risk = None
        if rsi > 76:
            risk = f"🔴 {saf_kod} (AŞIRI ŞİŞMİŞ) | Fiyat: {fiyat:.2f} | RSI ({rsi:.1f}) zirvede, kâr satışı an meselesi."
        elif fiyat < sma50 and onceki['Close'] >= onceki['SMA_50']:
            risk = f"🩸 {saf_kod} (DESTEK KIRILDI) | Fiyat: {fiyat:.2f} | 50 Günlük ana destek aşağı kırıldı!"

        return firsat, risk

    except:
        return None if not ozel_takip_mi else f"⚠️ {saf_kod}: Veri okunamadı."

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    simdi = datetime.datetime.now(tz)
    saat, dakika = simdi.hour, simdi.minute
    
    if simdi.weekday() >= 5 or not ((saat == 10 and dakika >= 0) or (10 < saat < 18) or (saat == 18 and dakika <= 10)):
        print("Borsa kapalı. İşlem yapılmadı.")
        sys.exit()

    telegram_mesaj_gonder(f"⚙️ Bot Devrede! Saat {saat:02d}:{dakika:02d} taraması başlatılıyor...\n(Akıllı Hafıza & Risk Radarı devrede.)")

    # Telegram'dan son komutu al
    ozel_takip_listesi = telegram_son_komutu_al()

    endeks_mesaji, tehlike = endeks_durumunu_analiz_et()
    
    ozel_rapor = []
    firsatlar = []
    riskler = []
    
    # Özel Takip Tarama (Eğer komutla veri geldiyse)
    if ozel_takip_listesi:
        for kod in ozel_takip_listesi:
            sonuc = detayli_hisse_analizi(kod, ozel_takip_mi=True)
            if sonuc: ozel_rapor.append(sonuc)
        
    # Genel Tarama (Özel listedekileri çift taramamak için çıkarıyoruz)
    taranacaklar = list(set(GENEL_HISSELER) - set(ozel_takip_listesi))
    
    for kod in taranacaklar:
        sonuc = detayli_hisse_analizi(kod, ozel_takip_mi=False)
        if sonuc:
            firsat, risk = sonuc
            if firsat: firsatlar.append(firsat)
            if risk: riskler.append(risk)
            
    final_mesaj = endeks_mesaji + "\n"
    
    if ozel_rapor:
        final_mesaj += "👁️ ÖZEL TAKİP LİSTENİZ:\n" + "\n".join(ozel_rapor) + "\n\n"
        
    if firsatlar:
        final_mesaj += "🎯 YENİ FIRSATLAR:\n" + "\n".join(firsatlar) + "\n\n"
    else:
        final_mesaj += "ℹ️ Kısa vadeli fırsat veya Fibo stratejisine uyan teknik bir hisse bulunamadı.\n\n"
        
    if riskler:
        final_mesaj += "⚠️ RİSK RADARI (Uzak Durulması Gerekenler):\n" + "\n".join(riskler)

    if len(final_mesaj) > 4000:
        telegram_mesaj_gonder(final_mesaj[:4000] + "\n... (Mesaj sınırına ulaşıldı)")
    else:
        telegram_mesaj_gonder(final_mesaj)
