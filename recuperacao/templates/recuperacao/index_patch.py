# This script shows exactly what to change in index.html
# Run from the project folder: python index_patch.py index.html

import sys, re

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
with open(path, encoding="utf-8") as f:
    html = f.read()

# 1. Add conversation sidebar CSS
old_css = "  @keyframes bounce"
new_css = """  /* conversas sidebar */
  .app-layout{display:flex;height:calc(100vh - 115px);overflow:hidden}
  .conv-sidebar{width:240px;min-width:200px;background:var(--accent);display:flex;flex-direction:column;border-right:1px solid #0f2540;overflow:hidden}
  .conv-sidebar-header{padding:12px 16px;border-bottom:1px solid rgba(255,255,255,.1);display:flex;justify-content:space-between;align-items:center}
  .conv-sidebar-header span{color:rgba(255,255,255,.7);font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:600}
  .btn-nova-conversa{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);color:#fff;padding:4px 10px;font-size:11px;border-radius:2px;cursor:pointer;font-family:var(--sans);font-weight:600;transition:background .15s}
  .btn-nova-conversa:hover{background:rgba(255,255,255,.22)}
  .conv-lista{flex:1;overflow-y:auto;padding:8px 0}
  .conv-item{padding:9px 16px;cursor:pointer;border-left:3px solid transparent;transition:all .15s;display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
  .conv-item:hover{background:rgba(255,255,255,.08)}
  .conv-item.active{background:rgba(255,255,255,.15);border-left-color:#fff}
  .conv-item-titulo{font-size:12px;color:rgba(255,255,255,.85);line-height:1.4;flex:1;word-break:break-word}
  .conv-item-data{font-size:10px;color:rgba(255,255,255,.4);white-space:nowrap;margin-top:2px}
  .conv-item-apagar{opacity:0;background:none;border:none;color:rgba(255,255,255,.4);cursor:pointer;font-size:14px;padding:0 2px;transition:opacity .15s}
  .conv-item:hover .conv-item-apagar{opacity:1}
  .conv-item-apagar:hover{color:#fff}
  .content-area{flex:1;overflow-y:auto;display:flex;flex-direction:column}
  @keyframes bounce"""

html = html.replace(old_css, new_css)

# 2. Replace the chat tab panel structure to include sidebar
old_panel = """<!-- TAB 1: CHAT -->
<div id="tab-chat" class="panel active">
<div class="main chat-layout">

  <div class="chat-panel">
    <div id="historico">
      <div class="empty-state">Coloca uma questão jurídica para começar.</div>
    </div>
    <div class="loading" id="loading-chat">
      <div class="dots"><span></span><span></span><span></span></div>
      A consultar documentos e a gerar resposta…
    </div>
    <div class="input-area">
      <label for="input-pergunta">Questão jurídica</label>
      <textarea id="input-pergunta" placeholder="Ex: Quais os pressupostos da responsabilidade civil extracontratual?" rows="3"></textarea>
      <div class="input-actions">
        <span class="hint">Enter para enviar · Shift+Enter para nova linha</span>
        <button id="btn-enviar" class="btn-primary">Enviar</button>
      </div>
    </div>
  </div>

  <div class="sidebar">
    <div class="card">
      <div class="card-title">Fontes recuperadas</div>
      <div id="fontes-lista"><div style="font-size:12px;color:var(--ink-muted);font-style:italic">As fontes da última resposta aparecem aqui.</div></div>
    </div>
    <div class="card">
      <div class="card-title">Configuração</div>
      <div class="info-row"><span class="info-key">Modelo LLM</span><span class="info-value">{{ modelo }}</span></div>
      <div class="info-row"><span class="info-key">Embedder</span><span class="info-value">{{ embedder }}</span></div>
      <div class="info-row"><span class="info-key">Chunks indexados</span><span class="info-value">{{ n_docs }}</span></div>
    </div>
  </div>

</div>
</div>"""

