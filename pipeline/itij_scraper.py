# # """
# # itij_scraper.py

# # Scraper para o portal ITIJ (dgsi.pt) — pesquisa e extracção de acórdãos.

# # Quatro tipos de pesquisa suportados (confirmados para Tribunal da Relação de Évora):
# #     livre      — texto em linguagem natural + operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*
# #     termos     — até 4 termos com operadores entre eles (AND/OR/NEAR/SENTENCE/PARAGRAPH)
# #     campo      — pesquisa num campo específico (PROCESSO, RELATOR, DESCRITORES, SUMARIO, etc.)
# #     descritor  — pesquisa na lista de descritores jurídicos (mesmo interface que livre)

# # Tribunais suportados:
# #     tre   → Tribunal da Relação de Évora      (hashes confirmados)
# #     trl   → Tribunal da Relação de Lisboa
# #     trp   → Tribunal da Relação do Porto
# #     trc   → Tribunal da Relação de Coimbra
# #     trg   → Tribunal da Relação de Guimarães
# #     stj   → Supremo Tribunal de Justiça
# #     sta   → Supremo Tribunal Administrativo
# #     tcas  → Tribunal Central Administrativo Sul
# #     tcan  → Tribunal Central Administrativo Norte

# # Nota: os form_hash dos tribunais que não o TRE precisam de ser confirmados
# # abrindo /jXXX.nsf/Pesquisa+Livre?OpenForm e verificando o action do form.

# # Dependências:
# #     pip install requests beautifulsoup4

# # Uso:
# #     from itij_scraper import ITIJScraper

# #     scraper = ITIJScraper()

# #     # Pesquisa livre
# #     resultados = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal="tre")

# #     # Pesquisa por termos
# #     resultados = scraper.pesquisar_termos(
# #         termos=["despedimento", "justa causa"],
# #         operadores=["AND"],
# #         tribunal="tre"
# #     )

# #     # Pesquisa por campo
# #     resultados = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal="tre")
# #     resultados = scraper.pesquisar_campo("RELATOR", "=", "PAULA DO PACO", tribunal="tre")
# #     resultados = scraper.pesquisar_campo("DATAAC", ">=", "2024-01-01", tribunal="tre")

# #     # Pesquisa por descritor
# #     resultados = scraper.pesquisar_descritor("despedimento ilicito", tribunal="tre")

# #     # Descarregar texto de um acordao
# #     texto = scraper.descarregar_texto(resultados[0]["url"])
# # """

# # import re
# # import time

# # import requests
# # from bs4 import BeautifulSoup


# # # ---------------------------------------------------------------------------
# # # Configuracao dos tribunais
# # # Hashes confirmados para TRE — os restantes precisam de verificacao
# # # ---------------------------------------------------------------------------

# # TRIBUNAIS = {
# #     "tre": {
# #         "nome":            "Tribunal da Relação de Évora",
# #         "prefixo":         "jtre",
# #         "hash_livre":      "8f8d2b7e72244bca80256879006d6594",  # confirmado
# #         "hash_termos":     "3d2a49955a5bf67080256879006d6595",  # confirmado
# #         "hash_campo":      "6d54606360981c7380256879006d6592",  # confirmado
# #         "hash_descritor":  "b8f3314245b23f0780256879006d6593",  # confirmado
# #     },
# #     "trl": {
# #         "nome":            "Tribunal da Relação de Lisboa",
# #         "prefixo":         "jtrl",
# #         "hash_livre":      None,  # confirmar em /jtrl.nsf/Pesquisa+Livre?OpenForm
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trp": {
# #         "nome":            "Tribunal da Relação do Porto",
# #         "prefixo":         "jtrp",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trc": {
# #         "nome":            "Tribunal da Relação de Coimbra",
# #         "prefixo":         "jtrc",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trg": {
# #         "nome":            "Tribunal da Relação de Guimarães",
# #         "prefixo":         "jtrg",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "stj": {
# #         "nome":            "Supremo Tribunal de Justiça",
# #         "prefixo":         "jstj",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "sta": {
# #         "nome":            "Supremo Tribunal Administrativo",
# #         "prefixo":         "jsta",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "tcas": {
# #         "nome":            "Tribunal Central Administrativo Sul",
# #         "prefixo":         "jtcas",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "tcan": {
# #         "nome":            "Tribunal Central Administrativo Norte",
# #         "prefixo":         "jtcan",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# # }

# # # Campos disponíveis na pesquisa por campo
# # CAMPOS_DISPONIVEIS = [
# #     "PROCESSO", "C1", "RELATOR", "DESCRITORES", "NUMDOC", "APENSO",
# #     "DATAAC", "NUMUNICO", "VOTACAO", "REFPUBL", "TRIBREC", "PROCREC",
# #     "DATA", "TEXTOINT", "RECURSO", "PROCREF", "PRIVAC", "MEIOPROCESSUAL",
# #     "DECISAO", "INDEVENTUAIS", "AREATEMATICA", "LEGNACIONAL",
# #     "LEGCOMUNITARIA", "LEGESTRANGEIRA", "REFINTERNAC", "JURNACIONAL",
# #     "JURINTERNAC", "JURESTRANGEIRA", "SUMARIO", "DECTINTEGRAL",
# # ]

# # OPERADORES_CAMPO = ["=", "<", ">", "<=", ">="]
# # OPERADORES_TERMOS = ["AND", "OR", "NEAR", "SENTENCE", "PARAGRAPH"]

# # BASE_URL = "https://www.dgsi.pt"

# # HEADERS = {
# #     "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# #                        "AppleWebKit/537.36 (KHTML, like Gecko) "
# #                        "Chrome/120.0.0.0 Safari/537.36",
# #     "Accept":          "text/html,application/xhtml+xml",
# #     "Accept-Language": "pt-PT,pt;q=0.9",
# # }


# # # ---------------------------------------------------------------------------
# # # ITIJScraper
# # # ---------------------------------------------------------------------------

# # class ITIJScraper:
# #     """
# #     Pesquisa e extracção de acordaos do portal ITIJ (dgsi.pt).
# #     Suporta os quatro tipos de pesquisa do formulário Lotus Domino.
# #     """

# #     def __init__(self, timeout: int = 15, delay: float = 1.0):
# #         """
# #         Args:
# #             timeout: segundos de timeout por pedido HTTP
# #             delay:   segundos de espera entre pedidos (respeitar o servidor)
# #         """
# #         self._timeout = timeout
# #         self._delay   = delay
# #         self._session = requests.Session()
# #         self._session.headers.update(HEADERS)

# #     # ------------------------------------------------------------------
# #     # Pesquisa Livre
# #     # ------------------------------------------------------------------

# #     def pesquisar_livre(
# #         self,
# #         query: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa em linguagem natural com operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*.

# #         Args:
# #             query:          Ex: "despedimento ilicito AND justa causa"
# #             tribunal:       Código do tribunal (ver TRIBUNAIS)
# #             max_resultados: Número máximo de resultados

# #         Returns:
# #             Lista de dicts com processo, data, relator, descritores, url, tribunal
# #         """
# #         hash_key = "hash_livre"
# #         dados    = {"Query": query}
# #         return self._pesquisar(tribunal, hash_key, dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Termos
# #     # ------------------------------------------------------------------

# #     def pesquisar_termos(
# #         self,
# #         termos: list[str],
# #         operadores: list[str] | None = None,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa com até 4 termos e operadores entre eles.

# #         Args:
# #             termos:     Lista de 1 a 4 termos. Ex: ["despedimento", "justa causa"]
# #             operadores: Lista de operadores entre termos (len = len(termos)-1).
# #                         Valores: AND, OR, NEAR, SENTENCE, PARAGRAPH.
# #                         Default: AND entre todos.
# #             tribunal:   Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplo:
# #             pesquisar_termos(
# #                 termos=["despedimento", "justa causa", "procedimento disciplinar"],
# #                 operadores=["AND", "NEAR"]
# #             )
# #         """
# #         if not termos:
# #             raise ValueError("É necessário pelo menos um termo.")
# #         if len(termos) > 4:
# #             raise ValueError("Máximo de 4 termos na pesquisa por termos.")

# #         if operadores is None:
# #             operadores = ["AND"] * (len(termos) - 1)

# #         # Preencher até 4 termos/operadores
# #         dados = {}
# #         for i, termo in enumerate(termos[:4], 1):
# #             dados[f"termo{i}"] = termo

# #         for i, op in enumerate(operadores[:3], 2):
# #             if op not in OPERADORES_TERMOS:
# #                 raise ValueError(f"Operador '{op}' inválido. Use: {OPERADORES_TERMOS}")
# #             dados[f"operador{i}"]              = op
# #             dados[f"%%Surrogate_operador{i}"]  = "1"

# #         # Campos vazios para os termos não usados
# #         for i in range(len(termos) + 1, 5):
# #             dados[f"termo{i}"] = ""

# #         return self._pesquisar(tribunal, "hash_termos", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Campo
# #     # ------------------------------------------------------------------

# #     def pesquisar_campo(
# #         self,
# #         campo: str,
# #         operador: str,
# #         valor: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa num campo específico do acórdão.

# #         Args:
# #             campo:    Campo a pesquisar. Ex: "DESCRITORES", "RELATOR",
# #                       "PROCESSO", "DATAAC", "SUMARIO", "TEXTOINT"
# #                       (ver CAMPOS_DISPONIVEIS para lista completa)
# #             operador: "=", "<", ">", "<=", ">="
# #             valor:    Valor a pesquisar. Ex: "DESPEDIMENTO ILICITO", "2024-01-01"
# #             tribunal: Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplos:
# #             pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")
# #             pesquisar_campo("RELATOR", "=", "PAULA DO PACO")
# #             pesquisar_campo("DATAAC", ">=", "01/01/2024")
# #             pesquisar_campo("SUMARIO", "=", "justa causa")
# #         """
# #         if campo not in CAMPOS_DISPONIVEIS:
# #             raise ValueError(
# #                 f"Campo '{campo}' inválido.\nCampos disponíveis: {CAMPOS_DISPONIVEIS}"
# #             )
# #         if operador not in OPERADORES_CAMPO:
# #             raise ValueError(
# #                 f"Operador '{operador}' inválido. Use: {OPERADORES_CAMPO}"
# #             )

# #         dados = {
# #             "campo":              campo,
# #             "%%Surrogate_campo":  "1",
# #             "operador":           operador,
# #             "%%Surrogate_operador": "1",
# #             "valor":              valor,
# #         }
# #         return self._pesquisar(tribunal, "hash_campo", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Descritor
# #     # ------------------------------------------------------------------

# #     def pesquisar_descritor(
# #         self,
# #         query: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa na lista de descritores jurídicos.
# #         Usa o mesmo interface que a pesquisa livre mas focado nos descritores.

# #         Args:
# #             query:    Descritor jurídico. Ex: "DESPEDIMENTO ILICITO"
# #                       Suporta os mesmos operadores que a pesquisa livre.
# #             tribunal: Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplos:
# #             pesquisar_descritor("DESPEDIMENTO ILICITO")
# #             pesquisar_descritor("PRESCRICAO AND INDEMNIZACAO")
# #             pesquisar_descritor("JUSTA CAUSA*")  # truncatura
# #         """
# #         dados = {"Query": query}
# #         return self._pesquisar(tribunal, "hash_descritor", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa em múltiplos tribunais
# #     # ------------------------------------------------------------------

