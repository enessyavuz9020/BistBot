import yfinance as yf
import pandas_ta as ta
import requests
import datetime
import pytz
import pandas as pd
import sys

# --- TELEGRAM AYARLARI ---
TELEGRAM_TOKEN = "8689264018:AAHPm5mzsa42K7q5SbNitYcJMLfTDr8Vh3I"
CHAT_ID = "1556530792"

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mesaj})

def endeks_durumunu_analiz_et():
    try:
        endeks = yf.Ticker("XU100.IS")
        df = endeks.history(period="3mo")
        if df.empty: return "⚠️ BIST 100 verisi çekilemedi.\n", False
        df.ta.sma(length=20, append=True)
        son_kapanis, sma_20 = df['Close'].iloc[-1], df['SMA_20'].iloc[-1]
        
        mesaj = f"📊 BIST 100: {son_kapanis:.2f}\n"
        tehlike = son_kapanis < sma_20
        mesaj += "⚠️ DİKKAT: Yön aşağı, piyasada tehlike var!\n" if tehlike else "✅ Piyasada yön pozitif.\n"
        return mesaj, tehlike
    except:
        return "⚠️ BIST 100 endeks verisi anlık okunamadı.\n", False

def hisse_analiz_et(hisse_kodu):
    saf_kod = hisse_kodu.replace(".IS", "")
    bugun = datetime.datetime.now()
    alti_ay_once = bugun - datetime.timedelta(days=180)
    url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseTekil?hisse={saf_kod}&startdate={alti_ay_once.strftime('%d-%m-%Y')}&enddate={bugun.strftime('%d-%m-%Y')}"
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        if 'value' not in res or not res['value']: return None
        
        df = pd.DataFrame(res['value'])[['HGDG_TARIH', 'HGDG_KAPANIS']]
        df.rename(columns={'HGDG_TARIH': 'Date', 'HGDG_KAPANIS': 'Close'}, inplace=True)
        df['Close'] = df['Close'].astype(float)
        
        if len(df) < 50: return None
        
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        son_gun = df.iloc[-1]
        
        # Profesyonel Kriterler
        if (son_gun['RSI_14'] < 45) and (son_gun['Close'] <= (son_gun['BBL_20_2.0'] * 1.02)) and (son_gun['MACDh_12_26_9'] > 0):
            return f"🟢 {saf_kod} -> Fiyat: {son_gun['Close']:.2f} | RSI: {son_gun['RSI_14']:.1f}"
    except:
        pass
    return None

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    simdi = datetime.datetime.now(tz)
    
    saat, dakika = simdi.hour, simdi.minute
    if simdi.weekday() >= 5 or not ((saat == 10 and dakika >= 0) or (10 < saat < 18) or (saat == 18 and dakika <= 10)):
        print("Borsa kapalı. İşlem yapılmadı.")
        sys.exit()

    # --- BİLDİRİM: BOT UYANDIĞINDA İLK BU MESAJI ATACAK ---
    telegram_mesaj_gonder(f"⚙️ Bot Devrede! Saat {saat:02d}:{dakika:02d} taraması başlatılıyor...\n(Tüm hisselerin derin analizi yaklaşık 15-20 dakika sürebilir, sonuçlar birazdan iletilecektir.)")

    hisseler = ["AEFES", "AGHOL", "AHGAZ", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALFAS", "ARCLK", "ASELS", "ASTOR", "BERA", "BIENY", "BIMAS", "BRMEN", "BRSAN", "CANTE", "CCOLA", "CEMAS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC", "ECZYT", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI", "EREGL", "EUPWR", "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GLYHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "IMASM", "IPEKE", "ISCTR", "ISDMR", "ISGYO", "ISMEN", "IZENR", "KCAER", "KCHOL", "KLSER", "KMPUR", "KONTR", "KONYA", "KOZAA", "KOZAL", "KRDMD", "KZBGY", "MAVI", "MGROS", "MIATK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "PNLSN", "QUAGR", "SAHOL", "SASA", "SDTTR", "SISE", "SKBNK", "SMRTG", "SOKM", "TABGD", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "YKBNK", "YYLGD", "ZOREN"]
    
    endeks_mesaji, tehlike = endeks_durumunu_analiz_et()
    firsat_hisseler = [sonuc for kod in hisseler if (sonuc := hisse_analiz_et(kod))]
    
    final_mesaj = endeks_mesaji
    if firsat_hisseler:
        final_mesaj += "\n🎯 TARAMA SONUÇLARI:\n" + "\n".join(firsat_hisseler)
        if tehlike: final_mesaj += "\n\n🚨 NOT: Endeks düşüş trendinde!"
    else:
        final_mesaj += "\nℹ️ Şu an profesyonel kriterlere uyan fırsat hissesi bulunamadı."
        
    telegram_mesaj_gonder(final_mesaj)
        
