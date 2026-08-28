import hashlib
import os
import re
import subprocess
import unicodedata
import uuid
from pathlib import Path
from typing import Optional

import requests


class PiperTTS:
    """Local Piper TTS using the community German JARVIS voice."""

    DEFAULT_PIPER_EXE = r"C:\Users\joelp\miniconda3\anaconda\Scripts\piper.exe"

    # German JARVIS voice based on the JARVIS voice dataset/model.
    # The model is published by ufozone and is derived from Thorsten-Voice/Piper.
    DEFAULT_MODEL_PATH = r"C:\Users\joelp\de_DE-jarvis-high.onnx"
    MODEL_URL = (
        "https://huggingface.co/ufozone/piper-de_DE-jarvis-high/resolve/main/model.onnx"
    )
    CONFIG_URL = (
        "https://huggingface.co/ufozone/piper-de_DE-jarvis-high/resolve/main/config.json"
    )

    LENGTH_SCALE = "0.92"
    NOISE_SCALE = "0.667"
    NOISE_W = "0.8"
    SENTENCE_SILENCE = "0.10"

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

    def __init__(self, piper_exe: Optional[str] = None, model_path: Optional[str] = None):
        self.piper_exe = piper_exe or self.DEFAULT_PIPER_EXE
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.config_path = Path(f"{self.model_path}.json")
        self.output_dir = Path(__file__).resolve().parent.parent / "ui" / "static" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._audio_cache = {}
        self._cache_limit = 32

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def _download(cls, url: str, destination: Path) -> bool:
        temporary = destination.with_suffix(destination.suffix + ".download")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(url, stream=True, timeout=(10, 300)) as response:
                response.raise_for_status()
                with temporary.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)
            temporary.replace(destination)
            return True
        except Exception as error:
            temporary.unlink(missing_ok=True)
            print(f"[PIPER TTS] Download failed: {error}")
            return False

    def ensure_model(self) -> bool:
        model = Path(self.model_path)
        config = self.config_path

        if model.is_file() and model.stat().st_size > 80_000_000 and config.is_file():
            return True

        print("[PIPER TTS] Installing German JARVIS voice (high quality)...")
        if not self._download(self.MODEL_URL, model):
            return False
        if not self._download(self.CONFIG_URL, config):
            model.unlink(missing_ok=True)
            return False

        print(f"[PIPER TTS] German JARVIS voice installed: {model}")
        return True

    def is_available(self) -> bool:
        return os.path.isfile(self.piper_exe) and os.path.isfile(self.model_path)

    @classmethod
    def prepare_text(cls, text: str) -> str:
        if not text:
            return ""

        clean = unicodedata.normalize("NFC", str(text).strip())
        clean = re.sub(r"```[\s\S]*?```", " ", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"https?://\S+|www\.\S+", " ", clean, flags=re.IGNORECASE)
        clean = re.sub(r"(^|\n)\s*#{1,6}\s*", r"\1", clean)
        clean = re.sub(r"[*_~`]+", "", clean)
        clean = re.sub(r"(^|\n)\s*[-•]\s+", r"\1", clean)

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

        for source, target in sorted(cls.PRONUNCIATION_REPLACEMENTS.items(), key=lambda item: -len(item[0])):
            clean = re.sub(
                rf"(?<!\w){re.escape(source)}(?!\w)",
                target,
                clean,
                flags=re.IGNORECASE,
            )

        clean = re.sub(r"[^\w\s.,!?;:'äöüÄÖÜß-]", " ", clean, flags=re.UNICODE)
        clean = re.sub(r"([!?.,;:])\1+", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        if len(clean) > 1400:
            clean = clean[:1400].rsplit(" ", 1)[0] + "."

        return clean

    def synthesize(self, text: str) -> Optional[str]:
        clean_text = self.prepare_text(text)
        if not clean_text:
            return None

        if not os.path.isfile(self.piper_exe):
            print("[PIPER TTS WARNING] Piper executable not found.")
            return None

        if not self.ensure_model():
            print("[PIPER TTS WARNING] German JARVIS model could not be installed.")
            return None

        model = Path(self.model_path)
        cache_key = (clean_text, str(model))
        cached_filename = self._audio_cache.get(cache_key)
        if cached_filename:
            cached_file = self.output_dir / cached_filename
            if cached_file.is_file() and cached_file.stat().st_size > 0:
                return cached_filename

        filename = f"speech_{uuid.uuid4().hex[:8]}.wav"
        output_file = self.output_dir / filename
        creationflags = 0x08000000 if os.name == "nt" else 0

        command = [
            self.piper_exe,
            "--model", str(model),
            "--length_scale", self.LENGTH_SCALE,
            "--noise_scale", self.NOISE_SCALE,
            "--noise_w", self.NOISE_W,
            "--sentence_silence", self.SENTENCE_SILENCE,
            "--output_file", str(output_file),
        ]

        try:
            process = subprocess.Popen(
                command,
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
                self._audio_cache[cache_key] = filename
                if len(self._audio_cache) > self._cache_limit:
                    oldest_key = next(iter(self._audio_cache))
                    oldest_filename = self._audio_cache.pop(oldest_key)
                    (self.output_dir / oldest_filename).unlink(missing_ok=True)
                print(f"[PIPER TTS] Generated German JARVIS speech: {filename}")
                return filename

            print(f"[PIPER TTS ERROR] Piper failed (code {process.returncode}): {stderr}")
        except Exception as error:
            print(f"[PIPER TTS ERROR] Synthesis exception: {error}")

        output_file.unlink(missing_ok=True)
        return None


tts = PiperTTS()
