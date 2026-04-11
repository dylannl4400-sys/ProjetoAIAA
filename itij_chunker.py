# """
# itij_chunker.py

# Chunker especializado para acórdãos do ITIJ (dgsi.pt).

# Em vez de texto puro, recebe o HTML completo do acórdão e usa
# BeautifulSoup para detectar a estrutura real do documento:

#     - Metadados do cabeçalho (processo, relator, descritores, data, etc.)
#     - Secções do texto integral marcadas com <b><u> (RELATÓRIO, FUNDAMENTAÇÃO, DECISÃO)
#     - Sub-secções numeradas (9.1, 9.2, 8.3, etc.)
#     - Sumário como chunk próprio

# Cada secção fica num chunk próprio com metadados da secção.
# Secções longas (> max_section_chars) são subdivididas com FixedChunker.

# Dependências:
#     pip install beautifulsoup4

# Uso:
#     from itij_chunker import ITIJChunker

#     chunker = ITIJChunker(chunk_size=1000, overlap=200)
#     chunks  = chunker.split_html(html_content)

#     for chunk in chunks:
#         print(chunk["section"], len(chunk["text"]))
# """

# import re
# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker


# class ITIJChunker:
#     """
#     Chunker estrutural para acórdãos HTML do ITIJ.

#     Detecta secções por:
#     - Tags <b><u> — títulos principais (I. RELATÓRIO, II. FUNDAMENTAÇÃO, III. DECISÃO)
#     - Tags <b> com padrão numérico — sub-secções (9.1., 9.2., 8.3.)
#     - Campos de metadados do cabeçalho (Processo, Relator, Sumário, etc.)
#     """

#     # Campos de metadados do cabeçalho do acórdão
#     CAMPOS_META = [
#         "Processo", "Relator", "Descritores", "Data do Acordão",
#         "Votação", "Texto Integral", "Meio Processual", "Decisão",
#         "Área Temática", "Sumário", "Decisão Texto Integral",
#         "Nº Convencional", "Tribunal Recurso",
#     ]

#     def __init__(
#         self,
#         chunk_size:        int = 1000,
#         overlap:           int = 200,
#         max_section_chars: int = 1500,
#     ):
#         self._chunk_size        = chunk_size
#         self._overlap           = overlap
#         self._max_section_chars = max_section_chars
#         self._fixed             = FixedChunker(chunk_size, overlap)

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def split_html(self, html: str) -> list[dict]:
#         """
#         Divide o HTML de um acórdão em chunks estruturados.

#         Args:
#             html: HTML completo do acórdão (string)

#         Returns:
#             Lista de dicts com:
#                 text     : texto do chunk
#                 section  : nome da secção
#                 chunk_idx: índice do chunk dentro da secção
#         """
#         soup = BeautifulSoup(html, "html.parser")
#         chunks = []

#         # 1. Extrair metadados do cabeçalho como chunk próprio
#         meta_chunk = self._extrair_metadados(soup)
#         if meta_chunk:
#             chunks.append(meta_chunk)

#         # 2. Extrair texto integral por secções
#         texto_integral = self._extrair_texto_integral(soup)
#         if texto_integral:
#             chunks.extend(texto_integral)

#         # 3. Fallback — se não encontrou secções, usa FixedChunker no texto completo
#         if not chunks:
#             texto = soup.get_text(separator="\n")
#             texto = self._limpar_texto(texto)
#             for c in self._fixed.split(texto):
#                 chunks.append({**c, "section": "unknown"})

#         return chunks

#     def split(self, source) -> list[dict]:
#         """
#         Interface compatível com os outros chunkers.
#         Aceita HTML como string ou caminho para ficheiro .txt com HTML.
#         """
#         if isinstance(source, str) and source.strip().startswith("<"):
#             # É HTML directamente
#             return self.split_html(source)
#         else:
#             # É caminho para ficheiro
#             with open(source, "r", encoding="utf-8") as f:
#                 content = f.read()
#             if content.strip().startswith("<"):
#                 return self.split_html(content)
#             else:
#                 # Texto puro — fallback para FixedChunker
#                 chunks = self._fixed.split(content)
#                 return [{**c, "section": "unknown"} for c in chunks]

#     # ------------------------------------------------------------------
#     # Extracção de metadados do cabeçalho
#     # ------------------------------------------------------------------

#     def _extrair_metadados(self, soup: BeautifulSoup) -> dict | None:
#         """
#         Extrai os campos do cabeçalho do acórdão (tabela superior).
#         Processo, Relator, Descritores, Data, Sumário, etc.
#         """
#         linhas = []
#         tabelas = soup.find_all("table")

#         for tabela in tabelas[:3]:  # cabeçalho está nas primeiras tabelas
#             for tr in tabela.find_all("tr"):
#                 tds = tr.find_all("td")
#                 if len(tds) >= 2:
#                     label = tds[0].get_text(strip=True)
#                     valor = tds[1].get_text(strip=True)
#                     if label and valor and len(label) < 50:
#                         linhas.append(f"{label}: {valor}")

#         if not linhas:
#             return None

#         texto = "\n".join(linhas)
#         if len(texto) < 20:
#             return None

#         return {
#             "text":      texto,
#             "section":   "Metadados",
#             "chunk_idx": 0,
#         }

#     # ------------------------------------------------------------------
#     # Extracção do texto integral por secções
#     # ------------------------------------------------------------------

#     def _extrair_texto_integral(self, soup: BeautifulSoup) -> list[dict]:
#         """
#         Detecta e extrai as secções do texto integral.

#         Títulos principais: <b><u>I.RELATÓRIO</u></b>
#         Sub-secções: <b>9.1. Nulidade da sentença</b>
#         """
#         chunks   = []
#         secções  = []  # lista de (título, texto)

#         # Encontrar a célula com "Decisão Texto Integral"
#         texto_td = None
#         for td in soup.find_all("td"):
#             txt = td.get_text(strip=True)
#             if len(txt) > 500:  # célula grande = texto integral
#                 texto_td = td
#                 break

#         if not texto_td:
#             return []

#         # Percorrer elementos e detectar títulos de secção
#         secção_actual = "Texto Integral"
#         parágrafos    = []

#         for elem in texto_td.descendants:
#             if not hasattr(elem, "get_text"):
#                 continue

#             tag_name = getattr(elem, "name", None)
#             if not tag_name:
#                 continue

#             texto_elem = elem.get_text(strip=True)
#             if not texto_elem or len(texto_elem) < 2:
#                 continue

#             # Detectar título principal: <b><u> ou <u><b>
#             is_titulo_principal = (
#                 tag_name in ("b", "u") and
#                 elem.find("u") is not None or
#                 (tag_name == "u" and elem.parent and elem.parent.name == "b")
#             )

#             # Detectar título de secção por padrão: I., II., III. ou 9.1., 9.2.
#             is_titulo = (
#                 tag_name in ("b", "u") and
#                 len(texto_elem) < 100 and
#                 (
#                     re.match(r"^(I{1,3}V?|VI{0,3}|IX|X{0,3})\.", texto_elem) or
#                     re.match(r"^\d+\.\d+", texto_elem) or
#                     texto_elem.upper() in (
#                         "RELATÓRIO", "FUNDAMENTAÇÃO", "DECISÃO",
#                         "I.RELATÓRIO", "II.FUNDAMENTAÇÃO", "III.DECISÃO",
#                         "I. RELATÓRIO", "II. FUNDAMENTAÇÃO", "III. DECISÃO",
#                     )
#                 )
#             )

#             if is_titulo and texto_elem != secção_actual:
#                 # Guardar secção anterior
#                 if parágrafos:
#                     secções.append((secção_actual, "\n".join(parágrafos)))
#                 secção_actual = texto_elem
#                 parágrafos    = []
#             elif tag_name == "p" and len(texto_elem) > 20:
#                 parágrafos.append(texto_elem)

#         # Guardar última secção
#         if parágrafos:
#             secções.append((secção_actual, "\n".join(parágrafos)))

#         # Converter secções em chunks
#         for titulo, texto in secções:
#             texto = self._limpar_texto(texto)
#             if not texto:
#                 continue

#             if len(texto) <= self._max_section_chars:
#                 chunks.append({
#                     "text":      texto,
#                     "section":   titulo,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 # Secção longa — subdividir com FixedChunker
#                 sub_chunks = self._fixed.split(texto)
#                 for i, sc in enumerate(sub_chunks):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   titulo,
#                         "chunk_idx": i,
#                     })

#         return chunks

#     # ------------------------------------------------------------------
#     # Utilitários
#     # ------------------------------------------------------------------

#     def _limpar_texto(self, texto: str) -> str:
#         """Remove espaços excessivos e linhas em branco."""
#         linhas = [l.strip() for l in texto.splitlines() if l.strip()]
#         return "\n".join(linhas)

# """
# itij_chunker.py

# Chunker especializado para acórdãos do ITIJ (dgsi.pt).

# Em vez de texto puro, recebe o HTML completo do acórdão e usa
# BeautifulSoup para detectar a estrutura real do documento:

