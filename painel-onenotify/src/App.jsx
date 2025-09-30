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

const DownloadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
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
  
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isBulkActionsMenuOpen, setIsBulkActionsMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [isDateModalOpen, setIsDateModalOpen] = useState(false);
  const [newDate, setNewDate] = useState('');

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

  useEffect(() => {
    setSelectedIds(new Set());
  }, [currentPage, itemsPerPage, statusFilter, searchTerm]);

  const handleNextPage = () => setCurrentPage(prev => Math.min(prev + 1, totalPages));
  const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const handleItemsPerPageChange = (e) => {
    setItemsPerPage(Number(e.target.value));
    setCurrentPage(1);
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

  const handleSelectAllOnPage = () => {
    const currentPageIds = paginatedNotificacoes.map(n => n.id);
    const allSelected = currentPageIds.length > 0 && currentPageIds.every(id => selectedIds.has(id));
    const newSelectedIds = new Set(selectedIds);
    if (allSelected) {
      currentPageIds.forEach(id => newSelectedIds.delete(id));
    } else {
      currentPageIds.forEach(id => newSelectedIds.add(id));
    }
    setSelectedIds(newSelectedIds);
  };

  const areAllOnPageSelected = paginatedNotificacoes.length > 0 && paginatedNotificacoes.every(n => selectedIds.has(n.id));

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
        setSelectedIds(new Set());
        fetchNotificacoes();
    } catch (error) {
        console.error("Erro na ação em massa:", error);
        alert(`Ocorreu um erro: ${error.message}`);
        setIsLoading(false);
    }
  };

  const handleBulkDateUpdate = async () => {
    if (!newDate || !/^\d{2}\/\d{2}\/\d{4}$/.test(newDate)) {
        alert("Por favor, insira uma data válida no formato DD/MM/AAAA.");
        return;
    }
    setIsLoading(true);
    setIsDateModalOpen(false);
    try {
        const response = await fetch('http://localhost:5000/api/notificacoes/bulk-update-date', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids: Array.from(selectedIds),
                nova_data: newDate,
            }),
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Falha ao corrigir as datas.');
        }
        
        let alertMessage = `${result.updated || 0} notificações foram atualizadas para a data ${newDate}.`;
        if (result.deleted > 0) {
            alertMessage += `\n${result.deleted} notificações duplicadas foram removidas para manter a consistência.`;
        }
        alert(alertMessage);
        
        setSelectedIds(new Set());
        setNewDate('');
        fetchNotificacoes();
    } catch (error) {
        console.error("Erro na correção de data:", error);
        alert(`Ocorreu um erro: ${error.message}`);
        setIsLoading(false);
    }
  };
  
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return timestamp;
      }
      return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return timestamp;
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
                                                    <div className="border-t border-gray-700 my-1"></div>
                                                    <button onClick={() => { setIsDateModalOpen(true); setIsBulkActionsMenuOpen(false); }} className="block w-full text-left px-4 py-2 text-sm text-yellow-400 hover:bg-gray-700" role="menuitem">
                                                        Corrigir Data...
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
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Captura</th>
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
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{formatTimestamp(n.data_criacao)}</td>
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
                        <table className="min-w-full divide-y divide-gray-600">
                           <thead className="bg-gray-750">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Timestamp</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Sucesso</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Falha</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Andamentos</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Documentos</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Duração (s)</th>
                                </tr>
                            </thead>
                            <tbody className="bg-gray-700 divide-y divide-gray-600">
                                {logs.map(log => (
                                    <tr key={log.id} className="hover:bg-gray-600">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{new Date(log.timestamp.replace('_', ' ')).toLocaleString('pt-BR')}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-green-400 font-bold">{log.npjs_sucesso}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-red-400 font-bold">{log.npjs_falha}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{log.andamentos}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{log.documentos}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{log.duracao_total.toFixed(2)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
      </main>
      
      {isDateModalOpen && (
        <div className="fixed z-20 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen">
                <div className="fixed inset-0 bg-black opacity-75" onClick={() => setIsDateModalOpen(false)}></div>
                <div className="relative bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:max-w-lg sm:w-full">
                    <div className="bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <h3 className="text-lg leading-6 font-medium text-white">Corrigir Data de Notificação</h3>
                        <div className="mt-4">
                            <p className="text-sm text-gray-400 mb-2">
                                A data informada abaixo será aplicada a todos os <strong>{selectedIds.size}</strong> itens selecionados.
                            </p>
                            <label htmlFor="newDate" className="block text-sm font-medium text-gray-300">Nova Data (DD/MM/AAAA)</label>
                            <input
                                type="text"
                                id="newDate"
                                value={newDate}
                                onChange={(e) => setNewDate(e.target.value)}
                                placeholder="DD/MM/AAAA"
                                className="mt-1 block w-full pl-3 pr-3 py-2 border border-gray-600 rounded-md leading-5 bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            />
                        </div>
                    </div>
                    <div className="bg-gray-800 border-t border-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                        <button onClick={handleBulkDateUpdate} type="button" className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 sm:ml-3 sm:w-auto sm:text-sm">
                            Confirmar Correção
                        </button>
                        <button onClick={() => setIsDateModalOpen(false)} type="button" className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-gray-700 text-base font-medium text-white hover:bg-gray-600 sm:mt-0 sm:w-auto sm:text-sm">
                            Cancelar
                        </button>
                    </div>
                </div>
            </div>
        </div>
      )}

      {selectedNotification && (
         <div className="fixed z-10 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={() => setSelectedNotification(null)}></div>
                <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                <div className="inline-block align-bottom bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
                    <div className="bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <div className="sm:flex sm:items-start">
                            <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                <h3 className="text-lg leading-6 font-medium text-white" id="modal-title">
                                    Detalhes da Notificação - NPJ: {selectedNotification.NPJ}
                                </h3>
                                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Coluna de Andamentos */}
                                    <div>
                                        <h4 className="font-semibold text-gray-300 border-b border-gray-700 pb-2 mb-2">Andamentos Capturados</h4>
                                        <div className="max-h-64 overflow-y-auto pr-2">
                                            {selectedNotification.andamentos && Array.isArray(selectedNotification.andamentos) && selectedNotification.andamentos.length > 0 ? (
                                                <ul className="space-y-3">
                                                    {selectedNotification.andamentos.map((andamento, index) => (
                                                        <li key={index} className="text-sm text-gray-300">
                                                            <p className="font-semibold text-blue-400">{andamento.data}: <span className="text-gray-300 font-normal">{andamento.descricao}</span></p>
                                                            <p className="pl-4 text-xs text-gray-400 whitespace-pre-wrap border-l-2 border-gray-700 ml-2 mt-1">{andamento.detalhes}</p>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum andamento capturado.</p>}
                                        </div>
                                    </div>
                                    {/* Coluna de Documentos */}
                                     <div>
                                        <h4 className="font-semibold text-gray-300 border-b border-gray-700 pb-2 mb-2">Documentos Baixados</h4>
                                        <div className="max-h-64 overflow-y-auto pr-2">
                                            {selectedNotification.documentos && Array.isArray(selectedNotification.documentos) && selectedNotification.documentos.length > 0 ? (
                                                <ul className="space-y-2">
                                                    {selectedNotification.documentos.map((doc, index) => (
                                                        <li key={index} className="text-sm text-gray-300 flex items-center justify-between bg-gray-900 p-2 rounded-md">
                                                            <span>{doc.nome}</span>
                                                            <a 
                                                                href={`http://localhost:5000/download-documento?path=${encodeURIComponent(doc.caminho)}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-blue-400 hover:text-blue-300 transition-colors duration-200"
                                                                title="Baixar Documento"
                                                            >
                                                                <DownloadIcon />
                                                            </a>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum documento baixado.</p>}
                                        </div>
                                    </div>
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

export default App;

