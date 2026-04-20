# # """
# # html_cleaner.py

# # Limpa o HTML de um acórdão do ITIJ e devolve:
# #     - metadados estruturados (dict)
# #     - sumário (str)
# #     - texto do corpo limpo (str) — pronto para o LLM classificar

# # Determinístico — não usa LLM.

# # Uso:
# #     from html_cleaner import limpar_acordao

# #     resultado = limpar_acordao(html_str)
# #     resultado["metadados"]  # dict com Processo, Relator, etc.
# #     resultado["sumario"]    # str
# #     resultado["corpo"]      # str com texto limpo do corpo do acórdão
# # """

# # import re
# # from bs4 import BeautifulSoup


# # # Campos que vão para metadados estruturados
# # _CAMPOS_META = {
# #     "Processo:", "Relator:", "Descritores:", "Data do Acordão:",
# #     "Votação:", "Meio Processual:", "Decisão:", "Área Temática:",
# #     "Texto Integral:", "Nº Convencional:", "Tribunal Recurso:",
# #     "Processo:", "Relator:",
# # }

# # _CAMPO_SUMARIO   = "Sumário:"
# # _CAMPO_TEXTO     = "Decisão Texto Integral:"


# # def limpar_acordao(html: str) -> dict:
# #     """
# #     Extrai e limpa o conteúdo de um acórdão HTML do ITIJ.

# #     Returns:
# #         {
# #             "metadados": dict,   # campos estruturados
# #             "sumario":   str,    # sumário limpo
# #             "corpo":     str,    # texto integral limpo (para LLM)
# #         }
# #     """
# #     soup   = BeautifulSoup(html, "html.parser")
# #     campos = _extrair_campos(soup)

# #     # Metadados estruturados
# #     metadados = {}
# #     for label, valor in campos.items():
# #         if label in (_CAMPO_SUMARIO, _CAMPO_TEXTO):
# #             continue
# #         valor = _limpar_texto(valor)
# #         if valor:
# #             metadados[label.rstrip(":")] = valor

# #     # Sumário
# #     sumario = _limpar_texto(campos.get(_CAMPO_SUMARIO, ""))

# #     # Corpo — texto integral sem tags e sem linhas em branco excessivas
# #     corpo_raw = campos.get(_CAMPO_TEXTO, "")
# #     corpo     = _limpar_texto(corpo_raw)

# #     return {
# #         "metadados": metadados,
# #         "sumario":   sumario,
# #         "corpo":     corpo,
# #     }


# # def metadados_para_texto(metadados: dict) -> str:
# #     """Converte dict de metadados em texto formatado para chunk."""
# #     linhas = [f"{k}: {v}" for k, v in metadados.items() if v]
# #     return "\n".join(linhas)


# # # ------------------------------------------------------------------
# # # Internos
# # # ------------------------------------------------------------------

# # def _extrair_campos(soup: BeautifulSoup) -> dict:
# #     """Extrai cada campo da tabela de cabeçalho."""
# #     campos = {}
# #     tabela = soup.find("table")
# #     if not tabela:
# #         return campos
# #     for tr in tabela.find_all("tr"):
# #         tds = tr.find_all("td", recursive=False)
# #         if len(tds) < 2:
# #             continue
# #         label = tds[0].get_text(strip=True)
# #         valor = tds[1].get_text(separator="\n", strip=True)
# #         if label and valor and len(label) < 60:
# #             campos[label] = valor
# #     return campos


# # def _limpar_texto(texto: str) -> str:
# #     """Remove linhas em branco excessivas e espaços desnecessários."""
# #     if not texto:
# #         return ""
# #     # Normalizar quebras de linha
# #     texto = texto.replace("\r\n", "\n").replace("\r", "\n")
# #     # Remover linhas com só espaços
# #     linhas = [l.strip() for l in texto.splitlines()]
# #     # Colapsar múltiplas linhas em branco para no máximo 1
# #     resultado = []
# #     blank    = 0
# #     for l in linhas:
# #         if not l:
# #             blank += 1
# #             if blank <= 1:
# #                 resultado.append("")
# #         else:
# #             blank = 0
# #             resultado.append(l)
# #     return "\n".join(resultado).strip()

# """
# html_cleaner.py

