import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional


class PiperTTS:
    """
    Piper TTS Voice Synthesizer using a local German Piper model.

    The TTS layer deliberately receives a cleaned, speech-friendly version of
    the LLM answer. Markdown, URLs, code, emojis and technical punctuation are
    removed or converted before Piper sees the text.
    """

    DEFAULT_PIPER_EXE = r"C:\Users\joelp\miniconda3\anaconda\Scripts\piper.exe"
    DEFAULT_MODEL_PATH = r"C:\Users\joelp\de_DE-thorsten-high.onnx"

    # Common technical/English terms which otherwise sound poor when read by
    # a German-only voice. These are intentionally conservative and can be
    # expanded later when the JARVIS voice pipeline gets language detection.
    PRONUNCIATION_REPLACEMENTS = {
        "JARVIS": "Jarvis",
        "J.A.R.V.I.S.": "Jarvis",
        "AI": "KI",
        "API": "A P I",
        "UI": "U I",
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
    }

    def __init__(self, piper_exe: Optional[str] = None, model_path: Optional[str] = None):
        self.piper_exe = piper_exe or self.DEFAULT_PIPER_EXE
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.output_dir = Path(__file__).resolve().parent.parent / "ui" / "static" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """Checks if Piper executable and model files exist."""
        return os.path.exists(self.piper_exe) and os.path.exists(self.model_path)

    @classmethod
    def prepare_text(cls, text: str) -> str:
        """
        Convert an LLM response into natural speech text.

        Important: this only affects TTS. The original answer shown in the
        JARVIS UI remains unchanged.
        """
        if not text:
            return ""

        clean = str(text).strip()

        # Remove fenced code blocks first. They should never be spoken aloud.
        clean = re.sub(r"```[\s\S]*?```", " ", clean)

        # Remove markdown links but keep their visible label.
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)

        # Remove bare URLs.
        clean = re.sub(r"https?://\S+|www\.\S+", " ", clean, flags=re.IGNORECASE)

        # Remove markdown headings, emphasis and list markers.
        clean = re.sub(r"(^|\n)\s*#{1,6}\s*", r"\1", clean)
        clean = re.sub(r"[*_~`]+", "", clean)
        clean = re.sub(r"(^|\n)\s*[-•]\s+", r"\1", clean)

        # Convert common symbols into words instead of deleting their meaning.
        replacements = {
            "&": " und ",
            "+": " plus ",
            "%": " Prozent ",
            "€": " Euro ",
            "$": " Dollar ",
            "°C": " Grad Celsius ",
            "°": " Grad ",
            "=": " gleich ",
            ">": " größer als ",
            "<": " kleiner als ",
            "/": " Schrägstrich ",
            "\\": " ",
            "@": " at ",
            "_": " ",
            "|": " ",
        }
        for symbol, spoken in replacements.items():
            clean = clean.replace(symbol, spoken)

        # Replace common technical words before punctuation filtering.
        for source, target in sorted(cls.PRONUNCIATION_REPLACEMENTS.items(), key=lambda item: -len(item[0])):
            clean = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, clean, flags=re.IGNORECASE)

        # Keep German characters. Remove control characters, emojis and other
        # symbols that a German Piper voice should not receive.
        clean = re.sub(r"[^\w\s.,!?;:'äöüÄÖÜß-]", " ", clean, flags=re.UNICODE)

        # Normalize repeated punctuation/whitespace.
        clean = re.sub(r"([!?.,;:])\1+", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        # Avoid absurdly long single TTS jobs. The UI still contains the full
        # answer; this is only a safety limit for speech generation.
        if len(clean) > 1800:
            clean = clean[:1800].rsplit(" ", 1)[0] + "."

        return clean

    def synthesize(self, text: str) -> Optional[str]:
        """Convert input text to speech using Piper TTS."""
        clean_text = self.prepare_text(text)

        if not clean_text:
            return None

        if not self.is_available():
            print("[PIPER TTS WARNING] Piper executable or model file not found!")
            return None

        filename = f"speech_{uuid.uuid4().hex[:8]}.wav"
        output_file = self.output_dir / filename

        # Hide console window on Windows.
        creationflags = 0x08000000 if os.name == "nt" else 0

        try:
            process = subprocess.Popen(
                [
                    self.piper_exe,
                    "--model", self.model_path,
                    "--output_file", str(output_file),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=creationflags,
            )

            stdout, stderr = process.communicate(input=clean_text)

            if process.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                print(f"[PIPER TTS] Generated speech audio: {filename}")
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