#     - Metadados do cabeçalho (processo, relator, descritores, data, etc.)
#     - Secções do texto integral marcadas com <b><u> (RELATÓRIO, FUNDAMENTAÇÃO, DECISÃO)
#     - Sub-secções numeradas (9.1, 9.2, 8.3, etc.)
#     - Sumário como chunk próprio

# Cada secção fica num chunk próprio com metadados da secção.
# Secções longas (> max_section_chars) são subdivididas com FixedChunker.

# Dependências:
#     pip install beautifulsoup4

# Uso:
#     from itij_chunker import ITIJChunker

#     chunker = ITIJChunker(chunk_size=1000, overlap=200)
#     chunks  = chunker.split_html(html_content)

#     for chunk in chunks:
#         print(chunk["section"], len(chunk["text"]))
# """

# import re
# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker


# class ITIJChunker:
#     """
#     Chunker estrutural para acórdãos HTML do ITIJ.

#     Detecta secções por:
#     - Tags <b><u> — títulos principais (I. RELATÓRIO, II. FUNDAMENTAÇÃO, III. DECISÃO)
#     - Tags <b> com padrão numérico — sub-secções (9.1., 9.2., 8.3.)
#     - Campos de metadados do cabeçalho (Processo, Relator, Sumário, etc.)
#     """

#     # Campos de metadados do cabeçalho do acórdão
#     CAMPOS_META = [
#         "Processo", "Relator", "Descritores", "Data do Acordão",
#         "Votação", "Texto Integral", "Meio Processual", "Decisão",
#         "Área Temática", "Sumário", "Decisão Texto Integral",
#         "Nº Convencional", "Tribunal Recurso",
#     ]

#     def __init__(
#         self,
#         chunk_size:        int = 1000,
#         overlap:           int = 200,
#         max_section_chars: int = 1500,
#     ):
#         self._chunk_size        = chunk_size
#         self._overlap           = overlap
#         self._max_section_chars = max_section_chars
#         self._fixed             = FixedChunker(chunk_size, overlap)

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def split_html(self, html: str) -> list[dict]:
#         """
#         Divide o HTML de um acórdão em chunks estruturados.

#         Args:
#             html: HTML completo do acórdão (string)

#         Returns:
#             Lista de dicts com:
#                 text     : texto do chunk
#                 section  : nome da secção
#                 chunk_idx: índice do chunk dentro da secção
#         """
#         soup = BeautifulSoup(html, "html.parser")
#         chunks = []

#         # 1. Extrair metadados do cabeçalho como chunk próprio
#         meta_chunk = self._extrair_metadados(soup)
#         if meta_chunk:
#             chunks.append(meta_chunk)

#         # 2. Extrair texto integral por secções
#         texto_integral = self._extrair_texto_integral(soup)
#         if texto_integral:
#             chunks.extend(texto_integral)

#         # 3. Fallback — se não encontrou secções, usa FixedChunker no texto completo
#         if not chunks:
#             texto = soup.get_text(separator="\n")
#             texto = self._limpar_texto(texto)
#             for c in self._fixed.split(texto):
#                 chunks.append({**c, "section": "unknown"})

#         return chunks

#     def split(self, source) -> list[dict]:
#         """
#         Interface compatível com os outros chunkers.
#         Aceita HTML como string ou caminho para ficheiro .txt com HTML.
#         """
#         if isinstance(source, str) and source.strip().startswith("<"):
#             # É HTML directamente
#             return self.split_html(source)
#         else:
#             # É caminho para ficheiro
#             with open(source, "r", encoding="utf-8") as f:
#                 content = f.read()
#             if content.strip().startswith("<"):
#                 return self.split_html(content)
#             else:
#                 # Texto puro — fallback para FixedChunker
#                 chunks = self._fixed.split(content)
#                 return [{**c, "section": "unknown"} for c in chunks]

#     # ------------------------------------------------------------------
#     # Extracção de metadados do cabeçalho
#     # ------------------------------------------------------------------

#     def _extrair_metadados(self, soup: BeautifulSoup) -> dict | None:
#         """
#         Extrai os campos do cabeçalho do acórdão (tabela superior).
#         Processo, Relator, Descritores, Data, Sumário, etc.
#         """
#         linhas = []
#         tabelas = soup.find_all("table")

#         for tabela in tabelas[:3]:  # cabeçalho está nas primeiras tabelas
#             for tr in tabela.find_all("tr"):
#                 tds = tr.find_all("td")
#                 if len(tds) >= 2:
#                     label = tds[0].get_text(strip=True)
#                     valor = tds[1].get_text(strip=True)
#                     if label and valor and len(label) < 50:
#                         linhas.append(f"{label}: {valor}")

#         if not linhas:
#             return None

#         texto = "\n".join(linhas)
#         if len(texto) < 20:
#             return None

#         return {
#             "text":      texto,
#             "section":   "Metadados",
#             "chunk_idx": 0,
#         }

#     # ------------------------------------------------------------------
#     # Extracção do texto integral por secções
#     # ------------------------------------------------------------------

#     def _extrair_texto_integral(self, soup: BeautifulSoup) -> list[dict]:
#         """
#         Detecta e extrai as secções do texto integral.

#         Títulos principais: <b><u>I.RELATÓRIO</u></b>
#         Sub-secções: <b>9.1. Nulidade da sentença</b>
#         """
#         chunks   = []
#         secções  = []  # lista de (título, texto)

#         # Encontrar a célula com "Decisão Texto Integral"
#         texto_td = None
#         for td in soup.find_all("td"):
#             txt = td.get_text(strip=True)
#             if len(txt) > 500:  # célula grande = texto integral
#                 texto_td = td
#                 break

#         if not texto_td:
#             return []

#         # Percorrer elementos e detectar títulos de secção
#         secção_actual = "Texto Integral"
#         parágrafos    = []

#         for elem in texto_td.descendants:
#             if not hasattr(elem, "get_text"):
#                 continue

#             tag_name = getattr(elem, "name", None)
#             if not tag_name:
#                 continue

#             texto_elem = elem.get_text(strip=True)
#             if not texto_elem or len(texto_elem) < 2:
#                 continue

#             # Detectar título principal: <b><u> ou <u><b>
#             is_titulo_principal = (
#                 tag_name in ("b", "u") and
#                 elem.find("u") is not None or
#                 (tag_name == "u" and elem.parent and elem.parent.name == "b")
#             )

#             # Detectar título de secção por padrão: I., II., III. ou 9.1., 9.2.
#             is_titulo = (
#                 tag_name in ("b", "u") and
#                 len(texto_elem) < 100 and
#                 (
#                     re.match(r"^(I{1,3}V?|VI{0,3}|IX|X{0,3})\.", texto_elem) or
#                     re.match(r"^\d+\.\d+", texto_elem) or
#                     texto_elem.upper() in (
#                         "RELATÓRIO", "FUNDAMENTAÇÃO", "DECISÃO",
#                         "I.RELATÓRIO", "II.FUNDAMENTAÇÃO", "III.DECISÃO",
#                         "I. RELATÓRIO", "II. FUNDAMENTAÇÃO", "III. DECISÃO",
#                     )
#                 )
#             )

#             if is_titulo and texto_elem != secção_actual:
#                 # Guardar secção anterior
#                 if parágrafos:
#                     secções.append((secção_actual, "\n".join(parágrafos)))
#                 secção_actual = texto_elem
#                 parágrafos    = []
#             elif tag_name == "p" and len(texto_elem) > 20:
#                 parágrafos.append(texto_elem)

#         # Guardar última secção
#         if parágrafos:
#             secções.append((secção_actual, "\n".join(parágrafos)))

#         # Converter secções em chunks
#         for titulo, texto in secções:
#             texto = self._limpar_texto(texto)
#             if not texto:
#                 continue

#             if len(texto) <= self._max_section_chars:
#                 chunks.append({
#                     "text":      texto,
#                     "section":   titulo,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 # Secção longa — subdividir com FixedChunker
#                 sub_chunks = self._fixed.split(texto)
#                 for i, sc in enumerate(sub_chunks):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   titulo,
#                         "chunk_idx": i,
#                     })

#         return chunks

#     # ------------------------------------------------------------------
#     # Utilitários
#     # ------------------------------------------------------------------

#     def _limpar_texto(self, texto: str) -> str:
#         """Remove espaços excessivos e linhas em branco."""
#         linhas = [l.strip() for l in texto.splitlines() if l.strip()]
#         return "\n".join(linhas)

# """
# itij_chunker.py

# Chunker especializado para acordaos HTML do ITIJ (dgsi.pt).

# Estrutura real confirmada dos acordaos TRE:
#     - Cabecalho: tabela com 18 linhas (Processo, Relator, Descritores, etc.)
#     - Texto integral: celula <td> com o texto completo
#     - Titulos principais: <b><u>I.RELATÓRIO</u></b>, <b><u>II. FUNDAMENTAÇÃO</u></b>, <b><u>III. DECISÃO</u></b>
#     - Sub-seccoes: <b>9.1. Nulidade da sentença</b>, <b>9.2. ...</b>

