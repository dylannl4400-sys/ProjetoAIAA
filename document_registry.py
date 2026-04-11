# """
# document_registry.py

# Registo de documentos indexados com verificação de duplicados por hash SHA-256.

# Garante que o mesmo documento não é indexado duas vezes,
# independentemente do nome do ficheiro.

# Fluxo:
#     PDF recebido
#         ↓
#     calcular SHA-256 do ficheiro completo
#         ↓
#     verificar se esse hash já existe no ChromaDB (metadados dos chunks)
#         ↓
#     SE JÁ EXISTE → rejeitar com mensagem "documento já indexado"
#     SE NÃO EXISTE → renomear para {hash[:8]}_nomeOriginal.pdf → indexar
# """

# import hashlib
# import os
# import shutil


# # ---------------------------------------------------------------------------
# # Hash
# # ---------------------------------------------------------------------------

# def calcular_hash(path: str) -> str:
#     """
#     Calcula SHA-256 do conteúdo do ficheiro.
#     Retorna string hex de 64 caracteres.
#     Lê em blocos de 64KB para não carregar ficheiros grandes em memória.
#     """
#     h = hashlib.sha256()
#     with open(path, "rb") as f:
#         for bloco in iter(lambda: f.read(65536), b""):
#             h.update(bloco)
#     return h.hexdigest()


# def nome_com_hash(path: str, hash_completo: str) -> str:
#     """
#     Gera nome de ficheiro com prefixo dos primeiros 8 caracteres do hash.

#     Exemplo:
#         'acordao_01.pdf'  ->  'a3f8c2d1_acordao_01.pdf'
#     """
#     nome_original = os.path.basename(path)
#     prefixo       = hash_completo[:8]
#     return f"{prefixo}_{nome_original}"


# # ---------------------------------------------------------------------------
# # Verificacao de duplicados
# # ---------------------------------------------------------------------------

# def documento_ja_indexado(store, hash_doc: str) -> tuple:
#     """
#     Verifica se um documento com este hash ja foi indexado no ChromaDB.

#     Pesquisa nos metadados de todos os chunks o campo 'hash_documento'.
#     Devolve (True, nome_ficheiro) se encontrado, (False, "") caso contrario.

#     Nota: pesquisa com n=store.count() para cobrir todos os chunks.
#     Em bases de dados grandes isto pode ser lento -- considerar
#     manter um registo separado em SQLite na Fase 2.
#     """
#     total = store.count()
#     if total == 0:
#         return False, ""

#     try:
#         resultados = store.search("documento juridico", n=min(total, 1000))
#         for r in resultados:
#             if r["metadata"].get("hash_documento") == hash_doc:
#                 nome = r["metadata"].get("nome_ficheiro", "desconhecido")
#                 return True, nome
#         return False, ""
#     except Exception:
#         return False, ""


# # ---------------------------------------------------------------------------
# # Fluxo principal
# # ---------------------------------------------------------------------------

# def registar_e_indexar(
#     path_original,
#     metadata_utilizador,
#     chunker,
#     store,
#     pasta_docs="legal_docs",
# ):
#     """
#     Fluxo completo de upload e indexacao de um documento PDF.

#     Passos:
#         1. Calcula hash SHA-256 do ficheiro
#         2. Verifica se ja existe no ChromaDB pelo hash
#         3. Renomeia para {hash[:8]}_nomeOriginal.pdf
#         4. Copia para pasta_docs/
#         5. Indexa no ChromaDB com hash e nome original nos metadados
#         6. Devolve resultado

#     Args:
#         path_original:       Caminho do ficheiro a indexar (pode ser temporario)
#         metadata_utilizador: Metadados fornecidos pelo utilizador
#                              (ex: {"type": "ruling", "year": "2024"})
#         chunker:             Instancia de Chunker
#         store:               Instancia de VectorStore
#         pasta_docs:          Pasta onde os ficheiros sao guardados permanentemente

#     Returns:
#         {
#             "status":     "indexado" | "duplicado" | "erro",
#             "mensagem":   str,
#             "hash":       str,
#             "nome_final": str,
#             "n_chunks":   int,
#         }
#     """
#     from pdf_loader import TextLoader
#     from structure_aware_chunker import StructureAwareChunker

#     try:
#         # 1. Calcular hash
#         hash_doc   = calcular_hash(path_original)
#         nome_final = nome_com_hash(path_original, hash_doc)

#         # 2. Verificar duplicado
#         ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
#         if ja_existe:
#             return {
#                 "status":    "duplicado",
#                 "mensagem":  (
#                     f"Este documento ja se encontra indexado como '{nome_existente}'. "
#                     f"Hash: {hash_doc[:8]}..."
#                 ),
#                 "hash":      hash_doc,
#                 "nome_final": nome_existente,
#                 "n_chunks":  0,
#             }

