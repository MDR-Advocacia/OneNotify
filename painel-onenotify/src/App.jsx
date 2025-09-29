import React, { useState, useEffect, useMemo } from 'react';

// --- ÍCONES SVG ---
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

  useEffect(() => {
    fetch('http://localhost:5000/api/logs')
      .then(response => response.json())
      .then(data => setLogs(data))
      .catch(error => console.error("Erro ao buscar logs:", error));

    fetch('http://localhost:5000/api/notificacoes')
      .then(response => response.json())
      .then(data => setNotificacoes(data))
      .catch(error => console.error("Erro ao buscar notificações:", error));
  }, []);

  const latestLog = logs.length > 0 ? logs[0] : {};

  const filteredNotificacoes = useMemo(() => {
    return notificacoes.filter(n => {
      const npjString = n.NPJ || '';
      const matchesSearch = npjString.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'Todos' || n.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [notificacoes, searchTerm, statusFilter]);
  
  const kpiData = {
    sucesso: latestLog.npjs_sucesso || 0,
    falha: latestLog.npjs_falha || 0,
    pendente: notificacoes.filter(n => n.status === 'Pendente').length,
    total: notificacoes.length,
    duracao: latestLog.duracao_total ? latestLog.duracao_total.toFixed(2) : 0,
    ultimoTimestamp: latestLog.timestamp ? new Date(latestLog.timestamp.replace('_', ' ')).toLocaleString('pt-BR') : 'N/A'
  };

  const renderStatusBadge = (status) => {
    const baseClasses = "px-2 py-1 text-xs font-semibold rounded-full";
    switch (status) {
      case 'Processado': return <span className={`${baseClasses} bg-green-200 text-green-900`}>Processado</span>;
      case 'Pendente': return <span className={`${baseClasses} bg-yellow-200 text-yellow-900`}>Pendente</span>;
      case 'Erro': return <span className={`${baseClasses} bg-red-200 text-red-900`}>Erro</span>;
      default: return <span className={`${baseClasses} bg-gray-600 text-gray-100`}>{status}</span>;
    }
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
                            <div className="relative w-1/3">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <SearchIcon />
                                </div>
                                <input type="text" placeholder="Buscar por NPJ..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="block w-full pl-10 pr-3 py-2 border border-gray-600 rounded-md leading-5 bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm" />
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
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">NPJ</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Adverso Principal</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Data Notificação</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider"></th>
                                    </tr>
                                </thead>
                                <tbody className="bg-gray-700 divide-y divide-gray-600">
                                    {filteredNotificacoes.map(n => (
                                        <tr key={n.id} className="hover:bg-gray-600">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{n.NPJ}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.adverso_principal}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{n.data_notificacao}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">{renderStatusBadge(n.status)}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button onClick={() => setSelectedNotification(n)} className="text-blue-400 hover:text-blue-300">Ver Detalhes</button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
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

      {/* Modal Detalhes */}
      {selectedNotification && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div className="fixed inset-0 transition-opacity" aria-hidden="true">
                    <div className="absolute inset-0 bg-black opacity-75"></div>
                </div>
                <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                <div className="inline-block align-bottom bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
                    <div className="bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <div className="sm:flex sm:items-start">
                            <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                <h3 className="text-lg leading-6 font-medium text-white" id="modal-title">
                                    Detalhes da Notificação - NPJ: {selectedNotification.NPJ}
                                </h3>
                                <div className="mt-4 space-y-4">
                                    <div>
                                        <h4 className="font-semibold text-gray-300">Andamentos Capturados:</h4>
                                        {selectedNotification.andamentos && selectedNotification.andamentos.length > 0 ? (
                                            <ul className="list-disc list-inside bg-gray-900 p-3 rounded-md max-h-48 overflow-y-auto mt-2">
                                                {selectedNotification.andamentos.map((andamento, index) => (
                                                    <li key={index} className="text-sm text-gray-300 mt-1">
                                                        <strong>{andamento.data}:</strong> {andamento.descricao}
                                                        <p className="pl-4 text-xs text-gray-400 whitespace-pre-wrap">{andamento.detalhes}</p>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum andamento capturado.</p>}
                                    </div>
                                     <div>
                                        <h4 className="font-semibold text-gray-300">Documentos Baixados:</h4>
                                        {selectedNotification.documentos && selectedNotification.documentos.length > 0 ? (
                                            <ul className="list-disc list-inside bg-gray-900 p-3 rounded-md max-h-48 overflow-y-auto mt-2">
                                                {selectedNotification.documentos.map((doc, index) => (
                                                    <li key={index} className="text-sm text-gray-300 mt-1">
                                                        {doc.nome} <span className="text-xs text-gray-500">({doc.caminho})</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : <p className="text-sm text-gray-500 italic mt-2">Nenhum documento baixado.</p>}
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

