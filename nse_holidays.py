"""
NSE Equity Segment Trading Holidays — 2026.

Source: NSE India च्या अधिकृत सूचनेवर आधारित (ClearTax/NSE holiday circular,
Aug 2026 पर्यंत verified). दर वर्षी NSE नवीन calendar जाहीर करतं
(https://www.nseindia.com/resources/exchange-communication-holidays)
— त्यामुळे हे दरवर्षी जानेवारीत अपडेट करावं लागेल.

⚠️ जर ही यादी न भरता ठेवली (नवीन वर्षी), तर is_nse_trading_holiday()
आपोआप False परत देईल (holiday समजणार नाही) — म्हणजे agent त्या दिवशीही
चालेल; scan fail झाला तर तो वेगळ्या sanity-check ने पकडला जाईल, चुकीचा
"clean digest" म्हणून दाखवला जाणार नाही.
"""

from datetime import date

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 15): "Maharashtra Municipal Elections",
    date(2026, 1, 26): "Republic Day",
    date(2026, 3, 3): "Holi",
    date(2026, 3, 26): "Shri Ram Navami",
    date(2026, 3, 31): "Shri Mahavir Jayanti",
    date(2026, 4, 3): "Good Friday",
    date(2026, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    date(2026, 5, 1): "Maharashtra Day",
    date(2026, 5, 28): "Bakri Id",
    date(2026, 6, 26): "Muharram",
    date(2026, 9, 14): "Ganesh Chaturthi",
    date(2026, 10, 2): "Mahatma Gandhi Jayanti",
    date(2026, 10, 20): "Dussehra",
    date(2026, 11, 10): "Diwali - Balipratipada",
    date(2026, 11, 24): "Prakash Gurpurb Sri Guru Nanak Dev",
    date(2026, 12, 25): "Christmas",
}


def is_nse_trading_holiday(check_date: date = None) -> tuple:
    """(is_holiday: bool, holiday_name: str|None) परत देतं.
    Weekend तपासणी इथे नाही (ती cron schedule मध्येच सोम-शुक्र आहे) —
    हे फक्त weekday-वरच्या घोषित सुट्ट्यांसाठी आहे."""
    check_date = check_date or date.today()
    name = NSE_HOLIDAYS_2026.get(check_date)
    return (name is not None), name