#         # 3. Copiar ficheiro com novo nome para pasta permanente
#         os.makedirs(pasta_docs, exist_ok=True)
#         path_destino = os.path.join(pasta_docs, nome_final)
#         shutil.copy2(path_original, path_destino)

#         # 4. Carregar texto e metadados
#         loader = TextLoader(path_destino)
#         texto  = loader.load()

#         if not texto.strip():
#             os.remove(path_destino)
#             return {
#                 "status":    "erro",
#                 "mensagem":  "O ficheiro nao contem texto extraivel (PDF digitalizado sem OCR?).",
#                 "hash":      hash_doc,
#                 "nome_final": nome_final,
#                 "n_chunks":  0,
#             }

#         # 5. Metadados completos com hash e nome original
#         meta = {
#             **loader.metadata(),
#             **metadata_utilizador,
#             "hash_documento": hash_doc,
#             "nome_original":  os.path.basename(path_original),
#             "nome_ficheiro":  nome_final,
#         }

#         # 6. Chunking
#         if isinstance(chunker, StructureAwareChunker):
#             chunks = chunker.split(path_destino)
#         else:
#             chunks = chunker.split(texto)

#         # 7. Indexar
#         for chunk in chunks:
#             chunk_meta = {
#                 **meta,
#                 **{k: v for k, v in chunk.items() if k != "text"},
#             }
#             store.add(chunk["text"], chunk_meta)

#         return {
#             "status":    "indexado",
#             "mensagem":  f"Documento indexado com sucesso. {len(chunks)} chunks adicionados.",
#             "hash":      hash_doc,
#             "nome_final": nome_final,
#             "n_chunks":  len(chunks),
#         }

#     except Exception as e:
#         return {
#             "status":    "erro",
#             "mensagem":  str(e),
#             "hash":      "",
#             "nome_final": "",
#             "n_chunks":  0,
#         }

# """
# document_registry.py

# Registo de documentos indexados com verificação de duplicados por hash SHA-256.

# Garante que o mesmo documento não é indexado duas vezes,
# independentemente do nome do ficheiro.

# Fluxo:
#     PDF recebido
#         ↓
#     calcular SHA-256 do ficheiro completo
#         ↓
#     verificar se esse hash já existe no ChromaDB (metadados dos chunks)
#         ↓
#     SE JÁ EXISTE → rejeitar com mensagem "documento já indexado"
#     SE NÃO EXISTE → renomear para {hash[:8]}_nomeOriginal.pdf → indexar
# """

# import hashlib
# import os
# import shutil


# # ---------------------------------------------------------------------------
# # Hash
# # ---------------------------------------------------------------------------

# def calcular_hash(path: str) -> str:
#     """
#     Calcula SHA-256 do conteúdo do ficheiro.
#     Retorna string hex de 64 caracteres.
#     Lê em blocos de 64KB para não carregar ficheiros grandes em memória.
#     """
#     h = hashlib.sha256()
#     with open(path, "rb") as f:
#         for bloco in iter(lambda: f.read(65536), b""):
#             h.update(bloco)
#     return h.hexdigest()


# def nome_com_hash(path: str, hash_completo: str) -> str:
#     """
#     Gera nome de ficheiro com prefixo dos primeiros 8 caracteres do hash.

#     Exemplo:
#         'acordao_01.pdf'  ->  'a3f8c2d1_acordao_01.pdf'
#     """
#     nome_original = os.path.basename(path)
#     prefixo       = hash_completo[:8]
#     return f"{prefixo}_{nome_original}"


# # ---------------------------------------------------------------------------
# # Verificacao de duplicados
# # ---------------------------------------------------------------------------

# def documento_ja_indexado(store, hash_doc: str) -> tuple:
#     """
#     Verifica se um documento com este hash ja foi indexado no ChromaDB.

#     Pesquisa nos metadados de todos os chunks o campo 'hash_documento'.
#     Devolve (True, nome_ficheiro) se encontrado, (False, "") caso contrario.

#     Nota: pesquisa com n=store.count() para cobrir todos os chunks.
#     Em bases de dados grandes isto pode ser lento -- considerar
#     manter um registo separado em SQLite na Fase 2.
#     """
#     total = store.count()
#     if total == 0:
#         return False, ""

#     try:
#         resultados = store.search("documento juridico", n=min(total, 1000))
#         for r in resultados:
#             if r["metadata"].get("hash_documento") == hash_doc:
#                 nome = r["metadata"].get("nome_ficheiro", "desconhecido")
#                 return True, nome
#         return False, ""
#     except Exception:
#         return False, ""


