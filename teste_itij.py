# """
# teste_itij.py

# Testa os 4 tipos de pesquisa do ITIJ e a extracção de texto.

# Uso:
#     python teste_itij.py                          # todos os testes (TRE)
#     python teste_itij.py livre                    # só pesquisa livre
#     python teste_itij.py termos                   # só pesquisa por termos
#     python teste_itij.py campo                    # só pesquisa por campo
#     python teste_itij.py descritor                # só pesquisa por descritor
#     python teste_itij.py hashes trl               # descobrir hashes do TRL
# """

# import sys
# from itij_scraper import ITIJScraper, TRIBUNAIS

# scraper  = ITIJScraper()
# tribunal = "tre"
# modo     = sys.argv[1] if len(sys.argv) > 1 else "todos"

# def separador(titulo):
#     print(f"\n{'=' * 65}")
#     print(f"  {titulo}")
#     print(f"{'=' * 65}\n")

# def mostrar(resultados, n=3):
#     if not resultados:
#         print("  Nenhum resultado.\n")
#         return
#     print(f"  {len(resultados)} resultados encontrados\n")
#     for r in resultados[:n]:
#         print(f"  [{r['processo']}]  {r['data']}  {r['relator']}")
#         print(f"  Descritores: {', '.join(r['descritores'][:3])}")
#         print(f"  URL: {r['url']}\n")


# # ── Descobrir hashes ────────────────────────────────────────────────────────
# if modo == "hashes":
#     t = sys.argv[2] if len(sys.argv) > 2 else "trl"
#     separador(f"Descobrir hashes — {TRIBUNAIS[t]['nome']}")
#     hashes = scraper.confirmar_hashes(t)
#     for k, v in hashes.items():
#         print(f"  {k}: {v}")
#     sys.exit(0)


# # ── Pesquisa Livre ──────────────────────────────────────────────────────────
# if modo in ("todos", "livre"):
#     separador("Pesquisa Livre — 'despedimento ilícito justa causa'")
#     r = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal)
#     mostrar(r)


# # ── Pesquisa por Termos ─────────────────────────────────────────────────────
# if modo in ("todos", "termos"):
#     separador("Pesquisa por Termos — despedimento AND justa causa")
#     r = scraper.pesquisar_termos(
#         termos=["despedimento", "justa causa"],
#         operadores=["AND"],
#         tribunal=tribunal
#     )
#     mostrar(r)


# # ── Pesquisa por Campo ──────────────────────────────────────────────────────
# if modo in ("todos", "campo"):
#     separador("Pesquisa por Campo — DESCRITORES = DESPEDIMENTO ILICITO")
#     r = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal)
#     mostrar(r)


# # ── Pesquisa por Descritor ──────────────────────────────────────────────────
# if modo in ("todos", "descritor"):
#     separador("Pesquisa por Descritor — PRESCRICAO")
#     r = scraper.pesquisar_descritor("RELATOR", tribunal)
#     mostrar(r)


# # ── Descarregar texto do 1º resultado ──────────────────────────────────────
# if modo == "todos":
#     separador("Descarregar texto — primeiro acórdão da pesquisa livre")
#     r = scraper.pesquisar_livre("despedimento ilicito", tribunal, max_resultados=1)
#     if r:
#         texto = scraper.descarregar_texto(r[0]["url"])
#         print(f"  Processo : {r[0]['processo']}")
#         print(f"  Caracteres: {len(texto)}\n")
#         print(texto[:600])
#         print("\n  [...]")

"""
teste_itij.py

Testa os 4 tipos de pesquisa do ITIJ e a extracção de texto.

Uso:
    python teste_itij.py                          # todos os testes (TRE)
    python teste_itij.py livre                    # só pesquisa livre
    python teste_itij.py termos                   # só pesquisa por termos
    python teste_itij.py campo                    # só pesquisa por campo
    python teste_itij.py descritor                # só pesquisa por descritor
    python teste_itij.py hashes trl               # descobrir hashes do TRL
"""

import sys
from itij_scraper import ITIJScraper, TRIBUNAIS

scraper  = ITIJScraper()
tribunal = "tre"
modo     = sys.argv[1] if len(sys.argv) > 1 else "todos"

def separador(titulo):
    print(f"\n{'=' * 65}")
    print(f"  {titulo}")
    print(f"{'=' * 65}\n")

def mostrar(resultados, n=3):
    if not resultados:
        print("  Nenhum resultado.\n")
        return
    print(f"  {len(resultados)} resultados encontrados\n")
    for r in resultados[:n]:
        print(f"  [{r['processo']}]  {r['data']}  {r['relator']}")
        print(f"  Descritores: {', '.join(r['descritores'][:3])}")
        print(f"  URL: {r['url']}\n")


# ── Descobrir hashes ────────────────────────────────────────────────────────
if modo == "hashes":
    t = sys.argv[2] if len(sys.argv) > 2 else "trl"
    separador(f"Descobrir hashes — {TRIBUNAIS[t]['nome']}")
    hashes = scraper.confirmar_hashes(t)
    for k, v in hashes.items():
        print(f"  {k}: {v}")
    sys.exit(0)


# ── Pesquisa Livre ──────────────────────────────────────────────────────────
if modo in ("todos", "livre"):
    separador("Pesquisa Livre — 'despedimento ilícito justa causa'")
    r = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal)
    mostrar(r)


# ── Pesquisa por Termos ─────────────────────────────────────────────────────
if modo in ("todos", "termos"):
    separador("Pesquisa por Termos — despedimento AND justa causa")
    r = scraper.pesquisar_termos(
        termos=["despedimento", "justa causa"],
        operadores=["AND"],
        tribunal=tribunal
    )
    mostrar(r)


# ── Pesquisa por Campo ──────────────────────────────────────────────────────
if modo in ("todos", "campo"):
    separador("Pesquisa por Campo — DESCRITORES = DESPEDIMENTO ILICITO")
    r = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal)
    mostrar(r)


# ── Pesquisa por Descritor ──────────────────────────────────────────────────
if modo in ("todos", "descritor"):
    separador("Pesquisa por Descritor — lista de descritores para despedimento")
    descritores = scraper.pesquisar_descritor("despedimento", tribunal)
    if not descritores:
        print("  Nenhum descritor encontrado.")
    else:
        print(f"  {len(descritores)} descritores encontrados")
        for d in descritores[:5]:
            print(f"  > {d['descritor_principal']}")
            if d['descritores_relacionados']:
                print(f"    Relacionados: {', '.join(d['descritores_relacionados'][:3])}")
        print()

    separador("Pesquisa de acordaos por descritor exacto — DESPEDIMENTO ILICITO")
    r = scraper.pesquisar_acordaos_por_descritor("DESPEDIMENTO ILICITO", tribunal)
    mostrar(r)


# ── Descarregar texto do 1º resultado ──────────────────────────────────────
if modo == "todos":
    separador("Descarregar texto — primeiro acórdão da pesquisa livre")
    r = scraper.pesquisar_livre("despedimento ilicito", tribunal, max_resultados=1)
    if r:
        texto = scraper.descarregar_texto(r[0]["url"])
        print(f"  Processo : {r[0]['processo']}")
        print(f"  Caracteres: {len(texto)}\n")
        print(texto[:600])
        print("\n  [...]")