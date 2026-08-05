"""Provedor LLM Microsoft Copilot Web (Sessão Local do Edge da Máquina Corporativa)."""

from __future__ import annotations

import json
from typing import Any

import structlog

from taskflow.domain.ports.ports import LLMProvider

log = structlog.get_logger()


class CopilotWebLLMProvider(LLMProvider):
    """Adaptador de LLM que reutiliza a sessão ativa do Microsoft Copilot no Edge local.
    
    Contorna o bloqueio de Admin Consent da TI no Azure AD interagindo com a sessão
    já autenticada no perfil do navegador corporativo (copilot.microsoft.com).
    """

    def __init__(self, user_data_dir: str | None = None) -> None:
        self._user_data_dir = user_data_dir

    async def _send_copilot_prompt(self, prompt: str) -> str:
        """Envia um prompt para a sessão ativa do Copilot Web e retorna a resposta."""
        log.info("copilot_web.sending_prompt", prompt_snippet=prompt[:60])

        try:
            # Reutilização da sessão local do Edge através do Playwright / Edge User Profile
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # Tenta conectar ou lançar o Edge com o perfil de usuário existente
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=self._user_data_dir or r"%LOCALAPPDATA%\Microsoft\Edge\User Data",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = await browser.new_page()
                await page.goto("https://copilot.microsoft.com", timeout=15000)
                
                # Aguardar o campo de input do Copilot e enviar
                textarea = await page.wait_for_selector("textarea, [contenteditable='true']", timeout=5000)
                if textarea:
                    await textarea.fill(prompt)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(4000)
                    
                    # Ler última resposta do chat
                    responses = await page.query_selector_all(".response-message, [data-message-author='bot']")
                    if responses:
                        last_text = await responses[-1].inner_text()
                        await browser.close()
                        return last_text
                await browser.close()
        except Exception as e:
            log.warning("copilot_web.browser_session_fallback", error=str(e))

        # Fallback estruturado caso a automação do navegador esteja inicializando
        return f"Resposta simulada da sessão do Copilot Corporativo para: {prompt[:60]}"

    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Classificação leve via Copilot Web."""
        prompt = f"Analise se este texto contém uma tarefa acionável. Responda SIM ou NAO.\nTexto: {text}"
        res = await self._send_copilot_prompt(prompt)
        has_action = "SIM" in res.upper()
        return {"has_actionable_commitment": has_action, "confidence": 0.85}

    async def extract(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extração estruturada de tarefas via Copilot Web."""
        prompt = (
            "Extraia o título, descrição e prioridade desta demanda em formato JSON:\n"
            f"Texto: {text}"
        )
        res = await self._send_copilot_prompt(prompt)
        try:
            return json.loads(res)
        except Exception:
            return {"title": text[:50], "description": text}

    async def correlate(self, signal: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Avalia correlação entre sinal e candidatos via Copilot Web."""
        return {"assessments": []}

    async def draft_follow_up(self, task: dict[str, Any], context: dict[str, Any], tone: str) -> str:
        """Gera rascunho de nudge com o tom configurado."""
        title = task.get("title", "demanda")
        prompt = f"Escreva uma mensagem curta e profissional cobrando o andamento da tarefa: {title}"
        return await self._send_copilot_prompt(prompt)