# # ---------------------------------------------------------------------------
# # Fluxo principal
# # ---------------------------------------------------------------------------

# def registar_e_indexar(
#     path_original,
#     metadata_utilizador,
#     chunker,
#     store,
#     pasta_docs="legal_docs",
# ):
#     """
#     Fluxo completo de upload e indexacao de um documento PDF.

#     Passos:
#         1. Calcula hash SHA-256 do ficheiro
#         2. Verifica se ja existe no ChromaDB pelo hash
#         3. Renomeia para {hash[:8]}_nomeOriginal.pdf
#         4. Copia para pasta_docs/
#         5. Indexa no ChromaDB com hash e nome original nos metadados
#         6. Devolve resultado

#     Args:
#         path_original:       Caminho do ficheiro a indexar (pode ser temporario)
#         metadata_utilizador: Metadados fornecidos pelo utilizador
#                              (ex: {"type": "ruling", "year": "2024"})
#         chunker:             Instancia de Chunker
#         store:               Instancia de VectorStore
#         pasta_docs:          Pasta onde os ficheiros sao guardados permanentemente

#     Returns:
#         {
#             "status":     "indexado" | "duplicado" | "erro",
#             "mensagem":   str,
#             "hash":       str,
#             "nome_final": str,
#             "n_chunks":   int,
#         }
#     """
#     from pdf_loader import TextLoader
#     from structure_aware_chunker import StructureAwareChunker
#     from fixed_chunker import FixedChunker

#     try:
#         # 1. Calcular hash
#         hash_doc   = calcular_hash(path_original)
#         nome_final = nome_com_hash(path_original, hash_doc)

#         # 2. Verificar duplicado
#         ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
#         if ja_existe:
#             return {
#                 "status":    "duplicado",
#                 "mensagem":  (
#                     f"Este documento ja se encontra indexado como '{nome_existente}'. "
#                     f"Hash: {hash_doc[:8]}..."
#                 ),
#                 "hash":      hash_doc,
#                 "nome_final": nome_existente,
#                 "n_chunks":  0,
#             }

#         # 3. Copiar ficheiro com novo nome para pasta permanente
#         os.makedirs(pasta_docs, exist_ok=True)
#         path_destino = os.path.join(pasta_docs, nome_final)
#         shutil.copy2(path_original, path_destino)

#         # 4. Carregar texto — PDF usa TextLoader, .txt lê directamente
#         ext = os.path.splitext(path_original)[1].lower()
#         if ext == ".txt":
#             with open(path_destino, "r", encoding="utf-8") as f:
#                 texto = f.read()
#             file_meta = {
#                 "filename": os.path.basename(path_destino),
#                 "num_pages": 1,
#             }
#         else:
#             loader    = TextLoader(path_destino)
#             texto     = loader.load()
#             file_meta = loader.metadata()

#         if not texto.strip():
#             os.remove(path_destino)
#             return {
#                 "status":    "erro",
#                 "mensagem":  "O ficheiro nao contem texto extraivel.",
#                 "hash":      hash_doc,
#                 "nome_final": nome_final,
#                 "n_chunks":  0,
#             }

#         # 5. Metadados completos com hash e nome original
#         meta = {
#             **file_meta,
#             **metadata_utilizador,
#             "hash_documento": hash_doc,
#             "nome_original":  os.path.basename(path_original),
#             "nome_ficheiro":  nome_final,
#         }

#         # 6. Chunking
#         # TXT do ITIJ nao tem tipografia — usa sempre FixedChunker
#         if ext == ".txt" or not isinstance(chunker, StructureAwareChunker):
#             chunks = chunker.split(texto)
#         else:
#             chunks = chunker.split(path_destino)

#         # 7. Indexar
#         for chunk in chunks:
#             chunk_meta = {
#                 **meta,
#                 **{k: v for k, v in chunk.items() if k != "text"},
#             }
#             store.add(chunk["text"], chunk_meta)

#         return {
#             "status":    "indexado",
#             "mensagem":  f"Documento indexado com sucesso. {len(chunks)} chunks adicionados.",
#             "hash":      hash_doc,
#             "nome_final": nome_final,
#             "n_chunks":  len(chunks),
#         }

#     except Exception as e:
#         return {
#             "status":    "erro",
#             "mensagem":  str(e),
#             "hash":      "",
#             "nome_final": "",
#             "n_chunks":  0,
#         }

# """
# document_registry.py

# Registo de documentos indexados com verificação de duplicados por hash SHA-256.

