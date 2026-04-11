import json
import urllib.request

from llm import LLM


class OllamaLLM(LLM):
    """
    LLM implementation backed by a model served locally via Ollama.

    Runs entirely on your machine — no API keys, no internet, no usage
    costs. Aligns with the AIAA requirement for open-source LLM tooling
    and guarantees that client data never leaves the local environment.

    Prerequisites
    -------------
    1. Install Ollama: https://ollama.com
    2. Pull a model:
           ollama pull mistral
           ollama pull llama3
           ollama pull qwen2
    3. Ollama must be running before calling generate():
           ollama serve      (starts automatically on most platforms)

    Recommended models for legal Portuguese text
    --------------------------------------------
    "mistral"    : 7B, fast, good multilingual quality. Best starting point.
    "llama3"     : 8B, strong reasoning, good Portuguese support.
    "qwen2"      : 7B, strong multilingual, good for structured output.
    "mixtral"    : 47B MoE, best quality, requires more RAM (32GB+).

    Args:
        model_name:  Name of the Ollama model to use (must be pulled first).
        base_url:    Base URL of the Ollama API (default: localhost:11434).
        temperature: Sampling temperature. Lower = more deterministic.
                     0.0 recommended for factual legal responses.
        timeout:     Request timeout in seconds.

    Example:
        llm    = OllamaLLM("mistral", temperature=0.0)
        answer = llm.generate(prompt)
    """
    
     # "model_name": "qwen2.5:7b-instruct-q4_K_M",
    # "base_url": "https://roselike-angelita-causational.ngrok-free.dev",

    def __init__(
        self,
        model_name: str = "mistral",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        timeout: int = 120,
    ) -> None:
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._timeout = timeout

    # ------------------------------------------------------------------
    # LLM interface
    # ------------------------------------------------------------------

    def generate(self, prompt: str) -> str:
        payload = json.dumps({
            "model":  self._model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._temperature,
            },
        }).encode()

        req = urllib.request.Request(
            url=f"{self._base_url}/api/generate",
            data=payload,
            # headers={"Content-Type": "application/json"},
            headers={
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "AIAA-Legal-Assistanteeeeeeee"
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self._timeout) as response:
            body = json.loads(response.read())

        return body["response"].strip()

    @property
    def model_name(self) -> str:
        return self._model_name