new_panel = """<!-- TAB 1: CHAT -->
<div id="tab-chat" class="panel active">
<div class="app-layout">

  <!-- Sidebar de conversas -->
  <div class="conv-sidebar">
    <div class="conv-sidebar-header">
      <span>Conversas</span>
      <button class="btn-nova-conversa" onclick="novaConversa()">+ Nova</button>
    </div>
    <div class="conv-lista" id="conv-lista">
      <div style="padding:16px;font-size:11px;color:rgba(255,255,255,.4);font-style:italic">A carregar…</div>
    </div>
  </div>

  <!-- Área principal -->
  <div class="content-area">
    <div class="main chat-layout" style="flex:1;overflow-y:auto">

      <div class="chat-panel">
        <div id="historico">
          <div class="empty-state">Selecciona uma conversa ou cria uma nova.</div>
        </div>
        <div class="loading" id="loading-chat">
          <div class="dots"><span></span><span></span><span></span></div>
          A consultar documentos e a gerar resposta…
        </div>
        <div class="input-area">
          <label for="input-pergunta">Questão jurídica</label>
          <textarea id="input-pergunta" placeholder="Ex: Quais os pressupostos da responsabilidade civil extracontratual?" rows="3"></textarea>
          <div class="input-actions">
            <span class="hint">Enter para enviar · Shift+Enter para nova linha</span>
            <button id="btn-enviar" class="btn-primary">Enviar</button>
          </div>
        </div>
      </div>

      <div class="sidebar">
        <div class="card">
          <div class="card-title">Fontes recuperadas</div>
          <div id="fontes-lista"><div style="font-size:12px;color:var(--ink-muted);font-style:italic">As fontes da última resposta aparecem aqui.</div></div>
        </div>
        <div class="card">
          <div class="card-title">Configuração</div>
          <div class="info-row"><span class="info-key">Modelo LLM</span><span class="info-value">{{ modelo }}</span></div>
          <div class="info-row"><span class="info-key">Embedder</span><span class="info-value">{{ embedder }}</span></div>
          <div class="info-row"><span class="info-key">Chunks indexados</span><span class="info-value">{{ n_docs }}</span></div>
        </div>
      </div>

    </div>
  </div>

</div>
</div>"""

html = html.replace(old_panel, new_panel)

# 3. Update JS — add conversation management
old_chat_js = """// ── Chat ──────────────────────────────────────────────────────────────────
const inputEl   = document.getElementById('input-pergunta');
const btnEnviar = document.getElementById('btn-enviar');

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviarPergunta(); }
});
btnEnviar.addEventListener('click', enviarPergunta);

async function enviarPergunta() {
  const pergunta = inputEl.value.trim();
  if (!pergunta) return;
  const hist  = document.getElementById('historico');
  const empty = hist.querySelector('.empty-state');
  if (empty) empty.remove();
  addBubble('pergunta', pergunta);
  inputEl.value = '';
  btnEnviar.disabled = true;
  document.getElementById('loading-chat').classList.add('active');
  document.getElementById('fontes-lista').innerHTML = '';
  try {
    const res  = await fetch('/api/pergunta/', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({pergunta}) });
    const data = await res.json();
    if (data.erro) addBubble('resposta', '⚠ ' + data.erro);
    else { addBubble('resposta', data.resposta); renderFontes(data.fontes); }
  } catch(e) { addBubble('resposta', 'Erro de ligação ao servidor.'); }
  finally {
    document.getElementById('loading-chat').classList.remove('active');
    btnEnviar.disabled = false;
    inputEl.focus();
  }
}"""