# Garante que o mesmo documento não é indexado duas vezes,
# independentemente do nome do ficheiro.

# Fluxo:
#     PDF recebido
#         ↓
#     calcular SHA-256 do ficheiro completo
#         ↓
#     verificar se esse hash já existe no ChromaDB (metadados dos chunks)
#         ↓
#     SE JÁ EXISTE → rejeitar com mensagem "documento já indexado"
#     SE NÃO EXISTE → renomear para {hash[:8]}_nomeOriginal.pdf → indexar
# """

# import hashlib
# import os
# import shutil


# # ---------------------------------------------------------------------------
# # Hash
# # ---------------------------------------------------------------------------

# def calcular_hash(path: str) -> str:
#     """
#     Calcula SHA-256 do conteúdo do ficheiro.
#     Retorna string hex de 64 caracteres.
#     Lê em blocos de 64KB para não carregar ficheiros grandes em memória.
#     """
#     h = hashlib.sha256()
#     with open(path, "rb") as f:
#         for bloco in iter(lambda: f.read(65536), b""):
#             h.update(bloco)
#     return h.hexdigest()


# def nome_com_hash(path: str, hash_completo: str) -> str:
#     """
#     Gera nome de ficheiro com prefixo dos primeiros 8 caracteres do hash.

#     Exemplo:
#         'acordao_01.pdf'  ->  'a3f8c2d1_acordao_01.pdf'
#     """
#     nome_original = os.path.basename(path)
#     prefixo       = hash_completo[:8]
#     return f"{prefixo}_{nome_original}"


# # ---------------------------------------------------------------------------
# # Verificacao de duplicados
# # ---------------------------------------------------------------------------

# def documento_ja_indexado(store, hash_doc: str) -> tuple:
#     """
#     Verifica se um documento com este hash ja foi indexado no ChromaDB.

#     Pesquisa nos metadados de todos os chunks o campo 'hash_documento'.
#     Devolve (True, nome_ficheiro) se encontrado, (False, "") caso contrario.

#     Nota: pesquisa com n=store.count() para cobrir todos os chunks.
#     Em bases de dados grandes isto pode ser lento -- considerar
#     manter um registo separado em SQLite na Fase 2.
#     """
#     total = store.count()
#     if total == 0:
#         return False, ""

#     try:
#         resultados = store.search("documento juridico", n=min(total, 1000))
#         for r in resultados:
#             if r["metadata"].get("hash_documento") == hash_doc:
#                 nome = r["metadata"].get("nome_ficheiro", "desconhecido")
#                 return True, nome
#         return False, ""
#     except Exception:
#         return False, ""


# # ---------------------------------------------------------------------------
# # Fluxo principal
# # ---------------------------------------------------------------------------

# def registar_e_indexar(
#     path_original,
#     metadata_utilizador,
#     chunker,
#     store,
#     pasta_docs="legal_docs",
# ):
#     """
#     Fluxo completo de upload e indexacao de um documento PDF.

#     Passos:
#         1. Calcula hash SHA-256 do ficheiro
#         2. Verifica se ja existe no ChromaDB pelo hash
#         3. Renomeia para {hash[:8]}_nomeOriginal.pdf
#         4. Copia para pasta_docs/
#         5. Indexa no ChromaDB com hash e nome original nos metadados
#         6. Devolve resultado

#     Args:
#         path_original:       Caminho do ficheiro a indexar (pode ser temporario)
#         metadata_utilizador: Metadados fornecidos pelo utilizador
#                              (ex: {"type": "ruling", "year": "2024"})
#         chunker:             Instancia de Chunker
#         store:               Instancia de VectorStore
#         pasta_docs:          Pasta onde os ficheiros sao guardados permanentemente

#     Returns:
#         {
#             "status":     "indexado" | "duplicado" | "erro",
#             "mensagem":   str,
#             "hash":       str,
#             "nome_final": str,
#             "n_chunks":   int,
#         }
#     """
#     from pdf_loader import TextLoader
#     from structure_aware_chunker import StructureAwareChunker
#     from fixed_chunker import FixedChunker

#     try:
#         # 1. Calcular hash
#         hash_doc   = calcular_hash(path_original)
#         nome_final = nome_com_hash(path_original, hash_doc)

#         # 2. Verificar duplicado
#         ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
#         if ja_existe:
#             return {
#                 "status":    "duplicado",
#                 "mensagem":  (
#                     f"Este documento ja se encontra indexado como '{nome_existente}'. "
#                     f"Hash: {hash_doc[:8]}..."
#                 ),
#                 "hash":      hash_doc,
#                 "nome_final": nome_existente,
#                 "n_chunks":  0,
#             }

