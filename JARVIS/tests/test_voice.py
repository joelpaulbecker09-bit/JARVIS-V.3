import unittest

from src.voice.piper_tts import PiperTTS


class PiperVoiceTests(unittest.TestCase):
    def test_german_umlauts_and_sz_are_preserved(self):
        text = PiperTTS.prepare_text(
            "Äpfel, Öl, Überprüfung, Größe, süß und Grüße."
        )
        self.assertIn("Äpfel", text)
        self.assertIn("Öl", text)
        self.assertIn("Überprüfung", text)
        self.assertIn("Größe", text)
        self.assertIn("süß", text)
        self.assertIn("Grüße", text)

    def test_markdown_urls_and_code_are_not_spoken(self):
        text = PiperTTS.prepare_text(
            "Hallo **Sir**! https://example.com ```print('test')``` [GitHub](https://github.com)"
        )
        self.assertNotIn("https", text.lower())
        self.assertNotIn("print", text.lower())
        self.assertNotIn("**", text)
        self.assertIn("GitHub", text)

    def test_technical_pronunciation_is_explicit(self):
        text = PiperTTS.prepare_text("JARVIS nutzt AI, API, JSON und CPU.")
        self.assertIn("Jarvis", text)
        self.assertIn("KI", text)
        self.assertIn("A P I", text)
        self.assertIn("Dschson", text)
        self.assertIn("C P U", text)

    def test_fast_voice_settings_are_enabled(self):
        self.assertEqual(PiperTTS.LENGTH_SCALE, "0.84")
        self.assertEqual(PiperTTS.SENTENCE_SILENCE, "0.08")
        self.assertEqual(PiperTTS.DEFAULT_SPEAKER, "4")

    def test_voice_fallback_path_is_valid(self):
        tts = PiperTTS(
            piper_exe="piper.exe",
            model_path="fallback.onnx",
            emotional_model_path="emotional.onnx",
        )
        model, speaker = tts._select_model()
        self.assertEqual(str(model), "fallback.onnx")
        self.assertIsNone(speaker)


if __name__ == "__main__":
    unittest.main()
