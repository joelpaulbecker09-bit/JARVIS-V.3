import unittest

from config.models import TaskType
from src.llm.model_manager import ModelManager


class LLMPerformanceTests(unittest.TestCase):
    def test_chat_defaults_are_latency_optimized(self):
        manager = ModelManager(provider=object())
        options = manager._build_options(TaskType.CHAT, None)

        self.assertEqual(options["think"], False)
        self.assertEqual(options["num_ctx"], 4096)
        self.assertEqual(options["num_predict"], 192)
        self.assertLess(options["num_predict"], 320)

    def test_analysis_defaults_are_smaller_than_chat(self):
        manager = ModelManager(provider=object())
        chat = manager._build_options(TaskType.CHAT, None)
        analysis = manager._build_options(TaskType.ANALYSIS, None)

        self.assertEqual(analysis["think"], False)
        self.assertLess(analysis["num_ctx"], chat["num_ctx"])
        self.assertLess(analysis["num_predict"], chat["num_predict"])


if __name__ == "__main__":
    unittest.main()