#         # 3. Copiar ficheiro com novo nome para pasta permanente
#         os.makedirs(pasta_docs, exist_ok=True)
#         path_destino = os.path.join(pasta_docs, nome_final)
#         shutil.copy2(path_original, path_destino)

#         # 4. Carregar texto — PDF usa TextLoader, .txt/.html lê directamente
#         ext = os.path.splitext(path_original)[1].lower()
#         if ext in (".txt", ".html"):
#             with open(path_destino, "r", encoding="utf-8") as f:
#                 texto = f.read()
#             # Para HTML extrair texto para validação
#             if ext == ".html":
#                 from bs4 import BeautifulSoup as _BS
#                 texto_validacao = _BS(texto, "html.parser").get_text()
#             else:
#                 texto_validacao = texto
#             file_meta = {
#                 "filename": os.path.basename(path_destino),
#                 "num_pages": 1,
#             }
#         else:
#             loader    = TextLoader(path_destino)
#             texto     = loader.load()
#             file_meta = loader.metadata()
#             texto_validacao = texto

#         if not texto_validacao.strip():
#             os.remove(path_destino)
#             return {
#                 "status":    "erro",
#                 "mensagem":  "O ficheiro nao contem texto extraivel.",
#                 "hash":      hash_doc,
#                 "nome_final": nome_final,
#                 "n_chunks":  0,
#             }

#         # 5. Metadados completos com hash e nome original
#         meta = {
#             **file_meta,
#             **metadata_utilizador,
#             "hash_documento": hash_doc,
#             "nome_original":  os.path.basename(path_original),
#             "nome_ficheiro":  nome_final,
#         }

#         # 6. Chunking
#         # 6. Chunking
#         # HTML: ITIJChunker recebe HTML; TXT: texto puro; PDF: caminho
#         from itij_chunker import ITIJChunker
#         if isinstance(chunker, ITIJChunker):
#             chunks = chunker.split(texto)  # HTML ou texto
#         elif ext == ".txt" or not isinstance(chunker, StructureAwareChunker):
#             chunks = chunker.split(texto_validacao)
#         else:
#             chunks = chunker.split(path_destino)

#         # 7. Indexar
#         for chunk in chunks:
#             chunk_meta = {
#                 **meta,
#                 **{k: v for k, v in chunk.items() if k != "text"},
#             }
#             store.add(chunk["text"], chunk_meta)

#         return {
#             "status":    "indexado",
#             "mensagem":  f"Documento indexado com sucesso. {len(chunks)} chunks adicionados.",
#             "hash":      hash_doc,
#             "nome_final": nome_final,
#             "n_chunks":  len(chunks),
#         }

#     except Exception as e:
#         return {
#             "status":    "erro",
#             "mensagem":  str(e),
#             "hash":      "",
#             "nome_final": "",
#             "n_chunks":  0,
#         }

# """
# document_registry.py

# Registo de documentos indexados com verificação de duplicados por hash SHA-256.

# Garante que o mesmo documento não é indexado duas vezes,
# independentemente do nome do ficheiro.

# Fluxo:
#     PDF recebido
#         ↓
#     calcular SHA-256 do ficheiro completo
#         ↓
#     verificar se esse hash já existe no ChromaDB (metadados dos chunks)
#         ↓
#     SE JÁ EXISTE → rejeitar com mensagem "documento já indexado"
#     SE NÃO EXISTE → renomear para {hash[:8]}_nomeOriginal.pdf → indexar
# """

# import hashlib
# import os
# import shutil


# # ---------------------------------------------------------------------------
# # Hash
# # ---------------------------------------------------------------------------

# def calcular_hash(path: str) -> str:
#     """
#     Calcula SHA-256 do conteúdo do ficheiro.
#     Retorna string hex de 64 caracteres.
#     Lê em blocos de 64KB para não carregar ficheiros grandes em memória.
#     """
#     h = hashlib.sha256()
#     with open(path, "rb") as f:
#         for bloco in iter(lambda: f.read(65536), b""):
#             h.update(bloco)
#     return h.hexdigest()


# def nome_com_hash(path: str, hash_completo: str) -> str:
#     """
#     Gera nome de ficheiro com prefixo dos primeiros 8 caracteres do hash.

#     Exemplo:
#         'acordao_01.pdf'  ->  'a3f8c2d1_acordao_01.pdf'
#     """
#     nome_original = os.path.basename(path)
#     prefixo       = hash_completo[:8]
#     return f"{prefixo}_{nome_original}"


# # ---------------------------------------------------------------------------
# # Verificacao de duplicados
# # ---------------------------------------------------------------------------