# #     def pesquisar_multiplos(
# #         self,
# #         query: str,
# #         tipo: str = "livre",
# #         tribunais: list[str] | None = None,
# #         max_por_tribunal: int = 10,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa em vários tribunais e agrega os resultados.

# #         Args:
# #             query:            Termos de pesquisa
# #             tipo:             "livre" | "descritor" (os outros tipos requerem
# #                               parâmetros específicos — usar directamente)
# #             tribunais:        Lista de códigos (None = todos os tribunais com hashes)
# #             max_por_tribunal: Máximo de resultados por tribunal
# #         """
# #         if tribunais is None:
# #             # Só tribunais com hashes confirmados
# #             tribunais = [
# #                 t for t, cfg in TRIBUNAIS.items()
# #                 if cfg.get(f"hash_{tipo}") is not None
# #             ]

# #         todos = []
# #         for t in tribunais:
# #             try:
# #                 if tipo == "livre":
# #                     resultados = self.pesquisar_livre(query, t, max_por_tribunal)
# #                 elif tipo == "descritor":
# #                     resultados = self.pesquisar_descritor(query, t, max_por_tribunal)
# #                 else:
# #                     raise ValueError(f"Tipo '{tipo}' não suportado em pesquisa múltipla.")
# #                 todos.extend(resultados)
# #                 print(f"  {TRIBUNAIS[t]['nome']}: {len(resultados)} resultados")
# #             except Exception as e:
# #                 print(f"  {TRIBUNAIS[t]['nome']}: erro — {e}")

# #         return todos

# #     # ------------------------------------------------------------------
# #     # Extracção de texto
# #     # ------------------------------------------------------------------

# #     def descarregar_texto(self, url: str) -> str:
# #         """
# #         Descarrega e extrai o texto completo de um acórdão.

# #         Args:
# #             url: URL do acórdão (relativo ou absoluto)

# #         Returns:
# #             Texto limpo do acórdão (sem HTML)
# #         """
# #         if url.startswith("/"):
# #             url = BASE_URL + url

# #         try:
# #             time.sleep(self._delay)
# #             resp = self._session.get(url, timeout=self._timeout)
# #             resp.encoding = resp.apparent_encoding or "utf-8"
# #             resp.raise_for_status()
# #         except requests.RequestException as e:
# #             raise RuntimeError(f"Erro ao descarregar acórdão: {e}")

# #         return self._parse_acordao(resp.text)

# #     def descarregar_para_ficheiro(self, url: str, path: str) -> str:
# #         """
# #         Descarrega texto de um acórdão e guarda num ficheiro .txt.
# #         """
# #         texto = self.descarregar_texto(url)
# #         with open(path, "w", encoding="utf-8") as f:
# #             f.write(texto)
# #         return path

# #     # ------------------------------------------------------------------
# #     # Utilitários
# #     # ------------------------------------------------------------------

# #     def confirmar_hashes(self, tribunal: str) -> dict:
# #         """
# #         Descobre automaticamente os hashes dos 4 formulários de um tribunal
# #         abrindo cada página de pesquisa e lendo o action do form.

# #         Útil para configurar tribunais cujos hashes ainda estão como None.

# #         Args:
# #             tribunal: Código do tribunal (ex: "trl")

# #         Returns:
# #             Dict com os 4 hashes descobertos
# #         """
# #         cfg     = TRIBUNAIS[tribunal]
# #         prefixo = cfg["prefixo"]
# #         tipos   = {
# #             "hash_livre":     "Pesquisa+Livre",
# #             "hash_termos":    "Pesquisa+Termos",
# #             "hash_campo":     "Pesquisa+Campo",
# #             "hash_descritor": "Pesquisa+Descritor",
# #         }
# #         hashes = {}
# #         for chave, nome_form in tipos.items():
# #             url = f"{BASE_URL}/{prefixo}.nsf/{nome_form}?OpenForm"
# #             try:
# #                 time.sleep(self._delay)
# #                 resp = self._session.get(url, timeout=self._timeout)
# #                 soup = BeautifulSoup(resp.text, "html.parser")
# #                 form = soup.find("form")
# #                 if form and form.get("action"):
# #                     # /jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument
# #                     action = form["action"]
# #                     match  = re.search(r"/[^/]+\.nsf/([a-f0-9]+)\?", action)
# #                     if match:
# #                         hashes[chave] = match.group(1)
# #                     else:
# #                         hashes[chave] = None
# #                 else:
# #                     hashes[chave] = None
# #             except Exception as e:
# #                 hashes[chave] = None
# #                 print(f"  Erro ao obter {nome_form}: {e}")

# #         return hashes

# #     # ------------------------------------------------------------------
# #     # Métodos internos
# #     # ------------------------------------------------------------------

# #     def _pesquisar(
# #         self,
# #         tribunal: str,
# #         hash_key: str,
# #         dados: dict,
# #         max_resultados: int,
# #     ) -> list[dict]:
# #         """Executa o POST e faz parse dos resultados."""
# #         if tribunal not in TRIBUNAIS:
# #             raise ValueError(
# #                 f"Tribunal '{tribunal}' desconhecido. "
# #                 f"Opções: {list(TRIBUNAIS.keys())}"
# #             )

# #         cfg  = TRIBUNAIS[tribunal]
# #         hash_val = cfg.get(hash_key)

# #         if hash_val is None:
# #             raise ValueError(
# #                 f"Hash do formulário '{hash_key}' não configurado para "
# #                 f"'{cfg['nome']}'. Usa confirmar_hashes('{tribunal}') para "
# #                 f"descobrir os hashes automaticamente."
# #             )

# #         post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"

# #         try:
# #             time.sleep(self._delay)
# #             resp = self._session.post(
# #                 post_url,
# #                 data=dados,
# #                 timeout=self._timeout,
# #                 allow_redirects=True,
# #             )
# #             resp.encoding = resp.apparent_encoding or "utf-8"
# #             resp.raise_for_status()
# #         except requests.RequestException as e:
# #             raise RuntimeError(f"Erro na pesquisa ITIJ: {e}")

# #         return self._parse_lista(resp.text, tribunal, max_resultados)

# #     def _parse_lista(
# #         self,
# #         html: str,
# #         tribunal: str,
# #         max_resultados: int,
# #     ) -> list[dict]:
# #         """Extrai lista de acórdãos do HTML de resultados."""
# #         soup    = BeautifulSoup(html, "html.parser")
# #         nome_t  = TRIBUNAIS[tribunal]["nome"]
# #         results = []

# #         for tr in soup.find_all("tr", valign="top"):
# #             tds = tr.find_all("td")
# #             if len(tds) < 4:
# #                 continue

# #             data_text = tds[0].get_text(strip=True)
# #             if not re.match(r"\d{2}/\d{2}/\d{4}", data_text):
# #                 continue

# #             link = tds[1].find("a")
# #             if not link:
# #                 continue

# #             processo = link.get_text(strip=True)
# #             href     = link.get("href", "")
# #             url      = href if href.startswith("http") else BASE_URL + href
# #             relator  = tds[2].get_text(strip=True)

# #             descritores = [
# #                 d.strip()
# #                 for d in tds[3].get_text(separator="\n", strip=True).split("\n")
# #                 if d.strip()
# #             ]

# #             results.append({
# #                 "processo":    processo,
# #                 "data":        data_text,
# #                 "relator":     relator,
# #                 "descritores": descritores,
# #                 "url":         url,
# #                 "tribunal":    nome_t,
# #                 "tribunal_id": tribunal,
# #             })

# #             if len(results) >= max_resultados:
# #                 break

# #         return results

# #     def _parse_acordao(self, html: str) -> str:
# #         """Extrai texto limpo do HTML de um acórdão individual."""
# #         soup = BeautifulSoup(html, "html.parser")

# #         for tag in soup(["script", "style", "head"]):
# #             tag.decompose()

# #         texto  = soup.get_text(separator="\n")
# #         linhas = [l.strip() for l in texto.splitlines() if l.strip()]

# #         ignorar = {
# #             "anterior", "seguinte", "principal",
# #             "pesquisa livre", "por termos", "por campo", "por descritor",
# #         }
# #         linhas = [l for l in linhas if l.lower() not in ignorar]

# #         return "\n".join(linhas)

# # """
# # itij_scraper.py

# # Scraper para o portal ITIJ (dgsi.pt) — pesquisa e extracção de acórdãos.

# # Quatro tipos de pesquisa suportados (confirmados para Tribunal da Relação de Évora):
# #     livre      — texto em linguagem natural + operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*
# #     termos     — até 4 termos com operadores entre eles (AND/OR/NEAR/SENTENCE/PARAGRAPH)
# #     campo      — pesquisa num campo específico (PROCESSO, RELATOR, DESCRITORES, SUMARIO, etc.)
# #     descritor  — pesquisa na lista de descritores jurídicos (mesmo interface que livre)

# # Tribunais suportados:
# #     tre   → Tribunal da Relação de Évora      (hashes confirmados)
# #     trl   → Tribunal da Relação de Lisboa
# #     trp   → Tribunal da Relação do Porto
# #     trc   → Tribunal da Relação de Coimbra
# #     trg   → Tribunal da Relação de Guimarães
# #     stj   → Supremo Tribunal de Justiça
# #     sta   → Supremo Tribunal Administrativo
# #     tcas  → Tribunal Central Administrativo Sul
# #     tcan  → Tribunal Central Administrativo Norte

# # Nota: os form_hash dos tribunais que não o TRE precisam de ser confirmados
# # abrindo /jXXX.nsf/Pesquisa+Livre?OpenForm e verificando o action do form.

# # Dependências:
# #     pip install requests beautifulsoup4

# # Uso:
# #     from itij_scraper import ITIJScraper

# #     scraper = ITIJScraper()

# #     # Pesquisa livre
# #     resultados = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal="tre")

# #     # Pesquisa por termos
# #     resultados = scraper.pesquisar_termos(
# #         termos=["despedimento", "justa causa"],
# #         operadores=["AND"],
# #         tribunal="tre"
# #     )

# #     # Pesquisa por campo
# #     resultados = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal="tre")
# #     resultados = scraper.pesquisar_campo("RELATOR", "=", "PAULA DO PACO", tribunal="tre")
# #     resultados = scraper.pesquisar_campo("DATAAC", ">=", "2024-01-01", tribunal="tre")

# #     # Pesquisa por descritor
# #     resultados = scraper.pesquisar_descritor("despedimento ilicito", tribunal="tre")

# #     # Descarregar texto de um acordao
# #     texto = scraper.descarregar_texto(resultados[0]["url"])
# # """

# # import re
# # import time

# # import requests
# # from bs4 import BeautifulSoup


# # # ---------------------------------------------------------------------------
# # # Configuracao dos tribunais
# # # Hashes confirmados para TRE — os restantes precisam de verificacao
# # # ---------------------------------------------------------------------------

