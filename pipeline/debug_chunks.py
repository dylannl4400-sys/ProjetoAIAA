"""
debug_chunks.py

# Mostra os chunks gerados pelo StructureAwareChunker para um PDF,
# sem indexar nada. Útil para verificar se as secções estão a ser
# detectadas correctamente.

# Uso:
#     python debug_chunks.py legal_docs/legislacao_01_codigo_civil_responsabilidade.pdf
# """

# import sys
# from structure_aware_chunker import StructureAwareChunker

# path = sys.argv[1] if len(sys.argv) > 1 else "legal_docs/legislacao_01_codigo_civil_responsabilidade.pdf"

# chunker = StructureAwareChunker()
# chunks  = chunker.split(path)

# print(f"\nFicheiro : {path}")
# print(f"Chunks   : {len(chunks)}\n")
# print("=" * 65)

# for i, chunk in enumerate(chunks, 1):
#     section  = chunk.get("section",     "unknown")
#     start    = chunk.get("char_start",  "?")
#     end      = chunk.get("char_end",    "?")
#     length   = len(chunk["text"])
#     preview  = chunk["text"][:].replace("\n", " ")

#     print(f"[{i}] Secção   : {section}")
#     print(f"     Caracteres: {start}–{end}  ({length} chars)")
#     print(f"     Preview  : {preview}...")
#     print("-" * 65)
# """
# debug_search.py
# Mostra os chunks devolvidos para uma pergunta, incluindo os que ficam fora do top-5.
# """
# from config import load_config, build_embedder, build_store

# cfg      = load_config()
# embedder = build_embedder(cfg.embedder)
# store    = build_store(cfg.vector_store, embedder)

# pergunta = "o que diz o artigo 483 do codigo civil"
# results  = store.search(pergunta, n=15)  # busca os 15 mais próximos

# print(f"\nTop 15 chunks para: '{pergunta}'\n")
# print("=" * 65)
# for i, r in enumerate(results, 1):
#     meta    = r["metadata"]
#     section = meta.get("section",  "unknown")
#     ficheiro= meta.get("filename", "?")
#     score   = r["score"]
#     preview = r["text"][:80].replace("\n", " ")
#     print(f"[{i:2}] score={score:.3f} | {ficheiro} | § {section}")
#     print(f"      {preview}...")
#     print()

from bs4 import BeautifulSoup
import requests, re

# url = "https://www.dgsi.pt/jtre.nsf/134973db04f39bf2802579bf005f080b/6d8e26d4edebf16080258db20051e5b3?OpenDocument"
url = "https://www.dgsi.pt/jtrp.nsf/56a6e7121657f91e80257cda00381fdf/52bbffe41f217b6f80258dbc003b7d5d?OpenDocument"

resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})

resp.encoding = "iso-8859-1"
soup = BeautifulSoup(resp.text, "html.parser")

print("=== Elementos <b><u> (titulos principais) ===")
for elem in soup.find_all("u"):
    txt = elem.get_text(strip=True)
    if txt and len(txt) < 150:
        print(f"  parent={elem.parent.name if elem.parent else '?'} | {txt[:100]}")

print("\n=== Elementos <b> com padrao de seccao ===")
for elem in soup.find_all("b"):
    txt = elem.get_text(strip=True)
    if txt and len(txt) < 100:
        if re.match(r"^(I{1,3}V?|IV|VI{0,3}|IX|X)[\.\s]", txt) or re.match(r"^\d+\.\d+", txt):
            print(f"  {txt[:100]}")

print("\n=== Primeiras 5 tabelas — estrutura ===")
for i, t in enumerate(soup.find_all("table")[:5]):
    rows = t.find_all("tr")
    print(f"  Tabela {i}: {len(rows)} linhas")