# Dependencias:
#     pip install beautifulsoup4
# """

# import re
# from bs4 import BeautifulSoup, NavigableString, Tag
# from fixed_chunker import FixedChunker


# # Padrao de titulo principal: I. / II. / III. ou ACÓRDÃO
# _RE_TITULO_ROMANO = re.compile(
#     r"^(ACÓRDÃO|I{1,3}V?|IV|VI{0,3}|IX|X{0,3})[.\s]",
#     re.IGNORECASE
# )
# # Padrao de sub-seccao: 9.1. / 8.3. / etc.
# _RE_SUB_SECCAO = re.compile(r"^\d+\.\d+")


# class ITIJChunker:
#     """
#     Chunker estrutural para acordaos HTML do ITIJ.
#     Detecta secções por tags <b><u> e <b> com padrões numerados.
#     """

#     def __init__(
#         self,
#         chunk_size:        int = 1000,
#         overlap:           int = 200,
#         max_section_chars: int = 2000,
#     ):
#         self._chunk_size        = chunk_size
#         self._overlap           = overlap
#         self._max_section_chars = max_section_chars
#         self._fixed             = FixedChunker(chunk_size, overlap)

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def split(self, source) -> list[dict]:
#         """
#         Interface compativel com os outros chunkers.
#         Aceita HTML como string ou caminho para ficheiro .html/.txt.
#         """
#         if isinstance(source, str) and source.strip().startswith("<"):
#             return self.split_html(source)
#         else:
#             with open(source, "r", encoding="utf-8") as f:
#                 content = f.read()
#             if content.strip().startswith("<"):
#                 return self.split_html(content)
#             else:
#                 chunks = self._fixed.split(content)
#                 return [{**c, "section": "unknown"} for c in chunks]

#     def split_html(self, html: str) -> list[dict]:
#         """
#         Divide o HTML de um acordao em chunks estruturados.
#         """
#         soup   = BeautifulSoup(html, "html.parser")
#         chunks = []

#         # 1. Chunk de metadados do cabecalho
#         meta = self._extrair_metadados(soup)
#         if meta:
#             chunks.append(meta)

#         # 2. Chunks do texto integral por seccoes
#         chunks.extend(self._extrair_seccoes(soup))

#         # 3. Fallback se nao encontrou nada
#         if not chunks:
#             texto = self._texto_limpo(soup.get_text(separator="\n"))
#             for c in self._fixed.split(texto):
#                 chunks.append({**c, "section": "unknown"})

#         return chunks

#     # ------------------------------------------------------------------
#     # Cabecalho
#     # ------------------------------------------------------------------

#     def _extrair_metadados(self, soup: BeautifulSoup) -> dict | None:
#         """Extrai campos do cabecalho — primeira tabela com Processo, Relator, etc."""
#         campos = []
#         tabela = soup.find("table")
#         if not tabela:
#             return None

#         for tr in tabela.find_all("tr"):
#             tds = tr.find_all("td")
#             if len(tds) >= 2:
#                 label = tds[0].get_text(strip=True)
#                 valor = tds[1].get_text(strip=True)
#                 if label and valor and len(label) < 50:
#                     campos.append(f"{label}: {valor}")

#         if not campos:
#             return None

#         return {
#             "text":      "\n".join(campos),
#             "section":   "Metadados",
#             "chunk_idx": 0,
#         }

#     # ------------------------------------------------------------------
#     # Seccoes do texto integral
#     # ------------------------------------------------------------------

#     def _extrair_seccoes(self, soup: BeautifulSoup) -> list[dict]:
#         """
#         Detecta seccoes no texto integral.

#         Titulos principais: <b><u>I.RELATÓRIO</u></b>
#         Sub-seccoes:        <b>9.1. Nulidade da sentença</b>
#         """
#         # Encontrar a celula com o texto integral (a maior celula <td>)
#         td_texto = None
#         for td in soup.find_all("td"):
#             if len(td.get_text()) > 1000:
#                 td_texto = td
#                 break

#         if not td_texto:
#             return []

#         # Percorrer todos os elementos e segmentar por titulos
#         seccoes        = []   # lista de (titulo, lista_de_paragrafos)
#         titulo_actual  = None
#         paragrafos     = []

#         for elem in td_texto.descendants:
#             if not isinstance(elem, Tag):
#                 continue

#             nome = elem.name
#             if nome not in ("b", "p", "font"):
#                 continue

#             texto = elem.get_text(strip=True)
#             if not texto:
#                 continue

#             # Detectar titulo principal: <b> que contém <u>
#             if nome == "b" and elem.find("u"):
#                 titulo_u = elem.find("u").get_text(strip=True)
#                 if (
#                     _RE_TITULO_ROMANO.match(titulo_u) or
#                     titulo_u.upper() in ("ACÓRDÃO", "ACORDÃO")
#                 ):
#                     if titulo_actual is not None and paragrafos:
#                         seccoes.append((titulo_actual, list(paragrafos)))
#                     titulo_actual = titulo_u
#                     paragrafos    = []
#                     continue

#             # Detectar sub-seccao: <b> com padrao numerico
#             if nome == "b" and _RE_SUB_SECCAO.match(texto) and len(texto) < 100:
#                 if titulo_actual is not None and paragrafos:
#                     seccoes.append((titulo_actual, list(paragrafos)))
#                 titulo_actual = texto
#                 paragrafos    = []
#                 continue

#             # Paragrafo normal — adicionar ao texto da seccao actual
#             if nome == "p" and len(texto) > 20 and titulo_actual is not None:
#                 paragrafos.append(texto)

#         # Guardar ultima seccao
#         if titulo_actual is not None and paragrafos:
#             seccoes.append((titulo_actual, list(paragrafos)))

#         # Converter seccoes em chunks
#         chunks = []
#         for titulo, paras in seccoes:
#             texto = "\n".join(paras)
#             texto = self._texto_limpo(texto)
#             if not texto:
#                 continue

#             if len(texto) <= self._max_section_chars:
#                 chunks.append({
#                     "text":      texto,
#                     "section":   titulo,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 # Seccao longa — subdividir com FixedChunker
#                 for i, sc in enumerate(self._fixed.split(texto)):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   f"{titulo} (parte {i+1})",
#                         "chunk_idx": i,
#                     })

#         return chunks

#     # ------------------------------------------------------------------
#     # Utilitarios
#     # ------------------------------------------------------------------

#     def _texto_limpo(self, texto: str) -> str:
#         linhas = [l.strip() for l in texto.splitlines() if l.strip()]
#         return "\n".join(linhas)

# """
# itij_chunker.py

# Chunker especializado para acordaos HTML do ITIJ (dgsi.pt).

# Abordagem: extrair o texto de cada campo da tabela de cabecalho
# individualmente, depois segmentar o campo "Decisao Texto Integral"
# por titulos de seccao usando regex no texto puro.
# """

# import re
# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker

# # Titulos de seccao no texto do acordao
# _RE_TITULO = re.compile(
#     r"^(ACÓRDÃO|ACORDÃO|I\.RELATÓRIO|I\. RELATÓRIO|II\. FUNDAMENTAÇÃO|"
#     r"II\.FUNDAMENTAÇÃO|III\. DECISÃO|III\.DECISÃO|"
#     r"\d+\.\d+\.\s+\w)",
#     re.IGNORECASE | re.MULTILINE
# )


# class ITIJChunker:

#     def __init__(self, chunk_size=1000, overlap=200, max_section_chars=2000):
#         self._chunk_size        = chunk_size
#         self._overlap           = overlap
#         self._max_section_chars = max_section_chars
#         self._fixed             = FixedChunker(chunk_size, overlap)

#     def split(self, source) -> list[dict]:
#         if isinstance(source, str) and source.strip().startswith("<"):
#             return self.split_html(source)
#         with open(source, "r", encoding="utf-8") as f:
#             content = f.read()
#         if content.strip().startswith("<"):
#             return self.split_html(content)
#         chunks = self._fixed.split(content)
#         return [{**c, "section": "unknown"} for c in chunks]

#     def split_html(self, html: str) -> list[dict]:
#         soup   = BeautifulSoup(html, "html.parser")
#         chunks = []

#         # Extrair todos os campos da tabela de cabecalho
#         campos = self._extrair_campos(soup)

#         for label, valor in campos.items():
#             valor = valor.strip()
#             if not valor:
#                 continue

#             if label == "Decisão Texto Integral":
#                 # Segmentar por seccoes
#                 chunks.extend(self._segmentar_texto(valor))
#             elif len(valor) > 500:
#                 # Campo longo (Sumário) — subdividir
#                 for i, sc in enumerate(self._fixed.split(f"{label}:\n{valor}")):
#                     chunks.append({"text": sc["text"], "section": label, "chunk_idx": i})
#             else:
#                 # Campo curto — acumular em metadados
#                 pass  # tratado abaixo

