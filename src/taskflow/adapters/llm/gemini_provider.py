import json
from typing import Any, cast

from google import genai
from google.genai import types

from taskflow.domain.ports.ports import EmbeddingProvider, LLMProvider


class GeminiProvider(LLMProvider, EmbeddingProvider):
    """Implementação do provedor LLM usando a API oficial Google GenAI (gemini-3.6-flash)."""

    def __init__(self, api_key: str | None = None) -> None:
        # Se api_key for None, a biblioteca tenta pegar do ambiente (GEMINI_API_KEY)
        self.client = genai.Client(api_key=api_key)
        # O usuário solicitou explicitamente o uso do Gemini 3.6 Flash para tudo (como estamos em Ago/2026)
        self.model_name = "gemini-3.6-flash"

    async def _generate_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Método auxiliar para requisições JSON estruturadas."""
        # A API Python é síncrona/assíncrona dependendo da chamada. 
        # Vamos usar ayncio wrapper se a SDK `genai` oferecer (normalmente offers `aio`).
        # Por simplicidade da MVP, se a API não for async nativa, bloquearia o event loop.
        # Assumindo suporte async na versão 2.16.0 de 2026: client.aio.models.generate_content
        
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        )
        # Se tiver um schema (Pydantic ou TypeDict), passaríamos via response_schema
        # Aqui simplificamos esperando o JSON bruto para manter flexibilidade do domínio.
        
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        
        try:
            return cast(dict[str, Any], json.loads(response.text or "{}"))
        except Exception:  # noqa: BLE001
            return {}

    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Classifique se o seguinte texto contém um compromisso acionável (task). Retorne {{'is_actionable': bool, 'confidence': float}}.\nTexto: {text}"
        return await self._generate_json(prompt)

    async def extract(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Você é um assistente de IA focado em extrair tarefas acionáveis a partir de e-mails ou anotações.\n\n"
            f"Contexto do E-mail:\n"
            f"- Remetente: {context.get('author_name', 'Desconhecido')} ({context.get('author_email', 'Desconhecido')})\n"
            f"- Assunto: {context.get('subject', 'Sem Assunto')}\n"
            f"- Data Atual: {context.get('date', 'Desconhecida')}\n\n"
            f"Texto Original:\n{text}\n\n"
            "Sua tarefa: Identifique a principal solicitação ou compromisso no texto acima.\n"
            "Retorne ESTRITAMENTE um objeto JSON válido (sem markdown, sem explicações) com a seguinte estrutura:\n"
            "{\n"
            "  \"title\": \"Um título curto, claro e direto para a tarefa (máx 60 caracteres)\",\n"
            "  \"description\": \"Uma descrição detalhada do que precisa ser feito, incluindo contexto relevante\",\n"
            "  \"due_date\": \"A data de prazo final no formato YYYY-MM-DD, baseada na Data Atual. Se não houver prazo claro, retorne null\",\n"
            "  \"priority\": \"low\", \"medium\" ou \"high\" (baseado na urgência do texto)\n"
            "}"
        )
        return await self._generate_json(prompt)

    async def correlate(self, signal: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = (
            f"Sinal de entrada: {json.dumps(signal)}\n\n"
            f"Tarefas candidatas: {json.dumps(candidates)}\n\n"
            "Avalie a correlação. Retorne o JSON:\n"
            "{ 'assessments': [ {'task_id': str, 'reasoning': str, 'score': float_0_to_1} ], "
            "'decision_hint': 'apply'|'triage'|'discard' }"
        )
        return await self._generate_json(prompt)

    async def draft_follow_up(self, task: dict[str, Any], context: dict[str, Any], tone: str) -> str:
        prompt = (
            f"Escreva uma mensagem de follow-up (tom: {tone}) para a tarefa: {task.get('title')}.\n"
            f"Contexto: {json.dumps(context)}\n"
            "Retorne apenas o texto da mensagem."
        )
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Modelo atual de embedding textual do Gemini
        response = await self.client.aio.models.embed_content(
            model="text-embedding-004",
            contents=texts,
        )
        return [emb.values for emb in response.embeddings if emb.values is not None] if response.embeddings else []
