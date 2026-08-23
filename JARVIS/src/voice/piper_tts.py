import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional


class PiperTTS:
    """
    Piper TTS Voice Synthesizer using local Thorsten model.
    """

    DEFAULT_PIPER_EXE = r"C:\Users\joelp\miniconda3\anaconda\Scripts\piper.exe"
    DEFAULT_MODEL_PATH = r"C:\Users\joelp\de_DE-thorsten-high.onnx"

    def __init__(self, piper_exe: Optional[str] = None, model_path: Optional[str] = None):
        self.piper_exe = piper_exe or self.DEFAULT_PIPER_EXE
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.output_dir = Path(__file__).resolve().parent.parent / "ui" / "static" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """Checks if piper executable and model files exist."""
        return os.path.exists(self.piper_exe) and os.path.exists(self.model_path)

    def synthesize(self, text: str) -> Optional[str]:
        """
        Converts input text to speech using Piper TTS.
        Hides console window on Windows using CREATE_NO_WINDOW.
        """
        if not text or not text.strip():
            return None

        if not self.is_available():
            print(f"[PIPER TTS WARNING] Piper executable or model file not found!")
            return None

        # Clean text: remove markdown formatting, emojis and non-standard symbols
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
        clean_text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\°äöüÄÖÜß]', '', clean_text)
        if not clean_text or len(clean_text.strip()) == 0:
            return None

        filename = f"speech_{uuid.uuid4().hex[:8]}.wav"
        output_file = self.output_dir / filename

        # CREATE_NO_WINDOW flag for Windows to suppress cmd popup window
        creationflags = 0x08000000 if os.name == 'nt' else 0

        try:
            process = subprocess.Popen(
                [
                    self.piper_exe,
                    "--model", self.model_path,
                    "--output_file", str(output_file)
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=creationflags
            )

            stdout, stderr = process.communicate(input=clean_text)

            if process.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                print(f"[PIPER TTS] Generated speech audio: {filename}")
                return filename
            else:
                print(f"[PIPER TTS ERROR] Piper process failed (code {process.returncode}): {stderr}")
                return None

        except Exception as e:
            print(f"[PIPER TTS ERROR] Exception during speech synthesis: {e}")
            return None


# Global instance
tts = PiperTTS()
