# import sys
# sys.path.insert(0, '.')

# from config import load_config, build_embedder, build_store, build_chunker
# from itij_scraper import ITIJScraper
# from itij_chunker import ITIJChunker
# from document_registry import registar_e_indexar
# import requests, os, tempfile

# # Configuração
# cfg      = load_config()
# embedder = build_embedder(cfg.embedder)
# store    = build_store(cfg.vector_store, embedder)

# # URL de teste
# # url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/6d8e26d4edebf16080258db20051e5b3?OpenDocument"
# url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/53904630995ab81a80258db20051e5aa?OpenDocument&Highlight=0,despedimento"
# print("1. A descarregar HTML...")
# resp = requests.get(url, timeout=30, headers={
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#     "Accept": "text/html,application/xhtml+xml",
#     "Referer": "https://www.dgsi.pt/",
# })
# print(f"   Status: {resp.status_code}, tamanho: {len(resp.text)} chars")
# resp.encoding = "iso-8859-1"

# print("2. A guardar ficheiro temporario...")
# tmp_path = os.path.join(tempfile.gettempdir(), "TRE_teste.html")
# with open(tmp_path, "w", encoding="utf-8") as f:
#     f.write(resp.text)
# print(f"   Guardado em: {tmp_path}")

# print("3. A criar ITIJChunker...")
# chunker = ITIJChunker(chunk_size=1000, overlap=200)

# print("4. A fazer chunking...")
# chunks = chunker.split(resp.text)
# print(f"   {len(chunks)} chunks gerados")
# for c in chunks[:3]:
#     print(f"   § {c['section']} ({len(c['text'])} chars)")
    
# print("\nTodos os chunks:")
# for c in chunks:
#     print(f"  § {c['section']} ({len(c['text'])} chars)")

# print("5. A indexar...")
# resultado = registar_e_indexar(
#     path_original       = tmp_path,
#     metadata_utilizador = {"type": "ruling", "court": "TRE", "source": "ITIJ"},
#     chunker             = chunker,
#     store               = store,
# )
# print(f"   Resultado: {resultado}")


# os.unlink(tmp_path)

# from html_cleaner import limpar_acordao, metadados_para_texto
# from llm_chunker import LLMChunker
# import requests

# url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/3731e3e4b692fdd980258db20051e5a7?OpenDocument"
# resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
# resp.encoding = "iso-8859-1"

# # Limpar
# resultado = limpar_acordao(resp.text)
# print("=== Metadados ===")
# for k, v in resultado["metadados"].items():
#     print(f"  {k}: {v[:60]}")

# print(f"\n=== Sumário ({len(resultado['sumario'])} chars) ===")
# print(resultado["sumario"][:200])

# print(f"\n=== Corpo ({len(resultado['corpo'])} chars) ===")
# print(resultado["corpo"][:300])

# # Classificar com LLM
# chunker = LLMChunker(base_url="https://roselike-angelita-causational.ngrok-free.dev", model="qwen2.5:14b")
# chunks  = chunker.chunks_para_indexar(
#     texto    =resultado["corpo"],
#     metadados=metadados_para_texto(resultado["metadados"]),
#     sumario  =resultado["sumario"],
# )

# print(f"\n=== Chunks gerados: {len(chunks)} ===")
# from collections import Counter
# for seccao, n in Counter(c["section"] for c in chunks).items():
#     print(f"  {seccao}: {n} chunks")

import os

from html_cleaner import limpar_acordao, metadados_para_texto
from llm_chunker import LLMChunker
import requests


# url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/3731e3e4b692fdd980258db20051e5a7?OpenDocument"
url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/6b91445b57eae95280258dc00041b27b?OpenDocument"
resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
resp.encoding = "iso-8859-1"

resultado = limpar_acordao(resp.text)
meta_dict = resultado["metadados"]
sumario = resultado["sumario"]
corpo = resultado["corpo"]

os.makedirs("acordaos_limpos", exist_ok=True)
path_txt = os.path.join("acordaos_limpos", "teste.txt")
texto_ficheiro = ""
if sumario:
    texto_ficheiro += f"SUMARIO:\n{sumario}\n\n"
texto_ficheiro += corpo
with open(path_txt, "w", encoding="utf-8") as f:
    f.write(texto_ficheiro)

chunker = LLMChunker(
    base_url="https://roselike-angelita-causational.ngrok-free.dev",
    model="qwen2.5:14b",
    block_size=2200,
    overlap=100,
)

# Ver quantos blocos e o tamanho do primeiro lote
# Ver cada lote individualmente
chunks = chunker.chunks_para_indexar(
    texto    =resultado["corpo"],
    metadados=metadados_para_texto(resultado["metadados"]),
    sumario  =resultado["sumario"],
)
print(f"Total chunks: {len(chunks)}")
from collections import Counter
for s, n in Counter(c["section"] for c in chunks).items():
    print(f"  {s}: {n}")
    
# Ver chunks por secção
print("\n" + "="*60)
seccao_ver = "relatorio"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
    
print("\n" + "="*60)
seccao_ver = "fundamentacao_direito"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
print("\n" + "="*60)
seccao_ver = "metadados"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
print("\n" + "="*60)
seccao_ver = "sumario"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")

print("\n" + "="*60)
seccao_ver = "decisao"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
print("\n" + "="*60)
seccao_ver = "outro"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
print("\n" + "="*60)
seccao_ver = "factos"  # muda para ver outra secção
chunks_seccao = [c for c in chunks if c["section"] == seccao_ver]
print(f"Chunks de '{seccao_ver}': {len(chunks_seccao)}")

for i, c in enumerate(chunks_seccao):
    print(f"\n--- Chunk {i+1} ({len(c['text'])} chars) ---")
    print(c["text"])
    print("...")
    
    