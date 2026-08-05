import logging

import msal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from taskflow.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Scopes needed for the application
# msal already includes offline_access, openid and profile by default
SCOPES = ["User.Read", "Mail.Read", "Calendars.Read"]

def _build_msal_app(cache=None):
    settings = get_settings()
    authority = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}"
    return msal.ConfidentialClientApplication(
        settings.MS_CLIENT_ID,
        authority=authority,
        client_credential=settings.MS_CLIENT_SECRET,
        token_cache=cache
    )

@router.get("/login")
async def login(request: Request):
    """Gera a URL de login da Microsoft e redireciona o usuário."""
    settings = get_settings()
    app = _build_msal_app()
    
    # State is used to prevent CSRF, but we'll keep it simple for MVP
    # In a real scenario, save the state in a secure cookie
    auth_url = app.get_authorization_request_url(
        SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
    )
    
    logger.info("Redirecionando para login da Microsoft")
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(code: str, request: Request):
    """Recebe o authorization_code e troca por access_token e refresh_token."""
    settings = get_settings()
    app = _build_msal_app()
    
    # Obtém o token
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
    )
    
    if "error" in result:
        logger.error(f"Erro na autenticação: {result.get('error_description')}")
        raise HTTPException(status_code=400, detail=result.get("error_description"))
        
    # Extrai os tokens
    access_token = result.get("access_token")
    refresh_token = result.get("refresh_token")
    
    if not refresh_token:
        logger.warning("Nenhum refresh token recebido. Verifique o escopo offline_access.")
    else:
        from taskflow.adapters.persistence.credentials_store import save_credential
        await save_credential("ms_graph_refresh_token", refresh_token)
        logger.info("Refresh token salvo com sucesso.")
        
    # Redireciona o usuário de volta para o Dashboard (SPA)
    return RedirectResponse("http://localhost:5173/settings?auth_success=true")