# def documento_ja_indexado(store, hash_doc: str) -> tuple:
#     """
#     Verifica se um documento com este hash ja foi indexado no ChromaDB.

#     Usa filtro por metadados (where) para pesquisa eficiente —
#     nao depende do numero total de chunks no store.
#     Devolve (True, nome_ficheiro) se encontrado, (False, "") caso contrario.
#     """
#     if store.count() == 0:
#         return False, ""

#     try:
#         # Usar filtro ChromaDB por hash_documento — muito mais eficiente
#         # do que pesquisar todos os chunks
#         resultados = store.search(
#             "documento",
#             filters={"hash_documento": hash_doc},
#             n=1,
#         )
#         if resultados:
#             nome = resultados[0]["metadata"].get("nome_ficheiro", "desconhecido")
#             return True, nome
#         return False, ""
#     except Exception:
#         return False, ""


# # ---------------------------------------------------------------------------
# # Fluxo principal
# # ---------------------------------------------------------------------------

# def registar_e_indexar(
#     path_original,
#     metadata_utilizador,
#     chunker,
#     store,
#     pasta_docs="legal_docs",
# ):
#     """
#     Fluxo completo de upload e indexacao de um documento PDF.

#     Passos:
#         1. Calcula hash SHA-256 do ficheiro
#         2. Verifica se ja existe no ChromaDB pelo hash
#         3. Renomeia para {hash[:8]}_nomeOriginal.pdf
#         4. Copia para pasta_docs/
#         5. Indexa no ChromaDB com hash e nome original nos metadados
#         6. Devolve resultado

#     Args:
#         path_original:       Caminho do ficheiro a indexar (pode ser temporario)
#         metadata_utilizador: Metadados fornecidos pelo utilizador
#                              (ex: {"type": "ruling", "year": "2024"})
#         chunker:             Instancia de Chunker
#         store:               Instancia de VectorStore
#         pasta_docs:          Pasta onde os ficheiros sao guardados permanentemente

#     Returns:
#         {
#             "status":     "indexado" | "duplicado" | "erro",
#             "mensagem":   str,
#             "hash":       str,
#             "nome_final": str,
#             "n_chunks":   int,
#         }
#     """
#     from pdf_loader import TextLoader
#     from structure_aware_chunker import StructureAwareChunker
#     from fixed_chunker import FixedChunker

#     try:
#         # 1. Calcular hash
#         hash_doc   = calcular_hash(path_original)
#         nome_final = nome_com_hash(path_original, hash_doc)

#         # 2. Verificar duplicado
#         ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
#         if ja_existe:
#             return {
#                 "status":    "duplicado",
#                 "mensagem":  (
#                     f"Este documento ja se encontra indexado como '{nome_existente}'. "
#                     f"Hash: {hash_doc[:8]}..."
#                 ),
#                 "hash":      hash_doc,
#                 "nome_final": nome_existente,
#                 "n_chunks":  0,
#             }

#         # 3. Copiar ficheiro com novo nome para pasta permanente
#         os.makedirs(pasta_docs, exist_ok=True)
#         path_destino = os.path.join(pasta_docs, nome_final)
#         shutil.copy2(path_original, path_destino)

#         # 4. Carregar texto — PDF usa TextLoader, .txt/.html lê directamente
#         ext = os.path.splitext(path_original)[1].lower()
#         if ext in (".txt", ".html"):
#             with open(path_destino, "r", encoding="utf-8") as f:
#                 texto = f.read()
#             # Para HTML extrair texto para validação
#             if ext == ".html":
#                 from bs4 import BeautifulSoup as _BS
#                 texto_validacao = _BS(texto, "html.parser").get_text()
#             else:
#                 texto_validacao = texto
#             file_meta = {
#                 "filename": os.path.basename(path_destino),
#                 "num_pages": 1,
#             }
#         else:
#             loader    = TextLoader(path_destino)
#             texto     = loader.load()
#             file_meta = loader.metadata()
#             texto_validacao = texto

#         if not texto_validacao.strip():
#             os.remove(path_destino)
#             return {
#                 "status":    "erro",
#                 "mensagem":  "O ficheiro nao contem texto extraivel.",
#                 "hash":      hash_doc,
#                 "nome_final": nome_final,
#                 "n_chunks":  0,
#             }

#         # 5. Metadados completos com hash e nome original
#         meta = {
#             **file_meta,
#             **metadata_utilizador,
#             "hash_documento": hash_doc,
#             "nome_original":  os.path.basename(path_original),
#             "nome_ficheiro":  nome_final,
#         }