# Limpa o HTML de um acórdão do ITIJ e devolve:
#     - metadados estruturados (dict)
#     - sumário (str)
#     - texto do corpo limpo (str) — pronto para o LLM classificar

# Determinístico — não usa LLM.

# Uso:
#     from html_cleaner import limpar_acordao

#     resultado = limpar_acordao(html_str)
#     resultado["metadados"]  # dict com Processo, Relator, etc.
#     resultado["sumario"]    # str
#     resultado["corpo"]      # str com texto limpo do corpo do acórdão
# """

# import re
# from bs4 import BeautifulSoup


# # Campos que vão para metadados estruturados
# _CAMPOS_META = {
#     "Processo:", "Relator:", "Descritores:", "Data do Acordão:",
#     "Votação:", "Meio Processual:", "Decisão:", "Área Temática:",
#     "Texto Integral:", "Nº Convencional:", "Tribunal Recurso:",
#     "Processo:", "Relator:",
# }

# # Variantes do label nos diferentes tribunais
# _CAMPOS_SUMARIO = {"Sumário:", "Sumario:", "Sumário :", "SUMÁRIO:"}
# _CAMPOS_TEXTO   = {
#     "Decisão Texto Integral:", "Decisao Texto Integral:",
#     "Texto Integral:", "Decisão:", "Texto:",
# }
# # Manter aliases simples para compatibilidade
# _CAMPO_SUMARIO = "Sumário:"
# _CAMPO_TEXTO   = "Decisão Texto Integral:"


# def limpar_acordao(html: str) -> dict:
#     """
#     Extrai e limpa o conteúdo de um acórdão HTML do ITIJ.

#     Returns:
#         {
#             "metadados": dict,   # campos estruturados
#             "sumario":   str,    # sumário limpo
#             "corpo":     str,    # texto integral limpo (para LLM)
#         }
#     """
#     soup   = BeautifulSoup(html, "html.parser")
#     campos = _extrair_campos(soup)

#     # Metadados estruturados
#     metadados = {}
#     for label, valor in campos.items():
#         if label in _CAMPOS_SUMARIO or label in _CAMPOS_TEXTO:
#             continue
#         valor = _limpar_texto(valor)
#         if valor:
#             metadados[label.rstrip(":")] = valor

#     # Sumário
#     sumario = ""
#     for k in _CAMPOS_SUMARIO:
#         if k in campos and campos[k].strip():
#             sumario = _limpar_texto(campos[k])
#             break

#     # Corpo — texto integral sem tags e sem linhas em branco excessivas
#     corpo_raw = ""
#     for k in _CAMPOS_TEXTO:
#         if k in campos and campos[k].strip():
#             corpo_raw = campos[k]
#             break
#     # Fallback: maior campo da tabela que nao seja sumario nem metadado curto
#     if not corpo_raw.strip():
#         for label, valor in campos.items():
#             if len(valor) > 1000 and label not in _CAMPOS_SUMARIO:
#                 corpo_raw = valor
#                 break
#     corpo     = _limpar_texto(corpo_raw)

#     return {
#         "metadados": metadados,
#         "sumario":   sumario,
#         "corpo":     corpo,
#     }


# def metadados_para_texto(metadados: dict) -> str:
#     """Converte dict de metadados em texto formatado para chunk."""
#     linhas = [f"{k}: {v}" for k, v in metadados.items() if v]
#     return "\n".join(linhas)


# # ------------------------------------------------------------------
# # Internos
# # ------------------------------------------------------------------

# def _extrair_campos(soup: BeautifulSoup) -> dict:
#     """Extrai cada campo da tabela de cabeçalho."""
#     campos = {}
#     tabela = soup.find("table")
#     if not tabela:
#         return campos
#     for tr in tabela.find_all("tr"):
#         tds = tr.find_all("td", recursive=False)
#         if len(tds) < 2:
#             continue
#         label = tds[0].get_text(strip=True)
#         valor = tds[1].get_text(separator="\n", strip=True)
#         if label and valor and len(label) < 60:
#             campos[label] = valor
#     return campos