# # TRIBUNAIS = {
# #     "tre": {
# #         "nome":            "Tribunal da Relação de Évora",
# #         "prefixo":         "jtre",
# #         "hash_livre":      "8f8d2b7e72244bca80256879006d6594",  # confirmado
# #         "hash_termos":     "3d2a49955a5bf67080256879006d6595",  # confirmado
# #         "hash_campo":      "6d54606360981c7380256879006d6592",  # confirmado
# #         "hash_descritor":  "b8f3314245b23f0780256879006d6593",  # confirmado
# #     },
# #     "trl": {
# #         "nome":            "Tribunal da Relação de Lisboa",
# #         "prefixo":         "jtrl",
# #         "hash_livre":      None,  # confirmar em /jtrl.nsf/Pesquisa+Livre?OpenForm
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trp": {
# #         "nome":            "Tribunal da Relação do Porto",
# #         "prefixo":         "jtrp",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trc": {
# #         "nome":            "Tribunal da Relação de Coimbra",
# #         "prefixo":         "jtrc",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "trg": {
# #         "nome":            "Tribunal da Relação de Guimarães",
# #         "prefixo":         "jtrg",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "stj": {
# #         "nome":            "Supremo Tribunal de Justiça",
# #         "prefixo":         "jstj",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "sta": {
# #         "nome":            "Supremo Tribunal Administrativo",
# #         "prefixo":         "jsta",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "tcas": {
# #         "nome":            "Tribunal Central Administrativo Sul",
# #         "prefixo":         "jtcas",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# #     "tcan": {
# #         "nome":            "Tribunal Central Administrativo Norte",
# #         "prefixo":         "jtcan",
# #         "hash_livre":      None,
# #         "hash_termos":     None,
# #         "hash_campo":      None,
# #         "hash_descritor":  None,
# #     },
# # }

# # # Campos disponíveis na pesquisa por campo
# # CAMPOS_DISPONIVEIS = [
# #     "PROCESSO", "C1", "RELATOR", "DESCRITORES", "NUMDOC", "APENSO",
# #     "DATAAC", "NUMUNICO", "VOTACAO", "REFPUBL", "TRIBREC", "PROCREC",
# #     "DATA", "TEXTOINT", "RECURSO", "PROCREF", "PRIVAC", "MEIOPROCESSUAL",
# #     "DECISAO", "INDEVENTUAIS", "AREATEMATICA", "LEGNACIONAL",
# #     "LEGCOMUNITARIA", "LEGESTRANGEIRA", "REFINTERNAC", "JURNACIONAL",
# #     "JURINTERNAC", "JURESTRANGEIRA", "SUMARIO", "DECTINTEGRAL",
# # ]

# # OPERADORES_CAMPO = ["=", "<", ">", "<=", ">="]
# # OPERADORES_TERMOS = ["AND", "OR", "NEAR", "SENTENCE", "PARAGRAPH"]

# # BASE_URL = "https://www.dgsi.pt"

# # HEADERS = {
# #     "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# #                        "AppleWebKit/537.36 (KHTML, like Gecko) "
# #                        "Chrome/120.0.0.0 Safari/537.36",
# #     "Accept":          "text/html,application/xhtml+xml",
# #     "Accept-Language": "pt-PT,pt;q=0.9",
# # }


# # # ---------------------------------------------------------------------------
# # # ITIJScraper
# # # ---------------------------------------------------------------------------

# # class ITIJScraper:
# #     """
# #     Pesquisa e extracção de acordaos do portal ITIJ (dgsi.pt).
# #     Suporta os quatro tipos de pesquisa do formulário Lotus Domino.
# #     """

# #     def __init__(self, timeout: int = 15, delay: float = 1.0):
# #         """
# #         Args:
# #             timeout: segundos de timeout por pedido HTTP
# #             delay:   segundos de espera entre pedidos (respeitar o servidor)
# #         """
# #         self._timeout = timeout
# #         self._delay   = delay
# #         self._session = requests.Session()
# #         self._session.headers.update(HEADERS)

# #     # ------------------------------------------------------------------
# #     # Pesquisa Livre
# #     # ------------------------------------------------------------------

# #     def pesquisar_livre(
# #         self,
# #         query: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa em linguagem natural com operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*.

# #         Args:
# #             query:          Ex: "despedimento ilicito AND justa causa"
# #             tribunal:       Código do tribunal (ver TRIBUNAIS)
# #             max_resultados: Número máximo de resultados

# #         Returns:
# #             Lista de dicts com processo, data, relator, descritores, url, tribunal
# #         """
# #         hash_key = "hash_livre"
# #         dados    = {"Query": query}
# #         return self._pesquisar(tribunal, hash_key, dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Termos
# #     # ------------------------------------------------------------------

# #     def pesquisar_termos(
# #         self,
# #         termos: list[str],
# #         operadores: list[str] | None = None,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa com até 4 termos e operadores entre eles.

# #         Args:
# #             termos:     Lista de 1 a 4 termos. Ex: ["despedimento", "justa causa"]
# #             operadores: Lista de operadores entre termos (len = len(termos)-1).
# #                         Valores: AND, OR, NEAR, SENTENCE, PARAGRAPH.
# #                         Default: AND entre todos.
# #             tribunal:   Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplo:
# #             pesquisar_termos(
# #                 termos=["despedimento", "justa causa", "procedimento disciplinar"],
# #                 operadores=["AND", "NEAR"]
# #             )
# #         """
# #         if not termos:
# #             raise ValueError("É necessário pelo menos um termo.")
# #         if len(termos) > 4:
# #             raise ValueError("Máximo de 4 termos na pesquisa por termos.")

# #         if operadores is None:
# #             operadores = ["AND"] * (len(termos) - 1)

# #         # Preencher até 4 termos/operadores
# #         dados = {}
# #         for i, termo in enumerate(termos[:4], 1):
# #             dados[f"termo{i}"] = termo

# #         for i, op in enumerate(operadores[:3], 2):
# #             if op not in OPERADORES_TERMOS:
# #                 raise ValueError(f"Operador '{op}' inválido. Use: {OPERADORES_TERMOS}")
# #             dados[f"operador{i}"]              = op
# #             dados[f"%%Surrogate_operador{i}"]  = "1"

# #         # Campos vazios para os termos não usados
# #         for i in range(len(termos) + 1, 5):
# #             dados[f"termo{i}"] = ""

# #         return self._pesquisar(tribunal, "hash_termos", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Campo
# #     # ------------------------------------------------------------------

# #     def pesquisar_campo(
# #         self,
# #         campo: str,
# #         operador: str,
# #         valor: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa num campo específico do acórdão.

# #         Args:
# #             campo:    Campo a pesquisar. Ex: "DESCRITORES", "RELATOR",
# #                       "PROCESSO", "DATAAC", "SUMARIO", "TEXTOINT"
# #                       (ver CAMPOS_DISPONIVEIS para lista completa)
# #             operador: "=", "<", ">", "<=", ">="
# #             valor:    Valor a pesquisar. Ex: "DESPEDIMENTO ILICITO", "2024-01-01"
# #             tribunal: Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplos:
# #             pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")
# #             pesquisar_campo("RELATOR", "=", "PAULA DO PACO")
# #             pesquisar_campo("DATAAC", ">=", "01/01/2024")
# #             pesquisar_campo("SUMARIO", "=", "justa causa")
# #         """
# #         if campo not in CAMPOS_DISPONIVEIS:
# #             raise ValueError(
# #                 f"Campo '{campo}' inválido.\nCampos disponíveis: {CAMPOS_DISPONIVEIS}"
# #             )
# #         if operador not in OPERADORES_CAMPO:
# #             raise ValueError(
# #                 f"Operador '{operador}' inválido. Use: {OPERADORES_CAMPO}"
# #             )

# #         dados = {
# #             "campo":              campo,
# #             "%%Surrogate_campo":  "1",
# #             "operador":           operador,
# #             "%%Surrogate_operador": "1",
# #             "valor":              valor,
# #         }
# #         return self._pesquisar(tribunal, "hash_campo", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa por Descritor
# #     # ------------------------------------------------------------------

# #     def pesquisar_descritor(
# #         self,
# #         query: str,
# #         tribunal: str = "tre",
# #         max_resultados: int = 20,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa na lista de descritores jurídicos.
# #         Usa o mesmo interface que a pesquisa livre mas focado nos descritores.

# #         Args:
# #             query:    Descritor jurídico. Ex: "DESPEDIMENTO ILICITO"
# #                       Suporta os mesmos operadores que a pesquisa livre.
# #             tribunal: Código do tribunal
# #             max_resultados: Número máximo de resultados

# #         Exemplos:
# #             pesquisar_descritor("DESPEDIMENTO ILICITO")
# #             pesquisar_descritor("PRESCRICAO AND INDEMNIZACAO")
# #             pesquisar_descritor("JUSTA CAUSA*")  # truncatura
# #         """
# #         dados = {"Query": query}
# #         return self._pesquisar(tribunal, "hash_descritor", dados, max_resultados)

# #     # ------------------------------------------------------------------
# #     # Pesquisa em múltiplos tribunais
# #     # ------------------------------------------------------------------

# #     def pesquisar_multiplos(
# #         self,
# #         query: str,
# #         tipo: str = "livre",
# #         tribunais: list[str] | None = None,
# #         max_por_tribunal: int = 10,
# #     ) -> list[dict]:
# #         """
# #         Pesquisa em vários tribunais e agrega os resultados.

# #         Args:
# #             query:            Termos de pesquisa
# #             tipo:             "livre" | "descritor" (os outros tipos requerem
# #                               parâmetros específicos — usar directamente)
# #             tribunais:        Lista de códigos (None = todos os tribunais com hashes)
# #             max_por_tribunal: Máximo de resultados por tribunal
# #         """
# #         if tribunais is None:
# #             # Só tribunais com hashes confirmados
# #             tribunais = [
# #                 t for t, cfg in TRIBUNAIS.items()
# #                 if cfg.get(f"hash_{tipo}") is not None
# #             ]

# #         todos = []
# #         for t in tribunais:
# #             try:
# #                 if tipo == "livre":
# #                     resultados = self.pesquisar_livre(query, t, max_por_tribunal)
# #                 elif tipo == "descritor":
# #                     resultados = self.pesquisar_descritor(query, t, max_por_tribunal)
# #                 else:
# #                     raise ValueError(f"Tipo '{tipo}' não suportado em pesquisa múltipla.")
# #                 todos.extend(resultados)
# #                 print(f"  {TRIBUNAIS[t]['nome']}: {len(resultados)} resultados")
# #             except Exception as e:
# #                 print(f"  {TRIBUNAIS[t]['nome']}: erro — {e}")

# #         return todos

# #     # ------------------------------------------------------------------
# #     # Extracção de texto
# #     # ------------------------------------------------------------------

# #     def descarregar_texto(self, url: str) -> str:
# #         """
# #         Descarrega e extrai o texto completo de um acórdão.

# #         Args:
# #             url: URL do acórdão (relativo ou absoluto)

# #         Returns:
# #             Texto limpo do acórdão (sem HTML)
# #         """
# #         if url.startswith("/"):
# #             url = BASE_URL + url

