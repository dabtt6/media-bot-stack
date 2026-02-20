import re

def extract_code(text):
    if not text:
        return None

    text = text.upper()

    # 1️⃣ Chuẩn CODE-123
    m = re.search(r'([A-Z]{2,10}-\d{2,7})', text)
    if m:
        return m.group(1)

    # 2️⃣ PPV 1234567 → PPV-1234567
    m = re.search(r'PPV\s?(\d{5,9})', text)
    if m:
        return f"PPV-{m.group(1)}"

    return None


# ================= TEST CASES =================

tests = [
    "(無修正-流出) EBOD-185  FC2 PPV 1317993 (Uncensored Leaked)",
    "START-046 jav torrents - Rei Kamiki",
    "SONE-269 4K BluRay",
    "ABF-319 Remu Suzumori",
    "PPV 1317993",
    "FC2 PPV 9876543 uncensored",
    "random text no code",
]

print("=== TEST EXTRACT CODE PRO ===\n")

for t in tests:
    print("TEXT:", t)
    print("CODE:", extract_code(t))
    print("-" * 50)

print("\nDONE.")