# def _limpar_texto(texto: str) -> str:
#     """Remove linhas em branco excessivas e espaços desnecessários."""
#     if not texto:
#         return ""
#     # Normalizar quebras de linha
#     texto = texto.replace("\r\n", "\n").replace("\r", "\n")
#     # Remover linhas com só espaços
#     linhas = [l.strip() for l in texto.splitlines()]
#     # Colapsar múltiplas linhas em branco para no máximo 1
#     resultado = []
#     blank    = 0
#     for l in linhas:
#         if not l:
#             blank += 1
#             if blank <= 1:
#                 resultado.append("")
#         else:
#             blank = 0
#             resultado.append(l)
#     return "\n".join(resultado).strip()

# """
# html_cleaner.py

# Limpa o HTML de um acórdão do ITIJ e devolve:
#     - metadados estruturados (dict)
#     - sumário (str)
#     - texto do corpo limpo (str) — pronto para o LLM classificar

# Determinístico — não usa LLM.

# Uso:
#     from html_cleaner import limpar_acordao

#     resultado = limpar_acordao(html_str)
#     resultado["metadados"]  # dict com Processo, Relator, etc.
#     resultado["sumario"]    # str
#     resultado["corpo"]      # str com texto limpo do corpo do acórdão
# """

# import re
# from bs4 import BeautifulSoup


# # Campos que vão para metadados estruturados
# _CAMPOS_META = {
#     "Processo:", "Relator:", "Descritores:", "Data do Acordão:",
#     "Votação:", "Meio Processual:", "Decisão:", "Área Temática:",
#     "Texto Integral:", "Nº Convencional:", "Tribunal Recurso:",
#     "Processo:", "Relator:",
# }

# # Variantes do label nos diferentes tribunais
# _CAMPOS_SUMARIO = {"Sumário:", "Sumario:", "Sumário :", "SUMÁRIO:"}
# _CAMPOS_TEXTO   = {
#     "Decisão Texto Integral:", "Decisao Texto Integral:",
#     "Texto Integral:", "Decisão:", "Texto:",
# }
# # Manter aliases simples para compatibilidade
# _CAMPO_SUMARIO = "Sumário:"
# _CAMPO_TEXTO   = "Decisão Texto Integral:"


# def limpar_acordao(html: str) -> dict:
#     """
#     Extrai e limpa o conteúdo de um acórdão HTML do ITIJ.

#     Returns:
#         {
#             "metadados": dict,   # campos estruturados
#             "sumario":   str,    # sumário limpo
#             "corpo":     str,    # texto integral limpo (para LLM)
#         }
#     """
#     soup   = BeautifulSoup(html, "html.parser")
#     campos = _extrair_campos(soup)

#     # Metadados estruturados
#     metadados = {}
#     for label, valor in campos.items():
#         if label in _CAMPOS_SUMARIO or label in _CAMPOS_TEXTO:
#             continue
#         valor = _limpar_texto(valor)
#         if valor:
#             metadados[label.rstrip(":")] = valor

#     # Sumário
#     sumario = ""
#     for k in _CAMPOS_SUMARIO:
#         if k in campos and campos[k].strip():
#             sumario = _limpar_texto(campos[k])
#             break

#     # Corpo — texto integral sem tags e sem linhas em branco excessivas
#     corpo_raw = ""
#     for k in _CAMPOS_TEXTO:
#         if k in campos and campos[k].strip():
#             corpo_raw = campos[k]
#             break
#     # Fallback: maior campo da tabela que nao seja sumario nem metadado curto
#     if not corpo_raw.strip():
#         for label, valor in campos.items():
#             if len(valor) > 1000 and label not in _CAMPOS_SUMARIO:
#                 corpo_raw = valor
#                 break
#     corpo     = _limpar_texto(corpo_raw)

#     return {
#         "metadados": metadados,
#         "sumario":   sumario,
#         "corpo":     corpo,
#     }


# def metadados_para_texto(metadados: dict) -> str:
#     """Converte dict de metadados em texto formatado para chunk."""
#     linhas = [f"{k}: {v}" for k, v in metadados.items() if v]
#     return "\n".join(linhas)


# # ------------------------------------------------------------------
# # Internos
# # ------------------------------------------------------------------

# def _extrair_campos(soup: BeautifulSoup) -> dict:
#     """
#     Extrai cada campo da tabela de cabeçalho como texto puro.
#     Usa cópia do td para não modificar o DOM ao remover subtabelas.
#     """
#     import copy as _copy