# #         try:
# #             time.sleep(self._delay)
# #             resp = self._session.get(url, timeout=self._timeout)
# #             # ITIJ usa ISO-8859-1 / Windows-1252 — forcar encoding correcto
# #             resp.encoding = "iso-8859-1"
# #             resp.raise_for_status()
# #         except requests.RequestException as e:
# #             raise RuntimeError(f"Erro ao descarregar acordao: {e}")

# #         return self._parse_acordao(resp.text)

# #     def descarregar_para_ficheiro(self, url: str, path: str) -> str:
# #         """
# #         Descarrega texto de um acórdão e guarda num ficheiro .txt.
# #         """
# #         texto = self.descarregar_texto(url)
# #         with open(path, "w", encoding="utf-8") as f:
# #             f.write(texto)
# #         return path

# #     # ------------------------------------------------------------------
# #     # Utilitários
# #     # ------------------------------------------------------------------

# #     def confirmar_hashes(self, tribunal: str) -> dict:
# #         """
# #         Descobre automaticamente os hashes dos 4 formulários de um tribunal
# #         abrindo cada página de pesquisa e lendo o action do form.

# #         Útil para configurar tribunais cujos hashes ainda estão como None.

# #         Args:
# #             tribunal: Código do tribunal (ex: "trl")

# #         Returns:
# #             Dict com os 4 hashes descobertos
# #         """
# #         cfg     = TRIBUNAIS[tribunal]
# #         prefixo = cfg["prefixo"]
# #         tipos   = {
# #             "hash_livre":     "Pesquisa+Livre",
# #             "hash_termos":    "Pesquisa+Termos",
# #             "hash_campo":     "Pesquisa+Campo",
# #             "hash_descritor": "Pesquisa+Descritor",
# #         }
# #         hashes = {}
# #         for chave, nome_form in tipos.items():
# #             url = f"{BASE_URL}/{prefixo}.nsf/{nome_form}?OpenForm"
# #             try:
# #                 time.sleep(self._delay)
# #                 resp = self._session.get(url, timeout=self._timeout)
# #                 soup = BeautifulSoup(resp.text, "html.parser")
# #                 form = soup.find("form")
# #                 if form and form.get("action"):
# #                     # /jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument
# #                     action = form["action"]
# #                     match  = re.search(r"/[^/]+\.nsf/([a-f0-9]+)\?", action)
# #                     if match:
# #                         hashes[chave] = match.group(1)
# #                     else:
# #                         hashes[chave] = None
# #                 else:
# #                     hashes[chave] = None
# #             except Exception as e:
# #                 hashes[chave] = None
# #                 print(f"  Erro ao obter {nome_form}: {e}")

# #         return hashes

# #     # ------------------------------------------------------------------
# #     # Métodos internos
# #     # ------------------------------------------------------------------

# #     def _pesquisar(
# #         self,
# #         tribunal: str,
# #         hash_key: str,
# #         dados: dict,
# #         max_resultados: int,
# #     ) -> list[dict]:
# #         """Executa o POST e faz parse dos resultados."""
# #         if tribunal not in TRIBUNAIS:
# #             raise ValueError(
# #                 f"Tribunal '{tribunal}' desconhecido. "
# #                 f"Opções: {list(TRIBUNAIS.keys())}"
# #             )

# #         cfg  = TRIBUNAIS[tribunal]
# #         hash_val = cfg.get(hash_key)

# #         if hash_val is None:
# #             raise ValueError(
# #                 f"Hash do formulário '{hash_key}' não configurado para "
# #                 f"'{cfg['nome']}'. Usa confirmar_hashes('{tribunal}') para "
# #                 f"descobrir os hashes automaticamente."
# #             )

# #         post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"

# #         try:
# #             time.sleep(self._delay)
# #             resp = self._session.post(
# #                 post_url,
# #                 data=dados,
# #                 timeout=self._timeout,
# #                 allow_redirects=True,
# #             )
# #             resp.encoding = "iso-8859-1"
# #             resp.raise_for_status()
# #         except requests.RequestException as e:
# #             raise RuntimeError(f"Erro na pesquisa ITIJ: {e}")

# #         return self._parse_lista(resp.text, tribunal, max_resultados)

# #     def _parse_lista(
# #         self,
# #         html: str,
# #         tribunal: str,
# #         max_resultados: int,
# #     ) -> list[dict]:
# #         """Extrai lista de acordaos do HTML de resultados.

# #         O ITIJ tem dois formatos:
# #         - Lista principal (por ano): 4 cols — data | processo | relator | descritores
# #         - Resultados de pesquisa:    5 cols — icone | data | processo | relator | descritores
# #         A data pode usar / ou - como separador.
# #         """
# #         soup    = BeautifulSoup(html, "html.parser")
# #         nome_t  = TRIBUNAIS[tribunal]["nome"]
# #         results = []

# #         for tr in soup.find_all("tr", valign="top"):
# #             tds = tr.find_all("td")
# #             if len(tds) < 4:
# #                 continue

# #             # Detectar formato pela primeira coluna:
# #             # pesquisa (5 cols) — col 0 e icone sem texto util
# #             # lista    (4 cols) — col 0 e a data
# #             if len(tds) >= 5:
# #                 idx_data, idx_proc, idx_rel, idx_desc = 1, 2, 3, 4
# #             else:
# #                 idx_data, idx_proc, idx_rel, idx_desc = 0, 1, 2, 3

# #             data_text = tds[idx_data].get_text(strip=True)
# #             if not re.match(r"\d{2}[/-]\d{2}[/-]\d{4}", data_text):
# #                 continue

# #             link = tds[idx_proc].find("a")
# #             if not link:
# #                 continue

# #             processo = link.get_text(strip=True)
# #             href     = link.get("href", "")
# #             # Remover parametros &Highlight do URL
# #             url_base = href.split("&")[0] if "&" in href else href
# #             url      = url_base if url_base.startswith("http") else BASE_URL + url_base
# #             relator  = tds[idx_rel].get_text(strip=True)

# #             descritores = [
# #                 d.strip()
# #                 for d in tds[idx_desc].get_text(separator="\n", strip=True).split("\n")
# #                 if d.strip()
# #             ]

# #             results.append({
# #                 "processo":    processo,
# #                 "data":        data_text,
# #                 "relator":     relator,
# #                 "descritores": descritores,
# #                 "url":         url,
# #                 "tribunal":    nome_t,
# #                 "tribunal_id": tribunal,
# #             })

# #             if len(results) >= max_resultados:
# #                 break

# #         return results

# #     def _parse_acordao(self, html: str) -> str:
# #         """Extrai texto limpo do HTML de um acórdão individual."""
# #         soup = BeautifulSoup(html, "html.parser")

# #         for tag in soup(["script", "style", "head"]):
# #             tag.decompose()

# #         texto  = soup.get_text(separator="\n")
# #         linhas = [l.strip() for l in texto.splitlines() if l.strip()]

# #         ignorar = {
# #             "anterior", "seguinte", "principal",
# #             "pesquisa livre", "por termos", "por campo", "por descritor",
# #         }
# #         linhas = [l for l in linhas if l.lower() not in ignorar]

# #         return "\n".join(linhas)

# """
# itij_scraper.py

# Scraper para o portal ITIJ (dgsi.pt) — pesquisa e extracção de acórdãos.

# Quatro tipos de pesquisa suportados (confirmados para Tribunal da Relação de Évora):
#     livre      — texto em linguagem natural + operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*
#     termos     — até 4 termos com operadores entre eles (AND/OR/NEAR/SENTENCE/PARAGRAPH)
#     campo      — pesquisa num campo específico (PROCESSO, RELATOR, DESCRITORES, SUMARIO, etc.)
#     descritor  — pesquisa na lista de descritores jurídicos (mesmo interface que livre)

# Tribunais suportados:
#     tre   → Tribunal da Relação de Évora      (hashes confirmados)
#     trl   → Tribunal da Relação de Lisboa
#     trp   → Tribunal da Relação do Porto
#     trc   → Tribunal da Relação de Coimbra
#     trg   → Tribunal da Relação de Guimarães
#     stj   → Supremo Tribunal de Justiça
#     sta   → Supremo Tribunal Administrativo
#     tcas  → Tribunal Central Administrativo Sul
#     tcan  → Tribunal Central Administrativo Norte

# Nota: os form_hash dos tribunais que não o TRE precisam de ser confirmados
# abrindo /jXXX.nsf/Pesquisa+Livre?OpenForm e verificando o action do form.

# Dependências:
#     pip install requests beautifulsoup4

# Uso:
#     from itij_scraper import ITIJScraper

#     scraper = ITIJScraper()

#     # Pesquisa livre
#     resultados = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal="tre")

#     # Pesquisa por termos
#     resultados = scraper.pesquisar_termos(
#         termos=["despedimento", "justa causa"],
#         operadores=["AND"],
#         tribunal="tre"
#     )

#     # Pesquisa por campo
#     resultados = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal="tre")
#     resultados = scraper.pesquisar_campo("RELATOR", "=", "PAULA DO PACO", tribunal="tre")
#     resultados = scraper.pesquisar_campo("DATAAC", ">=", "2024-01-01", tribunal="tre")

#     # Pesquisa por descritor
#     resultados = scraper.pesquisar_descritor("despedimento ilicito", tribunal="tre")

#     # Descarregar texto de um acordao
#     texto = scraper.descarregar_texto(resultados[0]["url"])
# """

# import re
# import time

# import requests
# from bs4 import BeautifulSoup


# # ---------------------------------------------------------------------------
# # Configuracao dos tribunais
# # Hashes confirmados para TRE — os restantes precisam de verificacao
# # ---------------------------------------------------------------------------

# # Hashes partilhados — TRE, TRP, TRC, TRG usam o mesmo template Lotus Domino
# _H_SHARED = {
#     "hash_livre":     "8f8d2b7e72244bca80256879006d6594",
#     "hash_termos":    "3d2a49955a5bf67080256879006d6595",
#     "hash_campo":     "6d54606360981c7380256879006d6592",
#     "hash_descritor": "b8f3314245b23f0780256879006d6593",
# }