#         # 6. Chunking
#         # 6. Chunking
#         # HTML: ITIJChunker recebe HTML; TXT: texto puro; PDF: caminho
#         from itij_chunker import ITIJChunker
#         if isinstance(chunker, ITIJChunker):
#             chunks = chunker.split(texto)  # HTML ou texto
#         elif ext == ".txt" or not isinstance(chunker, StructureAwareChunker):
#             chunks = chunker.split(texto_validacao)
#         else:
#             chunks = chunker.split(path_destino)

#         # 7. Indexar
#         for chunk in chunks:
#             chunk_meta = {
#                 **meta,
#                 **{k: v for k, v in chunk.items() if k != "text"},
#             }
#             store.add(chunk["text"], chunk_meta)

#         return {
#             "status":    "indexado",
#             "mensagem":  f"Documento indexado com sucesso. {len(chunks)} chunks adicionados.",
#             "hash":      hash_doc,
#             "nome_final": nome_final,
#             "n_chunks":  len(chunks),
#         }

#     except Exception as e:
#         return {
#             "status":    "erro",
#             "mensagem":  str(e),
#             "hash":      "",
#             "nome_final": "",
#             "n_chunks":  0,
#         }

"""
document_registry.py

Registo de documentos indexados com verificação de duplicados por hash SHA-256.

Novo pipeline para acórdãos ITIJ:
    1. Guardar HTML bruto em acordaos_html/
    2. Limpar HTML -> texto -> guardar em acordaos_limpos/
    3. LLM classifica blocos em secções semânticas
    4. Indexar no ChromaDB com secção como metadado

Para PDFs (upload manual) o fluxo original mantém-se.
"""

