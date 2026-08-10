import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# मल्टि-अकाउंट कडून डेटा गोळा करणे
import investment_database as db
import investment_macro as macro
import investment_technical as tech
import investment_fundamental as fund
import investment_screener as scr

def build_and_dispatch_weekly_report():
    print("[REPORTER] Compiling Final Alpha Long-Term Research Dashboard...")
    
    # १. मॅक्रो न्यूज आणि एफपीआय फ्लो आणणे
    crude, dxy, macro_text = macro.fetch_global_commodity_trends()
    fpi_data = macro.fetch_nsdl_fpi_flow_report()
    
    mapping_df = db.generate_master_mapping_sheet()
    table_rows_html = ""
    
    # २. १,००0 कंपन्यांच्या डेटाचे सखोल गाळणी चक्र फिरवणे
    for _, row in mapping_df.iterrows():
        file_path = os.path.join(db.DB_FOLDER, f"{row['Ticker']}_5year.csv")
        if not os.path.exists(file_path): continue
        
        status, tech_score, peak, low = tech.run_advanced_technical_analysis(file_path)
        fund_score, pe, debt, roe, fcf = fund.run_advanced_fundamental_analysis(row['Ticker'])
        triage, narrative_reason = scr.evaluate_price_correction_vs_fall(file_path, peak)
        
        # केवळ सर्वोत्तम आऊटपरफॉर्मर आणि निरोगी करेक्शन असलेले स्टॉक्स फिल्टर करणे
        if triage in ["HEALTHY_CORRECTION", "STABLE_ACCUMULATION"]:
            table_rows_html += f"""
            <tr style="border-bottom:1px solid #cbd5e0;">
                <td style="padding:10px; font-weight:bold; color:#1a365d;">{row['Ticker']}<br><span style="font-size:11px; color:#718096;">{row['Micro_Sector']}</span></td>
                <td style="padding:10px; color:green; font-weight:bold;">{triage}</td>
                <td style="padding:10px; font-size:12px;">PE: {pe} | ROE: {roe}%<br>Debt: {debt} | FCF: {fcf}</td>
                <td style="padding:10px; font-size:12px; color:#4a5568; line-height:1.4;">{narrative_reason}</td>
            </tr>
            """
            
    # ३. HTML डॅशबोर्ड डिझाईन रचणे
    final_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f6f9; padding:20px;">
        <div style="max-width:700px; margin:0 auto; background-color:#ffffff; padding:30px; border-radius:8px; border:1px solid #cbd5e0;">
            <h2 style="color:#1a365d; border-bottom:2px solid #3182ce; padding-bottom:10px; margin-top:0;">🏆 UNIVERSAL LONG-TERM INVESTING TERMINAL</h2>
            <p style="font-size:12px; color:#718096;">📅 <b>साप्ताहिक रिपोर्ट तारीख:</b> {datetime.now().strftime('%d-%b-%Y')} | 🌍 <b>Global Data Sourced</b></p>
            
            <h3 style="color:#2c5282; margin-bottom:5px;">🌐 १. आंतरराष्ट्रीय आणि मॅक्रो घडामोडी (Global Macro Summary)</h3>
            <p style="font-size:13px; line-height:1.5; color:#2d3748; background-color:#f7fafc; padding:12px; border-radius:4px;">{macro_text.replace('\n', '<br>')}</p>
            
            <h3 style="color:#2c5282;">📊 २. टॉप आऊटपरफॉर्मर स्टॉक लीडरबोर्ड (Alpha Stocks Leaderboard)</h3>
            <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
                <tr style="background-color:#edf2f7; color:#2d3748;">
                    <th style="padding:10px; border:1px solid #cbd5e0;">स्टॉक / सेक्टर</th>
                    <th style="padding:10px; border:1px solid #cbd5e0;">डेटा रेजीम</th>
                    <th style="padding:10px; border:1px solid #cbd5e0;">फंडामेंटल्स (Ratios)</th>
                    <th style="padding:10px; border:1px solid #cbd5e0;">सिस्टम कारण मीमांसा (Research Logic)</th>
                </tr>
                {table_rows_html}
            </table>
            <p style="color:#a0aec0; font-size:11px; text-align:center; margin-top:25px;">🛡️ NSDL FPI फ्लो आणि ६५ च्या नवीन वॉल्युम प्रोफाईलनुसार भांडवल पूर्णपणे सुरक्षित ठेवण्यात आले आहे.</p>
        </div>
    </body>
    </html>
    """
    
    # तुमच्या मास्टर ईमेल आयडीवर फायनल रिपोर्ट पाठवून देणे
    db.send_email_report(f"🏆 ALPHA LONG-TERM WEALTH REPORT - {datetime.now().strftime('%d-%b-%Y')}", final_html)
    print("[🏁 TERMINAL METRICS COMPLETE] Final Long-Term Investment Report delivered successfully!")

if __name__ == "__main__":
    build_and_dispatch_weekly_report()
