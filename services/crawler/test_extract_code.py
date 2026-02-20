import re

def extract_code(text):
    m = re.search(r'([A-Z0-9]+-\d+)', text.upper())
    return m.group(1) if m else None

tests = [
    "(無修正-流出) EBOD-185  FC2 PPV 1317993 (Uncensored Leaked) E-BODY-特別編- 灼熱の青姦情痴 みなせ優夏 (Yuka Minase)",
    "START-046 jav torrents - Rei Kamiki",
    "SONE-269 4K BluRay",
    "ABF-319 Remu Suzumori",
    "PPV 1317993",
]

print("\n=== TEST EXTRACT CODE ===\n")

for t in tests:
    print("TEXT:", t)
    print("CODE:", extract_code(t))
    print("-" * 50)

print("\nDONE.")
