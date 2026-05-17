# import urllib.request
# import json

# url = "https://roselike-angelita-causational.ngrok-free.dev/api/tags"

# req = urllib.request.Request(
#     url=url,
#     headers={
#         "ngrok-skip-browser-warning": "true",
#         "User-Agent": "AIAA-Legal-Assistant"
#     },
#     method="GET",
# )

# with urllib.request.urlopen(req, timeout=30) as response:
#     body = json.loads(response.read())
#     print(body)
import chromadb

old = chromadb.PersistentClient(
    path=r"C:\Users\dylan\PROJETO26\reunioes\semana1\chroma_db"
)

new = chromadb.HttpClient(host="localhost", port=8000)

for col in old.list_collections():
    c_old = old.get_collection(col.name)
    c_new = new.get_or_create_collection(col.name)

    data = c_old.get(include=["documents", "metadatas", "embeddings"])

    c_new.add(
        ids=data["ids"],
        documents=data["documents"],
        metadatas=data["metadatas"],
        embeddings=data["embeddings"]
    )