# TRIBUNAIS = {
#     "tre": {
#         "nome":    "Tribunal da Relação de Évora",
#         "prefixo": "jtre",
#         **_H_SHARED,  # confirmado
#     },
#     "trl": {
#         "nome":           "Tribunal da Relação de Lisboa",
#         "prefixo":        "jtrl",
#         "hash_livre":     "14adab75c943f8c480256879006e5bda",  # confirmado
#         "hash_termos":    "280913ebea31cc6f80256879006e5bdb",  # confirmado
#         "hash_campo":     "86e7be720738947280256879006e5bd8",  # confirmado
#         "hash_descritor": "a37a3990f3f371db80256879006e5bd9",  # confirmado
#     },
#     "trp": {
#         "nome":    "Tribunal da Relação do Porto",
#         "prefixo": "jtrp",
#         **_H_SHARED,  # confirmado (mesmo template que TRE)
#     },
#     "trc": {
#         "nome":    "Tribunal da Relação de Coimbra",
#         "prefixo": "jtrc",
#         **_H_SHARED,  # confirmado (mesmo template que TRE)
#     },
#     "trg": {
#         "nome":    "Tribunal da Relação de Guimarães",
#         "prefixo": "jtrg",
#         **_H_SHARED,  # confirmado (mesmo template que TRE)
#     },
#     "stj": {
#         "nome":           "Supremo Tribunal de Justiça",
#         "prefixo":        "jstj",
#         "hash_livre":     "f83eef66ec4efcb780256879006bc015",  # confirmado
#         "hash_termos":    "cde84ff44faf0d0680256879006bc016",  # confirmado
#         "hash_campo":     "38f33c44b0c8358280256879006bc013",  # confirmado
#         "hash_descritor": "9b28c5162249339d80256879006bc014",  # confirmado
#     },
#     "sta": {
#         "nome":           "Supremo Tribunal Administrativo",
#         "prefixo":        "jsta",
#         "hash_livre":     "02eae0bd4de5026e80256b480065970d",  # confirmado
#         "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
#         "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
#         "hash_descritor": "1ea881265b7d747c80256879004cbca8",  # confirmado
#     },
#     "tcas": {
#         # TCAS — Pareceres MP Contencioso Administrativo (3975 doc.)
#         # Usa os mesmos hashes que TCAN — template partilhado
#         # Sem pesquisa por descritor
#         # Campos proprios: CONTENCIOSO, PROCESSUAL, DATAAC, PROCESSO,
#         #   PROCESSOTAF, SECAO, RELATOR, DESCRITORES, TEMA, DATAACC
#         "nome":           "Tribunal Central Administrativo Sul",
#         "prefixo":        "jtcampca",  # confirmado
#         "hash_livre":     "afdac708791e461b802568720050bb7a",  # confirmado
#         "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
#         "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
#         "hash_descritor": None,  # TCAS nao tem pesquisa por descritor
#     },
#     "tcan": {
#         # TCAN usa prefixo jtcn (nao jtcan) e nao tem pesquisa por descritor
#         "nome":           "Tribunal Central Administrativo Norte",
#         "prefixo":        "jtcn",  # confirmado — prefixo real e jtcn
#         "hash_livre":     "afdac708791e461b802568720050bb7a",  # confirmado
#         "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
#         "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
#         "hash_descritor": None,  # TCAN nao tem pesquisa por descritor
#     },
# }

# # Campos disponíveis na pesquisa por campo
# CAMPOS_DISPONIVEIS = [
#     "PROCESSO", "C1", "RELATOR", "DESCRITORES", "NUMDOC", "APENSO",
#     "DATAAC", "NUMUNICO", "VOTACAO", "REFPUBL", "TRIBREC", "PROCREC",
#     "DATA", "TEXTOINT", "RECURSO", "PROCREF", "PRIVAC", "MEIOPROCESSUAL",
#     "DECISAO", "INDEVENTUAIS", "AREATEMATICA", "LEGNACIONAL",
#     "LEGCOMUNITARIA", "LEGESTRANGEIRA", "REFINTERNAC", "JURNACIONAL",
#     "JURINTERNAC", "JURESTRANGEIRA", "SUMARIO", "DECTINTEGRAL",
# ]

# OPERADORES_CAMPO = ["=", "<", ">", "<=", ">="]
# OPERADORES_TERMOS = ["AND", "OR", "NEAR", "SENTENCE", "PARAGRAPH"]

# BASE_URL = "https://www.dgsi.pt"

# HEADERS = {
#     "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                        "AppleWebKit/537.36 (KHTML, like Gecko) "
#                        "Chrome/120.0.0.0 Safari/537.36",
#     "Accept":          "text/html,application/xhtml+xml",
#     "Accept-Language": "pt-PT,pt;q=0.9",
# }


# # ---------------------------------------------------------------------------
# # ITIJScraper
# # ---------------------------------------------------------------------------

# class ITIJScraper:
#     """
#     Pesquisa e extracção de acordaos do portal ITIJ (dgsi.pt).
#     Suporta os quatro tipos de pesquisa do formulário Lotus Domino.
#     """

#     def __init__(self, timeout: int = 15, delay: float = 1.0):
#         """
#         Args:
#             timeout: segundos de timeout por pedido HTTP
#             delay:   segundos de espera entre pedidos (respeitar o servidor)
#         """
#         self._timeout = timeout
#         self._delay   = delay
#         self._session = requests.Session()
#         self._session.headers.update(HEADERS)

#     # ------------------------------------------------------------------
#     # Pesquisa Livre
#     # ------------------------------------------------------------------

#     def pesquisar_livre(
#         self,
#         query: str,
#         tribunal: str = "tre",
#         max_resultados: int = 20,
#     ) -> list[dict]:
#         """
#         Pesquisa em linguagem natural com operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*.

#         Args:
#             query:          Ex: "despedimento ilicito AND justa causa"
#             tribunal:       Código do tribunal (ver TRIBUNAIS)
#             max_resultados: Número máximo de resultados

#         Returns:
#             Lista de dicts com processo, data, relator, descritores, url, tribunal
#         """
#         hash_key = "hash_livre"
#         dados    = {"Query": query}
#         return self._pesquisar(tribunal, hash_key, dados, max_resultados)

#     # ------------------------------------------------------------------
#     # Pesquisa por Termos
#     # ------------------------------------------------------------------

#     def pesquisar_termos(
#         self,
#         termos: list[str],
#         operadores: list[str] | None = None,
#         tribunal: str = "tre",
#         max_resultados: int = 20,
#     ) -> list[dict]:
#         """
#         Pesquisa com até 4 termos e operadores entre eles.

#         Args:
#             termos:     Lista de 1 a 4 termos. Ex: ["despedimento", "justa causa"]
#             operadores: Lista de operadores entre termos (len = len(termos)-1).
#                         Valores: AND, OR, NEAR, SENTENCE, PARAGRAPH.
#                         Default: AND entre todos.
#             tribunal:   Código do tribunal
#             max_resultados: Número máximo de resultados

#         Exemplo:
#             pesquisar_termos(
#                 termos=["despedimento", "justa causa", "procedimento disciplinar"],
#                 operadores=["AND", "NEAR"]
#             )
#         """
#         if not termos:
#             raise ValueError("É necessário pelo menos um termo.")
#         if len(termos) > 4:
#             raise ValueError("Máximo de 4 termos na pesquisa por termos.")

#         if operadores is None:
#             operadores = ["AND"] * (len(termos) - 1)

#         # Preencher até 4 termos/operadores
#         dados = {}
#         for i, termo in enumerate(termos[:4], 1):
#             dados[f"termo{i}"] = termo

#         for i, op in enumerate(operadores[:3], 2):
#             if op not in OPERADORES_TERMOS:
#                 raise ValueError(f"Operador '{op}' inválido. Use: {OPERADORES_TERMOS}")
#             dados[f"operador{i}"]              = op
#             dados[f"%%Surrogate_operador{i}"]  = "1"

#         # Campos vazios para os termos não usados
#         for i in range(len(termos) + 1, 5):
#             dados[f"termo{i}"] = ""

#         return self._pesquisar(tribunal, "hash_termos", dados, max_resultados)

#     # ------------------------------------------------------------------
#     # Pesquisa por Campo
#     # ------------------------------------------------------------------

#     def pesquisar_campo(
#         self,
#         campo: str,
#         operador: str,
#         valor: str,
#         tribunal: str = "tre",
#         max_resultados: int = 20,
#     ) -> list[dict]:
#         """
#         Pesquisa num campo específico do acórdão.

#         Args:
#             campo:    Campo a pesquisar. Ex: "DESCRITORES", "RELATOR",
#                       "PROCESSO", "DATAAC", "SUMARIO", "TEXTOINT"
#                       (ver CAMPOS_DISPONIVEIS para lista completa)
#             operador: "=", "<", ">", "<=", ">="
#             valor:    Valor a pesquisar. Ex: "DESPEDIMENTO ILICITO", "2024-01-01"
#             tribunal: Código do tribunal
#             max_resultados: Número máximo de resultados

#         Exemplos:
#             pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")
#             pesquisar_campo("RELATOR", "=", "PAULA DO PACO")
#             pesquisar_campo("DATAAC", ">=", "01/01/2024")
#             pesquisar_campo("SUMARIO", "=", "justa causa")
#         """
#         if campo not in CAMPOS_DISPONIVEIS:
#             raise ValueError(
#                 f"Campo '{campo}' inválido.\nCampos disponíveis: {CAMPOS_DISPONIVEIS}"
#             )
#         if operador not in OPERADORES_CAMPO:
#             raise ValueError(
#                 f"Operador '{operador}' inválido. Use: {OPERADORES_CAMPO}"
#             )

#         dados = {
#             "campo":              campo,
#             "%%Surrogate_campo":  "1",
#             "operador":           operador,
#             "%%Surrogate_operador": "1",
#             "valor":              valor,
#         }
#         return self._pesquisar(tribunal, "hash_campo", dados, max_resultados)

#     # ------------------------------------------------------------------
#     # Pesquisa por Descritor
#     # ------------------------------------------------------------------

#     def pesquisar_descritor(
#         self,
#         query: str,
#         tribunal: str = "tre",
#         max_resultados: int = 20,
#     ) -> list[dict]:
#         """
#         Pesquisa na lista de descritores jurídicos do ITIJ.

#         NOTA: Esta pesquisa devolve uma lista de DESCRITORES (não de acordaos).
#         O utilizador escolhe um descritor e depois usa pesquisar_campo() para
#         encontrar os acordaos com esse descritor.

#         Fluxo tipico:
#             1. descritores = scraper.pesquisar_descritor("despedimento")
#             2. # utilizador escolhe: "DESPEDIMENTO ILICITO"
#             3. acordaos = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")

#         Args:
#             query:    Termo a pesquisar nos descritores. Ex: "despedimento", "prescricao"
#             tribunal: Codigo do tribunal
#             max_resultados: Numero maximo de descritores a devolver

#         Returns:
#             Lista de dicts com:
#                 descritor_principal:   str
#                 descritores_relacionados: list[str]
#         """
#         cfg      = TRIBUNAIS[tribunal]
#         hash_val = cfg.get("hash_descritor")
#         if hash_val is None:
#             raise ValueError(f"Hash do descritor nao configurado para {cfg['nome']}")

#         post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"

#         try:
#             time.sleep(self._delay)
#             resp = self._session.post(
#                 post_url,
#                 data={"Query": query},
#                 timeout=self._timeout,
#                 allow_redirects=True,
#             )
#             if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
#                 resp.encoding = "utf-8"
#             resp.raise_for_status()
#         except requests.RequestException as e:
#             raise RuntimeError(f"Erro na pesquisa de descritores: {e}")

#         return self._parse_descritores(resp.text, max_resultados)

#     def pesquisar_acordaos_por_descritor(
#         self,
#         descritor: str,
#         tribunal: str = "tre",
#         max_resultados: int = 20,
#     ) -> list[dict]:
#         """
#         Atalho conveniente: pesquisa acórdãos directamente por descritor exacto.
#         Equivalente a pesquisar_campo("DESCRITORES", "=", descritor).

#         Args:
#             descritor:      Descritor exacto. Ex: "DESPEDIMENTO ILÍCITO"
#             tribunal:       Codigo do tribunal
#             max_resultados: Numero maximo de resultados
#         """
#         return self.pesquisar_campo(
#             campo="DESCRITORES",
#             operador="=",
#             valor=descritor,
#             tribunal=tribunal,
#             max_resultados=max_resultados,
#         )

