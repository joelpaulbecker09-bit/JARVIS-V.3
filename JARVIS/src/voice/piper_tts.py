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
    """Local Piper TTS with automatic voice setup and German-safe preprocessing."""

    DEFAULT_PIPER_EXE = r"C:\Users\joelp\miniconda3\anaconda\Scripts\piper.exe"
    DEFAULT_MODEL_PATH = r"C:\Users\joelp\de_DE-thorsten-high.onnx"
    DEFAULT_EMOTIONAL_MODEL_PATH = r"C:\Users\joelp\de_DE-thorsten_emotional-medium.onnx"

    # Piper's official German emotional Thorsten voice. It has 8 speakers;
    # speaker 4 is the neutral voice used by JARVIS.
    EMOTIONAL_MODEL_URL = (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
        "de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium.onnx"
    )
    EMOTIONAL_CONFIG_URL = (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
        "de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium.onnx.json"
    )
    EMOTIONAL_MODEL_SHA256 = (
        "c1764e652266cd6dcebf1b95c61973df5970a5f5272e94b655ff1ddf9a99d1ff"
    )

    # Lower is faster. These values keep speech clear while reducing pauses.
    LENGTH_SCALE = "0.84"
    NOISE_SCALE = "0.667"
    NOISE_W = "0.45"
    SENTENCE_SILENCE = "0.08"
    DEFAULT_SPEAKER = "4"  # thorsten_emotional: neutral

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
        emotional_model_path: Optional[str] = None,
    ):
        self.piper_exe = piper_exe or self.DEFAULT_PIPER_EXE
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.emotional_model_path = (
            emotional_model_path or self.DEFAULT_EMOTIONAL_MODEL_PATH
        )
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
    def _download_verified(
        cls,
        url: str,
        destination: Path,
        sha256: Optional[str] = None,
    ) -> bool:
        temporary = destination.with_suffix(destination.suffix + ".download")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(url, stream=True, timeout=(10, 120)) as response:
                response.raise_for_status()
                with temporary.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)

            if sha256 and cls._sha256(temporary).lower() != sha256.lower():
                print("[PIPER TTS] Voice checksum mismatch; keeping fallback voice.")
                temporary.unlink(missing_ok=True)
                return False

            temporary.replace(destination)
            return True
        except Exception as error:
            temporary.unlink(missing_ok=True)
            print(f"[PIPER TTS] Voice download unavailable; using fallback voice: {error}")
            return False

    def ensure_emotional_model(self) -> bool:
        """Install the expressive German voice once, without user setup."""
        model = Path(self.emotional_model_path)
        config = Path(f"{model}.json")

        if model.is_file() and model.stat().st_size > 50_000_000 and config.is_file():
            return True

        print("[PIPER TTS] Installing the German emotional voice automatically...")
        if not self._download_verified(
            self.EMOTIONAL_MODEL_URL,
            model,
            self.EMOTIONAL_MODEL_SHA256,
        ):
            return False

        if not config.is_file():
            if not self._download_verified(self.EMOTIONAL_CONFIG_URL, config):
                model.unlink(missing_ok=True)
                return False

        return True

    def is_available(self) -> bool:
        return os.path.isfile(self.piper_exe) and (
            os.path.isfile(self.emotional_model_path)
            or os.path.isfile(self.model_path)
        )

    @classmethod
    def prepare_text(cls, text: str) -> str:
        """Make LLM output safe and natural for German Piper speech."""
        if not text:
            return ""

        # NFC preserves ä, ö, ü and ß as normal Unicode characters.
        clean = unicodedata.normalize("NFC", str(text).strip())

        # Never read code, Markdown links or URLs aloud.
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

        # Keep German umlauts and ß. This is intentionally Unicode-aware.
        clean = re.sub(
            r"[^\w\s.,!?;:'äöüÄÖÜß-]",
            " ",
            clean,
            flags=re.UNICODE,
        )
        clean = re.sub(r"([!?.,;:])\1+", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        # The UI still shows the full LLM answer; this only limits audio latency.
        if len(clean) > 1400:
            clean = clean[:1400].rsplit(" ", 1)[0] + "."

        return clean

    def _select_model(self) -> tuple[Path, Optional[str]]:
        emotional = Path(self.emotional_model_path)
        if emotional.is_file():
            return emotional, self.DEFAULT_SPEAKER
        return Path(self.model_path), None

    def synthesize(self, text: str) -> Optional[str]:
        clean_text = self.prepare_text(text)
        if not clean_text:
            return None

        if not os.path.isfile(self.piper_exe):
            print("[PIPER TTS WARNING] Piper executable not found.")
            return None

        # Prefer the expressive German voice; automatically install it once.
        if not os.path.isfile(self.emotional_model_path):
            self.ensure_emotional_model()

        selected_model, speaker = self._select_model()
        if not selected_model.is_file():
            print("[PIPER TTS WARNING] No German Piper model found.")
            return None

        cache_key = (clean_text, str(selected_model), speaker)
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
            "--model", str(selected_model),
            "--length_scale", self.LENGTH_SCALE,
            "--noise_scale", self.NOISE_SCALE,
            "--noise_w", self.NOISE_W,
            "--sentence_silence", self.SENTENCE_SILENCE,
            "--output_file", str(output_file),
        ]
        if speaker is not None:
            command.extend(["--speaker", speaker])

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
                print(f"[PIPER TTS] Generated German speech: {filename}")
                return filename

            print(
                f"[PIPER TTS ERROR] Piper failed "
                f"(code {process.returncode}): {stderr}"
            )
        except Exception as error:
            print(f"[PIPER TTS ERROR] Synthesis exception: {error}")

        output_file.unlink(missing_ok=True)
        return None


tts = PiperTTS()