#         # Chunk de metadados com campos curtos
#         meta_campos = [
#             f"{l}: {v}"
#             for l, v in campos.items()
#             if v.strip() and len(v.strip()) <= 500
#             and l not in ("Decisão Texto Integral",)
#         ]
#         if meta_campos:
#             chunks.insert(0, {
#                 "text":      "\n".join(meta_campos),
#                 "section":   "Metadados",
#                 "chunk_idx": 0,
#             })

#         if not chunks:
#             texto = "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())
#             for c in self._fixed.split(texto):
#                 chunks.append({**c, "section": "unknown"})

#         return chunks

#     # ------------------------------------------------------------------
#     # Extrair campos da tabela
#     # ------------------------------------------------------------------

#     def _extrair_campos(self, soup) -> dict:
#         """
#         Extrai cada campo da tabela de cabecalho como {label: texto}.
#         Preserva a ordem.
#         """
#         campos = {}
#         tabela = soup.find("table")
#         if not tabela:
#             return campos

#         for tr in tabela.find_all("tr"):
#             tds = tr.find_all("td", recursive=False)
#             if len(tds) < 2:
#                 continue
#             label = tds[0].get_text(strip=True)
#             valor = tds[1].get_text(separator="\n", strip=True)
#             if label and valor and len(label) < 60:
#                 campos[label] = valor

#         return campos

#     # ------------------------------------------------------------------
#     # Segmentar texto integral por seccoes
#     # ------------------------------------------------------------------

#     def _segmentar_texto(self, texto: str) -> list[dict]:
#         """
#         Divide o texto do campo 'Decisao Texto Integral' em seccoes
#         usando os titulos conhecidos (I.RELATÓRIO, II.FUNDAMENTAÇÃO, etc.)
#         """
#         # Normalizar linhas
#         linhas = [l.strip() for l in texto.splitlines() if l.strip()]
#         texto  = "\n".join(linhas)

#         # Titulos que marcam inicio de seccao
#         padroes = [
#             r"ACÓRDÃO",
#             r"I\.\s*RELATÓRIO",
#             r"II\.\s*FUNDAMENTAÇÃO",
#             r"III\.\s*DECISÃO",
#             r"\d+\.\d+\.\s+\w",   # 9.1. Nulidade...
#         ]
#         padrao_union = re.compile(
#             r"^(" + "|".join(padroes) + r")",
#             re.IGNORECASE | re.MULTILINE
#         )

#         # Encontrar posicoes dos titulos
#         titulos = []
#         for m in padrao_union.finditer(texto):
#             # Extrair titulo completo (ate fim da linha)
#             linha_inicio = texto.rfind("\n", 0, m.start()) + 1
#             linha_fim    = texto.find("\n", m.start())
#             if linha_fim == -1:
#                 linha_fim = len(texto)
#             titulo = texto[linha_inicio:linha_fim].strip()
#             titulos.append((m.start(), titulo))

#         if not titulos:
#             # Sem titulos detectados — usar FixedChunker
#             chunks = []
#             for i, sc in enumerate(self._fixed.split(texto)):
#                 chunks.append({
#                     "text":      sc["text"],
#                     "section":   "Decisão Texto Integral",
#                     "chunk_idx": i,
#                 })
#             return chunks

#         # Segmentar texto entre titulos
#         seccoes = []
#         for i, (pos, titulo) in enumerate(titulos):
#             inicio = pos
#             fim    = titulos[i+1][0] if i+1 < len(titulos) else len(texto)
#             conteudo = texto[inicio:fim].strip()
#             # Remover o titulo do inicio do conteudo
#             conteudo = conteudo[len(titulo):].strip()
#             if conteudo:
#                 seccoes.append((titulo, conteudo))

#         # Converter em chunks
#         chunks = []
#         for titulo, conteudo in seccoes:
#             if len(conteudo) <= self._max_section_chars:
#                 chunks.append({
#                     "text":      conteudo,
#                     "section":   titulo,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 for i, sc in enumerate(self._fixed.split(conteudo)):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   f"{titulo} (parte {i+1})",
#                         "chunk_idx": i,
#                     })

#         return chunks

# """
# itij_chunker.py

# Chunker para acordaos HTML do ITIJ (dgsi.pt).

# Estrategia: extrair cada campo da tabela de cabecalho individualmente,
# depois chunking fixo do texto integral. Simples e robusto para todos
# os tribunais e formatos de acordao.

# Cada acordao gera:
#     - 1 chunk de metadados (Processo, Relator, Descritores, Data, Decisao)
#     - 1 chunk de Sumario (se existir)
#     - N chunks do Texto Integral (FixedChunker)
# """

# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker


# # Campos que vao para o chunk de metadados (curtos)
# _CAMPOS_META = {
#     "Processo:", "Relator:", "Descritores:", "Data do Acordão:",
#     "Votação:", "Meio Processual:", "Decisão:", "Área Temática:",
#     "Texto Integral:", "Nº Convencional:", "Tribunal Recurso:",
#     "Processo:", "Relator:", "Descritores:",
# }

# # Campos longos — chunk proprio
# _CAMPOS_LONGOS = {"Sumário:", "Decisão Texto Integral:"}


# class ITIJChunker:

#     def __init__(self, chunk_size=1000, overlap=200, max_section_chars=2000):
#         self._chunk_size        = chunk_size
#         self._overlap           = overlap
#         self._max_section_chars = max_section_chars
#         self._fixed             = FixedChunker(chunk_size, overlap)

#     def split(self, source) -> list[dict]:
#         if isinstance(source, str) and source.strip().startswith("<"):
#             return self.split_html(source)
#         with open(source, "r", encoding="utf-8") as f:
#             content = f.read()
#         if content.strip().startswith("<"):
#             return self.split_html(content)
#         chunks = self._fixed.split(content)
#         return [{**c, "section": "unknown"} for c in chunks]

#     def split_html(self, html: str) -> list[dict]:
#         soup   = BeautifulSoup(html, "html.parser")
#         campos = self._extrair_campos(soup)
#         chunks = []

#         # 1. Chunk de metadados — campos curtos agrupados
#         meta = []
#         for label, valor in campos.items():
#             if label in _CAMPOS_LONGOS:
#                 continue
#             valor = valor.strip()
#             if valor and len(valor) <= 500:
#                 meta.append(f"{label} {valor}")

#         if meta:
#             chunks.append({
#                 "text":      "\n".join(meta),
#                 "section":   "Metadados",
#                 "chunk_idx": 0,
#             })

#         # 2. Sumario — chunk proprio se existir
#         sumario = campos.get("Sumário:", "").strip()
#         if sumario:
#             for i, sc in enumerate(self._fixed.split(sumario)):
#                 chunks.append({
#                     "text":      sc["text"],
#                     "section":   "Sumário",
#                     "chunk_idx": i,
#                 })

#         # 3. Texto integral — FixedChunker
#         texto_integral = campos.get("Decisão Texto Integral:", "").strip()
#         if texto_integral:
#             for i, sc in enumerate(self._fixed.split(texto_integral)):
#                 chunks.append({
#                     "text":      sc["text"],
#                     "section":   "Texto Integral",
#                     "chunk_idx": i,
#                 })

#         # Fallback
#         if not chunks:
#             texto = "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())
#             for c in self._fixed.split(texto):
#                 chunks.append({**c, "section": "unknown"})

#         return chunks

#     def _extrair_campos(self, soup) -> dict:
#         campos = {}
#         tabela = soup.find("table")
#         if not tabela:
#             return campos
#         for tr in tabela.find_all("tr"):
#             tds = tr.find_all("td", recursive=False)
#             if len(tds) < 2:
#                 continue
#             label = tds[0].get_text(strip=True)
#             valor = tds[1].get_text(separator="\n", strip=True)
#             if label and valor and len(label) < 60:
#                 campos[label] = valor
#         return campos

# """
# itij_chunker.py

# Chunker para acordaos do ITIJ com segmentacao via LLM.

# Pipeline:
#     1. Extrair texto limpo do HTML (BeautifulSoup)
#     2. Enviar ao LLM com prompt de segmentacao estrutural
#     3. LLM devolve JSON com seccoes: metadados, sumario, relatorio,
#        factos, fundamentacao_direito, decisao
#     4. Cada seccao nao-nula gera 1+ chunks (FixedChunker se longa)
#     5. Fallback para FixedChunker se LLM falhar ou devolver JSON invalido

# Dependencias:
#     pip install beautifulsoup4 requests
#     ollama deve estar a correr com o modelo configurado
# """

# import json
# import re
# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker


# SECCOES_ORDEM = [
#     "metadados",
#     "sumario",
#     "relatorio",
#     "factos",
#     "fundamentacao_direito",
#     "decisao",
# ]

# PROMPT_SEGMENTACAO = '''Tarefa: Segmentar um acórdão jurídico português em secções estruturais.

# Objetivo:
# Identificar as principais secções do documento com base no conteúdo semântico, não apenas na formatação.

