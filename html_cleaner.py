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

# _CAMPO_SUMARIO   = "Sumário:"
# _CAMPO_TEXTO     = "Decisão Texto Integral:"


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
#         if label in (_CAMPO_SUMARIO, _CAMPO_TEXTO):
#             continue
#         valor = _limpar_texto(valor)
#         if valor:
#             metadados[label.rstrip(":")] = valor

#     # Sumário
#     sumario = _limpar_texto(campos.get(_CAMPO_SUMARIO, ""))

#     # Corpo — texto integral sem tags e sem linhas em branco excessivas
#     corpo_raw = campos.get(_CAMPO_TEXTO, "")
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

"""
html_cleaner.py

Limpa o HTML de um acórdão do ITIJ e devolve:
    - metadados estruturados (dict)
    - sumário (str)
    - texto do corpo limpo (str) — pronto para o LLM classificar

Determinístico — não usa LLM.

Uso:
    from html_cleaner import limpar_acordao

    resultado = limpar_acordao(html_str)
    resultado["metadados"]  # dict com Processo, Relator, etc.
    resultado["sumario"]    # str
    resultado["corpo"]      # str com texto limpo do corpo do acórdão
"""

import re
from bs4 import BeautifulSoup


# Campos que vão para metadados estruturados
_CAMPOS_META = {
    "Processo:", "Relator:", "Descritores:", "Data do Acordão:",
    "Votação:", "Meio Processual:", "Decisão:", "Área Temática:",
    "Texto Integral:", "Nº Convencional:", "Tribunal Recurso:",
    "Processo:", "Relator:",
}

# Variantes do label nos diferentes tribunais
_CAMPOS_SUMARIO = {"Sumário:", "Sumario:", "Sumário :", "SUMÁRIO:"}
_CAMPOS_TEXTO   = {
    "Decisão Texto Integral:", "Decisao Texto Integral:",
    "Texto Integral:", "Decisão:", "Texto:",
}
# Manter aliases simples para compatibilidade
_CAMPO_SUMARIO = "Sumário:"
_CAMPO_TEXTO   = "Decisão Texto Integral:"


def limpar_acordao(html: str) -> dict:
    """
    Extrai e limpa o conteúdo de um acórdão HTML do ITIJ.

    Returns:
        {
            "metadados": dict,   # campos estruturados
            "sumario":   str,    # sumário limpo
            "corpo":     str,    # texto integral limpo (para LLM)
        }
    """
    soup   = BeautifulSoup(html, "html.parser")
    campos = _extrair_campos(soup)

    # Metadados estruturados
    metadados = {}
    for label, valor in campos.items():
        if label in _CAMPOS_SUMARIO or label in _CAMPOS_TEXTO:
            continue
        valor = _limpar_texto(valor)
        if valor:
            metadados[label.rstrip(":")] = valor

    # Sumário
    sumario = ""
    for k in _CAMPOS_SUMARIO:
        if k in campos and campos[k].strip():
            sumario = _limpar_texto(campos[k])
            break

    # Corpo — texto integral sem tags e sem linhas em branco excessivas
    corpo_raw = ""
    for k in _CAMPOS_TEXTO:
        if k in campos and campos[k].strip():
            corpo_raw = campos[k]
            break
    # Fallback: maior campo da tabela que nao seja sumario nem metadado curto
    if not corpo_raw.strip():
        for label, valor in campos.items():
            if len(valor) > 1000 and label not in _CAMPOS_SUMARIO:
                corpo_raw = valor
                break
    corpo     = _limpar_texto(corpo_raw)

    return {
        "metadados": metadados,
        "sumario":   sumario,
        "corpo":     corpo,
    }


def metadados_para_texto(metadados: dict) -> str:
    """Converte dict de metadados em texto formatado para chunk."""
    linhas = [f"{k}: {v}" for k, v in metadados.items() if v]
    return "\n".join(linhas)


# ------------------------------------------------------------------
# Internos
# ------------------------------------------------------------------

def _extrair_campos(soup: BeautifulSoup) -> dict:
    """Extrai cada campo da tabela de cabeçalho."""
    campos = {}
    tabela = soup.find("table")
    if not tabela:
        return campos
    for tr in tabela.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        label = tds[0].get_text(strip=True)
        valor = tds[1].get_text(separator="\n", strip=True)
        if label and valor and len(label) < 60:
            campos[label] = valor
    return campos


def _limpar_texto(texto: str) -> str:
    """Remove linhas em branco excessivas e espaços desnecessários."""
    if not texto:
        return ""
    # Normalizar quebras de linha
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    # Remover linhas com só espaços
    linhas = [l.strip() for l in texto.splitlines()]
    # Colapsar múltiplas linhas em branco para no máximo 1
    resultado = []
    blank    = 0
    for l in linhas:
        if not l:
            blank += 1
            if blank <= 1:
                resultado.append("")
        else:
            blank = 0
            resultado.append(l)
    return "\n".join(resultado).strip()