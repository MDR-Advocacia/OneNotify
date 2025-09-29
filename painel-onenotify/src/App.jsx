import React, { useState, useEffect, useMemo } from 'react';

// --- ÍCONES SVG ---
const EyeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block" viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
    <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
  </svg>
);

const CogIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.532 1.532 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.532 1.532 0 01-.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
  </svg>
);

const LogoIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-blue-400">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z" fill="currentColor"/>
    <path d="M12 12.5c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm0-5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" fill="currentColor"/>
    <path d="M12 17c-2.76 0-5-2.24-5-5h2c0 1.65 1.35 3 3 3s3-1.35 3-3h2c0 2.76-2.24 5-5 5z" fill="currentColor"/>
  </svg>
);

const SearchIcon = () => (
    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
);

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [logs, setLogs] = useState([]);
  const [notificacoes, setNotificacoes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('Todos');
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);

  // --- NOVOS ESTADOS PARA SELEÇÃO E AÇÕES ---
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isBulkActionsMenuOpen, setIsBulkActionsMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const fetchNotificacoes = () => {
    setIsLoading(true);
    fetch('http://localhost:5000/api/notificacoes')
      .then(response => response.json())
      .then(data => setNotificacoes(data))
      .catch(error => console.error("Erro ao buscar notificações:", error))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetch('http://localhost:5000/api/logs')
      .then(response => response.json())
      .then(data => setLogs(data))
      .catch(error => console.error("Erro ao buscar logs:", error));
    fetchNotificacoes();
  }, []);

  const latestLog = logs.length > 0 ? logs[0] : {};

  const filteredNotificacoes = useMemo(() => {
    return notificacoes.filter(n => {
      const npjString = n.NPJ || '';
      const processoString = n.numero_processo || '';
      const searchTermLower = searchTerm.toLowerCase();
      const matchesSearch = npjString.toLowerCase().includes(searchTermLower) || processoString.toLowerCase().includes(searchTermLower);
      const matchesStatus = statusFilter === 'Todos' || n.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [notificacoes, searchTerm, statusFilter]);

  const totalPages = Math.ceil(filteredNotificacoes.length / itemsPerPage);

  const paginatedNotificacoes = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredNotificacoes.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredNotificacoes, currentPage, itemsPerPage]);

  // Limpa a seleção ao mudar filtros ou página
  useEffect(() => {
    setSelectedIds(new Set());
  }, [currentPage, itemsPerPage, statusFilter, searchTerm]);

  const handleNextPage = () => setCurrentPage(prev => Math.min(prev + 1, totalPages));
  const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const handleItemsPerPageChange = (e) => {
    setItemsPerPage(Number(e.target.value));
    setCurrentPage(1);
  };
  
  // --- LÓGICA DOS CHECKBOXES ---
  const handleSelectOne = (id) => {
    const newSelectedIds = new Set(selectedIds);
    if (newSelectedIds.has(id)) {
      newSelectedIds.delete(id);
    } else {
      newSelectedIds.add(id);
    }
    setSelectedIds(newSelectedIds);
  };

  const handleSelectAllOnPage = () => {
    const currentPageIds = paginatedNotificacoes.map(n => n.id);
    if (currentPageIds.every(id => selectedIds.has(id))) {
      // Desmarcar todos da página
      const newSelectedIds = new Set(selectedIds);
      currentPageIds.forEach(id => newSelectedIds.delete(id));
      setSelectedIds(newSelectedIds);
    } else {
      // Marcar todos da página
      const newSelectedIds = new Set(selectedIds);
      currentPageIds.forEach(id => newSelectedIds.add(id));
      setSelectedIds(newSelectedIds);
    }
  };

  const areAllOnPageSelected = paginatedNotificacoes.length > 0 && paginatedNotificacoes.every(n => selectedIds.has(n.id));

  // --- LÓGICA DAS AÇÕES EM MASSA PARA ITENS SELECIONADOS ---
  const handleBulkAction = async (newStatus) => {
    setIsLoading(true);
    setIsBulkActionsMenuOpen(false);
    try {
        const response = await fetch('http://localhost:5000/api/notificacoes/bulk-update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids: Array.from(selectedIds),
                status: newStatus,
            }),
        });
        if (!response.ok) throw new Error('Falha ao executar ação em massa.');

        const result = await response.json();
        alert(`${result.updated_rows} notificações foram atualizadas para "${newStatus}".`);
        setSelectedIds(new Set()); // Limpa a seleção
        fetchNotificacoes(); // Re-busca os dados
    } catch (error) {
        console.error("Erro na ação em massa:", error);
        alert(`Ocorreu um erro: ${error.message}`);
        setIsLoading(false);
    }
  };


  const kpiData = {
    sucesso: latestLog.npjs_sucesso || 0,
    falha: latestLog.npjs_falha || 0,
    pendente: notificacoes.filter(n => n.status === 'Pendente').length,
    total: notificacoes.length,
    duracao: latestLog.duracao_total ? latestLog.duracao_total.toFixed(2) : 0,
    ultimoTimestamp: latestLog.timestamp ? new Date(latestLog.timestamp.replace('_', ' ')).toLocaleString('pt-BR') : 'N/A'
  };

  const StatusIcon = ({ status }) => {
    const colorClass = useMemo(() => {
      switch (status) {
        case 'Processado': return 'bg-green-500';
        case 'Pendente': return 'bg-yellow-500';
        case 'Erro': return 'bg-red-500';
        default: return 'bg-gray-500';
      }
    }, [status]);
    return <span className={`inline-block w-3 h-3 rounded-full ${colorClass}`}></span>;
  };
  
  const KpiCard = ({ title, value, subtext }) => (
    <div className="bg-gray-700 p-4 rounded-lg shadow-lg">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        <p className="text-2xl font-bold text-white">{value}</p>
        {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
    </div>
  );

  return (
    <div className="bg-gray-800 text-gray-200 min-h-screen font-sans">
      <header className="bg-gray-900 shadow-md">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <LogoIcon />
            <h1 className="text-xl font-bold text-white">OneNotify</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
            <KpiCard title="Sucesso" value={kpiData.sucesso} subtext="última execução" />
            <KpiCard title="Falha" value={kpiData.falha} subtext="última execução" />
            <KpiCard title="Pendentes" value={kpiData.pendente} subtext="no total" />
            <KpiCard title="Total Notificações" value={kpiData.total} subtext="no banco de dados" />
            <KpiCard title="Duração (s)" value={kpiData.duracao} subtext="última execução" />
            <KpiCard title="Última Execução" value={kpiData.ultimoTimestamp} />
        </div>

        <div className="bg-gray-700 rounded-lg shadow-lg">
            <div className="border-b border-gray-600">
                <nav className="-mb-px flex space-x-6 px-6" aria-label="Tabs">
                    <button onClick={() => setActiveTab('dashboard')} className={`${activeTab === 'dashboard' ? 'border-blue-400 text-blue-300' : 'border-transparent text-gray-400 hover:text-white hover:border-gray-500'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}>
                        Notificações
                    </button>
                    <button onClick={() => setActiveTab('logs')} className={`${activeTab === 'logs' ? 'border-blue-400 text-blue-300' : 'border-transparent text-gray-400 hover:text-white hover:border-gray-500'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}>
                        Histórico de Execuções
                    </button>
                </nav>
            </div>

            <div className="p-6">
                {activeTab === 'dashboard' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                             <div className="flex items-center space-x-4 flex-1">
                                <div className="relative w-1/2">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <SearchIcon />
                                    </div>
                                    <input type="text" placeholder="Buscar por NPJ ou Processo..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="block w-full pl-10 pr-3 py-2 border border-gray-600 rounded-md leading-5 bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm" />
                                </div>
                                
                                {/* --- NOVO BOTÃO DE AÇÕES CONTEXTUAL --- */}
                                {selectedIds.size > 0 && (
                                    <div className="relative">
                                        <button 
                                            onClick={() => setIsBulkActionsMenuOpen(!isBulkActionsMenuOpen)}
                                            disabled={isLoading}
                                            className="inline-flex items-center justify-center px-4 py-2 border border-blue-500 rounded-md bg-blue-600 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-blue-500 disabled:opacity-50"
                                        >
                                            <CogIcon/>
                                            <span className="ml-2">Ações para {selectedIds.size} item(s)</span>
                                        </button>
                                        {isBulkActionsMenuOpen && (
                                            <div className="origin-top-left absolute left-0 mt-2 w-56 rounded-md shadow-lg bg-gray-800 ring-1 ring-black ring-opacity-5 z-10">
                                                <div className="py-1" role="menu" aria-orientation="vertical">
                                                    <button onClick={() => handleBulkAction('Pendente')} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700" role="menuitem">
                                                        Marcar como Pendente
                                                    </button>
                                                    <button onClick={() => handleBulkAction('Arquivado')} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700" role="menuitem">
                                                        Arquivar
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            
                            <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-300">Status:</span>
                                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="pl-3 pr-8 py-2 border border-gray-600 rounded-md bg-gray-800 text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                                    <option>Todos</option>
                                    <option>Processado</option>
                                    <option>Pendente</option>
                                    <option>Erro</option>
                                </select>
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-600">
                                <thead className="bg-gray-750">
                                    <tr>
                                        <th className="px-4 py-3 w-12">
                                            <input 
                                                type="checkbox"
                                                className="h-4 w-4 bg-gray-600 border-gray-500 rounded text-blue-500 focus:ring-blue-600"
                                                checked={areAllOnPageSelected}
                                                onChange={handleSelectAllOnPage}
                                            />
                                        </th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider w-12"></th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Número do Processo</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">NPJ</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Tipo de Notificação</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Data Notificação</th>
                                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Ações</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-gray-700 divide-y divide-gray-600">
                                    {paginatedNotificacoes.map(n => (
                                        <tr key={n.id} className={`${selectedIds.has(n.id) ? 'bg-blue-900/50' : ''} hover:bg-gray-600`}>
                                            <td className="px-4 py-4">
                                                <input 
                                                    type="checkbox"
                                                    className="h-4 w-4 bg-gray-600 border-gray-500 rounded text-blue-500 focus:ring-blue-600"
                                                    checked={selectedIds.has(n.id)}
                                                    onChange={() => handleSelectOne(n.id)}
                                                />
                                            </td>
                                            <td className="px-4 py-4 text-center"><StatusIcon status={n.status} /></td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.numero_processo}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{n.NPJ}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.tipo_notificacao}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.data_notificacao}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-center text-lg space-x-4">
                                                <button onClick={() => setSelectedNotification(n)} className="text-blue-400 hover:text-blue-300 transition-colors duration-200"><EyeIcon /></button>
                                                <button onClick={() => alert(`Ações para o NPJ: ${n.NPJ}`)} className="text-gray-400 hover:text-white transition-colors duration-200"><CogIcon /></button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="flex items-center justify-between mt-4">
                           <div className="flex items-center space-x-2">
                                <span className="text-sm text-gray-300">Itens por página:</span>
                                <select value={itemsPerPage} onChange={handleItemsPerPageChange} className="pl-3 pr-8 py-1 border border-gray-600 rounded-md bg-gray-800 text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                                    <option value={10}>10</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                </select>
                            </div>
                            <div className="flex items-center space-x-4">
                                <span className="text-sm text-gray-300">Página {currentPage} de {totalPages > 0 ? totalPages : 1}</span>
                                <div className="flex space-x-2">
                                    <button onClick={handlePrevPage} disabled={currentPage === 1} className="px-3 py-1 text-sm font-medium text-white bg-gray-600 rounded-md disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-500 transition-colors">Anterior</button>
                                    <button onClick={handleNextPage} disabled={currentPage === totalPages || totalPages === 0} className="px-3 py-1 text-sm font-medium text-white bg-gray-600 rounded-md disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-500 transition-colors">Próxima</button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {activeTab === 'logs' && (
                     <div className="overflow-x-auto">
                        {/* A tabela de logs continua aqui */}
                    </div>
                )}
            </div>
        </div>
      </main>

      {/* Modal de Detalhes (sem alterações) */}
      {selectedNotification && (
         <div className="fixed z-10 inset-0 overflow-y-auto">
            {/* O código do modal de detalhes continua o mesmo, então foi omitido por brevidade */}
         </div>
      )}
    </div>
  );
}

export default App;

