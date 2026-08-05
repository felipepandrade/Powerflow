import { useState, useEffect } from 'react';
import { checkHealth } from '../api/client';

export const Settings = () => {
  const [provider, setProvider] = useState(localStorage.getItem('llm_provider') || 'gemini');
  const [apiKey, setApiKey] = useState(localStorage.getItem('llm_api_key') || '');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [apiHealth, setApiHealth] = useState<'unknown' | 'online' | 'error'>('unknown');
  const [authSuccess, setAuthSuccess] = useState(false);

  useEffect(() => {
    checkHealth().then(() => setApiHealth('online')).catch(() => setApiHealth('error'));
    
    // Check if coming back from MS login
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth_success') === 'true') {
      setAuthSuccess(true);
      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => setAuthSuccess(false), 5000);
    }
  }, []);

  const handleSave = () => {
    setStatus('saving');
    localStorage.setItem('llm_provider', provider);
    localStorage.setItem('llm_api_key', apiKey);
    
    // Simulate slight delay for feedback
    setTimeout(() => {
      setStatus('saved');
      setTimeout(() => setStatus('idle'), 2000);
    }, 400);
  };

  const handleMicrosoftLogin = () => {
    window.location.href = "http://localhost:8000/api/auth/login";
  };

  return (
    <div className="max-w-3xl animate-in fade-in slide-in-from-bottom-4 duration-500">
      <h2 className="text-4xl font-bold tracking-tight mb-2">Ajustes</h2>
      <p className="text-muted mb-12 text-lg">Configurações globais e conectividade com Inteligência Artificial.</p>

      <div className="space-y-8">
        <section className="card">
          <h3 className="text-xl font-semibold mb-6 flex items-center gap-3">
            <div className="w-1 h-6 bg-accent"></div>
            Configuração de Inteligência Artificial
          </h3>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-muted mb-2 uppercase tracking-widest text-xs">
                Provedor de IA
              </label>
              <select 
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="input-field max-w-sm"
              >
                <option value="gemini">Google Gemini (Default)</option>
                <option value="chatgpt_subscription">Assinatura ChatGPT (OAuth - Usar Franquia)</option>
                <option value="copilot_web">Microsoft Copilot Corporativo (Sessão Web Edge)</option>
                <option value="fake">Fake (Mock / Testes)</option>
                <option value="openai">OpenAI Platform (API Key)</option>
              </select>
            </div>

            {provider === 'chatgpt_subscription' && (
              <div className="p-4 bg-accent/10 border border-accent/30 rounded-lg space-y-3">
                <h4 className="text-sm font-semibold text-white">Conectar Conta do ChatGPT (OAuth PKCE)</h4>
                <p className="text-xs text-muted">
                  Conecte sua conta do ChatGPT (Plus, Team ou Pro) para usar os modelos sem pagar tokens avulsos da API.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    fetch('http://localhost:8000/api/auth/openai-subscription/login')
                      .then((r) => r.json())
                      .then((data) => {
                        if (data.auth_url) window.open(data.auth_url, '_blank');
                      });
                  }}
                  className="px-4 py-2 bg-accent text-white text-xs font-bold rounded hover:bg-accent/80 transition-colors"
                >
                  🔐 Conectar Assinatura ChatGPT via OAuth
                </button>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-muted mb-2 uppercase tracking-widest text-xs">
                Chave da API (Opcional para Fake)
              </label>
              <input 
                type="password" 
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Insira sua API Key..."
                className="input-field max-w-md"
              />
              <p className="text-surface2 text-xs mt-2">Sua chave é armazenada apenas localmente no seu navegador (localStorage).</p>
            </div>

            <div className="pt-4 border-t border-surface2">
              <button 
                onClick={handleSave}
                disabled={status === 'saving'}
                className="btn-primary"
              >
                {status === 'saving' ? 'Salvando...' : status === 'saved' ? 'Salvo ✓' : 'Salvar Configurações'}
              </button>
            </div>
          </div>
        </section>

        <section className="card">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-3">
            <div className="w-1 h-6 bg-blue-500"></div>
            Integrações
          </h3>
          
          {authSuccess && (
            <div className="mb-4 p-3 bg-accent/20 border border-accent text-accent rounded-md flex items-center gap-2 animate-in fade-in">
              <span>✓ Conta Microsoft conectada com sucesso!</span>
            </div>
          )}

          <div className="space-y-4">
            <p className="text-muted">Conecte sua conta corporativa para permitir a captura de tarefas.</p>
            <button 
              onClick={handleMicrosoftLogin}
              className="px-4 py-2 bg-[#2F2F2F] hover:bg-[#3F3F3F] text-white rounded-md font-medium transition-colors border border-[#4F4F4F] flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z"/>
              </svg>
              Conectar Microsoft 365
            </button>
          </div>
        </section>

        <section className="card">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-3">
            <div className="w-1 h-6 bg-surface2"></div>
            Diagnóstico do Sistema
          </h3>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-muted">Status do Backend (API):</span>
            {apiHealth === 'unknown' && <span className="text-surface2">Verificando...</span>}
            {apiHealth === 'online' && <span className="text-accent font-medium flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-accent animate-pulse"></div> Online</span>}
            {apiHealth === 'error' && <span className="text-red-400 font-medium flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-red-400"></div> Offline</span>}
          </div>
        </section>
      </div>
    </div>
  );
};