#     # ------------------------------------------------------------------
#     # Pesquisa em múltiplos tribunais
#     # ------------------------------------------------------------------

#     def pesquisar_multiplos(
#         self,
#         query: str,
#         tipo: str = "livre",
#         tribunais: list[str] | None = None,
#         max_por_tribunal: int = 10,
#     ) -> list[dict]:
#         """
#         Pesquisa em vários tribunais e agrega os resultados.

#         Args:
#             query:            Termos de pesquisa
#             tipo:             "livre" | "descritor" (os outros tipos requerem
#                               parâmetros específicos — usar directamente)
#             tribunais:        Lista de códigos (None = todos os tribunais com hashes)
#             max_por_tribunal: Máximo de resultados por tribunal
#         """
#         if tribunais is None:
#             # Só tribunais com hashes confirmados
#             tribunais = [
#                 t for t, cfg in TRIBUNAIS.items()
#                 if cfg.get(f"hash_{tipo}") is not None
#             ]

#         todos = []
#         for t in tribunais:
#             try:
#                 if tipo == "livre":
#                     resultados = self.pesquisar_livre(query, t, max_por_tribunal)
#                 elif tipo == "descritor":
#                     resultados = self.pesquisar_descritor(query, t, max_por_tribunal)
#                 else:
#                     raise ValueError(f"Tipo '{tipo}' não suportado em pesquisa múltipla.")
#                 todos.extend(resultados)
#                 print(f"  {TRIBUNAIS[t]['nome']}: {len(resultados)} resultados")
#             except Exception as e:
#                 print(f"  {TRIBUNAIS[t]['nome']}: erro — {e}")

#         return todos

#     # ------------------------------------------------------------------
#     # Extracção de texto
#     # ------------------------------------------------------------------

#     def descarregar_texto(self, url: str) -> str:
#         """
#         Descarrega e extrai o texto completo de um acórdão.

#         Args:
#             url: URL do acórdão (relativo ou absoluto)

#         Returns:
#             Texto limpo do acórdão (sem HTML)
#         """
#         if url.startswith("/"):
#             url = BASE_URL + url

#         try:
#             time.sleep(self._delay)
#             resp = self._session.get(url, timeout=self._timeout)
#             # ITIJ usa ISO-8859-1 / Windows-1252 — forcar encoding correcto
#             resp.encoding = "iso-8859-1"
#             resp.raise_for_status()
#         except requests.RequestException as e:
#             raise RuntimeError(f"Erro ao descarregar acordao: {e}")

#         return self._parse_acordao(resp.text)

#     def descarregar_para_ficheiro(self, url: str, path: str) -> str:
#         """
#         Descarrega texto de um acórdão e guarda num ficheiro .txt.
#         """
#         texto = self.descarregar_texto(url)
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(texto)
#         return path

#     # ------------------------------------------------------------------
#     # Utilitários
#     # ------------------------------------------------------------------

#     def confirmar_hashes(self, tribunal: str) -> dict:
#         """
#         Descobre automaticamente os hashes dos 4 formulários de um tribunal
#         abrindo cada página de pesquisa e lendo o action do form.

#         Útil para configurar tribunais cujos hashes ainda estão como None.

#         Args:
#             tribunal: Código do tribunal (ex: "trl")

#         Returns:
#             Dict com os 4 hashes descobertos
#         """
#         cfg     = TRIBUNAIS[tribunal]
#         prefixo = cfg["prefixo"]
#         tipos   = {
#             "hash_livre":     "Pesquisa+Livre",
#             "hash_termos":    "Pesquisa+Termos",
#             "hash_campo":     "Pesquisa+Campo",
#             "hash_descritor": "Pesquisa+Descritor",
#         }
#         hashes = {}
#         for chave, nome_form in tipos.items():
#             url = f"{BASE_URL}/{prefixo}.nsf/{nome_form}?OpenForm"
#             try:
#                 time.sleep(self._delay)
#                 resp = self._session.get(url, timeout=self._timeout)
#                 soup = BeautifulSoup(resp.text, "html.parser")
#                 form = soup.find("form")
#                 if form and form.get("action"):
#                     # /jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument
#                     action = form["action"]
#                     match  = re.search(r"/[^/]+\.nsf/([a-f0-9]+)\?", action)
#                     if match:
#                         hashes[chave] = match.group(1)
#                     else:
#                         hashes[chave] = None
#                 else:
#                     hashes[chave] = None
#             except Exception as e:
#                 hashes[chave] = None
#                 print(f"  Erro ao obter {nome_form}: {e}")

#         return hashes

#     # ------------------------------------------------------------------
#     # Métodos internos
#     # ------------------------------------------------------------------

#     def _pesquisar(
#         self,
#         tribunal: str,
#         hash_key: str,
#         dados: dict,
#         max_resultados: int,
#     ) -> list[dict]:
#         """Executa o POST e faz parse dos resultados."""
#         if tribunal not in TRIBUNAIS:
#             raise ValueError(
#                 f"Tribunal '{tribunal}' desconhecido. "
#                 f"Opções: {list(TRIBUNAIS.keys())}"
#             )

#         cfg  = TRIBUNAIS[tribunal]
#         hash_val = cfg.get(hash_key)

#         if hash_val is None:
#             raise ValueError(
#                 f"Hash do formulário '{hash_key}' não configurado para "
#                 f"'{cfg['nome']}'. Usa confirmar_hashes('{tribunal}') para "
#                 f"descobrir os hashes automaticamente."
#             )

#         post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"

#         try:
#             time.sleep(self._delay)
#             resp = self._session.post(
#                 post_url,
#                 data=dados,
#                 timeout=self._timeout,
#                 allow_redirects=True,
#             )
#             # Servidor declara UTF-8 — usar encoding do header
#             if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
#                 resp.encoding = "utf-8"
#             resp.raise_for_status()
#         except requests.RequestException as e:
#             raise RuntimeError(f"Erro na pesquisa ITIJ: {e}")

#         return self._parse_lista(resp.text, tribunal, max_resultados)

#     def _parse_descritores(self, html: str, max_resultados: int) -> list[dict]:
#         """Extrai lista de descritores do HTML de resultados da pesquisa por descritor."""
#         soup    = BeautifulSoup(html, "html.parser")
#         results = []

#         for tr in soup.find_all("tr", valign="top"):
#             tds = tr.find_all("td")
#             # Estrutura: icone | descritor principal | descritores relacionados
#             if len(tds) < 3:
#                 continue

#             # Col 1 — descritor principal (tem link)
#             link = tds[1].find("a")
#             if not link:
#                 continue
#             desc_principal = link.get_text(strip=True)
#             if not desc_principal:
#                 continue

#             # Col 2 — descritores relacionados
#             relacionados_raw = tds[2].get_text(separator="\n", strip=True)
#             relacionados = [
#                 d.strip()
#                 for d in relacionados_raw.split("\n")
#                 if d.strip()
#             ]

#             results.append({
#                 "descritor_principal":     desc_principal,
#                 "descritores_relacionados": relacionados,
#             })

#             if len(results) >= max_resultados:
#                 break

#         return results

#     def _parse_lista(
#         self,
#         html: str,
#         tribunal: str,
#         max_resultados: int,
#     ) -> list[dict]:
#         """Extrai lista de acordaos do HTML de resultados.

#         O ITIJ tem dois formatos:
#         - Lista principal (por ano): 4 cols — data | processo | relator | descritores
#         - Resultados de pesquisa:    5 cols — icone | data | processo | relator | descritores
#         A data pode usar / ou - como separador.
#         """
#         soup    = BeautifulSoup(html, "html.parser")
#         nome_t  = TRIBUNAIS[tribunal]["nome"]
#         results = []

#         for tr in soup.find_all("tr", valign="top"):
#             tds = tr.find_all("td")
#             if len(tds) < 4:
#                 continue

#             # Detectar formato pela primeira coluna:
#             # pesquisa (5 cols) — col 0 e icone sem texto util
#             # lista    (4 cols) — col 0 e a data
#             if len(tds) >= 5:
#                 idx_data, idx_proc, idx_rel, idx_desc = 1, 2, 3, 4
#             else:
#                 idx_data, idx_proc, idx_rel, idx_desc = 0, 1, 2, 3

#             data_text = tds[idx_data].get_text(strip=True)
#             if not re.match(r"\d{2}[/-]\d{2}[/-]\d{4}", data_text):
#                 continue

#             link = tds[idx_proc].find("a")
#             if not link:
#                 continue

#             processo = link.get_text(strip=True)
#             href     = link.get("href", "")
#             # Remover parametros &Highlight do URL
#             url_base = href.split("&")[0] if "&" in href else href
#             url      = url_base if url_base.startswith("http") else BASE_URL + url_base
#             relator  = tds[idx_rel].get_text(strip=True)

#             descritores = [
#                 d.strip()
#                 for d in tds[idx_desc].get_text(separator="\n", strip=True).split("\n")
#                 if d.strip()
#             ]

#             results.append({
#                 "processo":    processo,
#                 "data":        data_text,
#                 "relator":     relator,
#                 "descritores": descritores,
#                 "url":         url,
#                 "tribunal":    nome_t,
#                 "tribunal_id": tribunal,
#             })

#             if len(results) >= max_resultados:
#                 break

#         return results

#     def _parse_acordao(self, html: str) -> str:
#         """Extrai texto limpo do HTML de um acórdão individual."""
#         soup = BeautifulSoup(html, "html.parser")

#         for tag in soup(["script", "style", "head"]):
#             tag.decompose()

#         texto  = soup.get_text(separator="\n")
#         linhas = [l.strip() for l in texto.splitlines() if l.strip()]

#         ignorar = {
#             "anterior", "seguinte", "principal",
#             "pesquisa livre", "por termos", "por campo", "por descritor",
#         }
#         linhas = [l for l in linhas if l.lower() not in ignorar]

#         return "\n".join(linhas)

"""
itij_scraper.py

Scraper para o portal ITIJ (dgsi.pt) — pesquisa e extracção de acórdãos.

Quatro tipos de pesquisa suportados (confirmados para Tribunal da Relação de Évora):
    livre      — texto em linguagem natural + operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*
    termos     — até 4 termos com operadores entre eles (AND/OR/NEAR/SENTENCE/PARAGRAPH)
    campo      — pesquisa num campo específico (PROCESSO, RELATOR, DESCRITORES, SUMARIO, etc.)
    descritor  — pesquisa na lista de descritores jurídicos (mesmo interface que livre)

Tribunais suportados:
    tre   → Tribunal da Relação de Évora      (hashes confirmados)
    trl   → Tribunal da Relação de Lisboa
    trp   → Tribunal da Relação do Porto
    trc   → Tribunal da Relação de Coimbra
    trg   → Tribunal da Relação de Guimarães
    stj   → Supremo Tribunal de Justiça
    sta   → Supremo Tribunal Administrativo
    tcas  → Tribunal Central Administrativo Sul
    tcan  → Tribunal Central Administrativo Norte

Nota: os form_hash dos tribunais que não o TRE precisam de ser confirmados
abrindo /jXXX.nsf/Pesquisa+Livre?OpenForm e verificando o action do form.

Dependências:
    pip install requests beautifulsoup4

Uso:
    from itij_scraper import ITIJScraper

    scraper = ITIJScraper()

    # Pesquisa livre
    resultados = scraper.pesquisar_livre("despedimento ilicito justa causa", tribunal="tre")

    # Pesquisa por termos
    resultados = scraper.pesquisar_termos(
        termos=["despedimento", "justa causa"],
        operadores=["AND"],
        tribunal="tre"
    )

    # Pesquisa por campo
    resultados = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO", tribunal="tre")
    resultados = scraper.pesquisar_campo("RELATOR", "=", "PAULA DO PACO", tribunal="tre")
    resultados = scraper.pesquisar_campo("DATAAC", ">=", "2024-01-01", tribunal="tre")

    # Pesquisa por descritor
    resultados = scraper.pesquisar_descritor("despedimento ilicito", tribunal="tre")

    # Descarregar texto de um acordao
    texto = scraper.descarregar_texto(resultados[0]["url"])
"""

