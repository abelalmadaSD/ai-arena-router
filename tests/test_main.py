import sys
import os
import types
import unittest
from unittest.mock import AsyncMock, patch, Mock

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-pipeline-mock-key-12345"
os.environ["JWT_SECRET_KEY"] = "GmPjy5spV1C4ohKTZjqJMX3AkynY3127"

# Crear un módulo ficticio 'anthropic' para que la importación en main.py no falle
anthropic_mod = types.ModuleType("anthropic")

def fake_async_anthropic(*args, **kwargs):
    # Devuelve un cliente con `messages.create` asíncrono que puede ser sobreescrito en tests
    return Mock(messages=Mock(create=AsyncMock()))

anthropic_mod.AsyncAnthropic = fake_async_anthropic
sys.modules['anthropic'] = anthropic_mod

import src.servicios.claudeModels as main  # Importamos el módulo que queremos testear

class TestMainAsync(unittest.IsolatedAsyncioTestCase):

    async def test_optimizar_prompt_success(self):
        # Mock response object with .content blocks that have .text
        class Block:
            def __init__(self, text):
                self.text = text

        mock_response = Mock()
        mock_response.content = [Block("Prompt mejorado generado por el modelo.")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)  # Requisito para créditos

        async_mock = AsyncMock(return_value=mock_response)

        with patch('src.servicios.claudeModels.client.messages.create', new=async_mock):
            resultado = await main.optimizar_prompt("¿Qué es la retropropagación?")
            self.assertEqual(resultado["texto"], "Prompt mejorado generado por el modelo.")
            self.assertIn("metricas", resultado)
            async_mock.assert_awaited_once()

    async def test_definir_roles_success(self):
        # Respuesta JSON pura desde el modelo
        class Block:
            def __init__(self, text):
                self.text = text

        json_text = '{"expertos": ["Programador", "Historiador", "Poeta"]}'
        mock_response = Mock()
        mock_response.content = [Block(json_text)]
        mock_response.usage = Mock(input_tokens=80, output_tokens=40)  # Requisito para créditos

        async_mock = AsyncMock(return_value=mock_response)

        with patch('src.servicios.claudeModels.client.messages.create', new=async_mock):
            expertos = await main.definir_roles("Analiza esta consulta y elige roles adecuados")
            self.assertEqual(expertos["datos"], ["Programador", "Historiador", "Poeta"])
            self.assertIn("metricas", expertos)
            async_mock.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
