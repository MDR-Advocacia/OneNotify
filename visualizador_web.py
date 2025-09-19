# arquivo: visualizador_web.py
import sqlite3
import json
import os
import webbrowser
import re
from threading import Timer
from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, flash

# Importa as funções do módulo de banco de dados central
import database

# --- CONFIGURAÇÃO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, database.DB_NOME)
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')

app = Flask(__name__)
app.secret_key = 'super-secret-key-for-rpa-dashboard'

# --- ANTI-CACHE PARA DESENVOLVIMENTO ---
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# --- FUNÇÕES AUXILIARES ---
def formatar_duracao(segundos):
    try:
        segundos = float(segundos)
    except (ValueError, TypeError):
        return "0 segundos"
    if segundos < 0: return "0 segundos"
    if segundos < 60:
        return f"{segundos:.1f} segundos"
    minutos, seg = divmod(segundos, 60)
    return f"{int(minutos)} minuto(s) e {int(seg)} segundo(s)"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_pagination_range(current_page, total_pages, context_size=2):
    if total_pages <= 1:
        return []

    pages = set()
    pages.add(1)
    pages.add(total_pages)

    for i in range(context_size + 1):
        pages.add(max(1, current_page - i))
        pages.add(min(total_pages, current_page + i))

    page_list = sorted(list(pages))
    
    pagination_range = []
    last_page = 0
    for page in page_list:
        if last_page != 0 and page - last_page > 1:
            pagination_range.append('...')
        pagination_range.append(page)
        last_page = page
        
    return pagination_range