# Secções possíveis (usar apenas estas):
# - metadados
# - sumario
# - relatorio
# - factos
# - fundamentacao_direito
# - decisao

# Regras obrigatórias:
# 1. Cada parte do texto deve aparecer em no máximo uma secção (não duplicar conteúdo).
# 2. Mantém o texto original. Não resumir, não reescrever.
# 3. Respeita a ordem do documento.
# 4. Se uma secção não existir claramente, usa null.
# 5. Não inventes secções nem conteúdo.
# 6. Usa estes critérios:
#    - metadados: bloco inicial com tribunal, processo, relator, datas, descritores.
#    - sumario: normalmente no início, frequentemente numerado (I, II, III).
#    - relatorio: descrição do caso, partes e tramitação.
#    - factos: apenas se existir lista clara de factos provados/não provados.
#    - fundamentacao_direito: análise jurídica (normalmente a maior secção).
#    - decisao: parte final com decisão (ex: "decidem", "julga-se", "custas").
# 7. Se não conseguires separar claramente "factos" da fundamentação, inclui-os dentro de "fundamentacao_direito".
# 8. Não cries secções artificiais.

# Formato de saída (JSON válido, sem texto adicional):
# {
#   "metadados": "...",
#   "sumario": "...",
#   "relatorio": "...",
#   "factos": null,
#   "fundamentacao_direito": "...",
#   "decisao": "..."
# }

# Texto:
# """
# {texto}
# """'''


# class ITIJChunker:
#     """
#     Chunker para acordaos HTML do ITIJ.

#     Usa o LLM para segmentacao estrutural semantica.
#     Fallback automatico para FixedChunker se o LLM falhar.
#     """

#     def __init__(
#         self,
#         chunk_size:    int = 1000,
#         overlap:       int = 200,
#         llm_base_url:  str = "http://localhost:11434",
#         llm_model:     str = "qwen2.5:7b-instruct-q4_K_M",
#         max_chars_llm: int = 12000,   # limite de texto enviado ao LLM
#         timeout:       int = 120,     # segundos para o LLM responder
#     ):
#         self._chunk_size    = chunk_size
#         self._overlap       = overlap
#         self._llm_base_url  = llm_base_url.rstrip("/")
#         self._llm_model     = llm_model
#         self._max_chars_llm = max_chars_llm
#         self._timeout       = timeout
#         self._fixed         = FixedChunker(chunk_size, overlap)

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def split(self, source) -> list[dict]:
#         """
#         Aceita:
#             - string HTML (começa com '<')
#             - caminho para ficheiro .html ou .txt
#         """
#         if isinstance(source, str) and source.strip().startswith("<"):
#             html = source
#         else:
#             with open(source, "r", encoding="utf-8") as f:
#                 html = f.read()

#         if html.strip().startswith("<"):
#             return self.split_html(html)
#         else:
#             # Texto puro — fallback directo
#             return self._fallback(html, motivo="texto puro sem HTML")

#     def split_html(self, html: str) -> list[dict]:
#         """Pipeline principal: HTML → texto limpo → LLM → chunks."""

#         # 1. Extrair texto limpo
#         texto_limpo = extrair_texto_limpo(html)
#         if not texto_limpo.strip():
#             return []

#         # 2. Tentar segmentacao via LLM
#         try:
#             seccoes = self._segmentar_com_llm(texto_limpo)
#             if seccoes:
#                 chunks = self._seccoes_para_chunks(seccoes)
#                 if chunks:
#                     print(f"  [ITIJChunker] LLM segmentou em {len(chunks)} chunks "
#                           f"({sum(1 for c in chunks if c['section'] != 'unknown')} com seccao)")
#                     return chunks
#         except Exception as e:
#             print(f"  [ITIJChunker] LLM falhou ({e}), usando fallback")

#         # 3. Fallback para FixedChunker
#         return self._fallback(texto_limpo, motivo="LLM nao segmentou")

#     # ------------------------------------------------------------------
#     # Limpeza do HTML
#     # ------------------------------------------------------------------

#     def _segmentar_com_llm(self, texto: str) -> dict | None:
#         """
#         Envia o texto ao LLM e devolve o JSON de seccoes.
#         Trunca o texto se exceder max_chars_llm.
#         """
#         import requests

#         # Truncar texto se muito longo (LLM tem limite de contexto)
#         if len(texto) > self._max_chars_llm:
#             texto_envio = texto[:self._max_chars_llm]
#             print(f"  [ITIJChunker] Texto truncado de {len(texto)} para {self._max_chars_llm} chars")
#         else:
#             texto_envio = texto

#         prompt = PROMPT_SEGMENTACAO.replace("{texto}", texto_envio)

#         resp = requests.post(
#             f"{self._llm_base_url}/api/chat",
#             json={
#                 "model":    self._llm_model,
#                 "messages": [{"role": "user", "content": prompt}],
#                 "stream":   False,
#                 "options":  {"temperature": 0},  # determinista
#             },
#             timeout=self._timeout,
#             headers={"ngrok-skip-browser-warning": "true"},
#         )
#         resp.raise_for_status()

#         conteudo = resp.json()["message"]["content"].strip()

#         # Extrair JSON da resposta (pode ter texto antes/depois)
#         json_match = re.search(r"\{.*\}", conteudo, re.DOTALL)
#         if not json_match:
#             raise ValueError(f"LLM nao devolveu JSON valido: {conteudo[:200]}")

#         seccoes = json.loads(json_match.group())

#         # Validar que tem pelo menos as chaves esperadas
#         if not any(seccoes.get(s) for s in SECCOES_ORDEM):
#             raise ValueError("JSON vazio — todas as seccoes sao null")

#         return seccoes

#     def _seccoes_para_chunks(self, seccoes: dict) -> list[dict]:
#         """Converte o JSON de seccoes em lista de chunks."""
#         chunks = []
#         for nome in SECCOES_ORDEM:
#             texto = seccoes.get(nome)
#             if not texto or not texto.strip():
#                 continue
#             texto = texto.strip()

#             if len(texto) <= self._chunk_size * 2:
#                 # Seccao curta — chunk unico
#                 chunks.append({
#                     "text":      texto,
#                     "section":   nome,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 # Seccao longa — subdividir com FixedChunker
#                 for i, sc in enumerate(self._fixed.split(texto)):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   f"{nome}_parte_{i+1}",
#                         "chunk_idx": i,
#                     })

#         return chunks

#     def _fallback(self, texto: str, motivo: str = "") -> list[dict]:
#         """FixedChunker como fallback."""
#         if motivo:
#             print(f"  [ITIJChunker] Fallback ({motivo})")
#         chunks = self._fixed.split(texto)
#         return [{**c, "section": "texto_integral"} for c in chunks]


# # ------------------------------------------------------------------
# # Funcao publica para extrair texto limpo do HTML
# # (usada tambem pelo views.py para guardar acordaos_limpos/)
# # ------------------------------------------------------------------

# def extrair_texto_limpo(html: str) -> str:
#     """
#     Limpa o HTML de um acordao do ITIJ removendo o que e desnecessario
#     mas mantendo a estrutura semantica importante.

#     Remove:
#         - <script>, <style>, <img>
#         - Links de navegacao (<a href=...>) mas mantem o texto do link
#         - Atributos de apresentacao: bgcolor, color, face, size, width,
#           height, cellspacing, cellpadding, valign, align, border
#         - Tags <font> (substituidas pelo seu conteudo)
#         - <br> excessivos (mais de 2 seguidos)
#         - Linhas/paragrafos completamente vazios

#     Mantem:
#         - Estrutura da tabela de cabecalho (<table>, <tr>, <td>)
#         - Formatacao semantica: <b>, <u>, <i>, <p>
#         - Texto integral completo
#     """
#     soup = BeautifulSoup(html, "html.parser")

#     # 1. Remover tags inuteis completamente
#     for tag in soup.find_all(["script", "style", "img"]):
#         tag.decompose()

#     # 2. Substituir <a> pelo seu texto (remover links mas manter texto)
#     for a in soup.find_all("a"):
#         a.replace_with(a.get_text())

#     # 3. Substituir <font> pelo seu conteudo (tag decorativa)
#     for font in soup.find_all("font"):
#         font.unwrap()

#     # 4. Remover atributos de apresentacao de todas as tags
#     ATTRS_REMOVER = {
#         "bgcolor", "color", "face", "size",
#         "width", "height", "cellspacing", "cellpadding",
#         "valign", "align", "border", "style",
#         "class", "id",
#     }
#     for tag in soup.find_all(True):
#         for attr in list(tag.attrs.keys()):
#             if attr in ATTRS_REMOVER:
#                 del tag[attr]

#     # 5. Remover <br> excessivos (mais de 2 seguidos)
#     br_count = 0
#     for tag in soup.find_all(True):
#         children = list(tag.children)
#         for child in children:
#             if getattr(child, "name", None) == "br":
#                 br_count += 1
#                 if br_count > 1:
#                     child.decompose()
#             else:
#                 br_count = 0

