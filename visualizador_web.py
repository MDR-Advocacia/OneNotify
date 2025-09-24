# arquivo: visualizador_web.py
import sqlite3
import json
import os
import webbrowser
import re
from threading import Timer
from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, flash

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


# --- TEMPLATE HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OneNotify - Dashboard</title>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #1d2b4b;
            --bg-light: #3a506b;
            --primary-accent: #5bc0de;
            --text-light: #e0e0e0;
            --text-dark: #ffffff;
            --border-color: rgba(255, 255, 255, 0.18);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(120deg, var(--bg-dark) 0%, var(--bg-light) 100%);
            color: var(--text-light);
            min-height: 100vh;
        }
        .container { padding: 2rem; max-width: 1800px; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
        .card {
            padding: 2rem;
            text-align: left;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid var(--border-color);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        }
        h1, h2 { color: var(--text-dark); }
        h2 { margin-bottom: 1.5rem; border-bottom: 2px solid var(--primary-accent); padding-bottom: 0.5rem; display: inline-block; }
        header {
            display: flex; align-items: center; justify-content: flex-start;
            padding: 1rem 2rem; background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        header h1 { font-size: 1.75rem; font-weight: 600; }
        
        /* Forms & Buttons */
        .filter-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; align-items: flex-end; }
        .filter-group label { margin-bottom: 0.5rem; font-weight: bold; }
        .filter-group.search-field { grid-column: 1 / -1; }
        select, textarea, input[type="text"], input[type="date"] {
            width: 100%; padding: 12px; margin-bottom: 1rem; border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px; font-size: 1rem; background: rgba(0, 0, 0, 0.2); color: #f0f0f0;
        }
        button {
            padding: 12px 24px; border: none; border-radius: 8px; color: white; background-color: var(--primary-accent);
            cursor: pointer; font-weight: bold; font-size: 1rem; transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(91, 192, 222, 0.4); }
        button:disabled { background-color: #555; cursor: not-allowed; opacity: 0.6; }
        
        /* Table */
        table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; }
        th, td { padding: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); text-align: left; vertical-align: middle; }
        thead { background-color: rgba(0, 0, 0, 0.2); }
        th { font-weight: bold; color: var(--text-dark); }
        tbody tr:hover { background-color: rgba(91, 192, 222, 0.1); }
        .status { display: inline-block; width: 12px; height: 12px; border-radius: 50%; vertical-align: middle; }
        .status-Pendente { background-color: #f0ad4e; }
        .status-Processado, .status-Processado-em-Teste { background-color: #007bff; }
        .status-Arquivado { background-color: #6c757d; }
        .status-Erro, .status-Erro_GED { background-color: #dc3545; }
        
        /* Tabs */
        .tabs { display: flex; border-bottom: 1px solid rgba(255, 255, 255, 0.2); margin-bottom: 2rem; }
        .tab-button { padding: 10px 20px; cursor: pointer; background: transparent; border: none; color: rgba(255, 255, 255, 0.6); font-size: 1rem; border-bottom: 3px solid transparent; margin-bottom: -1px; }
        .tab-button.active { color: white; border-bottom: 3px solid var(--primary-accent); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        a { color: var(--primary-accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <header><h1>OneNotify</h1></header>
    <div class="container">
        <div class="tabs">
            <button class="tab-button active" onclick="openTab(event, 'Dashboard')">Dashboard</button>
            <button class="tab-button" onclick="openTab(event, 'Logs')">Histórico</button>
            <button class="tab-button" onclick="openTab(event, 'Teste')">Sessão de Teste</button>
        </div>
        
        <div id="Dashboard" class="tab-content active card">
            <h2>Notificações</h2>
            <!-- Conteúdo do Dashboard aqui -->
        </div>

        <div id="Logs" class="tab-content card">
            <h2>Histórico de Execuções</h2>
            <!-- Conteúdo dos Logs aqui -->
        </div>

        <div id="Teste" class="tab-content card">
            <h2>Criar Sessão de Teste</h2>
            <!-- Conteúdo da Sessão de Teste aqui -->
        </div>
    </div>
    <script>
        function openTab(evt, tabName) {
            document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = "none");
            document.querySelectorAll('.tab-button').forEach(tb => tb.classList.remove('active'));
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.classList.add('active');
        }
        // Lógica para abas (se precisar manter estado)
        document.addEventListener('DOMContentLoaded', function() {
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab');
            if (tab) {
                const tabButton = document.querySelector(`.tab-button[onclick*="'${tab}'"]`);
                if (tabButton) tabButton.click();
            }
        });
    </script>
</body>
</html>
"""