# --- TEMPLATE HTML E CSS ATUALIZADO ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OneNotify - Dashboard</title>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        /* ============================================== */
        /* ===         RESET E ESTILOS GLOBAIS        === */
        /* ============================================== */
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          background: linear-gradient(120deg, #1d2b4b 0%, #3a506b 100%);
          color: #e0e0e0;
          min-height: 100vh;
        }
        /* ============================================== */
        /* ===             ESTRUTURA GERAL            === */
        /* ============================================== */
        .App {
          text-align: center;
        }
        .App-header {
          display: flex;
          align-items: center;
          justify-content: flex-start; /* Alinha o título à esquerda */
          padding: 1rem 2rem;
          color: white;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.15);
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        .main-title {
            font-size: 1.75rem; /* Tamanho um pouco menor e mais sutil */
            font-weight: 600; /* Um pouco menos pesado que o bold padrão */
            color: #e0e0e0;
        }
        .panel-container {
          padding: 2rem;
          max-width: 1800px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }
        .input-section, .results-section {
          padding: 2rem;
          text-align: left;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.08);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          border: 1px solid rgba(255, 255, 255, 0.18);
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        }
        .input-section h2, .results-section h2 {
          margin-bottom: 1.5rem;
          color: #ffffff;
          border-bottom: 2px solid #5bc0de;
          padding-bottom: 0.5rem;
          display: inline-block;
        }
        /* ============================================== */
        /* ===           INPUTS E BOTÕES              === */
        /* ============================================== */
        select, textarea, input.filter-input, .item-add-form input, input[type="text"], input[type="date"] {
          width: 100%;
          padding: 12px;
          margin-bottom: 1rem;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          font-size: 1rem;
          background: rgba(0, 0, 0, 0.2);
          color: #f0f0f0;
        }
        textarea {
            min-height: 120px;
            resize: vertical;
        }
        textarea::placeholder, input::placeholder {
          color: #a0a0a0;
        }
        .button-group {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
          align-items: center;
        }
        button {
          padding: 12px 24px;
          border: none;
          border-radius: 8px;
          color: white;
          background-color: #5bc0de;
          cursor: pointer;
          font-weight: bold;
          font-size: 1rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(91, 192, 222, 0.4);
        }
        button:disabled {
          background-color: #555;
          cursor: not-allowed;
          opacity: 0.6;
        }
        /* ============================================== */
        /* ===             TABELA E FILTROS           === */
        /* ============================================== */
        .filter-container {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 1rem;
          align-items: flex-end;
        }
        .filter-group {
          display: flex;
          flex-direction: column;
        }
        .filter-group.search-field {
            grid-column: 1 / -1; /* Ocupa a linha inteira */
        }
        .filter-group label {
          margin-bottom: 0.5rem;
          font-weight: bold;
          text-align: left;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 1.5rem;
          color: #e0e0e0;
        }
        th, td {
          padding: 15px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          text-align: left;
          vertical-align: middle;
        }
        thead {
          background-color: rgba(0, 0, 0, 0.2);
        }
        th {
          font-weight: bold;
          color: #ffffff;
        }
        tbody tr:hover {
          background-color: rgba(91, 192, 222, 0.1);
        }
        .status {
          display: inline-block;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          vertical-align: middle;
        }
        .status-Pendente { background-color: #f0ad4e; }
        .status-Processado, .status-Processado-em-Teste { background-color: #007bff; }
        .status-Arquivado { background-color: #6c757d; }
        .status-Erro { background-color: #dc3545; }
        .badge { background-color: #5bc0de; color: #1d2b4b; border-radius: 10px; padding: 3px 8px; font-size: 0.8em; font-weight: bold; margin-left: 8px; }
        /* ============================================== */
        /* ===        PAGINAÇÃO E AÇÕES EM LOTE       === */
        /* ============================================== */
        .pagination-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.5rem;
            padding: 10px;
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .items-per-page-selector {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .items-per-page-selector select {
            padding: 8px;
            margin: 0;
            width: auto;
        }
        .page-navigation { display: flex; align-items: center; gap: 5px; }
        .page-navigation a, .page-navigation span {
            color: white;
            padding: 8px 12px;
            text-decoration: none;
            border-radius: 4px;
            border: 1px solid transparent;
            transition: all 0.3s ease;
        }
        .page-navigation a:hover {
            background-color: #5bc0de;
            border-color: #5bc0de;
        }
        .page-navigation .active {
            background-color: #5bc0de;
            font-weight: bold;
            border-color: #5bc0de;
        }
        .page-navigation .disabled {
            color: #777;
            cursor: not-allowed;
        }
        .page-navigation .ellipsis {
            padding: 8px 0;
        }
        .flash-message {
            padding: 1em;
            margin-bottom: 1.5rem;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
            color: white;
        }
        .flash-success { background-color: rgba(40, 167, 69, 0.3); border-left: 5px solid #28a745; }
        .flash-warning { background-color: rgba(255, 193, 7, 0.3); border-left: 5px solid #ffc107; }
        a { color: #5bc0de; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .publication-text { white-space: pre-wrap; background-color: rgba(0,0,0,0.3); padding: 10px; margin-top: 5px; border-radius: 4px; font-family: monospace; max-height: 200px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.1); }
        .bulk-actions-select {
            padding: 12px;
            margin: 0;
            width: auto;
            flex-grow: 0;
        }
        /* ============================================== */
        /* ===          MENU DE AÇÕES (GEAR)          === */
        /* ============================================== */
        .actions-cell { position: relative; }
        .actions-button {
            background: none;
            border: none;
            color: #e0e0e0;
            cursor: pointer;
            padding: 5px;
            border-radius: 50%;
        }
        .actions-button:hover { background-color: rgba(255, 255, 255, 0.2); }
        .dropdown-menu {
            display: none;
            position: absolute;
            right: 0;
            top: 40px;
            background-color: #3a506b;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            z-index: 100;
            min-width: 180px;
        }
        .dropdown-menu.show { display: block; }
        .dropdown-item, .dropdown-header {
            padding: 10px 15px;
            color: white;
            text-decoration: none;
            display: block;
            text-align: left;
            background: none;
            border: none;
            width: 100%;
            cursor: pointer;
        }
        .dropdown-item:hover { background-color: #5bc0de; }
        .dropdown-header { font-weight: bold; color: #bbb; cursor: default; }
        .dropdown-divider { height: 1px; background-color: rgba(255,255,255,0.1); margin: 5px 0; }
        .submenu { position: relative; }
        .submenu .submenu-items {
            display: none;
            position: absolute;
            left: 100%;
            top: 0;
            background-color: #3a506b;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
        }
        .submenu:hover .submenu-items { display: block; }

        /* ============================================== */
        /* ===      ESTILOS ABAS E OUTROS             === */
        /* ============================================== */
        .modal-tabs {
          display: flex;
          border-bottom: 1px solid rgba(255, 255, 255, 0.2);
          margin-bottom: 2rem;
        }
        .tab-button {
          padding: 10px 20px;
          cursor: pointer;
          background-color: transparent;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          font-size: 1rem;
          border-bottom: 3px solid transparent;
          margin-bottom: -1px;
        }
        .tab-button.active {
          color: white;
          border-bottom: 3px solid #5bc0de;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .user-management-form { display: flex; gap: 1rem; margin-bottom: 2rem; }
        .user-management-form input { flex-grow: 1; margin: 0; }
        .user-management-form button { flex-shrink: 0; }
        .user-list-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .user-list-item button { background-color: #dc3545; font-size: 0.9rem; padding: 8px 16px;}
        .instruction-box {
            background-color: rgba(0, 0, 0, 0.2);
            border-left: 4px solid #f0ad4e;
            padding: 15px;
            border-radius: 8px;
            margin-top: 1.5rem;
        }
        .instruction-box p { margin-bottom: 10px; }
        .instruction-box code {
            background-color: rgba(0,0,0,0.3);
            padding: 3px 6px;
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="App">
        <header class="App-header">
            <h1 class="main-title">OneNOTIFY</h1>
        </header>

        <div class="panel-container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message | safe }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="modal-tabs">
                <button class="tab-button active" onclick="openTab(event, 'Dashboard')">Dashboard Principal</button>
                <button class="tab-button" onclick="openTab(event, 'Logs')">Histórico</button>
                <button class="tab-button" onclick="openTab(event, 'Usuarios')">Usuários</button>
                <button class="tab-button" onclick="openTab(event, 'Teste')">Sessão de Teste</button>
            </div>

            <div id="Dashboard" class="tab-content active">
                <section class="input-section">
                    <form method="get">
                        <div class="filter-container">
                             <div class="filter-group search-field">
                                <label for="busca-input">Buscar por NPJ ou Nº Processo:</label>
                                <input type="text" id="busca-input" name="busca" value="{{ termo_busca }}" placeholder="Digite para buscar...">
                            </div>
                            <div class="filter-group">
                                <label for="status-filter">Status:</label>
                                <select id="status-filter" name="status">
                                    <option value="Todos" {% if status_selecionado == 'Todos' %}selected{% endif %}>Todos</option>
                                    <option value="Processado" {% if status_selecionado == 'Processado' %}selected{% endif %}>Processado</option>
                                    <option value="Pendente" {% if status_selecionado == 'Pendente' %}selected{% endif %}>Pendente</option>
                                    <option value="Arquivado" {% if status_selecionado == 'Arquivado' %}selected{% endif %}>Arquivado</option>
                                    <option value="Erro" {% if status_selecionado == 'Erro' %}selected{% endif %}>Erro</option>
                                </select>
                            </div>
                            <div class="filter-group">
                                <label for="tipo-filter">Tipo de Notificação:</label>
                                <select id="tipo-filter" name="tipo">
                                    <option value="Todos" {% if tipo_selecionado == 'Todos' %}selected{% endif %}>Todos</option>
                                    {% for tipo in tipos_notificacao %}<option value="{{ tipo }}" {% if tipo_selecionado == tipo %}selected{% endif %}>{{ tipo }}</option>{% endfor %}
                                </select>
                            </div>
                             <div class="filter-group">
                                <label for="responsavel-filter">Responsável:</label>
                                <select id="responsavel-filter" name="responsavel">
                                    <option value="Todos" {% if responsavel_selecionado == 'Todos' %}selected{% endif %}>Todos</option>
                                    <option value="Nenhum" {% if responsavel_selecionado == 'Nenhum' %}selected{% endif %}>Nenhum</option>
                                    {% for usuario in usuarios %}<option value="{{ usuario.id }}" {% if responsavel_selecionado == usuario.id|string %}selected{% endif %}>{{ usuario.nome }}</option>{% endfor %}
                                </select>
                            </div>
                            <div class="filter-group">
                                <label for="data-inicio">Data Início:</label>
                                <input type="date" id="data-inicio" name="data_inicio" value="{{ data_inicio_filtro }}">
                            </div>
                            <div class="filter-group">
                                <label for="data-fim">Data Fim:</label>
                                <input type="date" id="data-fim" name="data_fim" value="{{ data_fim_filtro }}">
                            </div>
                            <div class="filter-group">
                                <button type="submit" style="margin-top: 28px;">Filtrar</button>
                            </div>
                        </div>
                    </form>
                </section>
                
                <section class="results-section">
                    <form id="bulk-action-form" action="" method="post">
                        <div class="button-group">
                            <label for="bulk-action-select" class="visually-hidden">Ação em lote</label>
                            <select id="bulk-action-select" class="bulk-actions-select" name="acao">
                                <option value="arquivar">Arquivar Selecionados</option>
                                <option value="atribuir">Atribuir Selecionados a...</option>
                                <option value="desatribuir">Remover Atribuição dos Selecionados</option>
                            </select>
                            <select id="bulk-user-select" class="bulk-actions-select" name="usuario_id" style="display:none;">
                                {% for usuario in usuarios %}
                                <option value="{{ usuario.id }}">{{ usuario.nome }}</option>
                                {% endfor %}
                            </select>
                            <button type="submit">Aplicar</button>
                        </div>
                        
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 3%;"><input type="checkbox" id="select-all"></th>
                                    <th>NPJ</th>
                                    <th>Nº do Processo</th>
                                    <th>Responsável</th>
                                    <th>Tipo(s) de Notificação</th>
                                    <th>Data da Notificação</th>
                                    <th>Status</th>
                                    <th>Andamentos e Documentos</th>
                                    <th style="width: 5%;">Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for reg in registros %}
                                <tr>
                                    <td><input type="checkbox" name="selecao_npj" value="{{ reg.NPJ }}" class="row-checkbox"></td>
                                    <td>{{ reg.NPJ }} {% if reg.notificacao_count > 1 %}<span class="badge" title="{{ reg.notificacao_count }} notificações para esta data">{{ reg.notificacao_count }}</span>{% endif %}</td>
                                    <td>{{ reg.numero_processo }}</td>
                                    <td>{{ reg.responsavel_nome or 'N/A' }}</td>
                                    <td>{{ reg.tipos_notificacao.replace(',', '<br>') | safe }}</td>
                                    <td>{{ reg.data_notificacao }}</td>
                                    <td><span class="status status-{{ reg.status.replace(' ', '-') }}" title="{{ reg.status }}"></span></td>
                                    <td>
                                        {% if reg.andamentos %}
                                            {% for andamento in reg.andamentos %}
                                                {% if andamento.texto %}<details><summary>{{ andamento.data }} - {{ andamento.tipo }}</summary><div class="publication-text">{{ andamento.texto }}</div></details>
                                                {% else %}<div>{{ andamento.data }} - {{ andamento.tipo }}</div>{% endif %}
                                            {% endfor %}
                                        {% endif %}
                                        {% if reg.documentos %}
                                            <div style="margin-top: 10px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 10px;">
                                            {% for doc in reg.documentos %}<div><a href="/downloads/{{ doc.caminho_relativo | replace('\\\\', '/') }}" download>{{ doc.nome_arquivo }}</a></div>{% endfor %}
                                            </div>
                                        {% endif %}
                                    </td>
                                    <td class="actions-cell">
                                        <button type="button" class="actions-button" onclick="toggleDropdown(event)">
                                            <i class="material-icons">settings</i>
                                        </button>
                                        <div class="dropdown-menu">
                                            <div class="dropdown-header">Atribuir/Transferir para:</div>
                                            {% for usuario in usuarios %}
                                                <form action="{{ url_for('atribuir_lote') }}" method="post" style="margin:0;">
                                                    <input type="hidden" name="selecao_npj" value="{{ reg.NPJ }}">
                                                    <input type="hidden" name="usuario_id" value="{{ usuario.id }}">
                                                    <button type="submit" class="dropdown-item">{{ usuario.nome }}</button>
                                                </form>
                                            {% endfor %}
                                            <div class="dropdown-divider"></div>
                                            <form action="{{ url_for('desatribuir_lote') }}" method="post" style="margin:0;">
                                                 <input type="hidden" name="selecao_npj" value="{{ reg.NPJ }}">
                                                 <button type="submit" class="dropdown-item">Remover Atribuição</button>
                                            </form>
                                            <div class="dropdown-divider"></div>
                                            {% if reg.status in ['Processado', 'Processado em Teste'] %}
                                                <form action="{{ url_for('arquivar', npj=reg.NPJ) }}" method="post" style="margin:0;"><button type="submit" class="dropdown-item">Arquivar</button></form>
                                            {% elif reg.status == 'Arquivado' %}
                                                <form action="{{ url_for('desarquivar', npj=reg.NPJ) }}" method="post" style="margin:0;"><button type="submit" class="dropdown-item">Desarquivar</button></form>
                                            {% endif %}
                                        </div>
                                    </td>
                                </tr>
                                {% else %}
                                <tr><td colspan="9" style="text-align:center; padding: 20px;">Nenhuma notificação encontrada para os filtros selecionados.</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </form>
                        
                    <div class="pagination-container">
                        <div class="items-per-page-selector">
                            <label for="per-page">Itens por página:</label>
                            <select id="per-page" onchange="changeItemsPerPage(this)">
                                <option value="10" {% if itens_por_pagina == 10 %}selected{% endif %}>10</option>
                                <option value="20" {% if itens_por_pagina == 20 %}selected{% endif %}>20</option>
                                <option value="50" {% if itens_por_pagina == 50 %}selected{% endif %}>50</option>
                                <option value="100" {% if itens_por_pagina == 100 %}selected{% endif %}>100</option>
                            </select>
                        </div>

                        <div class="page-navigation">
                            {% if total_paginas > 1 %}
                                <a href="{{ url_for('index', page=1, **query_params) }}" class="{{ 'disabled' if pagina_atual == 1 else '' }}">&laquo;</a>
                                <a href="{{ url_for('index', page=pagina_atual - 1, **query_params) }}" class="{{ 'disabled' if pagina_atual == 1 else '' }}">&lsaquo;</a>
                                {% for p in pagination_range %}
                                    {% if p == '...' %}<span class="ellipsis">...</span>
                                    {% elif p == pagina_atual %}<span class="active">{{ p }}</span>
                                    {% else %}<a href="{{ url_for('index', page=p, **query_params) }}">{{ p }}</a>
                                    {% endif %}
                                {% endfor %}
                                <a href="{{ url_for('index', page=pagina_atual + 1, **query_params) }}" class="{{ 'disabled' if pagina_atual == total_paginas else '' }}">&rsaquo;</a>
                                <a href="{{ url_for('index', page=total_paginas, **query_params) }}" class="{{ 'disabled' if pagina_atual == total_paginas else '' }}">&raquo;</a>
                            {% endif %}
                        </div>
                    </div>
                </section>
            </div>

            <div id="Logs" class="tab-content">
                <section class="results-section">
                    <h2>Histórico Completo de Execuções da RPA</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Data e Hora</th><th>Duração Total</th><th>Notificações Novas</th>
                                <th>NPJs Processados</th><th>Documentos Baixados</th><th>Andamentos Capturados</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td>{{ log.timestamp }}</td><td>{{ formatar_duracao(log.duracao_total) }}</td>
                                <td>{{ log.notificacoes_salvas }}</td><td>{{ log.npjs_processados }}</td>
                                <td>{{ log.documentos_baixados }}</td><td>{{ log.andamentos_capturados }}</td>
                            </tr>
                            {% else %}
                            <tr><td colspan="6" style="text-align:center; padding: 20px;">Nenhum log de execução encontrado.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </section>
            </div>
            
            <div id="Usuarios" class="tab-content">
                <section class="input-section">
                    <h2>Gerenciar Usuários</h2>
                    <form action="{{ url_for('add_user') }}" method="post" class="user-management-form">
                        <input type="text" name="nome" placeholder="Primeiro nome do usuário" required>
                        <button type="submit">Adicionar Usuário</button>
                    </form>
                    <div class="user-list">
                        {% for usuario in usuarios %}
                        <div class="user-list-item">
                            <span>{{ usuario.nome }}</span>
                            <form action="{{ url_for('remove_user', usuario_id=usuario.id) }}" method="post" onsubmit="return confirm('Tem certeza que deseja remover este usuário? As notificações atribuídas a ele ficarão sem responsável.');">
                                <button type="submit">Remover</button>
                            </form>
                        </div>
                        {% else %}
                        <p>Nenhum usuário cadastrado.</p>
                        {% endfor %}
                    </div>
                </section>
            </div>

            <div id="Teste" class="tab-content">
                <section class="input-section">
                    <h2>Criar Sessão de Teste</h2>
                    <form action="{{ url_for('criar_teste') }}" method="post">
                        <div class="filter-group">
                            <label for="npjs-teste">Lista de NPJs para Teste</label>
                            <textarea id="npjs-teste" name="npjs_para_teste" placeholder="Cole os NPJs aqui, um por linha ou separados por vírgula/espaço."></textarea>
                        </div>
                        <button type="submit">Criar e Preparar Teste</button>
                    </form>
                    <div id="instruction-box-container">
                        <!-- As instruções aparecerão aqui via Flask flash messages -->
                    </div>
                </section>
            </div>
        </div>
    </div>
    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) { tabcontent[i].style.display = "none"; }
            tablinks = document.getElementsByClassName("tab-button");
            for (i = 0; i < tablinks.length; i++) { tablinks[i].className = tablinks[i].className.replace(" active", ""); }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }

        function changeItemsPerPage(select) {
            const newPerPage = select.value;
            const url = new URL(window.location.href);
            url.searchParams.set('per_page', newPerPage);
            url.searchParams.set('page', '1');
            window.location.href = url.toString();
        }
        
        function toggleDropdown(event) {
            // Fecha todos os outros dropdowns abertos
            document.querySelectorAll('.dropdown-menu.show').forEach(openDropdown => {
                if (openDropdown !== event.currentTarget.nextElementSibling) {
                    openDropdown.classList.remove('show');
                }
            });
            // Alterna o dropdown clicado
            event.currentTarget.nextElementSibling.classList.toggle('show');
            event.stopPropagation();
        }

        window.onclick = function(event) {
            if (!event.target.matches('.actions-button, .actions-button *')) {
                document.querySelectorAll('.dropdown-menu.show').forEach(openDropdown => {
                    openDropdown.classList.remove('show');
                });
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            // Lógica para abas
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab');
            if (tab) {
                const tabButton = document.querySelector(`.tab-button[onclick*="'${tab}'"]`);
                if (tabButton) {
                    tabButton.click();
                }
            }

            // Lógica para Ações em lote
            const selectAllCheckbox = document.getElementById('select-all');
            const rowCheckboxes = document.querySelectorAll('.row-checkbox');
            
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', function() {
                    rowCheckboxes.forEach(checkbox => { checkbox.checked = selectAllCheckbox.checked; });
                });
            }
            
            const bulkActionSelect = document.getElementById('bulk-action-select');
            const bulkUserSelect = document.getElementById('bulk-user-select');
            const bulkActionForm = document.getElementById('bulk-action-form');

            bulkActionSelect.addEventListener('change', function() {
                if (this.value === 'atribuir') {
                    bulkUserSelect.style.display = 'inline-block';
                } else {
                    bulkUserSelect.style.display = 'none';
                }
            });

            bulkActionForm.addEventListener('submit', function(e) {
                const selectedAction = bulkActionSelect.value;
                if (selectedAction === 'atribuir') {
                    bulkActionForm.action = "{{ url_for('atribuir_lote') }}";
                } else if (selectedAction === 'desatribuir') {
                    bulkActionForm.action = "{{ url_for('desatribuir_lote') }}";
                } else { // arquivar
                    bulkActionForm.action = "{{ url_for('arquivar_lote') }}";
                }
            });
        });
    </script>
</body>
</html>
"""

# --- ROTAS FLASK ---
@app.route('/')
def index():
    conn = get_db_connection()

    # --- Coleta de parâmetros de filtro e paginação ---
    status_filtro = request.args.get('status', 'Processado') 
    responsavel_filtro = request.args.get('responsavel', 'Todos')
    termo_busca = request.args.get('busca', '') 
    tipo_filtro = request.args.get('tipo', 'Todos')
    data_inicio_filtro = request.args.get('data_inicio', '')
    data_fim_filtro = request.args.get('data_fim', '')
    
    itens_por_pagina = request.args.get('per_page', 10, type=int)
    if itens_por_pagina not in [10, 20, 50, 100]:
        itens_por_pagina = 10

    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * itens_por_pagina
    
    # --- Construção da Query Principal ---
    query_base = f"""
        SELECT
            t.NPJ,
            t.data_notificacao,
            MAX(t.numero_processo) as numero_processo,
            u.nome as responsavel_nome,
            GROUP_CONCAT(DISTINCT t.tipo_notificacao) as tipos_notificacao,
            CASE
                WHEN SUM(CASE WHEN t.status = 'Erro' THEN 1 ELSE 0 END) > 0 THEN 'Erro'
                WHEN SUM(CASE WHEN t.status = 'Pendente' THEN 1 ELSE 0 END) > 0 THEN 'Pendente'
                ELSE MAX(t.status)
            END as status,
            MAX(t.andamentos) as andamentos,
            MAX(t.documentos) as documentos,
            MAX(t.data_criacao) as data_criacao_recente,
            COUNT(t.id) as notificacao_count
        FROM {database.TABELA_NOTIFICACOES} t
        LEFT JOIN {database.TABELA_USUARIOS} u ON t.usuario_id = u.id
    """
    conditions = []
    params = []

    if termo_busca:
        conditions.append("(t.NPJ LIKE ? OR t.numero_processo LIKE ?)")
        params.extend([f'%{termo_busca}%', f'%{termo_busca}%'])

    if status_filtro and status_filtro != 'Todos':
        conditions.append("t.status = ?")
        params.append(status_filtro)
    
    if tipo_filtro and tipo_filtro != 'Todos':
        # Esta condição precisa ser aplicada a um subconjunto de notificações antes do agrupamento.
        # Usamos uma subquery para filtrar os NPJs/Datas relevantes primeiro.
        conditions.append(f"(t.NPJ, t.data_notificacao) IN (SELECT NPJ, data_notificacao FROM {database.TABELA_NOTIFICACOES} WHERE tipo_notificacao = ?)")
        params.append(tipo_filtro)


    if responsavel_filtro != 'Todos':
        if responsavel_filtro == 'Nenhum':
            conditions.append("t.usuario_id IS NULL")
        else:
            conditions.append("t.usuario_id = ?")
            params.append(responsavel_filtro)
            
    if data_inicio_filtro:
        conditions.append("STRFTIME('%Y-%m-%d', SUBSTR(t.data_notificacao, 7, 4) || '-' || SUBSTR(t.data_notificacao, 4, 2) || '-' || SUBSTR(t.data_notificacao, 1, 2)) >= ?")
        params.append(data_inicio_filtro)
    if data_fim_filtro:
        conditions.append("STRFTIME('%Y-%m-%d', SUBSTR(t.data_notificacao, 7, 4) || '-' || SUBSTR(t.data_notificacao, 4, 2) || '-' || SUBSTR(t.data_notificacao, 1, 2)) <= ?")
        params.append(data_fim_filtro)
    
    if conditions:
        query_base += " WHERE " + " AND ".join(conditions)

    query_base += " GROUP BY t.NPJ, t.data_notificacao ORDER BY data_criacao_recente DESC"
    
    # --- Execução das Queries ---
    query_paginada = f"{query_base} LIMIT ? OFFSET ?"
    params_paginados = params + [itens_por_pagina, offset]
    registros = conn.execute(query_paginada, params_paginados).fetchall()

    count_query = f"SELECT COUNT(*) FROM ({query_base.replace('SELECT ... FROM', 'SELECT 1 FROM')})"
    total_registros = conn.execute(count_query, params).fetchone()[0]
    total_paginas = (total_registros + itens_por_pagina - 1) // itens_por_pagina

    # --- Processamento dos dados para o template ---
    registros_processados = []
    for reg in registros:
        reg_dict = dict(reg)
        try:
            reg_dict['andamentos'] = json.loads(reg_dict['andamentos']) if reg_dict.get('andamentos') else []
            reg_dict['documentos'] = json.loads(reg_dict['documentos']) if reg_dict.get('documentos') else []
        except (json.JSONDecodeError, TypeError):
            reg_dict['andamentos'] = []
            reg_dict['documentos'] = []
        registros_processados.append(reg_dict)
    
    usuarios = database.listar_usuarios()
    tipos_notificacao_query = f"SELECT DISTINCT tipo_notificacao FROM {database.TABELA_NOTIFICACOES} WHERE tipo_notificacao IS NOT NULL ORDER BY tipo_notificacao"
    tipos_notificacao = [row[0] for row in conn.execute(tipos_notificacao_query).fetchall()]
    logs_query = f"SELECT * FROM {database.TABELA_LOGS} ORDER BY id DESC"
    logs_raw = conn.execute(logs_query).fetchall()
    logs = []
    for row in logs_raw:
        log_item = dict(row)
        sucesso = log_item.get('npjs_sucesso', 0) or 0
        falha_raw = log_item.get('npjs_falha', 0)
        falha = 1 if isinstance(falha_raw, str) else (falha_raw or 0)
        log_item['npjs_processados'] = sucesso + falha
        logs.append(log_item)
    
    conn.close()

    # --- Preparação dos dados para renderização ---
    query_params = {
        'status': status_filtro, 
        'responsavel': responsavel_filtro,
        'per_page': itens_por_pagina,
        'busca': termo_busca,
        'tipo': tipo_filtro,
        'data_inicio': data_inicio_filtro,
        'data_fim': data_fim_filtro
    }
    
    return render_template_string(
        HTML_TEMPLATE,
        registros=registros_processados,
        logs=logs,
        usuarios=usuarios,
        tipos_notificacao=tipos_notificacao,
        pagina_atual=page,
        total_paginas=total_paginas,
        pagination_range=get_pagination_range(page, total_paginas),
        status_selecionado=status_filtro,
        tipo_selecionado=tipo_filtro,
        responsavel_selecionado=responsavel_filtro,
        data_inicio_filtro=data_inicio_filtro,
        data_fim_filtro=data_fim_filtro,
        itens_por_pagina=itens_por_pagina,
        query_params=query_params,
        termo_busca=termo_busca,
        formatar_duracao=formatar_duracao
    )

# --- ROTAS DE AÇÕES ---

@app.route('/arquivar/<string:npj>', methods=['POST'])
def arquivar(npj):
    database.arquivar_notificacao_por_npj(npj)
    flash(f'Notificações para o NPJ {npj} foram arquivadas.', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/desarquivar/<string:npj>', methods=['POST'])
def desarquivar(npj):
    database.desarquivar_notificacao_por_npj(npj)
    flash(f'Notificações para o NPJ {npj} foram desarquivadas.', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/arquivar_lote', methods=['POST'])
def arquivar_lote():
    npjs = request.form.getlist('selecao_npj')
    if npjs:
        database.arquivar_notificacoes_em_lote_por_npj(npjs)
        flash(f'{len(npjs)} NPJ(s) selecionado(s) foram arquivados.', 'success')
    else:
        flash('Nenhum NPJ selecionado.', 'warning')
    return redirect(request.referrer or url_for('index'))

@app.route('/atribuir_lote', methods=['POST'])
def atribuir_lote():
    npjs = request.form.getlist('selecao_npj')
    usuario_id = request.form.get('usuario_id')
    if npjs and usuario_id:
        database.atribuir_notificacoes_em_lote(npjs, usuario_id)
        flash(f'Notificações de {len(npjs)} NPJ(s) atribuídas.', 'success')
    else:
        flash('Seleção ou usuário inválido.', 'warning')
    return redirect(request.referrer or url_for('index'))

@app.route('/desatribuir_lote', methods=['POST'])
def desatribuir_lote():
    npjs = request.form.getlist('selecao_npj')
    if npjs:
        database.desatribuir_notificacoes_em_lote(npjs)
        flash(f'Atribuição removida para {len(npjs)} NPJ(s).', 'success')
    else:
        flash('Nenhum NPJ selecionado.', 'warning')
    return redirect(request.referrer or url_for('index'))


# --- ROTAS DE GESTÃO DE USUÁRIOS E TESTES ---

@app.route('/add_user', methods=['POST'])
def add_user():
    nome = request.form.get('nome')
    if nome:
        if database.adicionar_usuario(nome):
            flash('Usuário adicionado com sucesso!', 'success')
        else:
            flash(f'Usuário "{nome}" já existe.', 'warning')
    return redirect(url_for('index', tab='Usuarios'))

@app.route('/remove_user/<int:usuario_id>', methods=['POST'])
def remove_user(usuario_id):
    database.remover_usuario(usuario_id)
    flash('Usuário removido com sucesso!', 'success')
    return redirect(url_for('index', tab='Usuarios'))

@app.route('/criar_teste', methods=['POST'])
def criar_teste():
    npjs_raw = request.form.get('npjs_para_teste', '')
    # Usa regex para extrair qualquer sequência que pareça um NPJ ou número
    npjs_limpos = re.findall(r'[\d/.-]+', npjs_raw)
    
    if not npjs_limpos:
        flash('Nenhum NPJ válido foi inserido.', 'warning')
        return redirect(url_for('index', tab='Teste'))
    
    criados = database.criar_notificacoes_de_teste(npjs_limpos)
    
    mensagem = f"""
    <div class="instruction-box">
        <p><strong>{criados} caso(s) de teste foram criados com sucesso!</strong></p>
        <p>Agora, para iniciar o processamento dedicado a estes casos, abra um novo terminal na pasta do projeto e execute o seguinte comando:</p>
        <code>python run_test_session.py</code>
    </div>
    """
    flash(mensagem, 'success')
    return redirect(url_for('index', tab='Teste'))


@app.route('/downloads/<path:path>')
def serve_download(path):
    try:
        return send_from_directory(DOWNLOADS_DIR, path, as_attachment=True)
    except Exception as e:
        print(f"ERRO ao tentar servir o arquivo: {path}. Detalhes: {e}")
        return "Arquivo não encontrado ou acesso negado.", 404

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)

    database.inicializar_banco()

    print("="*50)
    print("Servidor web OneNotify iniciado.")
    print("Acesse em seu navegador: http://127.0.0.1:5000")
    print("Para parar o servidor, pressione CTRL+C no terminal.")
    print("="*50)
    Timer(1, abrir_navegador).start()
    app.run(port=5000, debug=True, use_reloader=False)

