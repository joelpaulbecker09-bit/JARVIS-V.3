"""
JARVIS LLM Provider – Ollama

Abstraktion der Ollama-Kommunikation.
Kapselt direkte API-Aufrufe an das lokale Ollama-Modell.
"""

from typing import List, Dict, Any, Optional
import ollama
from config.config import config


class OllamaProvider:
    """Schnittstelle für den Zugriff auf den lokalen Ollama-Dienst."""

    def __init__(self, host: Optional[str] = None):
        self.host = host or config.ollama_host

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Führt einen lokalen Ollama-Chat-Aufruf aus.

        Das Modell bleibt länger im Speicher, damit aufeinanderfolgende
        Sprachbefehle nicht ständig einen neuen Modell-Ladevorgang auslösen.
        """
        options = dict(options or {})
        think = options.pop("think", None)

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "keep_alive": "30m",
        }

        if json_mode:
            kwargs["format"] = "json"

        if think is not None:
            kwargs["think"] = bool(think)

        if options:
            kwargs["options"] = options

        try:
            response = ollama.chat(**kwargs)
            content = response.get("message", {}).get("content", "")
            return content.strip()
        except Exception as error:
            print(f"[LLM ERROR] Ollama-Aufruf fehlgeschlagen (Modell {model}): {error}")
            raise ConnectionError(f"Ollama-Kommunikationsfehler: {error}") from error
