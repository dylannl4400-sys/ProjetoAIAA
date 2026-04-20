import requests

BASE_URL = "https://www.dgsi.pt"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "text/html,application/xhtml+xml",
    "Accept-Language": "pt-PT,pt;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)

post_url = f"{BASE_URL}/jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument"
resp = session.post(post_url, data={"Query": "despedimento"}, timeout=15, allow_redirects=True)
resp.encoding = resp.apparent_encoding or "utf-8"

print(f"Status  : {resp.status_code}")
print(f"URL final: {resp.url}")
print(f"Tamanho : {len(resp.text)} chars")
print("\n--- HTML (primeiros 3000 chars) ---\n")
print(resp.text[:3000])
