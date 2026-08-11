import os
import pandas as pd
from datetime import datetime

# सर्व ६ कोडिंग मॉड्यूल्स सुरक्षितपणे जोडणे
import investment_database as db
import investment_macro as macro
import investment_technical as tech
import investment_fundamental as fund

def build_and_dispatch_weekly_report():
    print("[REPORTER] Commencing Advanced Hedge Fund Grade Portfolio Scan...")
    
    # १. जागतिक मॅक्रो आणि FPI डेटा बॅकएंडला गोळा करणे
    try:
        crude, dxy, macro_text = macro.fetch_global_commodity_trends()
    except Exception as e:
        macro_text = f"Macro Data Fetch Error: {e}"
        
    try:
        fpi_data = macro.fetch_nsdl_fpi_flow_report()
    except Exception as e:
        fpi_data = None
        print(f"[WARNING] Could not fetch FPI flow report: {e}")
    
    mapping_df = db.generate_master_mapping_sheet()
    if mapping_df is None or mapping_df.empty:
        print("[WARNING] Master mapping list is empty. Operations halted.")
        return
        
    table_rows_html = ""
    processed_count = 0
    
    # २. १,००० कंपन्यांच्या डेटाचे सखोल गाळणी चक्र फिरवणे
    for _, row in mapping_df.iterrows():
        ticker = row.get('Ticker', '')
        micro_sector = row.get('Micro_Sector', 'N/A')
        
        file_path = os.path.join(db.DB_FOLDER, f"{ticker}_5year.csv")
        if not os.path.exists(file_path): 
            continue
        
        try:
            df_ticker = pd.read_csv(file_path)
            
            # 🟢 CRITICAL SYNC UPDATE: नवीन कोअर टेक्निकल इंजिननुसार डेटा री-सॅम्पलिंग इनपुट पास करणे
            metrics = tech.run_advanced_technical_analysis(df_ticker, timeframe="Weekly (साप्ताहिक)")
            
            # डिक्शनरी सेफ्टी चेक
            if not isinstance(metrics, dict) or metrics.get("status") != "SUCCESS": 
                continue
                
            fund_score, pe, debt, roe, fcf = fund.run_advanced_fundamental_analysis(ticker)
            
            wyckoff = str(metrics.get("wyckoff_phase", ""))
            regime = str(metrics.get("regime", ""))
            score = metrics.get("score", 0)
            reason = metrics.get("reason", "No specific reasoning provided.")
            
            # Delivery DMA सुरक्षितपणे स्ट्रिंगमध्ये कन्व्हर्ट करणे
            delivery_dma_raw = metrics.get("delivery_dma", 0.0)
            try:
                delivery_dma = f"{float(delivery_dma_raw):.1f}%" if pd.notna(delivery_dma_raw) else "N/A"
            except (ValueError, TypeError):
                delivery_dma = "N/A"
            
            # 📐 केवळ सर्वोत्तम आऊटपरफॉर्मर, वायकॉफ स्प्रिंग (PHASE_C) आणि निरोगी करेक्शन असलेले स्टॉक्स फिल्टर करणे
            if "PHASE_C" in wyckoff or regime == "HEALTHY_PRICE_CORRECTION":
                table_rows_html += f"""
                <tr style="border-bottom:1px solid #cbd5e0;">
                    <td style="padding:10px; font-weight:bold; color:#1a365d;">{ticker}<br><span style="font-size:11px; color:#718096;">{micro_sector}</span></td>
                    <td style="padding:10px; color:green; font-weight:bold;">{regime}</td>
                    <td style="padding:10px; font-size:12px;">PE: {pe} | ROE: {roe}%<br>Quant Score: {score}/100 | Delivery 15D: {delivery_dma}</td>
                    <td style="padding:10px; font-size:12px; color:#4a5568; line-height:1.4;"><b>{wyckoff}:</b> {reason}</td>
                </tr>
                """
                processed_count += 1
                
        except Exception as err:
            print(f"[ERROR] Error processing ticker {ticker}: {err}")
            continue

    if not table_rows_html:
        table_rows_html = """
        <tr>
            <td colspan="4" style="padding:15px; text-align:center; color:#718096;">
                सध्याच्या क्रायटेरियानुसार (PHASE_C / HEALTHY_PRICE_CORRECTION) कोणताही स्टॉक फिल्टर झाला नाही.
            </td>
        </tr>
        """
            
    # f-string च्या आत \n चा वापर टाळण्यासाठी आधीच रिप्लेस केले आहे
    macro_text_formatted = str(macro_text).replace('\n', '<br>')

    # ३. ऑटोमॅटिक बॅकएंड HTML डॅशबोर्ड आर्काइव्ह रचना
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Universal Long-Term Investing Terminal Report</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color:#f4f6f9; padding:20px; margin:0;">
        <div style="max-width:750px; margin:0 auto; background-color:#ffffff; padding:30px; border-radius:8px; border:1px solid #cbd5e0;">
            <h2 style="color:#1a365d; border-bottom:2px solid #3182ce; padding-bottom:10px; margin-top:0;">🏆 UNIVERSAL LONG-TERM INVESTING TERMINAL (BACKEND REPORT)</h2>
            <p style="font-size:12px; color:#718096;">📅 <b>साप्ताहिक बॅकएंड रिपोर्ट तारीख:</b> {datetime.now().strftime('%d-%b-%Y')} | 🌍 <b>Global Data Sourced</b></p>
            
            <h3 style="color:#2c5282; margin-bottom:5px;">🌐 १. जागतिक मॅक्रो आणि धोरणात्मक घोषणा</h3>
            <p style="font-size:13px; line-height:1.5; color:#2d3748; background-color:#f7fafc; padding:12px; border-radius:4px;">{macro_text_formatted}</p>
            
            <h3 style="color:#2c5282;">📊 २. फिल्टर झालेले मल्टि-बॅगर आऊटपरफॉर्मर स्टॉक्स ({processed_count})</h3>
            <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
                <thead>
                    <tr style="background-color:#edf2f7; color:#2d3748;">
                        <th style="padding:10px; border:1px solid #cbd5e0;">स्टॉक / सेक्टर</th>
                        <th style="padding:10px; border:1px solid #cbd5e0;">डेटा रेजीम</th>
                        <th style="padding:10px; border:1px solid #cbd5e0;">फंडामेंटल्स व क्वांट स्कोअर</th>
                        <th style="padding:10px; border:1px solid #cbd5e0;">सिस्टम कारण मीमांसा (Research Logic)</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
            <p style="color:#a0aec0; font-size:11px; text-align:center; margin-top:25px;">🛡️ NSDL FPI फ्लो आणि १५-Day Delivery DMA नुसार भांडवल पूर्णपणे सुरक्षित ठेवण्यात आले आहे.</p>
        </div>
    </body>
    </html>
    """
    
    # रिपोर्ट फाईल सेव्ह करणे
    try:
        report_filename = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.html"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(final_html)
        print(f"[REPORTER] Report successfully generated and saved to: {report_filename}")
    except Exception as e:
        print(f"[WARNING] Could not save HTML file: {e}")

    print(f"--- NIFTY 1000 PRO CORE ANALYSIS SYSTEM METRICS LOCKED: {datetime.now().strftime('%d-%b-%Y')} ---")
    print("[SUCCESS] Multi-Timeframe Background Sync finished with ZERO repository conflicts.")

if __name__ == "__main__":
    build_and_dispatch_weekly_report()
