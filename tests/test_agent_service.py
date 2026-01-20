
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Ensure app can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent_service import AgentService, get_agent_service

class TestAgentService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Reset singleton
        AgentService._instance = None
        self.service = AgentService()

    @patch('app.services.agent_service.get_settings')
    def test_initialize_without_openai(self, mock_get_settings):
        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = False
        mock_settings.OPENAI_API_KEY = None
        mock_get_settings.return_value = mock_settings

        self.service.initialize()
        
        self.assertTrue(self.service.is_initialized)
        self.assertIsNone(self.service._agent)

    @patch('app.services.agent_service.get_settings')
    @patch('app.services.agent_service.ReActAgent') # Mock the class constructor
    def test_initialize_with_openai(self, mock_react_agent_cls, mock_get_settings):
        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = True
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL_NAME = "gpt-4o"
        mock_settings.OPENAI_BASE_URL = "https://api.openai.com/v1"
        mock_settings.AGENT_PROVIDER = "openai"
        mock_settings.LLM_SSL_VERIFY = False
        mock_settings.LLM_SSL_CERT = None
        mock_settings.DEBUG = True
        mock_get_settings.return_value = mock_settings
        
        # Mock ReActAgent instance
        mock_agent_instance = MagicMock()
        mock_react_agent_cls.return_value = mock_agent_instance

        self.service.initialize()
        
        self.assertTrue(self.service.is_initialized)
        self.assertIsNotNone(self.service._agent)
        
        # Verify ReActAgent was initialized
        mock_react_agent_cls.assert_called_once()
        
        # Verify add_tools was called
        mock_agent_instance.add_tools.assert_called()

    def test_detect_intent(self):
        # Test existing logic regression
        self.assertEqual(self.service.detect_intent("删除这张图")['intent'], "delete")
        self.assertEqual(self.service.detect_intent("上传图片")['intent'], "upload")
        self.assertEqual(self.service.detect_intent("分析这个")['intent'], "analyze")
        # 更新测试用例：未明确搜索意图的查询应识别为 chat
        self.assertEqual(self.service.detect_intent("找猫")['intent'], "chat")
        # 显式搜索意图测试（如果未来优化了规则，这里可以加上更明确的搜索词测试）

    @patch('app.services.agent_service.get_settings')
    async def test_chat_fallback(self, mock_get_settings):
        # Initialize without agent
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = False
        mock_get_settings.return_value = mock_settings
        self.service.initialize()

        # 更新测试用例：找猫现在默认会被识别为chat（如果没有Agent智能处理），或者我们需要调整detect_intent的规则
        # 但在fallback模式下，我们希望看到它是如何响应的。
        # 由于我们把默认意图改为了chat，所以这里期望得到chat的回复
        response = await self.service.chat("找猫")
        self.assertIn("智慧相册助手", response.get("answer", ""))

    @patch('app.services.agent_service.get_settings')
    async def test_chat_with_agent(self, mock_get_settings):
        # Mock agent directly
        self.service._agent = MagicMock()
        # invoke is async, so we need to set return_value to a future or use AsyncMock if available
        # But MagicMock with side_effect or return_value being a coroutine works too
        
        async def mock_invoke(inputs):
            return {"output": "Agent Response", "result_type": "answer"}
            
        self.service._agent.invoke.side_effect = mock_invoke
        
        response = await self.service.chat("Hello")
        self.assertEqual(response.get("answer"), "Agent Response")
        # Verify invoke called with correct inputs
        self.service._agent.invoke.assert_called()
        call_args = self.service._agent.invoke.call_args[0][0]
        self.assertEqual(call_args["query"], "Hello")

    def test_singleton(self):
        s1 = get_agent_service()
        s2 = get_agent_service()
        self.assertIs(s1, s2)

if __name__ == '__main__':
    unittest.main()
