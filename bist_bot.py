import yfinance as yf
import pandas_ta as ta
import requests
import datetime
import pytz
import pandas as pd
import sys
import matplotlib.pyplot as plt
import io

plt.switch_backend('Agg') # Sunucu ortamında grafik çizimi için arkayüz

# --- AYARLAR ---
TELEGRAM_TOKEN = "8689264018:AAHPm5mzsa42K7q5SbNitYcJMLfTDr8Vh3I"
CHAT_ID = "1556530792"

GENEL_HISSELER = ["ALTINS1", "AEFES", "AGHOL", "AHGAZ", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALFAS", "ARCLK", "ASELS", "ASTOR", "BERA", "BIENY", "BIMAS", "BRMEN", "BRSAN", "CANTE", "CCOLA", "CEMAS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC", "ECZYT", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI", "EREGL", "EUPWR", "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GLYHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "IMASM", "IPEKE", "ISCTR", "ISDMR", "ISGYO", "ISMEN", "IZENR", "KCAER", "KCHOL", "KLSER", "KMPUR", "KONTR", "KONYA", "KOZAA", "KOZAL", "KRDMD", "KZBGY", "MAVI", "MGROS", "MIATK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "PNLSN", "QUAGR", "SAHOL", "SASA", "SDTTR", "SISE", "SKBNK", "SMRTG", "SOKM", "TABGD", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "YKBNK", "YYLGD", "ZOREN"]

def telegram_mesaj_gonder(mesaj, gorsel_bytes=None):
    if gorsel_bytes:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': ('grafik.png', gorsel_bytes, 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': mesaj}
        requests.post(url, data=data, files=files)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": mesaj})

def telegram_son_komutu_al():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("ok") and "result" in res:
            for m in reversed(res["result"]):
                if "message" in m and "text" in m["message"]:
                    text = m["message"]["text"].upper()
                    if text.startswith("/TAKIP"):
                        # /takip TUPRS:155.50 ASELS:45.00 formatını destekler
                        hisseler = text.replace("/TAKIP", "").strip().split()
                        return [h.replace(",", "").strip() for h in hisseler if h.strip()]
    except:
        pass
    return []

def rsi_durumu_belirle(rsi_degeri):
    if rsi_degeri < 35: return "Aşırı Satım"
    elif 35 <= rsi_degeri < 45: return "Toplanma Bölgesi"
    elif 45 <= rsi_degeri < 60: return "Nötr"
    elif 60 <= rsi_degeri < 75: return "Yükseliş İvmesi"
    else: return "Aşırı Alım/Riskli"

