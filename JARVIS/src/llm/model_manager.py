"""
JARVIS LLM Model Manager

Zentraler Verwalter für LLM-Aufrufe, Modellwahl und Fallbacks.
"""

from typing import List, Dict, Any, Optional
from config.config import config
from config.models import TaskType, DEFAULT_TASK_MODELS
from src.llm.ollama_provider import OllamaProvider


class ModelManager:
    """
    ModelManager entkoppelt das Gehirn von spezifischen LLM-Providern.
    Ermöglicht dynamischen Modellwechsel je nach Aufgabe.

    Chat requests use conservative generation limits by default so JARVIS
    answers stay responsive. Callers can override these values through
    ``options`` when a task needs more output.
    """

    DEFAULT_CHAT_OPTIONS = {
        "temperature": 0.6,
        "top_p": 0.9,
        "num_predict": 384,
        "repeat_penalty": 1.05,
    }

    DEFAULT_ANALYSIS_OPTIONS = {
        "temperature": 0.1,
        "top_p": 0.9,
        "num_predict": 256,
    }

    def __init__(self, provider: Optional[OllamaProvider] = None):
        self.provider = provider or OllamaProvider()
        self.default_model = config.default_model

    def get_model_for_task(self, task_type: TaskType) -> str:
        """
        Ermittelt das passende Modell für einen bestimmten Task-Typ.
        """
        return DEFAULT_TASK_MODELS.get(task_type, self.default_model)

    def _build_options(
        self,
        task_type: TaskType,
        options: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Build fast, predictable defaults without overriding explicit options."""
        if options is not None:
            return dict(options)

        if task_type == TaskType.CHAT:
            return dict(self.DEFAULT_CHAT_OPTIONS)

        if task_type == TaskType.ANALYSIS:
            return dict(self.DEFAULT_ANALYSIS_OPTIONS)

        return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task_type: TaskType = TaskType.CHAT,
        json_mode: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Verarbeitet eine Chat-Anfrage mit dem ausgewählten Modell.
        """
        selected_model = model or self.get_model_for_task(task_type)
        selected_options = self._build_options(task_type, options)

        try:
            return self.provider.chat(
                model=selected_model,
                messages=messages,
                json_mode=json_mode,
                options=selected_options
            )
        except Exception as err:
            # Fallback auf Default-Modell, falls ein spezifisches Modell fehlschlägt
            if selected_model != self.default_model:
                print(f"[MODEL MANAGER] Fallback von {selected_model} auf {self.default_model}")
                return self.provider.chat(
                    model=self.default_model,
                    messages=messages,
                    json_mode=json_mode,
                    options=selected_options
                )
            raise err