import re
import time

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Configuracao dos tribunais
# Hashes confirmados para TRE — os restantes precisam de verificacao
# ---------------------------------------------------------------------------

# Hashes partilhados — TRE, TRP, TRC, TRG usam o mesmo template Lotus Domino
_H_SHARED = {
    "hash_livre":     "8f8d2b7e72244bca80256879006d6594",
    "hash_termos":    "3d2a49955a5bf67080256879006d6595",
    "hash_campo":     "6d54606360981c7380256879006d6592",
    "hash_descritor": "b8f3314245b23f0780256879006d6593",
}

TRIBUNAIS = {
    "tre": {
        "nome":    "Tribunal da Relação de Évora",
        "prefixo": "jtre",
        **_H_SHARED,  # confirmado
    },
    "trl": {
        "nome":           "Tribunal da Relação de Lisboa",
        "prefixo":        "jtrl",
        "hash_livre":     "14adab75c943f8c480256879006e5bda",  # confirmado
        "hash_termos":    "280913ebea31cc6f80256879006e5bdb",  # confirmado
        "hash_campo":     "86e7be720738947280256879006e5bd8",  # confirmado
        "hash_descritor": "a37a3990f3f371db80256879006e5bd9",  # confirmado
    },
    "trp": {
        "nome":    "Tribunal da Relação do Porto",
        "prefixo": "jtrp",
        **_H_SHARED,  # confirmado (mesmo template que TRE)
    },
    "trc": {
        "nome":    "Tribunal da Relação de Coimbra",
        "prefixo": "jtrc",
        **_H_SHARED,  # confirmado (mesmo template que TRE)
    },
    "trg": {
        "nome":    "Tribunal da Relação de Guimarães",
        "prefixo": "jtrg",
        **_H_SHARED,  # confirmado (mesmo template que TRE)
    },
    "stj": {
        "nome":           "Supremo Tribunal de Justiça",
        "prefixo":        "jstj",
        "hash_livre":     "f83eef66ec4efcb780256879006bc015",  # confirmado
        "hash_termos":    "cde84ff44faf0d0680256879006bc016",  # confirmado
        "hash_campo":     "38f33c44b0c8358280256879006bc013",  # confirmado
        "hash_descritor": "9b28c5162249339d80256879006bc014",  # confirmado
    },
    "sta": {
        "nome":           "Supremo Tribunal Administrativo",
        "prefixo":        "jsta",
        "hash_livre":     "02eae0bd4de5026e80256b480065970d",  # confirmado
        "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
        "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
        "hash_descritor": "1ea881265b7d747c80256879004cbca8",  # confirmado
    },
    "tcas": {
        # TCAS — Pareceres MP Contencioso Administrativo (3975 doc.)
        # Usa os mesmos hashes que TCAN — template partilhado
        # Sem pesquisa por descritor
        # Campos proprios: CONTENCIOSO, PROCESSUAL, DATAAC, PROCESSO,
        #   PROCESSOTAF, SECAO, RELATOR, DESCRITORES, TEMA, DATAACC
        "nome":           "Tribunal Central Administrativo Sul",
        "prefixo":        "jtca",  # confirmado
        "hash_livre":     "afdac708791e461b802568720050bb7a",  # confirmado
        "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
        "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
        "hash_descritor": None,  # TCAS nao tem pesquisa por descritor
    },
    "tcan": {
        # TCAN usa prefixo jtcn (nao jtcan) e nao tem pesquisa por descritor
        "nome":           "Tribunal Central Administrativo Norte",
        "prefixo":        "jtcn",  # confirmado — prefixo real e jtcn
        "hash_livre":     "afdac708791e461b802568720050bb7a",  # confirmado
        "hash_termos":    "182c23acfa36219d802568720050bb7b",  # confirmado
        "hash_campo":     "4e0ebda5744f203f802568720050bb79",  # confirmado
        "hash_descritor": None,  # TCAN nao tem pesquisa por descritor
    },
}

# Campos disponíveis na pesquisa por campo
CAMPOS_DISPONIVEIS = [
    "PROCESSO", "C1", "RELATOR", "DESCRITORES", "NUMDOC", "APENSO",
    "DATAAC", "NUMUNICO", "VOTACAO", "REFPUBL", "TRIBREC", "PROCREC",
    "DATA", "TEXTOINT", "RECURSO", "PROCREF", "PRIVAC", "MEIOPROCESSUAL",
    "DECISAO", "INDEVENTUAIS", "AREATEMATICA", "LEGNACIONAL",
    "LEGCOMUNITARIA", "LEGESTRANGEIRA", "REFINTERNAC", "JURNACIONAL",
    "JURINTERNAC", "JURESTRANGEIRA", "SUMARIO", "DECTINTEGRAL",
]

OPERADORES_CAMPO = ["=", "<", ">", "<=", ">="]
OPERADORES_TERMOS = ["AND", "OR", "NEAR", "SENTENCE", "PARAGRAPH"]

BASE_URL = "https://www.dgsi.pt"

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml",
    "Accept-Language": "pt-PT,pt;q=0.9",
}


# ---------------------------------------------------------------------------
# ITIJScraper
# ---------------------------------------------------------------------------