def grafik_ciz(df, kod):
    plt.figure(figsize=(10, 5))
    son_60 = df.tail(60)
    plt.plot(son_60.index, son_60['Close'], label='Fiyat', color='blue', linewidth=2)
    plt.plot(son_60.index, son_60['SMA_20'], label='20G Ort', color='orange', linestyle='--')
    plt.plot(son_60.index, son_60['SMA_50'], label='50G Ort', color='red', linestyle='--')
    
    plt.title(f"{kod} - Son 60 Günlük Teknik Görünüm")
    plt.xlabel('Tarih')
    plt.ylabel('Fiyat (TL)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    plt.close()
    return buf

def detayli_hisse_analizi(giris_kodu, ozel_takip_mi=False):
    # Maliyet analizi için ayrıştırma (Örn: TUPRS:150.5)
    if ":" in giris_kodu:
        saf_kod, maliyet_str = giris_kodu.split(":")
        maliyet = float(maliyet_str)
    else:
        saf_kod = giris_kodu
        maliyet = None

    bugun = datetime.datetime.now()
    alti_ay_once = bugun - datetime.timedelta(days=200)
    url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseTekil?hisse={saf_kod}&startdate={alti_ay_once.strftime('%d-%m-%Y')}&enddate={bugun.strftime('%d-%m-%Y')}"
    
    sonuc_dict = {'kod': saf_kod, 'ozel_mesaj': None, 'firsat': None, 'risk': None, 'puan': 0, 'fiyat': 0, 'df': None}
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        if 'value' not in res or not res['value']: return sonuc_dict
        
        df = pd.DataFrame(res['value'])[['HGDG_TARIH', 'HGDG_KAPANIS', 'HGDG_HACIM']]
        df.rename(columns={'HGDG_TARIH': 'Date', 'HGDG_KAPANIS': 'Close', 'HGDG_HACIM': 'Volume'}, inplace=True)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        if len(df) < 60: return sonuc_dict
        
        # Göstergeler
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=5, append=True)
        df.ta.ema(length=20, append=True)
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean() # Hacim Ortalaması
        
        son_60 = df.tail(60)
        max_f = son_60['Close'].max()
        min_f = son_60['Close'].min()
        fib_618 = max_f - ((max_f - min_f) * 0.618)
        
        # İzleyen Stop (Trailing Stop) - Son 15 günün zirvesinden %5 aşağısı
        zirve_15 = df['Close'].tail(15).max()
        izleyen_stop = zirve_15 * 0.95 
        
        son = df.iloc[-1]
        onceki = df.iloc[-2]
        
        fiyat = son['Close']
        rsi = son['RSI_14']
        macd, macd_s = son['MACD_12_26_9'], son['MACDs_12_26_9']
        sma20, sma50 = son['SMA_20'], son['SMA_50']
        ema5, ema20 = son['EMA_5'], son['EMA_20']
        hacim_katsayisi = son['Volume'] / son['Vol_SMA20'] if son['Vol_SMA20'] > 0 else 1
        
        sonuc_dict['fiyat'] = fiyat
        sonuc_dict['df'] = df
        
        seviye_tipi = "Güçlü Destek" if fiyat > sma50 else "Güçlü Direnç"
        rsi_metni = rsi_durumu_belirle(rsi)
        
        # 1. ÖZEL TAKİP LİSTESİ MANTIĞI
        if ozel_takip_mi:
            trend = "Yükseliş" if fiyat > sma20 else ("Düşüş" if fiyat < sma50 else "Yatay")
            
            # Kâr/Zarar Hesaplama
            kz_metni = ""
            tavsiye = ""
            if maliyet:
                fark_yuzde = ((fiyat - maliyet) / maliyet) * 100
                kz_durumu = "KÂR" if fark_yuzde > 0 else "ZARAR"
                isaret = "+" if fark_yuzde > 0 else ""
                kz_metni = f"\n     💰 Anlık Durum: {isaret}%{fark_yuzde:.2f} {kz_durumu} (Maliyet: {maliyet:.2f})"
                
                # Risk Asistanı Karar Mekanizması
                if fark_yuzde < -5 and fiyat < sma50:
                    tavsiye = "\n     🛑 ASİSTAN TAVSİYESİ: Zarar %5'i aştı ve ana destek kırıldı. Pozisyonu kapatmak (Stop-Loss) düşünülebilir."
                elif fark_yuzde > 0 and fiyat < izleyen_stop:
                    tavsiye = f"\n     🛡️ ASİSTAN TAVSİYESİ: İzleyen stop seviyesi ({izleyen_stop:.2f}) kırıldı. Kârı alıp çıkmak güvenli olabilir."
                elif trend == "Yükseliş":
                    tavsiye = "\n     ✅ ASİSTAN TAVSİYESİ: Trend güçlü, pozisyon korunabilir."

            sonuc_dict['ozel_mesaj'] = f"🔹 {saf_kod}: {fiyat:.2f} | Trend: {trend}\n     RSI: {rsi:.1f} ({rsi_metni})\n     {seviye_tipi}: {sma50:.2f}{kz_metni}{tavsiye}"
            
        # 2. PUANLAMA VE FIRSATLAR
        puan = 0
        if rsi < 40: puan += 3
        if ema5 > ema20: puan += 3
        if macd > macd_s: puan += 2
        if abs(fiyat - fib_618) / fib_618 < 0.03: puan += 2
        if hacim_katsayisi > 1.5: puan += 2 # Hacim artışı ekstra puan
        
        sonuc_dict['puan'] = puan

        if abs(fiyat - fib_618) / fib_618 < 0.02 and rsi > 40:
            sonuc_dict['firsat'] = f"🟢 {saf_kod} (FIBONACCI TEPKİSİ) | Fiyat: {fiyat:.2f}\n     Altın Oran noktasına yakın. (Hacim Katsayısı: {hacim_katsayisi:.1f}x)"
        elif ema5 > ema20 and onceki['EMA_5'] <= onceki['EMA_20'] and rsi < 70:
            sonuc_dict['firsat'] = f"🚀 {saf_kod} (ALTIN KESİŞİM) | Fiyat: {fiyat:.2f}\n     Ortalamalar yukarı kesti. Momentum başlıyor."
        elif rsi < 33:
            sonuc_dict['firsat'] = f"🛒 {saf_kod} (AŞIRI UCUZ) | Fiyat: {fiyat:.2f}\n     Hisse dipten dönüş sinyali arıyor. (RSI: {rsi:.1f})"

        if hacim_katsayisi > 2.0 and fiyat > sma20:
            sonuc_dict['firsat'] = f"💥 {saf_kod} (BÜYÜK PARA GİRİŞİ) | Fiyat: {fiyat:.2f}\n     Hacim ortalamanın {hacim_katsayisi:.1f} katına ulaştı!"

        # 3. RİSK RADARI
        if rsi > 76:
            sonuc_dict['risk'] = f"🔴 {saf_kod} (ŞİŞKİN/AŞIRI ALIM) | Fiyat: {fiyat:.2f}\n     Zirvelerde geziyor, sert kâr satışı yiyebilir."
        elif fiyat < sma50 and onceki['Close'] >= onceki['SMA_50']:
            sonuc_dict['risk'] = f"🩸 {saf_kod} (DESTEK KIRILIMI) | Fiyat: {fiyat:.2f}\n     50 Günlük ana desteğini hacimli kırarsa düşüş sertleşir."

    except:
        pass
    return sonuc_dict

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    simdi = datetime.datetime.now(tz)
    saat, dakika = simdi.hour, simdi.minute
    
    if simdi.weekday() >= 5 or not ((saat == 10 and dakika >= 0) or (10 < saat < 18) or (saat == 18 and dakika <= 10)):
        print("Borsa kapalı. İşlem yapılmadı.")
        sys.exit()

    # BIST Analizi
    endeks = yf.Ticker("XU100.IS")
    df_endeks = endeks.history(period="6mo")
    df_endeks.ta.sma(length=20, append=True)
    df_endeks.ta.sma(length=50, append=True)
    son_bist = df_endeks['Close'].iloc[-1]
    sma_20 = df_endeks['SMA_20'].iloc[-1]
    sma_50 = df_endeks['SMA_50'].iloc[-1]
    
    endeks_mesaji = f"📊 BIST 100 GÜNCEL: {son_bist:.2f}\n"
    piyasa_tehlikeli = False
    if son_bist > sma_20 and son_bist > sma_50:
        endeks_mesaji += "✅ PİYASA YÖNÜ YUKARI: Endeks güçlü."
    elif son_bist < sma_20 and son_bist > sma_50:
        endeks_mesaji += "⚠️ KARARSIZ PİYASA: Kısa vadeli düzeltme var, destek çalışıyor."
        piyasa_tehlikeli = True
    else:
        endeks_mesaji += "🚨 PİYASA YÖNÜ AŞAĞI: Satış baskısı hakim."
        piyasa_tehlikeli = True

    telegram_mesaj_gonder(f"⚙️ Bot Devrede! Saat {saat:02d}:{dakika:02d} taraması başlatılıyor...\n(Hacim, Fiyat ve Grafik Asistanı devrede.)")

    ozel_takip_listesi = telegram_son_komutu_al()
    saf_ozel_hisseler = [k.split(":")[0] for k in ozel_takip_listesi]
    
    ozel_rapor = []
    firsatlar = []
    riskler = []
    tum_firsat_objeleri = []
    
    if ozel_takip_listesi:
        for kod in ozel_takip_listesi:
            veri = detayli_hisse_analizi(kod, ozel_takip_mi=True)
            if veri.get('ozel_mesaj'): ozel_rapor.append(veri['ozel_mesaj'])
        
    taranacaklar = list(set(GENEL_HISSELER) - set(saf_ozel_hisseler))
    
    for kod in taranacaklar:
        veri = detayli_hisse_analizi(kod, ozel_takip_mi=False)
        if veri.get('firsat'):
            firsatlar.append(veri['firsat'])
            tum_firsat_objeleri.append(veri)
        if veri.get('risk'):
            riskler.append(veri['risk'])
            
    final_mesaj = endeks_mesaji + "\n\n"
    
    if ozel_rapor:
        final_mesaj += "👁️ ÖZEL TAKİP & PORTFÖY:\n" + "\n".join(ozel_rapor) + "\n\n"
        
    gorsel = None
    if firsatlar:
        final_mesaj += "🎯 YENİ FIRSATLAR:\n" + "\n".join(firsatlar) + "\n\n"
        
        en_iyi = max(tum_firsat_objeleri, key=lambda x: x['puan'])
        final_mesaj += f"🏆 GÜNÜN YILDIZI: {en_iyi['kod']} (Teknik Skor: {en_iyi['puan']}/10)\n"
        
        if piyasa_tehlikeli:
            final_mesaj += f"💡 Asistan Stratejisi: {en_iyi['kod']} teknik olarak çok güçlü bir kurulumda. ANCAK endeks baskısı nedeniyle kademeli alım daha güvenlidir."
        else:
            final_mesaj += f"💡 Asistan Stratejisi: Endeks pozitif. {en_iyi['kod']} hacim ve göstergeler bakımından alım için oldukça cazip duruyor."
            
        # Günün yıldızının grafiğini çiz
        if en_iyi['df'] is not None:
            gorsel = grafik_ciz(en_iyi['df'], en_iyi['kod'])
    else:
        final_mesaj += "ℹ️ Şu an kriterleri tam karşılayan net bir fırsat bulunamadı.\n\n"
        
    if riskler:
        final_mesaj += "⚠️ RİSK RADARI:\n" + "\n".join(riskler)

    # Önce metni ve (eğer varsa) grafiği beraber yolla
    if len(final_mesaj) > 4000:
        telegram_mesaj_gonder(final_mesaj[:4000] + "\n... (Mesaj sınırı)", gorsel_bytes=gorsel)
    else:
        telegram_mesaj_gonder(final_mesaj, gorsel_bytes=gorsel)