#     # 6. Serializar de volta para HTML limpo
#     html_limpo = str(soup)

#     # 7. Limpar linhas vazias excessivas no HTML resultante
#     html_limpo = re.sub(r"(<br[^>]*>\s*){2,}", "<br>", html_limpo)
#     html_limpo = re.sub(r"\n{3,}", "\n\n", html_limpo)

#     return html_limpo

# """
# itij_chunker.py

# Chunker para acordaos do ITIJ com segmentacao via LLM.

# Pipeline:
#     1. Extrair texto limpo do HTML (BeautifulSoup)
#     2. Enviar ao LLM com prompt de segmentacao estrutural
#     3. LLM devolve JSON com seccoes: metadados, sumario, relatorio,
#        factos, fundamentacao_direito, decisao
#     4. Cada seccao nao-nula gera 1+ chunks (FixedChunker se longa)
#     5. Fallback para FixedChunker se LLM falhar ou devolver JSON invalido

# Dependencias:
#     pip install beautifulsoup4 requests
#     ollama deve estar a correr com o modelo configurado
# """

# import json
# import re
# from bs4 import BeautifulSoup
# from fixed_chunker import FixedChunker


# SECCOES_ORDEM = [
#     "metadados",
#     "sumario",
#     "relatorio",
#     "factos",
#     "fundamentacao_direito",
#     "decisao",
# ]

# PROMPT_SEGMENTACAO = '''És um assistente especializado em direito português. A tua única tarefa é segmentar o texto de um acórdão nas secções indicadas e devolver JSON válido.

# INSTRUÇÕES OBRIGATÓRIAS:
# - Responde APENAS com o bloco JSON. Sem explicações, sem texto antes ou depois do JSON.
# - Usa EXACTAMENTE estas 6 chaves: metadados, sumario, relatorio, factos, fundamentacao_direito, decisao
# - Não uses outras chaves. Não inventes secções.
# - Se uma secção não existir no texto, o valor é null (sem aspas).
# - Copia o texto original. Não resumir, não traduzir, não reescrever.
# - Responde sempre em português.

# CRITÉRIOS PARA CADA SECÇÃO:
# - metadados: tribunal, processo, relator, data, descritores, votação, meio processual, decisão, área temática
# - sumario: síntese numerada (I, II, III...) normalmente antes do texto integral
# - relatorio: descrição do caso, partes envolvidas, pedidos, tramitação processual
# - factos: lista explícita de "factos provados" ou "factos não provados" — null se não existir lista explícita
# - fundamentacao_direito: análise jurídica, enquadramento legal, apreciação do tribunal, toda a fundamentação
# - decisao: parte final com "acordam", "julga-se", "decide-se", custas, data, assinaturas

# RESPONDE APENAS COM ESTE JSON (sem mais nada):
# {
#   "metadados": "texto aqui",
#   "sumario": "texto aqui",
#   "relatorio": "texto aqui",
#   "factos": "texto aqui",
#   "fundamentacao_direito": "texto aqui",
#   "decisao": "texto aqui"
# }

# TEXTO DO ACÓRDÃO:
# """
# {texto}
# """'''


# class ITIJChunker:
#     """
#     Chunker para acordaos HTML do ITIJ.

#     Usa o LLM para segmentacao estrutural semantica.
#     Fallback automatico para FixedChunker se o LLM falhar.
#     """

#     def __init__(
#         self,
#         chunk_size:    int = 1000,
#         overlap:       int = 200,
#         llm_base_url:  str = "http://localhost:11434",
#         llm_model:     str = "qwen2.5:7b-instruct-q4_K_M",
#         max_chars_llm: int = 100000,  # qwen2.5 suporta 128k tokens (~400k chars)
#         timeout:       int = 120,     # segundos para o LLM responder
#     ):
#         self._chunk_size    = chunk_size
#         self._overlap       = overlap
#         self._llm_base_url  = llm_base_url.rstrip("/")
#         self._llm_model     = llm_model
#         self._max_chars_llm = max_chars_llm
#         self._timeout       = timeout
#         self._fixed         = FixedChunker(chunk_size, overlap)

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def split(self, source) -> list[dict]:
#         """
#         Aceita:
#             - string HTML (começa com '<')
#             - caminho para ficheiro .html ou .txt
#         """
#         if isinstance(source, str) and source.strip().startswith("<"):
#             html = source
#         else:
#             with open(source, "r", encoding="utf-8") as f:
#                 html = f.read()

#         if html.strip().startswith("<"):
#             return self.split_html(html)
#         else:
#             # Texto puro — fallback directo
#             return self._fallback(html, motivo="texto puro sem HTML")

#     def split_html(self, html: str) -> list[dict]:
#         """Pipeline principal: HTML → HTML limpo (guardado) + texto puro → LLM → chunks."""

#         # 1. HTML limpo para guardar em disco (estrutura preservada)
#         # texto puro para enviar ao LLM (mais facil de processar)
#         html_limpo  = extrair_texto_limpo(html)
#         texto_puro  = BeautifulSoup(html_limpo, "html.parser").get_text(separator="\n")
#         texto_puro  = re.sub(r"\n{3,}", "\n\n", texto_puro).strip()

#         if not texto_puro:
#             return []

#         # 2. Tentar segmentacao via LLM (recebe texto puro)
#         try:
#             seccoes = self._segmentar_com_llm(texto_puro)
#             if seccoes:
#                 chunks = self._seccoes_para_chunks(seccoes)
#                 if chunks:
#                     print(f"  [ITIJChunker] LLM segmentou em {len(chunks)} chunks "
#                           f"({sum(1 for c in chunks if c['section'] != 'unknown')} com seccao)")
#                     return chunks
#         except Exception as e:
#             print(f"  [ITIJChunker] LLM falhou ({e}), usando fallback")

#         # 3. Fallback para FixedChunker (usa texto puro)
#         return self._fallback(texto_puro, motivo="LLM nao segmentou")

#     # ------------------------------------------------------------------
#     # Limpeza do HTML
#     # ------------------------------------------------------------------

#     def _segmentar_com_llm(self, texto: str) -> dict | None:
#         """
#         Envia o texto ao LLM e devolve o JSON de seccoes.

#         Para documentos longos divide em duas passagens:
#             1a: primeira metade -> metadados, sumario, relatorio, factos
#             2a: segunda metade  -> fundamentacao_direito, decisao
#         Depois funde os dois JSONs.
#         """
#         import requests as _req

#         if len(texto) <= self._max_chars_llm:
#             print(f"  [ITIJChunker] Enviando {len(texto)} chars ao LLM")
#             return self._chamar_llm(_req, texto)
#         else:
#             print(f"  [ITIJChunker] Documento longo ({len(texto)} chars) — duas passagens")
#             meio = len(texto) // 2
#             parte1 = texto[:self._max_chars_llm]
#             parte2_inicio = max(0, meio - 500)
#             parte2 = texto[parte2_inicio:]
#             if len(parte2) > self._max_chars_llm:
#                 parte2 = parte2[:self._max_chars_llm]

#             seccoes1 = self._chamar_llm(_req, parte1) or {}
#             seccoes2 = self._chamar_llm(_req, parte2) or {}

#             return {
#                 "metadados":             seccoes1.get("metadados")             or seccoes2.get("metadados"),
#                 "sumario":               seccoes1.get("sumario")               or seccoes2.get("sumario"),
#                 "relatorio":             seccoes1.get("relatorio")             or seccoes2.get("relatorio"),
#                 "factos":                seccoes1.get("factos")                or seccoes2.get("factos"),
#                 "fundamentacao_direito": seccoes2.get("fundamentacao_direito") or seccoes1.get("fundamentacao_direito"),
#                 "decisao":               seccoes2.get("decisao")               or seccoes1.get("decisao"),
#             }

#     def _chamar_llm(self, _req, texto_envio: str) -> dict | None:
#         """Faz uma chamada ao LLM com o prompt de segmentacao."""
#         prompt = PROMPT_SEGMENTACAO.replace("{texto}", texto_envio)

#         resp = _req.post(
#             f"{self._llm_base_url}/api/chat",
#             json={
#                 "model": self._llm_model,
#                 "messages": [
#                     {
#                         "role": "system",
#                         "content": (
#                             "You are a JSON extractor. "
#                             "You ALWAYS respond with ONLY a valid JSON object. "
#                             "No text before or after the JSON. No explanations. No summaries. "
#                             "Only the JSON object with exactly these keys: "
#                             "metadados, sumario, relatorio, factos, fundamentacao_direito, decisao."
#                         ),
#                     },
#                     {"role": "user", "content": prompt},
#                 ],
#                 "stream":  False,
#                 "format":  {
#                     "type": "object",
#                     "properties": {
#                         "metadados":             {"type": ["string", "null"]},
#                         "sumario":               {"type": ["string", "null"]},
#                         "relatorio":             {"type": ["string", "null"]},
#                         "factos":                {"type": ["string", "null"]},
#                         "fundamentacao_direito": {"type": ["string", "null"]},
#                         "decisao":               {"type": ["string", "null"]},
#                     },
#                     "required": ["metadados", "sumario", "relatorio", "factos",
#                                  "fundamentacao_direito", "decisao"],
#                     "additionalProperties": False,
#                 },
#                 "options": {"temperature": 0, "num_predict": 8000},
#             },
#             timeout=self._timeout,
#             headers={"ngrok-skip-browser-warning": "true"},
#         )
#         resp.raise_for_status()

