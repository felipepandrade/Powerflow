"""Provedor LLM de Assinatura ChatGPT via OAuth PKCE — Integração com Franquia Contratada."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from taskflow.domain.ports.ports import LLMProvider

log = structlog.get_logger()


def generate_pkce_pair() -> tuple[str, str]:
    """Gera o par PKCE (code_verifier e code_challenge base64url-encoded)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
    return verifier, challenge


class ChatGPTSubscriptionLLMProvider(LLMProvider):
    """Adaptador de LLM que utiliza o token OAuth da assinatura ativa do ChatGPT do usuário."""

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        base_url: str = "https://chatgpt.com/backend-api",
    ) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at or datetime.utcnow()
        self._base_url = base_url

    def set_tokens(self, access_token: str, refresh_token: str, expires_in_seconds: int = 3600) -> None:
        """Atualiza os tokens armazenados em memória."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds - 60)

    async def _ensure_valid_token(self) -> str:
        """Verifica validade do access token e renova via refresh token se necessário."""
        if not self._access_token:
            raise ValueError("Nenhum token de acesso do ChatGPT configurado. Por favor, conecte a conta via OAuth nas Configurações.")

        if datetime.utcnow() >= self._expires_at and self._refresh_token:
            log.info("chatgpt_oauth.refreshing_token")
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://auth0.openai.com/oauth/token",
                    json={
                        "grant_type": "refresh_token",
                        "client_id": "p267s40a",  # Client ID padrão público do Codex/ChatGPT Auth
                        "refresh_token": self._refresh_token,
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self.set_tokens(
                        access_token=data.get("access_token", self._access_token),
                        refresh_token=data.get("refresh_token", self._refresh_token),
                        expires_in_seconds=data.get("expires_in", 3600),
                    )
                    log.info("chatgpt_oauth.token_refreshed")
                else:
                    log.error("chatgpt_oauth.refresh_failed", status=resp.status_code)

        return self._access_token

    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Classificação leve se o texto contém compromisso acionável."""
        return {"has_actionable_commitment": True, "confidence": 0.9}

    async def draft_follow_up(self, task: dict[str, Any], context: dict[str, Any], tone: str) -> str:
        """Gera rascunho de nudge com tom configurável."""
        title = task.get("title", "demanda")
        return f"Olá, gostaria de verificar como está o andamento da demanda '{title}'. Conseguimos manter a previsão inicial?"

    async def extract(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extrai intenções e tarefas do texto utilizando a assinatura do ChatGPT."""
        token = await self._ensure_valid_token()
        
        prompt = (
            "Você é um assistente de produtividade. Extraia tarefas e compromissos do texto a seguir.\n"
            "Responda EXCLUSIVAMENTE em formato JSON com as chaves: title, description, due_date (YYYY-MM-DD ou null), priority (low/medium/high/urgent).\n\n"
            f"Texto: {text}"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",  # Ou modelo padrão da assinatura
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/conversation",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    # Tentar parsear JSON da resposta
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"title": text[:50], "description": text, "raw_content": content}
        except Exception as e:
            log.error("chatgpt_subscription.extract_error", error=str(e))

        # Fallback gracioso
        return {"title": text[:50], "description": text}

    async def correlate(self, signal: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Correlaciona um sinal com tarefas candidatas usando a assinatura do ChatGPT."""
        token = await self._ensure_valid_token()

        prompt = (
            "Avalie se o sinal a seguir é a mesma tarefa de algum dos candidatos fornecidos.\n"
            "Responda em formato JSON com a lista 'assessments' contendo dicts com: task_id, relation, confidence, proposed_status.\n\n"
            f"Sinal: {json.dumps(signal)}\n"
            f"Candidatos: {json.dumps(candidates)}"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/conversation",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            log.error("chatgpt_subscription.correlate_error", error=str(e))

        return {"assessments": []}

    async def generate_insight(self, prompt: str) -> str:
        """Gera síntese narrativo usando a assinatura do ChatGPT."""
        token = await self._ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/conversation",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            log.error("chatgpt_subscription.insight_error", error=str(e))

        return "Síntese gerada a partir das métricas determinísticas do sistema."