new_chat_js = """// ── Conversas ────────────────────────────────────────────────────────────
let conversaActualId = null;

// Carregar lista de conversas ao iniciar
document.addEventListener('DOMContentLoaded', () => {
  carregarConversas();
  novaConversa();  // começa com conversa nova
});

async function carregarConversas() {
  try {
    const res  = await fetch('/api/conversas/');
    const data = await res.json();
    renderConvLista(data.conversas);
  } catch(e) { console.error('Erro ao carregar conversas:', e); }
}

function renderConvLista(conversas) {
  const lista = document.getElementById('conv-lista');
  if (!conversas.length) {
    lista.innerHTML = '<div style="padding:16px;font-size:11px;color:rgba(255,255,255,.4);font-style:italic">Sem conversas anteriores.</div>';
    return;
  }
  lista.innerHTML = conversas.map(c => `
    <div class="conv-item ${c.id === conversaActualId ? 'active' : ''}" onclick="carregarConversa(${c.id})" id="conv-item-${c.id}">
      <div>
        <div class="conv-item-titulo">${escHtml(c.titulo)}</div>
        <div class="conv-item-data">${c.alterada_em}</div>
      </div>
      <button class="conv-item-apagar" onclick="event.stopPropagation();apagarConversa(${c.id})" title="Apagar">×</button>
    </div>`).join('');
}

async function novaConversa() {
  conversaActualId = null;
  document.getElementById('historico').innerHTML =
    '<div class="empty-state">Coloca uma questão jurídica para começar.</div>';
  document.getElementById('fontes-lista').innerHTML =
    '<div style="font-size:12px;color:var(--ink-muted);font-style:italic">As fontes da última resposta aparecem aqui.</div>';
  // Desactivar item activo
  document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
  document.getElementById('input-pergunta').focus();
}

async function carregarConversa(id) {
  try {
    const res  = await fetch(`/api/conversas/${id}/`);
    const data = await res.json();
    conversaActualId = id;

    // Marcar activo na sidebar
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    const item = document.getElementById(`conv-item-${id}`);
    if (item) item.classList.add('active');

    // Renderizar mensagens
    const hist = document.getElementById('historico');
    hist.innerHTML = '';
    if (!data.mensagens.length) {
      hist.innerHTML = '<div class="empty-state">Conversa vazia.</div>';
      return;
    }
    data.mensagens.forEach(m => {
      addBubble(m.papel === 'user' ? 'pergunta' : 'resposta', m.texto);
    });
    // Mostrar fontes da última resposta
    const ultResposta = data.mensagens.filter(m => m.papel === 'assistant').pop();
    if (ultResposta && ultResposta.fontes) renderFontes(ultResposta.fontes);

    hist.lastElementChild?.scrollIntoView({behavior:'smooth', block:'end'});
  } catch(e) { console.error('Erro ao carregar conversa:', e); }
}

async function apagarConversa(id) {
  if (!confirm('Apagar esta conversa?')) return;
  try {
    await fetch(`/api/conversas/${id}/apagar/`, {method:'DELETE'});
    if (conversaActualId === id) novaConversa();
    carregarConversas();
  } catch(e) { console.error('Erro ao apagar:', e); }
}

// ── Chat ──────────────────────────────────────────────────────────────────
const inputEl   = document.getElementById('input-pergunta');
const btnEnviar = document.getElementById('btn-enviar');

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviarPergunta(); }
});
btnEnviar.addEventListener('click', enviarPergunta);

async function enviarPergunta() {
  const pergunta = inputEl.value.trim();
  if (!pergunta) return;
  const hist  = document.getElementById('historico');
  const empty = hist.querySelector('.empty-state');
  if (empty) empty.remove();
  addBubble('pergunta', pergunta);
  inputEl.value = '';
  btnEnviar.disabled = true;
  document.getElementById('loading-chat').classList.add('active');
  document.getElementById('fontes-lista').innerHTML = '';
  try {
    const res  = await fetch('/api/pergunta/', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({pergunta, conversa_id: conversaActualId})
    });
    const data = await res.json();
    if (data.erro) {
      addBubble('resposta', '⚠ ' + data.erro);
    } else {
      addBubble('resposta', data.resposta);
      renderFontes(data.fontes);
      // Actualizar ID e lista de conversas
      conversaActualId = data.conversa_id;
      carregarConversas();
      // Marcar activo
      setTimeout(() => {
        document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
        const item = document.getElementById(`conv-item-${data.conversa_id}`);
        if (item) item.classList.add('active');
      }, 300);
    }
  } catch(e) { addBubble('resposta', 'Erro de ligação ao servidor.'); }
  finally {
    document.getElementById('loading-chat').classList.remove('active');
    btnEnviar.disabled = false;
    inputEl.focus();
  }
}"""

html = html.replace(old_chat_js, new_chat_js)

# 4. Update fetch URLs for new app structure
html = html.replace("'/api/itij/pesquisar/", "'/ingestao/pesquisar/")
html = html.replace('"/api/itij/pesquisar/', '"/ingestao/pesquisar/')
html = html.replace("'/api/itij/indexar/",   "'/ingestao/indexar/")
html = html.replace('"/api/itij/indexar/',   '"/ingestao/indexar/')
html = html.replace("'/api/itij/sumario/",   "'/ingestao/sumario/")
html = html.replace('"/api/itij/sumario/',   '"/ingestao/sumario/')
html = html.replace("'/api/gerar_peca/",     "'/geracao/gerar/")
html = html.replace('"/api/gerar_peca/',     '"/geracao/gerar/')

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"OK — {path} actualizado")