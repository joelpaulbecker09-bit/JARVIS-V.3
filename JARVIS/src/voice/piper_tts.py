import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional


class PiperTTS:
    """Local Piper TTS with a speech-safe preprocessing layer.

    The UI keeps the original JARVIS response. Only the text sent to Piper is
    transformed so Markdown, URLs, code, emojis and technical symbols are not
    spoken literally.
    """

    DEFAULT_PIPER_EXE = r"C:\Users\joelp\miniconda3\anaconda\Scripts\piper.exe"
    DEFAULT_MODEL_PATH = r"C:\Users\joelp\de_DE-thorsten-high.onnx"

    # Optional English voice. If it is not installed, JARVIS automatically
    # falls back to the German Thorsten voice with pronunciation hints.
    DEFAULT_ENGLISH_MODEL_PATH = r"C:\Users\joelp\en_US-lessac-medium.onnx"

    # Slightly faster than Piper's default while remaining natural.
    LENGTH_SCALE = "0.92"

    PRONUNCIATION_REPLACEMENTS = {
        "J.A.R.V.I.S.": "Jarvis",
        "JARVIS": "Jarvis",
        "AI": "KI",
        "API": "A P I",
        "UI": "U I",
        "UX": "U X",
        "URL": "U R L",
        "HTTP": "H T T P",
        "HTTPS": "H T T P S",
        "WebSocket": "Web Socket",
        "websocket": "Web Socket",
        "GitHub": "Git Hub",
        "Git": "Git",
        "Python": "Paiton",
        "PowerShell": "Power Shell",
        "Windows": "Windows",
        "Ollama": "Ollama",
        "Qwen": "Kwen",
        "JSON": "Dschson",
        "CPU": "C P U",
        "GPU": "G P U",
        "RAM": "R A M",
        "SSD": "S S D",
        "PC": "P C",
        "Echo Show": "Echo Show",
        "Wi-Fi": "Wai Fai",
        "WiFi": "Wai Fai",
        "Bluetooth": "Blutooth",
        "TTS": "T T S",
        "LLM": "L L M",
        "JARVIS V.3": "Jarvis Version drei",
    }

    def __init__(
        self,
        piper_exe: Optional[str] = None,
        model_path: Optional[str] = None,
        english_model_path: Optional[str] = None,
    ):
        self.piper_exe = piper_exe or self.DEFAULT_PIPER_EXE
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.english_model_path = english_model_path or self.DEFAULT_ENGLISH_MODEL_PATH
        self.output_dir = Path(__file__).resolve().parent.parent / "ui" / "static" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return os.path.isfile(self.piper_exe) and os.path.isfile(self.model_path)

    @classmethod
    def prepare_text(cls, text: str) -> str:
        """Turn an LLM response into natural, speech-friendly German text."""
        if not text:
            return ""

        clean = str(text).strip()

        # Never read code, markdown links or URLs aloud.
        clean = re.sub(r"```[\s\S]*?```", " ", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"https?://\S+|www\.\S+", " ", clean, flags=re.IGNORECASE)

        # Markdown formatting.
        clean = re.sub(r"(^|\n)\s*#{1,6}\s*", r"\1", clean)
        clean = re.sub(r"[*_~`]+", "", clean)
        clean = re.sub(r"(^|\n)\s*[-•]\s+", r"\1", clean)

        # Common symbols expressed as words.
        symbol_replacements = {
            "°C": " Grad Celsius ",
            "°F": " Grad Fahrenheit ",
            "%": " Prozent ",
            "€": " Euro ",
            "$": " Dollar ",
            "&": " und ",
            "+": " plus ",
            "=": " gleich ",
            ">": " größer als ",
            "<": " kleiner als ",
            "@": " at ",
            "/": " Schrägstrich ",
            "|": " ",
            "\\": " ",
            "_": " ",
        }
        for symbol, spoken in symbol_replacements.items():
            clean = clean.replace(symbol, spoken)

        # Technical terms are replaced before symbol filtering.
        for source, target in sorted(
            cls.PRONUNCIATION_REPLACEMENTS.items(),
            key=lambda item: -len(item[0]),
        ):
            clean = re.sub(
                rf"(?<!\w){re.escape(source)}(?!\w)",
                target,
                clean,
                flags=re.IGNORECASE,
            )

        # Keep German umlauts and ß. Remove emojis/control symbols.
        clean = re.sub(
            r"[^\w\s.,!?;:'äöüÄÖÜß-]",
            " ",
            clean,
            flags=re.UNICODE,
        )

        # Do not let punctuation become a spoken stutter.
        clean = re.sub(r"([!?.,;:])\1+", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        # Keep spoken responses reasonably short. The UI still shows the full
        # answer; this only prevents giant audio files and long delays.
        if len(clean) > 1400:
            clean = clean[:1400].rsplit(" ", 1)[0] + "."

        return clean

    @staticmethod
    def _looks_english(text: str) -> bool:
        """Small heuristic for deciding whether an answer is mainly English."""
        words = re.findall(r"[A-Za-zÄÖÜäöüß]+", text.lower())
        if len(words) < 5:
            return False

        english_markers = {
            "the", "this", "that", "you", "your", "are", "is", "and", "with",
            "from", "for", "can", "will", "what", "how", "please", "system",
            "ready", "online", "offline", "hello", "good", "morning", "evening",
        }
        return sum(word in english_markers for word in words) >= 2

    def _select_model(self, text: str) -> str:
        if self._looks_english(text) and os.path.isfile(self.english_model_path):
            return self.english_model_path
        return self.model_path

    def synthesize(self, text: str) -> Optional[str]:
        """Convert input text to a WAV file using local Piper."""
        clean_text = self.prepare_text(text)

        if not clean_text:
            return None

        if not self.is_available():
            print("[PIPER TTS WARNING] Piper executable or German model not found!")
            return None

        filename = f"speech_{uuid.uuid4().hex[:8]}.wav"
        output_file = self.output_dir / filename
        selected_model = self._select_model(clean_text)

        creationflags = 0x08000000 if os.name == "nt" else 0

        try:
            process = subprocess.Popen(
                [
                    self.piper_exe,
                    "--model", selected_model,
                    "--length_scale", self.LENGTH_SCALE,
                    "--output_file", str(output_file),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )

            _, stderr = process.communicate(input=clean_text)

            if process.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                voice = "English" if selected_model == self.english_model_path else "Deutsch"
                print(f"[PIPER TTS] Generated {voice} speech: {filename}")
                return filename

            print(
                f"[PIPER TTS ERROR] Piper process failed "
                f"(code {process.returncode}): {stderr}"
            )
            return None

        except Exception as error:
            print(f"[PIPER TTS ERROR] Exception during speech synthesis: {error}")
            return None


# Global instance
tts = PiperTTS()