#         conteudo = resp.json()["message"]["content"].strip()
#         print(f"  [ITIJChunker] Resposta LLM ({len(conteudo)} chars): {conteudo}")

#         json_match = re.search(r"\{.*\}", conteudo, re.DOTALL)
#         if not json_match:
#             print(f"  [ITIJChunker] Sem JSON na resposta")
#             return None

#         seccoes = json.loads(json_match.group())
#         encontradas = [k for k, v in seccoes.items() if v]
#         print(f"  [ITIJChunker] Seccoes encontradas: {encontradas}")

#         # Validar que tem exactamente as chaves esperadas
#         chaves_validas = [k for k in SECCOES_ORDEM if seccoes.get(k)]
#         if not chaves_validas:
#             print(f"  [ITIJChunker] AVISO: LLM usou chaves erradas: {list(seccoes.keys())}")
#             return None

#         return seccoes

#     def _seccoes_para_chunks(self, seccoes: dict) -> list[dict]:
#         """Converte o JSON de seccoes em lista de chunks."""
#         chunks = []
#         for nome in SECCOES_ORDEM:
#             texto = seccoes.get(nome)
#             if not texto or not texto.strip():
#                 continue
#             texto = texto.strip()

#             if len(texto) <= self._chunk_size * 2:
#                 # Seccao curta — chunk unico
#                 chunks.append({
#                     "text":      texto,
#                     "section":   nome,
#                     "chunk_idx": 0,
#                 })
#             else:
#                 # Seccao longa — subdividir com FixedChunker
#                 for i, sc in enumerate(self._fixed.split(texto)):
#                     chunks.append({
#                         "text":      sc["text"],
#                         "section":   f"{nome}_parte_{i+1}",
#                         "chunk_idx": i,
#                     })

#         return chunks

#     def _fallback(self, texto: str, motivo: str = "") -> list[dict]:
#         """FixedChunker como fallback."""
#         if motivo:
#             print(f"  [ITIJChunker] Fallback ({motivo})")
#         chunks = self._fixed.split(texto)
#         return [{**c, "section": "texto_integral"} for c in chunks]


# # ------------------------------------------------------------------
# # Funcao publica para extrair texto limpo do HTML
# # (usada tambem pelo views.py para guardar acordaos_limpos/)
# # ------------------------------------------------------------------

# def extrair_texto_limpo(html: str) -> str:
#     """
#     Limpa o HTML de um acordao do ITIJ removendo o que e desnecessario
#     mas mantendo a estrutura semantica importante.

#     Remove:
#         - <script>, <style>, <img>
#         - Links de navegacao (<a href=...>) mas mantem o texto do link
#         - Atributos de apresentacao: bgcolor, color, face, size, width,
#           height, cellspacing, cellpadding, valign, align, border
#         - Tags <font> (substituidas pelo seu conteudo)
#         - <br> excessivos (mais de 2 seguidos)
#         - Linhas/paragrafos completamente vazios

#     Mantem:
#         - Estrutura da tabela de cabecalho (<table>, <tr>, <td>)
#         - Formatacao semantica: <b>, <u>, <i>, <p>
#         - Texto integral completo
#     """
#     soup = BeautifulSoup(html, "html.parser")

#     # 1. Remover tags inuteis completamente
#     for tag in soup.find_all(["script", "style", "img"]):
#         tag.decompose()

#     # 2. Substituir <a> pelo seu texto (remover links mas manter texto)
#     for a in soup.find_all("a"):
#         a.replace_with(a.get_text())

#     # 3. Substituir <font> pelo seu conteudo (tag decorativa)
#     for font in soup.find_all("font"):
#         font.unwrap()

#     # 4. Remover atributos de apresentacao de todas as tags
#     ATTRS_REMOVER = {
#         "bgcolor", "color", "face", "size",
#         "width", "height", "cellspacing", "cellpadding",
#         "valign", "align", "border", "style",
#         "class", "id",
#     }
#     for tag in soup.find_all(True):
#         for attr in list(tag.attrs.keys()):
#             if attr in ATTRS_REMOVER:
#                 del tag[attr]

#     # 5. Remover <br> excessivos (mais de 2 seguidos)
#     br_count = 0
#     for tag in soup.find_all(True):
#         children = list(tag.children)
#         for child in children:
#             if getattr(child, "name", None) == "br":
#                 br_count += 1
#                 if br_count > 1:
#                     child.decompose()
#             else:
#                 br_count = 0

#     # 6. Serializar de volta para HTML limpo
#     html_limpo = str(soup)

#     # 7. Limpar linhas vazias excessivas no HTML resultante
#     html_limpo = re.sub(r"(<br[^>]*>\s*){2,}", "<br>", html_limpo)
#     html_limpo = re.sub(r"\n{3,}", "\n\n", html_limpo)

#     return html_limpo

"""
itij_chunker.py

Chunker para acordaos do ITIJ com segmentacao via LLM.

Pipeline:
    1. Extrair texto limpo do HTML (BeautifulSoup)
    2. Enviar ao LLM com prompt de segmentacao estrutural
    3. LLM devolve JSON com seccoes: metadados, sumario, relatorio,
       factos, fundamentacao_direito, decisao
    4. Cada seccao nao-nula gera 1+ chunks (FixedChunker se longa)
    5. Fallback para FixedChunker se LLM falhar ou devolver JSON invalido

Dependencias:
    pip install beautifulsoup4 requests
    ollama deve estar a correr com o modelo configurado
"""

import json
import re
from bs4 import BeautifulSoup
from fixed_chunker import FixedChunker


SECCOES_ORDEM = [
    "metadados",
    "sumario",
    "relatorio",
    "factos",
    "fundamentacao_direito",
    "decisao",
]

PROMPT_SEGMENTACAO = '''És um assistente especializado em direito português. A tua única tarefa é segmentar o texto de um acórdão nas secções indicadas e devolver JSON válido.

INSTRUÇÕES OBRIGATÓRIAS:
- Responde APENAS com o bloco JSON. Sem explicações, sem texto antes ou depois do JSON.
- Usa EXACTAMENTE estas 6 chaves: metadados, sumario, relatorio, factos, fundamentacao_direito, decisao
- Não uses outras chaves. Não inventes secções.
- Se uma secção não existir no texto, o valor é null (sem aspas).
- Copia o texto original. Não resumir, não traduzir, não reescrever.
- Responde sempre em português.

CRITÉRIOS PARA CADA SECÇÃO:
- metadados: tribunal, processo, relator, data, descritores, votação, meio processual, decisão, área temática
- sumario: síntese numerada (I, II, III...) normalmente antes do texto integral
- relatorio: descrição do caso, partes envolvidas, pedidos, tramitação processual
- factos: lista explícita de "factos provados" ou "factos não provados" — null se não existir lista explícita
- fundamentacao_direito: análise jurídica, enquadramento legal, apreciação do tribunal, toda a fundamentação
- decisao: parte final com "acordam", "julga-se", "decide-se", custas, data, assinaturas

RESPONDE APENAS COM ESTE JSON (sem mais nada):
{
  "metadados": "texto aqui",
  "sumario": "texto aqui",
  "relatorio": "texto aqui",
  "factos": null,
  "fundamentacao_direito": "texto aqui",
  "decisao": "texto aqui"
}

TEXTO DO ACÓRDÃO:
"""
{texto}
"""'''


