import re
from datetime import datetime, date
from typing import Optional, Tuple

DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

HINDI_MONTHS = {
    "जनवरी": "Jan", "फ़रवरी": "Feb", "फरवरी": "Feb", "मार्च": "Mar",
    "अप्रैल": "Apr", "मई": "May", "जून": "Jun", "जुलाई": "Jul",
    "अगस्त": "Aug", "सितंबर": "Sep", "अक्टूबर": "Oct", "नवंबर": "Nov", "दिसंबर": "Dec"
}

INDIAN_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
    # Hindi words
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "पंद्रह": 15, "बीस": 20, "पच्चीस": 25, "तीस": 30, "पैंतीस": 35,
    "चालीस": 40, "पचास": 50, "पचहत्तर": 75, "अस्सी": 80, "नब्बे": 90
}


def normalize_hindi_digits(text: str) -> str:
    """Replaces Devanagari numerals with ASCII Arabic digits."""
    if not text:
        return ""
    result = []
    for ch in text:
        result.append(DEVANAGARI_DIGITS.get(ch, ch))
    return "".join(result)


def normalize_amount(raw: str) -> Optional[float]:
    """
    Normalizes Indian currency amount strings (e.g. ₹ 35,00,000.00 or Rs. 10,00,000/-)
    into standard numeric float.
    """
    if not raw:
        return None
    cleaned = normalize_hindi_digits(raw)
    cleaned = re.sub(r'[₹$]|Rs\.?|INR|/-|रु\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(',', '').strip()
    match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def normalize_date(raw: str) -> Optional[str]:
    """
    Normalizes various date formats (DD/MM/YYYY, DD-Mon-YYYY, Hindi names)
    to standard ISO YYYY-MM-DD.
    """
    if not raw:
        return None
    text = normalize_hindi_digits(raw.strip())
    
    # Replace Hindi months if present
    for h_month, en_month in HINDI_MONTHS.items():
        text = text.replace(h_month, en_month)

    patterns = [
        (r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', "%d/%m/%Y"),
        (r'(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{4})', "%d-%b-%Y"),
        (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', "%Y-%m-%d"),
    ]

    for regex, fmt in patterns:
        m = re.search(regex, text)
        if m:
            clean_str = m.group(0).replace('-', '/').replace(' ', '/')
            for test_fmt in ["%d/%m/%Y", "%d/%b/%Y", "%d/%B/%Y", "%Y/%m/%d"]:
                try:
                    dt = datetime.strptime(clean_str, test_fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
    return None


def words_to_amount_approx(words: str) -> Optional[float]:
    """
    Parses common Indian currency word representations into approximate numeric amount
    (e.g., 'Thirty Five Lakhs Only' -> 3500000.0, 'Ten Lakh' -> 1000000.0).
    """
    if not words:
        return None
    lower = words.lower().replace("only", "").strip()
    
    total = 0.0
    current = 0.0

    tokens = re.split(r'[\s\-]+', lower)
    for token in tokens:
        if token in INDIAN_NUMBER_WORDS:
            current += INDIAN_NUMBER_WORDS[token]
        elif token in ["hundred", "सौ"]:
            current = (current if current > 0 else 1) * 100
        elif token in ["thousand", "हजार"]:
            total += (current if current > 0 else 1) * 1000
            current = 0.0
        elif token in ["lakh", "lakhs", "लाख"]:
            total += (current if current > 0 else 1) * 100000
            current = 0.0
        elif token in ["crore", "crores", "करोड़"]:
            total += (current if current > 0 else 1) * 10000000
            current = 0.0
    
    total += current
    return total if total > 0 else None
