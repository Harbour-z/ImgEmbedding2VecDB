
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent_service import AgentService, get_agent_service

class TestAgentService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        AgentService._instance = None
        self.service = AgentService()

    @patch('app.services.agent_service.get_settings')
    def test_initialize_without_openai(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = False
        mock_get_settings.return_value = mock_settings

        self.service.initialize()
        
        self.assertTrue(self.service.is_initialized)
        self.assertIsNone(self.service._agent)

    @patch('app.services.agent_service.get_settings')
    @patch('app.services.agent_service.ReActAgent')
    def test_initialize_with_openai(self, mock_react_agent_cls, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = True
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL_NAME = "gpt-4o"
        mock_settings.OPENAI_BASE_URL = "https://api.openai.com/v1"
        mock_settings.AGENT_PROVIDER = "openai"
        mock_settings.DEBUG = True
        mock_settings.LLM_SSL_VERIFY = False
        mock_settings.LLM_SSL_CERT = None
        mock_get_settings.return_value = mock_settings
        
        mock_agent_instance = MagicMock()
        mock_react_agent_cls.return_value = mock_agent_instance

        self.service.initialize()
        
        self.assertTrue(self.service.is_initialized)
        self.assertIsNotNone(self.service._agent)
        
        mock_react_agent_cls.assert_called_once()
        mock_agent_instance.add_tools.assert_called()

    def test_detect_intent(self):
        self.assertEqual(self.service.detect_intent("删除这张图")['intent'], "delete")
        self.assertEqual(self.service.detect_intent("上传图片")['intent'], "upload")
        self.assertEqual(self.service.detect_intent("分析这个")['intent'], "analyze")
        self.assertEqual(self.service.detect_intent("找猫")['intent'], "chat")

    @patch('app.services.agent_service.get_settings')
    async def test_chat_fallback(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.AGENT_ENABLED = False
        mock_get_settings.return_value = mock_settings
        self.service.initialize()

        response = await self.service.chat("找猫")
        self.assertIn("answer", response)
        self.assertIn("智慧相册助手", response["answer"])

    @patch('app.services.agent_service.get_settings')
    async def test_chat_with_agent(self, mock_get_settings):
        self.service._agent = MagicMock()
        
        async def mock_invoke(inputs):
            return {"output": "Agent Response", "result_type": "answer"}
            
        self.service._agent.invoke.side_effect = mock_invoke
        
        response = await self.service.chat("Hello")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["answer"], "Agent Response")
        self.assertEqual(response["images"], [])
        self.service._agent.invoke.assert_called()
        call_args = self.service._agent.invoke.call_args[0][0]
        self.assertEqual(call_args["query"], "Hello")

    @patch('app.services.agent_service.get_settings')
    async def test_chat_with_session_id(self, mock_get_settings):
        self.service._agent = MagicMock()
        
        async def mock_invoke(inputs):
            return {"output": "Session response", "result_type": "answer"}
            
        self.service._agent.invoke.side_effect = mock_invoke
        
        session_id = "test_session_123"
        response = await self.service.chat("Hello", session_id=session_id)
        
        self.assertEqual(response["answer"], "Session response")
        session = self.service.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(len(session["history"]), 2)
        self.assertEqual(session["history"][0]["role"], "user")
        self.assertEqual(session["history"][1]["role"], "assistant")

    @patch('app.services.agent_service.get_settings')
    async def test_chat_exception_handling(self, mock_get_settings):
        self.service._agent = MagicMock()
        self.service._agent.invoke.side_effect = Exception("Test exception")
        
        response = await self.service.chat("Hello")
        self.assertIn("answer", response)
        self.assertIn("暂时无法响应", response["answer"])

    def test_singleton(self):
        s1 = get_agent_service()
        s2 = get_agent_service()
        self.assertIs(s1, s2)

    def test_create_session(self):
        session_id = self.service.create_session()
        self.assertIsNotNone(session_id)
        session = self.service.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertIn("history", session)
        self.assertIn("context", session)

    def test_ensure_session(self):
        session_id = "existing_session"
        session = self.service.ensure_session(session_id)
        self.assertEqual(session, session_id)
        self.assertIsNotNone(self.service.get_session(session_id))

if __name__ == '__main__':
    unittest.main()
