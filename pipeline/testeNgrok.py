import urllib.request
import json

url = "https://roselike-angelita-causational.ngrok-free.dev/api/tags"

req = urllib.request.Request(
    url=url,
    headers={
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "AIAA-Legal-Assistant"
    },
    method="GET",
)

with urllib.request.urlopen(req, timeout=30) as response:
    body = json.loads(response.read())
    print(body)