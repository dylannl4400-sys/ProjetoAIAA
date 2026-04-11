# import requests

# session = requests.Session()
# session.headers.update({
#     "User-Agent": "Mozilla/5.0",
#     "Accept-Language": "pt-PT,pt;q=0.9",
# })

# post_url = "https://www.dgsi.pt/jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument"
# resp = session.post(post_url, data={"Query": "despedimento"}, timeout=15)

# print(f"Content-Type header : {resp.headers.get('Content-Type', 'não encontrado')}")
# print(f"Encoding detectado  : {resp.encoding}")
# print(f"Apparent encoding   : {resp.apparent_encoding}")
# print()

# # Mostrar bytes raw dos primeiros caracteres especiais encontrados
# for i, char in enumerate(resp.text[:500]):
#     if ord(char) > 127:
#         raw = resp.content[i:i+2].hex()
#         print(f"  char='{char}' ord={ord(char)} raw_bytes={raw}")

import requests
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
post_url = "https://www.dgsi.pt/jtre.nsf/b8f3314245b23f0780256879006d6593?CreateDocument"
resp = session.post(post_url, data={"Query": "DESPEDIMENTO"}, timeout=15)
resp.encoding = "iso-8859-1"
print(f"Status: {resp.status_code}, tamanho: {len(resp.text)}")
print(resp.text[:1000])