class ITIJChunker:
    """
    Chunker para acordaos HTML do ITIJ.

    Usa o LLM para segmentacao estrutural semantica.
    Fallback automatico para FixedChunker se o LLM falhar.
    """

    def __init__(
        self,
        chunk_size:    int = 1000,
        overlap:       int = 200,
        llm_base_url:  str = "http://localhost:11434",
        llm_model:     str = "qwen2.5:7b-instruct-q4_K_M",
        max_chars_llm: int = 100000,  # qwen2.5 suporta 128k tokens (~400k chars)
        timeout:       int = 120,     # segundos para o LLM responder
    ):
        self._chunk_size    = chunk_size
        self._overlap       = overlap
        self._llm_base_url  = llm_base_url.rstrip("/")
        self._llm_model     = llm_model
        self._max_chars_llm = max_chars_llm
        self._timeout       = timeout
        self._fixed         = FixedChunker(chunk_size, overlap)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def split(self, source) -> list[dict]:
        """
        Aceita:
            - string HTML (começa com '<')
            - caminho para ficheiro .html ou .txt
        """
        if isinstance(source, str) and source.strip().startswith("<"):
            html = source
        else:
            with open(source, "r", encoding="utf-8") as f:
                html = f.read()

        if html.strip().startswith("<"):
            return self.split_html(html)
        else:
            # Texto puro — fallback directo
            return self._fallback(html, motivo="texto puro sem HTML")

    def split_html(self, html: str) -> list[dict]:
        """Pipeline principal: HTML → HTML limpo (guardado) + texto puro → LLM → chunks."""

        # 1. HTML limpo para guardar em disco (estrutura preservada)
        # texto puro para enviar ao LLM (mais facil de processar)
        html_limpo  = extrair_texto_limpo(html)
        texto_puro  = BeautifulSoup(html_limpo, "html.parser").get_text(separator="\n")
        texto_puro  = re.sub(r"\n{3,}", "\n\n", texto_puro).strip()

        if not texto_puro:
            return []

        # 2. Tentar segmentacao via LLM (recebe texto puro)
        try:
            seccoes = self._segmentar_com_llm(texto_puro)
            if seccoes:
                chunks = self._seccoes_para_chunks(seccoes)
                if chunks:
                    print(f"  [ITIJChunker] LLM segmentou em {len(chunks)} chunks "
                          f"({sum(1 for c in chunks if c['section'] != 'unknown')} com seccao)")
                    return chunks
        except Exception as e:
            print(f"  [ITIJChunker] LLM falhou ({e}), usando fallback")

        # 3. Fallback para FixedChunker (usa texto puro)
        return self._fallback(texto_puro, motivo="LLM nao segmentou")

    # ------------------------------------------------------------------
    # Limpeza do HTML
    # ------------------------------------------------------------------

    def _segmentar_com_llm(self, texto: str) -> dict | None:
        """
        Envia o texto ao LLM e devolve o JSON de seccoes.

        Para documentos longos divide em duas passagens:
            1a: primeira metade -> metadados, sumario, relatorio, factos
            2a: segunda metade  -> fundamentacao_direito, decisao
        Depois funde os dois JSONs.
        """
        import requests as _req

        if len(texto) <= self._max_chars_llm:
            print(f"  [ITIJChunker] Enviando {len(texto)} chars ao LLM")
            return self._chamar_llm(_req, texto)
        else:
            print(f"  [ITIJChunker] Documento longo ({len(texto)} chars) — duas passagens")
            meio = len(texto) // 2
            parte1 = texto[:self._max_chars_llm]
            parte2_inicio = max(0, meio - 500)
            parte2 = texto[parte2_inicio:]
            if len(parte2) > self._max_chars_llm:
                parte2 = parte2[:self._max_chars_llm]

            seccoes1 = self._chamar_llm(_req, parte1) or {}
            seccoes2 = self._chamar_llm(_req, parte2) or {}

            return {
                "metadados":             seccoes1.get("metadados")             or seccoes2.get("metadados"),
                "sumario":               seccoes1.get("sumario")               or seccoes2.get("sumario"),
                "relatorio":             seccoes1.get("relatorio")             or seccoes2.get("relatorio"),
                "factos":                seccoes1.get("factos")                or seccoes2.get("factos"),
                "fundamentacao_direito": seccoes2.get("fundamentacao_direito") or seccoes1.get("fundamentacao_direito"),
                "decisao":               seccoes2.get("decisao")               or seccoes1.get("decisao"),
            }

    def _chamar_llm(self, _req, texto_envio: str) -> dict | None:
        """Faz uma chamada ao LLM com o prompt de segmentacao."""
        prompt = PROMPT_SEGMENTACAO.replace("{texto}", texto_envio)

        resp = _req.post(
            f"{self._llm_base_url}/api/chat",
            json={
                "model": self._llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a JSON extractor. "
                            "You ALWAYS respond with ONLY a valid JSON object. "
                            "No text before or after the JSON. No explanations. No summaries. "
                            "Only the JSON object with exactly these keys: "
                            "metadados, sumario, relatorio, factos, fundamentacao_direito, decisao."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream":  False,
                "format":  {
                    "type": "object",
                    "properties": {
                        "metadados":             {"type": ["string", "null"]},
                        "sumario":               {"type": ["string", "null"]},
                        "relatorio":             {"type": ["string", "null"]},
                        "factos":                {"type": ["string", "null"]},
                        "fundamentacao_direito": {"type": ["string", "null"]},
                        "decisao":               {"type": ["string", "null"]},
                    },
                    "required": ["metadados", "sumario", "relatorio", "factos",
                                 "fundamentacao_direito", "decisao"],
                    "additionalProperties": False,
                },
                "options": {"temperature": 0, "num_predict": 8000},
            },
            timeout=self._timeout,
            headers={"ngrok-skip-browser-warning": "true"},
        )
        resp.raise_for_status()

        conteudo = resp.json()["message"]["content"].strip()
        print(f"  [ITIJChunker] Resposta LLM ({len(conteudo)} chars): {conteudo[:300]}")

        json_match = re.search(r"\{.*\}", conteudo, re.DOTALL)
        if not json_match:
            print(f"  [ITIJChunker] Sem JSON na resposta")
            return None

        seccoes = json.loads(json_match.group())
        encontradas = [k for k, v in seccoes.items() if v]
        print(f"  [ITIJChunker] Seccoes encontradas: {encontradas}")

        # Validar que tem exactamente as chaves esperadas
        chaves_validas = [k for k in SECCOES_ORDEM if seccoes.get(k)]
        if not chaves_validas:
            print(f"  [ITIJChunker] AVISO: LLM usou chaves erradas: {list(seccoes.keys())}")
            return None

        return seccoes

    def _seccoes_para_chunks(self, seccoes: dict) -> list[dict]:
        """Converte o JSON de seccoes em lista de chunks."""
        chunks = []
        for nome in SECCOES_ORDEM:
            texto = seccoes.get(nome)
            if not texto or not texto.strip():
                continue
            texto = texto.strip()

            if len(texto) <= self._chunk_size * 2:
                # Seccao curta — chunk unico
                chunks.append({
                    "text":      texto,
                    "section":   nome,
                    "chunk_idx": 0,
                })
            else:
                # Seccao longa — subdividir com FixedChunker
                for i, sc in enumerate(self._fixed.split(texto)):
                    chunks.append({
                        "text":      sc["text"],
                        "section":   f"{nome}_parte_{i+1}",
                        "chunk_idx": i,
                    })

        return chunks

    def _fallback(self, texto: str, motivo: str = "") -> list[dict]:
        """FixedChunker como fallback."""
        if motivo:
            print(f"  [ITIJChunker] Fallback ({motivo})")
        chunks = self._fixed.split(texto)
        return [{**c, "section": "texto_integral"} for c in chunks]


# ------------------------------------------------------------------
# Funcao publica para extrair texto limpo do HTML
# (usada tambem pelo views.py para guardar acordaos_limpos/)
# ------------------------------------------------------------------

def extrair_texto_limpo(html: str) -> str:
    """
    Limpa o HTML de um acordao do ITIJ removendo o que e desnecessario
    mas mantendo a estrutura semantica importante.

    Remove:
        - <script>, <style>, <img>
        - Links de navegacao (<a href=...>) mas mantem o texto do link
        - Atributos de apresentacao: bgcolor, color, face, size, width,
          height, cellspacing, cellpadding, valign, align, border
        - Tags <font> (substituidas pelo seu conteudo)
        - <br> excessivos (mais de 2 seguidos)
        - Linhas/paragrafos completamente vazios

    Mantem:
        - Estrutura da tabela de cabecalho (<table>, <tr>, <td>)
        - Formatacao semantica: <b>, <u>, <i>, <p>
        - Texto integral completo
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remover tags inuteis completamente
    for tag in soup.find_all(["script", "style", "img"]):
        tag.decompose()

    # 2. Substituir <a> pelo seu texto (remover links mas manter texto)
    for a in soup.find_all("a"):
        a.replace_with(a.get_text())

    # 3. Substituir <font> pelo seu conteudo (tag decorativa)
    for font in soup.find_all("font"):
        font.unwrap()

    # 4. Remover atributos de apresentacao de todas as tags
    ATTRS_REMOVER = {
        "bgcolor", "color", "face", "size",
        "width", "height", "cellspacing", "cellpadding",
        "valign", "align", "border", "style",
        "class", "id",
    }
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ATTRS_REMOVER:
                del tag[attr]

    # 5. Remover <br> excessivos (mais de 2 seguidos)
    br_count = 0
    for tag in soup.find_all(True):
        children = list(tag.children)
        for child in children:
            if getattr(child, "name", None) == "br":
                br_count += 1
                if br_count > 1:
                    child.decompose()
            else:
                br_count = 0

    # 6. Serializar de volta para HTML limpo
    html_limpo = str(soup)

    # 7. Limpar linhas vazias excessivas no HTML resultante
    html_limpo = re.sub(r"(<br[^>]*>\s*){2,}", "<br>", html_limpo)
    html_limpo = re.sub(r"\n{3,}", "\n\n", html_limpo)

    return html_limpo