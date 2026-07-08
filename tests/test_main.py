import sys
import types
import unittest
from unittest.mock import AsyncMock, patch, Mock

# Crear un módulo ficticio 'anthropic' para que la importación en main.py no falle
anthropic_mod = types.ModuleType("anthropic")

def fake_async_anthropic(*args, **kwargs):
    # Devuelve un cliente con `messages.create` asíncrono que puede ser sobreescrito en tests
    return Mock(messages=Mock(create=AsyncMock()))

anthropic_mod.AsyncAnthropic = fake_async_anthropic
sys.modules['anthropic'] = anthropic_mod

import main


class TestMainAsync(unittest.IsolatedAsyncioTestCase):

    async def test_optimizar_prompt_success(self):
        # Mock response object with .content blocks that have .text
        class Block:
            def __init__(self, text):
                self.text = text

        mock_response = Mock()
        mock_response.content = [Block("Prompt mejorado generado por el modelo.")]

        async_mock = AsyncMock(return_value=mock_response)

        with patch('main.client.messages.create', new=async_mock):
            resultado = await main.optimizar_prompt("¿Qué es la retropropagación?")
            self.assertEqual(resultado, "Prompt mejorado generado por el modelo.")
            async_mock.assert_awaited_once()

    async def test_definir_roles_success(self):
        # Respuesta JSON pura desde el modelo
        class Block:
            def __init__(self, text):
                self.text = text

        json_text = '{"expertos": ["Programador", "Historiador", "Poeta"]}'
        mock_response = Mock()
        mock_response.content = [Block(json_text)]

        async_mock = AsyncMock(return_value=mock_response)

        with patch('main.client.messages.create', new=async_mock):
            expertos = await main.definir_roles("Analiza esta consulta y elige roles adecuados")
            self.assertEqual(expertos, ["Programador", "Historiador", "Poeta"])
            async_mock.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
