import React, { useState, useEffect, useMemo, useCallback } from 'react';

// --- ÍCONES SVG (Do seu código original) ---
const EyeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block" viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
    <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
  </svg>
);

const CogIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106.886-.54 2.042.061 2.287.947.379 1.561 2.6 1.561 2.978 0a1.532 1.532 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106-.54-.886-.061-2.042.947-2.287 1.561-.379-1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
  </svg>
);

const DownloadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
);


// --- NOVO: Componente da Tela de Login ---
const LoginScreen = ({ onLogin, error, loading }) => {
  const [login, setLogin] = useState('');
  const [senha, setSenha] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (login && senha && !loading) {
      onLogin(login, senha);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="w-full max-w-md p-8 space-y-8 bg-gray-800 rounded-2xl shadow-2xl">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-blue-400">OneNotify</h1>
          <p className="mt-2 text-gray-400">Bem-vindo! Por favor, faça o login.</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <input
              id="login"
              name="login"
              type="text"
              required
              className="relative block w-full px-4 py-3 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded-md appearance-none focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Login"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
            />
          </div>
          <div>
            <input
              id="senha"
              name="senha"
              type="password"
              required
              className="relative block w-full px-4 py-3 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded-md appearance-none focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Senha"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
            />
          </div>
          {error && (<div className="p-3 text-sm text-red-300 bg-red-900 bg-opacity-50 rounded-md">{error}</div>)}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="relative flex justify-center w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md group hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};


// --- SEU PAINEL ORIGINAL, AGORA COMO COMPONENTE 'Dashboard' ---
// Todo o seu código de 500+ linhas está aqui, intacto.
const Dashboard = ({ user, onLogout }) => {
  const [notificacoes, setNotificacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filtroNPJ, setFiltroNPJ] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [filtroStatus, setFiltroStatus] = useState('');
  const [filtroData, setFiltroData] = useState('');
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [selectAll, setSelectAll] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showDateModal, setShowDateModal] = useState(false);
  const [newDate, setNewDate] = useState('');

  // MUDANÇA: Esta função agora busca os dados da API segura
  const fetchNotificacoes = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
        const token = localStorage.getItem('oneNotifyToken');
        if (!token) throw new Error("Token de autenticação não encontrado.");
        
        const response = await fetch('http://127.0.0.1:5001/api/notificacoes', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.mensagem || "Falha ao buscar notificações.");
        }

        const data = await response.json();
        // O parse dos campos JSON que você já fazia
        const parsedData = data.map(n => ({
            ...n,
            andamentos: n.andamentos ? JSON.parse(n.andamentos) : [],
            documentos: n.documentos ? JSON.parse(n.documentos) : [],
        }));
        setNotificacoes(parsedData);
    } catch (err) {
        setError(err.message);
        if (err.message.includes("Token")) onLogout();
    } finally {
        setLoading(false);
    }
  }, [onLogout]);

  // MUDANÇA: O useEffect agora chama a nova função de busca
  useEffect(() => {
    fetchNotificacoes();
  }, [fetchNotificacoes]);

  // Todo o resto do seu código permanece igual
  const notificacoesFiltradas = useMemo(() => {
    return notificacoes.filter(n =>
        (n.NPJ?.toLowerCase().includes(filtroNPJ.toLowerCase()) ?? true) &&
        (n.tipo_notificacao?.toLowerCase().includes(filtroTipo.toLowerCase()) ?? true) &&
        (filtroStatus === '' || n.status?.toLowerCase() === filtroStatus.toLowerCase()) &&
        (filtroData === '' || n.data_notificacao === filtroData)
    );
  }, [notificacoes, filtroNPJ, filtroTipo, filtroStatus, filtroData]);

  const handleSelectAll = () => {
    const newSelectAll = !selectAll;
    setSelectAll(newSelectAll);
    if (newSelectAll) {
        const allIds = new Set(notificacoesFiltradas.map(n => n.id));
        setSelectedIds(allIds);
    } else {
        setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id) => {
    const newSelectedIds = new Set(selectedIds);
    if (newSelectedIds.has(id)) {
        newSelectedIds.delete(id);
    } else {
        newSelectedIds.add(id);
    }
    setSelectedIds(newSelectedIds);
  };
  
  const handleDownload = async (path) => {
    try {
        const token = localStorage.getItem('oneNotifyToken');
        const relativePath = path.split('documentos\\')[1] || path.split('documentos/')[1];
        if (!relativePath) {
            throw new Error("Caminho do arquivo inválido.")
        }
        const response = await fetch(`http://127.0.0.1:5001/download-documento?path=${encodeURIComponent(relativePath)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`Falha no download: ${errorData}`);
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const filename = path.split('\\').pop().split('/').pop();
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erro no download:', error);
        setError(`Não foi possível baixar o arquivo: ${error.message}`);
    }
  };

  const handleUpdateStatus = async (novoStatus) => {
    setShowStatusModal(false);
    if (selectedIds.size === 0) return;

    try {
        const token = localStorage.getItem('oneNotifyToken');
        const response = await fetch('http://127.0.0.1:5001/api/update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ ids: Array.from(selectedIds), novo_status: novoStatus })
        });
        if (!response.ok) throw new Error('Falha ao atualizar status.');
        await fetchNotificacoes();
        setSelectedIds(new Set());
        setSelectAll(false);
    } catch (err) {
        setError(err.message);
    }
  };

  const handleUpdateDate = async () => {
    setShowDateModal(false);
    if (selectedIds.size === 0 || !newDate) return;

    try {
        const token = localStorage.getItem('oneNotifyToken');
        const response = await fetch('http://127.0.0.1:5001/api/update-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ ids: Array.from(selectedIds), nova_data: newDate })
        });
        if (!response.ok) throw new Error('Falha ao atualizar data.');
        await fetchNotificacoes();
        setSelectedIds(new Set());
        setSelectAll(false);
        setNewDate('');
    } catch (err) {
        setError(err.message);
    }
  };
  
  // SEU JSX ORIGINAL ESTÁ AQUI
  if (loading) {
    return (
        <div className="min-h-screen bg-gray-900 text-gray-200 font-sans">
            <header className="bg-gray-800 shadow-lg sticky top-0 z-20">
                <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center animate-pulse">
                    <div className="h-8 bg-gray-700 rounded w-1/4"></div>
                    <div className="flex items-center space-x-4">
                        <div className="text-right">
                            <div className="h-4 bg-gray-700 rounded w-24 mb-2"></div>
                            <div className="h-3 bg-gray-700 rounded w-16"></div>
                        </div>
                        <div className="h-10 bg-red-800 rounded w-16"></div>
                    </div>
                </div>
            </header>
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="text-center text-gray-400">Carregando tarefas...</div>
            </main>
        </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 font-sans">
      <header className="bg-gray-800 shadow-lg sticky top-0 z-20">
            <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
              <h1 className="text-2xl font-bold text-blue-400">Painel de Tarefas</h1>
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm font-medium text-white">{user.nome_completo}</p>
                  <p className="text-xs text-gray-400 capitalize">{user.perfil}</p>
                </div>
                <button
                  onClick={onLogout}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none"
                >
                  Sair
                </button>
              </div>
            </div>
          </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
         <div className="mb-6 p-4 bg-gray-800 rounded-lg shadow-md flex items-center space-x-4">
              <input type="text" placeholder="Filtrar por NPJ..." value={filtroNPJ} onChange={e => setFiltroNPJ(e.target.value)} className="flex-grow px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"/>
              <input type="text" placeholder="Filtrar por Tipo..." value={filtroTipo} onChange={e => setFiltroTipo(e.target.value)} className="flex-grow px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"/>
              <select value={filtroStatus} onChange={e => setFiltroStatus(e.target.value)} className="px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">Todos Status</option>
                  <option value="Processado">Processado</option>
                  <option value="Pendente">Pendente</option>
                  <option value="Concluido">Concluído</option>
                  <option value="Erro">Erro</option>
              </select>
              <input type="date" value={filtroData} onChange={e => setFiltroData(e.target.value)} className="px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"/>
              
              <div className="flex-shrink-0">
                  <button onClick={() => setShowStatusModal(true)} disabled={selectedIds.size === 0} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed">Mudar Status</button>
                  <button onClick={() => setShowDateModal(true)} disabled={selectedIds.size === 0} className="ml-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed">Corrigir Data</button>
              </div>
          </div>
          
          {error && <div className="text-red-400 bg-red-900 bg-opacity-50 p-3 rounded-md mb-4">{error}</div>}

          <div className="overflow-x-auto bg-gray-800 rounded-lg shadow-lg">
            <table className="min-w-full divide-y divide-gray-700">
              <thead className="bg-gray-700">
                  <tr>
                      <th scope="col" className="px-6 py-3 text-left">
                          <input type="checkbox" className="h-4 w-4 text-blue-600 bg-gray-700 border-gray-500 rounded focus:ring-blue-500" checked={selectAll} onChange={handleSelectAll} />
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">NPJ</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Tipo de Notificação</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Data</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
                      <th scope="col" className="relative px-6 py-3"><span className="sr-only">Ações</span></th>
                  </tr>
              </thead>
              <tbody className="bg-gray-800 divide-y divide-gray-700">
                {notificacoesFiltradas.length > 0 ? notificacoesFiltradas.map((n) => (
                  <tr key={n.id} className="hover:bg-gray-700 transition-colors duration-200">
                    <td className="px-6 py-4 whitespace-nowrap">
                        <input type="checkbox" className="h-4 w-4 text-blue-600 bg-gray-700 border-gray-500 rounded focus:ring-blue-500" checked={selectedIds.has(n.id)} onChange={() => handleSelectOne(n.id)} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{n.NPJ}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.tipo_notificacao}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.data_notificacao}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ n.status === 'Processado' ? 'bg-green-800 text-green-200' : n.status === 'Pendente' ? 'bg-yellow-800 text-yellow-200' : n.status === 'Concluido' ? 'bg-blue-800 text-blue-200' : 'bg-red-800 text-red-200' }`}>
                            {n.status}
                        </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button onClick={() => setSelectedNotification(n)} className="text-blue-400 hover:text-blue-300 mr-4" title="Detalhes"><EyeIcon /></button>
                      <button className="text-indigo-400 hover:text-indigo-300" title="Processar"><CogIcon /></button>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan="6" className="text-center py-10 text-gray-500">Nenhuma tarefa encontrada para os filtros aplicados.</td></tr>
                )}
              </tbody>
            </table>
          </div>
      </main>

      {showStatusModal && (
        <div className="fixed z-30 inset-0 overflow-y-auto"><div className="flex items-center justify-center min-h-screen"><div className="fixed inset-0 bg-gray-900 bg-opacity-75"></div><div className="bg-gray-800 rounded-lg overflow-hidden shadow-xl transform transition-all sm:max-w-lg sm:w-full"><div className="p-6"><h3 className="text-lg font-medium text-white">Alterar Status</h3><div className="mt-4 space-x-4"><button onClick={() => handleUpdateStatus('Concluido')} className="px-4 py-2 bg-green-600 rounded-md">Concluído</button><button onClick={() => handleUpdateStatus('Pendente')} className="px-4 py-2 bg-yellow-600 rounded-md">Pendente</button><button onClick={() => handleUpdateStatus('Erro')} className="px-4 py-2 bg-red-600 rounded-md">Erro</button><button onClick={() => setShowStatusModal(false)} className="px-4 py-2 bg-gray-600 rounded-md">Cancelar</button></div></div></div></div></div>
      )}
      {showDateModal && (
          <div className="fixed z-30 inset-0 overflow-y-auto"><div className="flex items-center justify-center min-h-screen"><div className="fixed inset-0 bg-gray-900 bg-opacity-75"></div><div className="bg-gray-800 rounded-lg overflow-hidden shadow-xl transform transition-all sm:max-w-lg sm:w-full"><div className="p-6"><h3 className="text-lg font-medium text-white">Corrigir Data de Notificação</h3><div className="mt-4"><input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} className="w-full px-3 py-2 bg-gray-700 text-white border border-gray-600 rounded-md"/></div><div className="mt-4 space-x-4"><button onClick={handleUpdateDate} className="px-4 py-2 bg-blue-600 rounded-md">Confirmar</button><button onClick={() => setShowDateModal(false)} className="px-4 py-2 bg-gray-600 rounded-md">Cancelar</button></div></div></div></div></div>
      )}
      {selectedNotification && (
        <div className="fixed z-30 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen p-4 text-center">
            <div className="fixed inset-0 bg-gray-900 bg-opacity-75" onClick={() => setSelectedNotification(null)}></div>
            <div className="inline-block bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-4xl sm:w-full">
              <div className="px-6 py-4"><h3 className="text-lg font-medium text-white">Detalhes da Notificação</h3></div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                      <div><strong className="text-gray-400 block">NPJ:</strong> <span className="text-lg">{selectedNotification.NPJ}</span></div>
                      <div><strong className="text-gray-400 block">Processo Judicial:</strong> <span>{selectedNotification.numero_processo || 'N/A'}</span></div>
                      <div><strong className="text-gray-400 block">Adverso Principal:</strong> <span>{selectedNotification.adverso_principal}</span></div>
                      <div><strong className="text-gray-400 block">Tipo de Notificação:</strong> <span>{selectedNotification.tipo_notificacao}</span></div>
                      <div><strong className="text-gray-400 block">Data da Notificação:</strong> <span>{selectedNotification.data_notificacao}</span></div>
                      <div><strong className="text-gray-400 block">Status Atual:</strong> <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ selectedNotification.status === 'Processado' ? 'bg-green-800 text-green-200' : selectedNotification.status === 'Pendente' ? 'bg-yellow-800 text-yellow-200' : selectedNotification.status === 'Concluido' ? 'bg-blue-800 text-blue-200' : 'bg-red-800 text-red-200' }`}>{selectedNotification.status}</span></div>
                  </div>
                  <div className="space-y-6">
                      <div>
                          <h4 className="font-semibold text-blue-400">Andamentos Recentes</h4>
                          {selectedNotification.andamentos?.length > 0 ? (
                            <ul className="mt-2 space-y-2 max-h-48 overflow-y-auto pr-2">
                              {selectedNotification.andamentos.map((andamento, index) => (
                                <li key={index} className="text-sm p-2 bg-gray-700 rounded-md">
                                  <strong className="text-gray-400">{andamento.data}:</strong> {andamento.detalhes || andamento.descricao}
                                </li>
                              ))}
                            </ul>
                          ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum andamento capturado.</p>}
                        </div>
                        <div>
                          <h4 className="font-semibold text-blue-400">Documentos Baixados</h4>
                          {selectedNotification.documentos?.length > 0 ? (
                            <ul className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                              {selectedNotification.documentos.map((doc, index) => (
                                <li key={index} className="flex items-center justify-between text-sm p-2 bg-gray-700 rounded-md">
                                  <span>{doc.nome}</span>
                                  <button onClick={() => handleDownload(doc.caminho)} className="text-blue-400 hover:text-blue-300" title="Baixar Documento"><DownloadIcon /></button>
                                </li>
                              ))}
                            </ul>
                          ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum documento baixado.</p>}
                        </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-800 border-t border-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button onClick={() => setSelectedNotification(null)} type="button" className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-gray-700 text-base font-medium text-white hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// --- COMPONENTE PRINCIPAL QUE GERENCIA A AUTENTICAÇÃO ---
function App() {
  const [token, setToken] = useState(localStorage.getItem('oneNotifyToken'));
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('oneNotifyUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (login, senha) => {
    setError('');
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5001/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login, senha }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.mensagem || 'Erro ao tentar fazer login.');
      }

      localStorage.setItem('oneNotifyToken', data.token);
      localStorage.setItem('oneNotifyUser', JSON.stringify(data.usuario));

      setToken(data.token);
      setUser(data.usuario);

    } catch (err) {
      setError(err.message);
    } finally {
        setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('oneNotifyToken');
    localStorage.removeItem('oneNotifyUser');
    setToken(null);
    setUser(null);
  };

  if (!token || !user) {
    return <LoginScreen onLogin={handleLogin} error={error} loading={loading} />;
  }

  return <Dashboard user={user} onLogout={handleLogout} />;
}

export default App;

