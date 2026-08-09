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
        df = endeks.history(period="6mo")
        if df.empty: return "⚠️ BIST 100 verisi çekilemedi.\n", False
        
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        son_kapanis = df['Close'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        
        mesaj = f"📊 BIST 100 GÜNCEL DURUM: {son_kapanis:.2f}\n\n"
        
        if son_kapanis > sma_20 and son_kapanis > sma_50:
            mesaj += f"✅ YÖN YUKARI: Endeks ({son_kapanis:.0f}), hem 20 günlük ({sma_20:.0f}) hem de 50 günlük ({sma_50:.0f}) hareketli ortalamasının üzerinde güçlü seyrediyor.\n"
            tehlike = False
        elif son_kapanis < sma_20 and son_kapanis > sma_50:
            mesaj += f"⚠️ DÜZELTME: Endeks kısa vadeli 20 günlük ortalamanın ({sma_20:.0f}) altına sarkmış ancak 50 günlük ana desteğin ({sma_50:.0f}) üzerinde tutunmaya çalışıyor.\n"
            tehlike = True
        else:
            mesaj += f"🚨 YÖN AŞAĞI: Endeks ({son_kapanis:.0f}), 20 ve 50 günlük ortalamaların altında. Teknik olarak düşüş trendi (satış baskısı) hakim.\n"
            tehlike = True
            
        return mesaj, tehlike
    except Exception as e:
        return f"⚠️ BIST 100 endeks verisi anlık okunamadı. Hata: {e}\n", False

def hisse_analiz_et(hisse_kodu):
    saf_kod = hisse_kodu.replace(".IS", "")
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
        
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.sma(length=20, append=True)
        
        son = df.iloc[-1]
        onceki = df.iloc[-2]
        
        fiyat = son['Close']
        rsi = son['RSI_14']
        macd = son['MACD_12_26_9']
        macd_sinyal = son['MACDs_12_26_9']
        alt_bant = son['BBL_20_2.0']
        sma20 = son['SMA_20']
        
        # Strateji 1: Dip Avcısı (Aşırı satılmış ve alt banttan dönüyor)
        if rsi < 35 and fiyat <= (alt_bant * 1.015):
            return f"🟢 {saf_kod} (DİP AVCISI)\n   Fiyat: {fiyat:.2f} | RSI çok düşük ({rsi:.1f}). Fiyat Bollinger alt bandına değdi, tepki alımı gelebilir."
            
        # Strateji 2: MACD Kesişimi (Trend başlangıcı)
        if (macd > macd_sinyal) and (onceki['MACD_12_26_9'] <= onceki['MACDs_12_26_9']) and rsi > 40:
            return f"🚀 {saf_kod} (YENİ TREND)\n   Fiyat: {fiyat:.2f} | MACD göstergesi bugün yukarı kesti. Yükseliş ivmesi başlıyor olabilir."
            
        # Strateji 3: Güçlü Momentum (Hareketli ortalama kırılımı)
        if fiyat > sma20 and onceki['Close'] <= onceki['SMA_20'] and rsi > 50:
            return f"💪 {saf_kod} (GÜÇLÜ HACİM)\n   Fiyat: {fiyat:.2f} | Fiyat bugün 20 günlük ortalamayı yukarı yönlü kırdı. RSI: {rsi:.1f}"

    except:
        pass
    return None

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    simdi = datetime.datetime.now(tz)
    saat, dakika = simdi.hour, simdi.minute
    
    # Hafta sonu veya mesai dışı kontrolü
    if simdi.weekday() >= 5 or not ((saat == 10 and dakika >= 0) or (10 < saat < 18) or (saat == 18 and dakika <= 10)):
        print("Borsa kapalı. İşlem yapılmadı.")
        sys.exit()

    telegram_mesaj_gonder(f"⚙️ Bot Devrede! Saat {saat:02d}:{dakika:02d} taraması başlatılıyor...\n(Gelişmiş Algoritma Devrede. Analiz yaklaşık 15-20 dakika sürecektir.)")

    # ALTINS1 listeye eklendi
    hisseler = ["ALTINS1", "AEFES", "AGHOL", "AHGAZ", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALFAS", "ARCLK", "ASELS", "ASTOR", "BERA", "BIENY", "BIMAS", "BRMEN", "BRSAN", "CANTE", "CCOLA", "CEMAS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC", "ECZYT", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI", "EREGL", "EUPWR", "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GLYHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "IMASM", "IPEKE", "ISCTR", "ISDMR", "ISGYO", "ISMEN", "IZENR", "KCAER", "KCHOL", "KLSER", "KMPUR", "KONTR", "KONYA", "KOZAA", "KOZAL", "KRDMD", "KZBGY", "MAVI", "MGROS", "MIATK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "PNLSN", "QUAGR", "SAHOL", "SASA", "SDTTR", "SISE", "SKBNK", "SMRTG", "SOKM", "TABGD", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "YKBNK", "YYLGD", "ZOREN"]
    
    endeks_mesaji, tehlike = endeks_durumunu_analiz_et()
    
    bulunan_hisseler = []
    for kod in hisseler:
        sonuc = hisse_analiz_et(kod)
        if sonuc:
            bulunan_hisseler.append(sonuc)
    
    final_mesaj = endeks_mesaji
    if bulunan_hisseler:
        final_mesaj += "\n🎯 YENİ FIRSATLAR:\n\n" + "\n\n".join(bulunan_hisseler)
        if tehlike:
            final_mesaj += "\n\n🚨 NOT: Endeks genel olarak riskli bölgede. Bulunan hisseler kendi iç dinamikleriyle seçilmiştir, piyasa geneline karşı dikkatli olun."
    else:
        final_mesaj += "\nℹ️ 3 farklı stratejiden (Dip, Kesişim, Momentum) hiçbirine uyan teknik bir fırsat hissesi şu an bulunamadı."
        
    # Telegram mesaj uzunluğu limiti için önlem
    if len(final_mesaj) > 4000:
        telegram_mesaj_gonder(final_mesaj[:4000] + "\n... (Mesaj sınırına ulaşıldı)")
    else:
        telegram_mesaj_gonder(final_mesaj)