#     campos = {}
#     tabela = soup.find("table")
#     if not tabela:
#         return campos

#     # Recolher apenas tr directos da tabela principal
#     trs = []
#     for filho in tabela.children:
#         if not hasattr(filho, "name"):
#             continue
#         if filho.name == "tr":
#             trs.append(filho)
#         elif filho.name in ("tbody", "thead"):
#             for tr in filho.children:
#                 if hasattr(tr, "name") and tr.name == "tr":
#                     trs.append(tr)

#     for tr in trs:
#         tds = tr.find_all("td", recursive=False)
#         if len(tds) < 2:
#             continue
#         label = tds[0].get_text(strip=True)
#         if not label or len(label) > 60:
#             continue

#         # Copiar td para nao alterar o DOM ao remover subtabelas
#         # td_copia = _copy.copy(tds[1])
#         td_copia = _copy.deepcopy(tds[1])
#         for subtabela in td_copia.find_all("table"):
#             subtabela.decompose()

#         valor = td_copia.get_text(separator="\n", strip=True)
#         if valor:
#             campos[label] = valor

#     return campos

# def _limpar_texto(texto: str) -> str:
#     """Remove linhas em branco excessivas e espaços desnecessários."""
#     if not texto:
#         return ""
#     # Normalizar quebras de linha
#     texto = texto.replace("\r\n", "\n").replace("\r", "\n")
#     # Remover linhas com só espaços
#     linhas = [l.strip() for l in texto.splitlines()]
#     # Colapsar múltiplas linhas em branco para no máximo 1
#     resultado = []
#     blank    = 0
#     for l in linhas:
#         if not l:
#             blank += 1
#             if blank <= 1:
#                 resultado.append("")
#         else:
#             blank = 0
#             resultado.append(l)
#     return "\n".join(resultado).strip()

import re
from bs4 import BeautifulSoup, Tag
import unicodedata

def limpar_acordao(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head", "img", "noscript"]):
        tag.decompose()
    metadados, sumario = _extrair_metadados_e_sumario(soup)
    corpo = _extrair_texto_pagina(soup)
    if sumario and sumario in corpo:
        corpo = corpo.replace(sumario, "").strip()
    return {"metadados": metadados, "sumario": sumario, "corpo": corpo}

_CAMPOS_SUMARIO = {"sumario", "sumario"}

def _extrair_metadados_e_sumario(soup):
    metadados = {}
    sumario   = ""
    for tabela in soup.find_all("table"):
        for tr in tabela.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            label = _normalizar_label(tds[0].get_text())
            valor = _celula_para_texto(tds[1])
            if not label or not valor:
                continue
            if label in _CAMPOS_SUMARIO:
                sumario = valor
                continue
            if len(valor) < 300:
                metadados[label] = valor
    return metadados, sumario.strip()

def metadados_para_texto(metadados: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in metadados.items() if v)

def _extrair_texto_pagina(soup) -> str:
    for br in soup.find_all("br"):
        br.replace_with("\n")
    return _limpar_texto(soup.get_text(separator="\n"))

def _celula_para_texto(td: Tag) -> str:
    for br in td.find_all("br"):
        br.replace_with("\n")
    for p in td.find_all("p"):
        p.insert_before("\n")
    return _limpar_texto(td.get_text(separator="\n"))

def _normalizar_label(label: str) -> str:
    # Normalizar acentos antes de remover caracteres especiais
    label = unicodedata.normalize("NFD", label)
    label = "".join(c for c in label if unicodedata.category(c) != "Mn")
    label = label.lower()
    label = re.sub(r"[^a-z0-9 ]", "", label)
    return label.strip()

def _limpar_texto(texto: str) -> str:
    _IGNORAR = {
        "anterior", "seguinte", "principal", "pesquisa livre",
        "por termos", "por campo", "por descritor",
        "acordaos tre", "acordaos trl", "acordaos trp",
        "acordaos trc", "acordaos trg", "acordaos stj",
    }
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    linhas    = [l.strip() for l in texto.splitlines()]
    resultado = []
    blanks    = 0
    for l in linhas:
        if not l:
            blanks += 1
            if blanks <= 1:
                resultado.append("")
        else:
            if l.lower() in _IGNORAR:
                continue
            blanks = 0
            resultado.append(l)
    return "\n".join(resultado).strip()