class ITIJScraper:
    """
    Pesquisa e extracção de acordaos do portal ITIJ (dgsi.pt).
    Suporta os quatro tipos de pesquisa do formulário Lotus Domino.
    """

    def __init__(self, timeout: int = 15, delay: float = 1.0):
        """
        Args:
            timeout: segundos de timeout por pedido HTTP
            delay:   segundos de espera entre pedidos (respeitar o servidor)
        """
        self._timeout = timeout
        self._delay   = delay
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    # ------------------------------------------------------------------
    # Pesquisa Livre
    # ------------------------------------------------------------------

    def pesquisar_livre(
        self,
        query: str,
        tribunal: str = "tre",
        max_resultados: int = 20,
        start: int = 1,
    ) -> dict:
        """
        Pesquisa em linguagem natural com operadores AND/OR/NOT/NEAR/SENTENCE/PARAGRAPH/*.

        Args:
            query:          Ex: "despedimento ilicito AND justa causa"
            tribunal:       Código do tribunal (ver TRIBUNAIS)
            max_resultados: Número máximo de resultados

        Returns:
            Lista de dicts com processo, data, relator, descritores, url, tribunal
        """
        hash_key = "hash_livre"
        dados    = {"Query": query}
        return self._pesquisar(tribunal, hash_key, dados, max_resultados, start)

    # ------------------------------------------------------------------
    # Pesquisa por Termos
    # ------------------------------------------------------------------

    def pesquisar_termos(
        self,
        termos: list[str],
        operadores: list[str] | None = None,
        tribunal: str = "tre",
        max_resultados: int = 20,
        start: int = 1,
    ) -> dict:
        """
        Pesquisa com até 4 termos e operadores entre eles.

        Args:
            termos:     Lista de 1 a 4 termos. Ex: ["despedimento", "justa causa"]
            operadores: Lista de operadores entre termos (len = len(termos)-1).
                        Valores: AND, OR, NEAR, SENTENCE, PARAGRAPH.
                        Default: AND entre todos.
            tribunal:   Código do tribunal
            max_resultados: Número máximo de resultados

        Exemplo:
            pesquisar_termos(
                termos=["despedimento", "justa causa", "procedimento disciplinar"],
                operadores=["AND", "NEAR"]
            )
        """
        if not termos:
            raise ValueError("É necessário pelo menos um termo.")
        if len(termos) > 4:
            raise ValueError("Máximo de 4 termos na pesquisa por termos.")

        if operadores is None:
            operadores = ["AND"] * (len(termos) - 1)

        # Preencher até 4 termos/operadores
        dados = {}
        for i, termo in enumerate(termos[:4], 1):
            dados[f"termo{i}"] = termo

        for i, op in enumerate(operadores[:3], 2):
            if op not in OPERADORES_TERMOS:
                raise ValueError(f"Operador '{op}' inválido. Use: {OPERADORES_TERMOS}")
            dados[f"operador{i}"]              = op
            dados[f"%%Surrogate_operador{i}"]  = "1"

        # Campos vazios para os termos não usados
        for i in range(len(termos) + 1, 5):
            dados[f"termo{i}"] = ""

        return self._pesquisar(tribunal, "hash_termos", dados, max_resultados, start)

    # ------------------------------------------------------------------
    # Pesquisa por Campo
    # ------------------------------------------------------------------

    def pesquisar_campo(
        self,
        campo: str,
        operador: str,
        valor: str,
        tribunal: str = "tre",
        max_resultados: int = 20,
        start: int = 1,
    ) -> dict:
        """
        Pesquisa num campo específico do acórdão.

        Args:
            campo:    Campo a pesquisar. Ex: "DESCRITORES", "RELATOR",
                      "PROCESSO", "DATAAC", "SUMARIO", "TEXTOINT"
                      (ver CAMPOS_DISPONIVEIS para lista completa)
            operador: "=", "<", ">", "<=", ">="
            valor:    Valor a pesquisar. Ex: "DESPEDIMENTO ILICITO", "2024-01-01"
            tribunal: Código do tribunal
            max_resultados: Número máximo de resultados

        Exemplos:
            pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")
            pesquisar_campo("RELATOR", "=", "PAULA DO PACO")
            pesquisar_campo("DATAAC", ">=", "01/01/2024")
            pesquisar_campo("SUMARIO", "=", "justa causa")
        """
        if campo not in CAMPOS_DISPONIVEIS:
            raise ValueError(
                f"Campo '{campo}' inválido.\nCampos disponíveis: {CAMPOS_DISPONIVEIS}"
            )
        if operador not in OPERADORES_CAMPO:
            raise ValueError(
                f"Operador '{operador}' inválido. Use: {OPERADORES_CAMPO}"
            )

        dados = {
            "campo":              campo,
            "%%Surrogate_campo":  "1",
            "operador":           operador,
            "%%Surrogate_operador": "1",
            "valor":              valor,
        }
        return self._pesquisar(tribunal, "hash_campo", dados, max_resultados, start)

    # ------------------------------------------------------------------
    # Pesquisa por Descritor
    # ------------------------------------------------------------------

    def pesquisar_descritor(
        self,
        query: str,
        tribunal: str = "tre",
        max_resultados: int = 20,
        start: int = 1,
    ) -> dict:
        """
        Pesquisa na lista de descritores jurídicos do ITIJ.

        NOTA: Esta pesquisa devolve uma lista de DESCRITORES (não de acordaos).
        O utilizador escolhe um descritor e depois usa pesquisar_campo() para
        encontrar os acordaos com esse descritor.

        Fluxo tipico:
            1. descritores = scraper.pesquisar_descritor("despedimento")
            2. # utilizador escolhe: "DESPEDIMENTO ILICITO"
            3. acordaos = scraper.pesquisar_campo("DESCRITORES", "=", "DESPEDIMENTO ILICITO")

        Args:
            query:    Termo a pesquisar nos descritores. Ex: "despedimento", "prescricao"
            tribunal: Codigo do tribunal
            max_resultados: Numero maximo de descritores a devolver

        Returns:
            Lista de dicts com:
                descritor_principal:   str
                descritores_relacionados: list[str]
        """
        cfg      = TRIBUNAIS[tribunal]
        hash_val = cfg.get("hash_descritor")
        if hash_val is None:
            raise ValueError(f"Hash do descritor nao configurado para {cfg['nome']}")

        post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"

        try:
            time.sleep(self._delay)
            resp = self._session.post(
                post_url,
                data={"Query": query},
                timeout=self._timeout,
                allow_redirects=True,
            )
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Erro na pesquisa de descritores: {e}")

        return self._parse_descritores(resp.text, max_resultados)

    def pesquisar_acordaos_por_descritor(
        self,
        descritor: str,
        tribunal: str = "tre",
        max_resultados: int = 20,
    ) -> list[dict]:
        """
        Atalho conveniente: pesquisa acórdãos directamente por descritor exacto.
        Equivalente a pesquisar_campo("DESCRITORES", "=", descritor).

        Args:
            descritor:      Descritor exacto. Ex: "DESPEDIMENTO ILÍCITO"
            tribunal:       Codigo do tribunal
            max_resultados: Numero maximo de resultados
        """
        return self.pesquisar_campo(
            campo="DESCRITORES",
            operador="=",
            valor=descritor,
            tribunal=tribunal,
            max_resultados=max_resultados,
        )

    # ------------------------------------------------------------------
    # Pesquisa em múltiplos tribunais
    # ------------------------------------------------------------------

    def pesquisar_multiplos(
        self,
        query: str,
        tipo: str = "livre",
        tribunais: list[str] | None = None,
        max_por_tribunal: int = 10,
    ) -> list[dict]:
        """
        Pesquisa em vários tribunais e agrega os resultados.

        Args:
            query:            Termos de pesquisa
            tipo:             "livre" | "descritor" (os outros tipos requerem
                              parâmetros específicos — usar directamente)
            tribunais:        Lista de códigos (None = todos os tribunais com hashes)
            max_por_tribunal: Máximo de resultados por tribunal
        """
        if tribunais is None:
            # Só tribunais com hashes confirmados
            tribunais = [
                t for t, cfg in TRIBUNAIS.items()
                if cfg.get(f"hash_{tipo}") is not None
            ]

        todos = []
        for t in tribunais:
            try:
                if tipo == "livre":
                    resultados = self.pesquisar_livre(query, t, max_por_tribunal)
                elif tipo == "descritor":
                    resultados = self.pesquisar_descritor(query, t, max_por_tribunal)
                else:
                    raise ValueError(f"Tipo '{tipo}' não suportado em pesquisa múltipla.")
                todos.extend(resultados)
                print(f"  {TRIBUNAIS[t]['nome']}: {len(resultados)} resultados")
            except Exception as e:
                print(f"  {TRIBUNAIS[t]['nome']}: erro — {e}")

        return todos

    # ------------------------------------------------------------------
    # Extracção de texto
    # ------------------------------------------------------------------

    def descarregar_texto(self, url: str) -> str:
        """
        Descarrega e extrai o texto completo de um acórdão.

        Args:
            url: URL do acórdão (relativo ou absoluto)

        Returns:
            Texto limpo do acórdão (sem HTML)
        """
        if url.startswith("/"):
            url = BASE_URL + url

        try:
            time.sleep(self._delay)
            resp = self._session.get(url, timeout=self._timeout)
            # ITIJ usa ISO-8859-1 / Windows-1252 — forcar encoding correcto
            resp.encoding = "iso-8859-1"
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Erro ao descarregar acordao: {e}")

        return self._parse_acordao(resp.text)

    def descarregar_para_ficheiro(self, url: str, path: str) -> str:
        """
        Descarrega texto de um acórdão e guarda num ficheiro .txt.
        """
        texto = self.descarregar_texto(url)
        with open(path, "w", encoding="utf-8") as f:
            f.write(texto)
        return path

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def confirmar_hashes(self, tribunal: str) -> dict:
        """
        Descobre automaticamente os hashes dos 4 formulários de um tribunal
        abrindo cada página de pesquisa e lendo o action do form.

        Útil para configurar tribunais cujos hashes ainda estão como None.

        Args:
            tribunal: Código do tribunal (ex: "trl")

        Returns:
            Dict com os 4 hashes descobertos
        """
        cfg     = TRIBUNAIS[tribunal]
        prefixo = cfg["prefixo"]
        tipos   = {
            "hash_livre":     "Pesquisa+Livre",
            "hash_termos":    "Pesquisa+Termos",
            "hash_campo":     "Pesquisa+Campo",
            "hash_descritor": "Pesquisa+Descritor",
        }
        hashes = {}
        for chave, nome_form in tipos.items():
            url = f"{BASE_URL}/{prefixo}.nsf/{nome_form}?OpenForm"
            try:
                time.sleep(self._delay)
                resp = self._session.get(url, timeout=self._timeout)
                soup = BeautifulSoup(resp.text, "html.parser")
                form = soup.find("form")
                if form and form.get("action"):
                    # /jtre.nsf/8f8d2b7e72244bca80256879006d6594?CreateDocument
                    action = form["action"]
                    match  = re.search(r"/[^/]+\.nsf/([a-f0-9]+)\?", action)
                    if match:
                        hashes[chave] = match.group(1)
                    else:
                        hashes[chave] = None
                else:
                    hashes[chave] = None
            except Exception as e:
                hashes[chave] = None
                print(f"  Erro ao obter {nome_form}: {e}")

        return hashes

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _pesquisar(
        self,
        tribunal: str,
        hash_key: str,
        dados: dict,
        max_resultados: int,
        start: int = 1,
    ) -> dict:
        """Executa o POST e faz parse dos resultados."""
        if tribunal not in TRIBUNAIS:
            raise ValueError(
                f"Tribunal '{tribunal}' desconhecido. "
                f"Opções: {list(TRIBUNAIS.keys())}"
            )

        cfg  = TRIBUNAIS[tribunal]
        hash_val = cfg.get(hash_key)

        if hash_val is None:
            raise ValueError(
                f"Hash do formulário '{hash_key}' não configurado para "
                f"'{cfg['nome']}'. Usa confirmar_hashes('{tribunal}') para "
                f"descobrir os hashes automaticamente."
            )

        post_url = f"{BASE_URL}/{cfg['prefixo']}.nsf/{hash_val}?CreateDocument"
        if start > 1:
            post_url += f"&Start={start}"

        try:
            time.sleep(self._delay)
            resp = self._session.post(
                post_url,
                data=dados,
                timeout=self._timeout,
                allow_redirects=True,
            )
            # Servidor declara UTF-8 — usar encoding do header
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Erro na pesquisa ITIJ: {e}")

        return self._parse_lista(resp.text, tribunal, max_resultados)

    def _parse_descritores(self, html: str, max_resultados: int) -> dict:
        """Extrai lista de descritores do HTML de resultados da pesquisa por descritor."""
        soup    = BeautifulSoup(html, "html.parser")
        results = []

        for tr in soup.find_all("tr", valign="top"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            link = tds[1].find("a")
            if not link:
                continue
            desc_principal = link.get_text(strip=True)
            if not desc_principal:
                continue

            relacionados_raw = tds[2].get_text(separator="\n", strip=True)
            relacionados = [
                d.strip()
                for d in relacionados_raw.split("\n")
                if d.strip()
            ]

            results.append({
                "descritor_principal":     desc_principal,
                "descritores_relacionados": relacionados,
            })

            if len(results) >= max_resultados:
                break

        return {"resultados": results, "total": len(results)}

    def _parse_lista(
        self,
        html: str,
        tribunal: str,
        max_resultados: int,
    ) -> dict:
        """Extrai lista de acordaos do HTML de resultados.
        ...
        """
        soup    = BeautifulSoup(html, "html.parser")
        nome_t  = TRIBUNAIS[tribunal]["nome"]
        results = []

        # Extrair total de resultados (ex: "Documentos 1 a 20 de 154")
        total_count = 0
        text_nodes = soup.find_all(string=re.compile(r"de\s+\d+"))
        for node in text_nodes:
            # Padrão: "Documentos 1 a 20 de 154" ou "Document 1 to 20 of 154"
            match = re.search(r"(?:Documentos|Document)\s+\d+\s+(?:a|to)\s+\d+\s+(?:de|of)\s+([\d.]+)", node)
            if match:
                total_count = int(match.group(1).replace(".", ""))
                break
        
        # Fallback: se não encontrar o texto, o total é o número de resultados na página
        # (Acontece quando há apenas uma página)
        
        for tr in soup.find_all("tr", valign="top"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            # Detectar formato pela primeira coluna:
            # pesquisa (5 cols) — col 0 e icone sem texto util
            # lista    (4 cols) — col 0 e a data
            if len(tds) >= 5:
                idx_data, idx_proc, idx_rel, idx_desc = 1, 2, 3, 4
            else:
                idx_data, idx_proc, idx_rel, idx_desc = 0, 1, 2, 3

            data_text = tds[idx_data].get_text(strip=True)
            if not re.match(r"\d{2}[/-]\d{2}[/-]\d{4}", data_text):
                continue

            link = tds[idx_proc].find("a")
            if not link:
                continue

            processo = link.get_text(strip=True)
            href     = link.get("href", "")
            # Remover parametros &Highlight do URL
            url_base = href.split("&")[0] if "&" in href else href
            url      = url_base if url_base.startswith("http") else BASE_URL + url_base
            relator  = tds[idx_rel].get_text(strip=True)

            descritores = [
                d.strip()
                for d in tds[idx_desc].get_text(separator="\n", strip=True).split("\n")
                if d.strip()
            ]

            results.append({
                "processo":    processo,
                "data":        data_text,
                "relator":     relator,
                "descritores": descritores,
                "url":         url,
                "tribunal":    nome_t,
                "tribunal_id": tribunal,
            })

        if total_count == 0:
            total_count = len(results)

        return {"resultados": results, "total": total_count}

    def _parse_acordao(self, html: str) -> str:
        """Extrai texto limpo do HTML de um acórdão individual."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "head"]):
            tag.decompose()

        texto  = soup.get_text(separator="\n")
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]

        ignorar = {
            "anterior", "seguinte", "principal",
            "pesquisa livre", "por termos", "por campo", "por descritor",
        }
        linhas = [l for l in linhas if l.lower() not in ignorar]

        return "\n".join(linhas)