import hashlib
import os
import shutil
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def calcular_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def calcular_hash_str(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def nome_com_hash(path_ou_nome: str, hash_completo: str) -> str:
    nome = os.path.basename(path_ou_nome)
    return f"{hash_completo[:8]}_{nome}"


# ---------------------------------------------------------------------------
# Verificacao de duplicados
# ---------------------------------------------------------------------------

def documento_ja_indexado(store, hash_doc: str) -> tuple:
    if store.count() == 0:
        return False, ""
    try:
        resultados = store.search(
            "documento",
            filters={"hash_documento": hash_doc},
            n=1,
        )
        if resultados:
            nome = resultados[0]["metadata"].get("nome_ficheiro", "desconhecido")
            return True, nome
        return False, ""
    except Exception:
        return False, ""


# ---------------------------------------------------------------------------
# Pipeline ITIJ
# ---------------------------------------------------------------------------

def registar_e_indexar_itij(
    html_content,
    nome_base,
    metadata_utilizador,
    store,
    llm_chunker,
    pasta_html="acordaos_html",
    pasta_limpos="acordaos_limpos",
):
    from html_cleaner import limpar_acordao, metadados_para_texto

    try:
        # 1. Hash
        hash_doc  = calcular_hash_str(html_content)
        nome_html = f"{hash_doc[:8]}_{nome_base}.html"
        nome_txt  = f"{hash_doc[:8]}_{nome_base}.txt"

        # 2. Verificar duplicado
        ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
        if ja_existe:
            return {
                "status":     "duplicado",
                "mensagem":   f"Ja indexado como '{nome_existente}'. Hash: {hash_doc[:8]}...",
                "hash":       hash_doc,
                "nome_final": nome_existente,
                "n_chunks":   0,
            }

        # 3. Guardar HTML bruto
        os.makedirs(pasta_html, exist_ok=True)
        path_html = os.path.join(pasta_html, nome_html)
        with open(path_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 4. Limpar HTML
        resultado_limpeza = limpar_acordao(html_content)
        meta_dict = resultado_limpeza["metadados"]
        sumario   = resultado_limpeza["sumario"]
        corpo     = resultado_limpeza["corpo"]

        if not corpo.strip() and not sumario.strip():
            return {
                "status":     "erro",
                "mensagem":   "Acordao sem texto extraivel.",
                "hash":       hash_doc,
                "nome_final": nome_html,
                "n_chunks":   0,
            }

        # 5. Guardar texto limpo
        os.makedirs(pasta_limpos, exist_ok=True)
        path_txt = os.path.join(pasta_limpos, nome_txt)
        texto_ficheiro = ""
        if sumario:
            texto_ficheiro += f"SUMARIO:\n{sumario}\n\n"
        texto_ficheiro += corpo
        with open(path_txt, "w", encoding="utf-8") as f:
            f.write(texto_ficheiro)

        # 6. Metadados base
        meta_base = {
            **metadata_utilizador,
            **{k: str(v) for k, v in meta_dict.items()},
            "hash_documento": hash_doc,
            "nome_ficheiro":  nome_html,
            "nome_txt":       nome_txt,
            "indexado_em":    datetime.now().isoformat(),
        }

        # 7. LLMChunker
        meta_texto = metadados_para_texto(meta_dict)
        chunks = llm_chunker.chunks_para_indexar(
            texto    =corpo,
            metadados=meta_texto,
            sumario  =sumario,
        )

        if not chunks:
            return {
                "status":     "erro",
                "mensagem":   "Nenhum chunk gerado.",
                "hash":       hash_doc,
                "nome_final": nome_html,
                "n_chunks":   0,
            }

        # 8. Indexar
        for chunk in chunks:
            chunk_meta = {
                **meta_base,
                "section":   chunk.get("section", "outro"),
                "chunk_idx": chunk.get("chunk_idx", 0),
            }
            store.add(chunk["text"], chunk_meta)

        # 9. Registo JSON
        _guardar_registo(pasta_html, hash_doc, nome_base, metadata_utilizador, len(chunks))

        from collections import Counter
        seccoes = Counter(c.get("section","?") for c in chunks)
        resumo  = ", ".join(f"{s}:{n}" for s,n in seccoes.items())

        return {
            "status":     "indexado",
            "mensagem":   f"Indexado. {len(chunks)} chunks ({resumo}).",
            "hash":       hash_doc,
            "nome_final": nome_html,
            "n_chunks":   len(chunks),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status":     "erro",
            "mensagem":   str(e),
            "hash":       "",
            "nome_final": "",
            "n_chunks":   0,
        }


def _guardar_registo(pasta, hash_doc, nome, meta, n_chunks):
    try:
        registo = {
            "hash": hash_doc, "nome": nome,
            "indexado_em": datetime.now().isoformat(),
            "n_chunks": n_chunks, **meta,
        }
        with open(os.path.join(pasta, f"{hash_doc[:8]}_registo.json"), "w", encoding="utf-8") as f:
            json.dump(registo, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Pipeline PDF (upload manual)
# ---------------------------------------------------------------------------

def registar_e_indexar(
    path_original,
    metadata_utilizador,
    chunker,
    store,
    pasta_docs="legal_docs",
):
    from pdf_loader import TextLoader
    from structure_aware_chunker import StructureAwareChunker

    try:
        hash_doc   = calcular_hash(path_original)
        nome_final = nome_com_hash(path_original, hash_doc)

        ja_existe, nome_existente = documento_ja_indexado(store, hash_doc)
        if ja_existe:
            return {
                "status":     "duplicado",
                "mensagem":   f"Ja indexado como '{nome_existente}'. Hash: {hash_doc[:8]}...",
                "hash":       hash_doc,
                "nome_final": nome_existente,
                "n_chunks":   0,
            }

        os.makedirs(pasta_docs, exist_ok=True)
        path_destino = os.path.join(pasta_docs, nome_final)
        shutil.copy2(path_original, path_destino)

        ext = os.path.splitext(path_original)[1].lower()
        if ext in (".txt", ".html"):
            with open(path_destino, "r", encoding="utf-8") as f:
                texto = f.read()
            from bs4 import BeautifulSoup as _BS
            texto_validacao = _BS(texto, "html.parser").get_text() if ext == ".html" else texto
            file_meta = {"filename": os.path.basename(path_destino), "num_pages": 1}
        else:
            loader          = TextLoader(path_destino)
            texto           = loader.load()
            texto_validacao = texto
            file_meta       = loader.metadata()

        if not texto_validacao.strip():
            os.remove(path_destino)
            return {"status": "erro", "mensagem": "Sem texto extraivel.",
                    "hash": hash_doc, "nome_final": nome_final, "n_chunks": 0}

        meta = {
            **file_meta, **metadata_utilizador,
            "hash_documento": hash_doc,
            "nome_original":  os.path.basename(path_original),
            "nome_ficheiro":  nome_final,
        }

        if isinstance(chunker, StructureAwareChunker) and ext == ".pdf":
            chunks = chunker.split(path_destino)
        else:
            chunks = chunker.split(texto_validacao if ext != ".html" else texto)

        for chunk in chunks:
            chunk_meta = {**meta, **{k: v for k, v in chunk.items() if k != "text"}}
            store.add(chunk["text"], chunk_meta)

        return {
            "status":     "indexado",
            "mensagem":   f"Indexado. {len(chunks)} chunks.",
            "hash":       hash_doc,
            "nome_final": nome_final,
            "n_chunks":   len(chunks),
        }

    except Exception as e:
        return {"status": "erro", "mensagem": str(e),
                "hash": "", "nome_final": "", "n_chunks": 0}