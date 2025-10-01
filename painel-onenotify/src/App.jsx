import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';

// --- ÍCONES (SVG como componentes React) ---
const IconBox = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>);
const IconClock = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>);
const IconCheckCircle = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>);
const IconAlertTriangle = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>);
const IconRefresh = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>);
const IconChevronDown = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>;
const IconChevronUp = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>;
const IconSearch = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const IconEye = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>;
const IconMoreVertical = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>;
const IconDownload = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>);
const IconRewind = ({ className }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 19 2 12 11 5 11 19"></polygon><polygon points="22 19 13 12 22 5 22 19"></polygon></svg>);


// --- COMPONENTES DA UI ---

const StatCard = ({ title, value, icon, colorClass }) => ( <div className="bg-gray-800 p-6 rounded-lg shadow-lg flex items-center space-x-4"> <div className={`p-3 rounded-full ${colorClass}`}>{icon}</div> <div> <p className="text-sm text-gray-400 font-medium">{title}</p> <p className="text-2xl font-bold text-white">{value}</p> </div> </div> );
const DateCorrectionModal = ({ isOpen, onClose, onSubmit, selectedCount }) => { const [novaData, setNovaData] = useState(''); if (!isOpen) return null; const handleSubmit = (e) => { e.preventDefault(); if (novaData) onSubmit(novaData); }; return ( <div className="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50"> <div className="bg-gray-800 rounded-lg p-8 shadow-2xl w-full max-w-md"> <h2 className="text-xl font-bold text-white mb-4">Corrigir Data da Notificação</h2> <p className="text-gray-400 mb-6">Você selecionou {selectedCount} notificação(ões). A nova data será aplicada a todas.</p> <form onSubmit={handleSubmit}> <input type="text" placeholder="DD/MM/AAAA" value={novaData} onChange={(e) => setNovaData(e.target.value)} className="w-full bg-gray-700 text-white p-3 rounded-md border border-gray-600 focus:ring-2 focus:ring-blue-500 focus:outline-none" /> <div className="mt-6 flex justify-end space-x-4"> <button type="button" onClick={onClose} className="px-4 py-2 rounded-md bg-gray-600 text-white hover:bg-gray-500 transition">Cancelar</button> <button type="submit" className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-500 transition font-semibold">Confirmar Correção</button> </div> </form> </div> </div> ); };
const Pagination = ({ currentPage, totalPages, onPageChange, itemsPerPage, onItemsPerPageChange }) => { if (totalPages <= 1) return null; return ( <div className="flex justify-center items-center space-x-4 p-4"> <select value={itemsPerPage} onChange={e => onItemsPerPageChange(Number(e.target.value))} className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2"> <option value="10">10 / página</option> <option value="25">25 / página</option> <option value="50">50 / página</option> <option value="100">100 / página</option> </select> <button onClick={() => onPageChange(currentPage - 1)} disabled={currentPage === 1} className="px-4 py-2 bg-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-500 transition">Anterior</button> <span className="text-gray-400">Página {currentPage} de {totalPages}</span> <button onClick={() => onPageChange(currentPage + 1)} disabled={currentPage === totalPages} className="px-4 py-2 bg-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-500 transition">Próxima</button> </div> ); };

const DetailsModal = ({ isOpen, onClose, details, onDownload }) => {
    const [expandedIndex, setExpandedIndex] = useState(null);
    if (!isOpen) return null;

    const toggleAndamento = (index) => {
        setExpandedIndex(prevIndex => (prevIndex === index ? null : index));
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg p-8 shadow-2xl w-full max-w-4xl h-[75vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <h2 className="text-xl font-bold text-white mb-6 flex-shrink-0">Detalhes do Processamento</h2>
                {details.loading && <p className="text-center text-gray-400">Carregando detalhes...</p>}
                {details.error && <p className="text-center text-red-400">{details.error}</p>}
                {!details.loading && !details.error && (
                    <div className="flex-grow grid grid-cols-1 md:grid-cols-2 gap-6 overflow-hidden">
                        <section className="flex flex-col overflow-hidden">
                            <h3 className="text-lg font-semibold text-blue-400 mb-3 flex-shrink-0">Andamentos Capturados</h3>
                            <ul className="space-y-2 text-sm overflow-y-auto pr-3">
                                {details.andamentos?.length > 0 ? details.andamentos.map((a, i) => (
                                    <li key={i}>
                                        <button onClick={() => toggleAndamento(i)} className="w-full text-left bg-gray-700 p-3 rounded-md flex justify-between items-center hover:bg-gray-600 transition">
                                            <span className="font-semibold text-gray-300 truncate">{a.data} - {a.descricao}</span>
                                            <IconChevronDown className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${expandedIndex === i ? 'rotate-180' : ''}`} />
                                        </button>
                                        {expandedIndex === i && (
                                            <div className="bg-gray-900/50 p-3 mt-1 rounded-b-md">
                                                <p className="text-gray-400 whitespace-pre-wrap">{a.detalhes}</p>
                                            </div>
                                        )}
                                    </li>
                                )) : <p className="text-gray-500">Nenhum andamento capturado.</p>}
                            </ul>
                        </section>
                        <section className="flex flex-col overflow-hidden">
                            <h3 className="text-lg font-semibold text-green-400 mb-3 flex-shrink-0">Documentos Baixados</h3>
                            <ul className="space-y-2 text-sm overflow-y-auto pr-3">
                                {details.documentos?.length > 0 ? details.documentos.map((d, i) => (
                                    <li key={i}>
                                        <button onClick={() => onDownload(d.caminho)} className="w-full text-left bg-gray-700 p-3 rounded-md flex justify-between items-center hover:bg-gray-600 transition">
                                            <span className="text-gray-300 truncate">{d.nome}</span>
                                            <IconDownload className="w-5 h-5 text-gray-400" />
                                        </button>
                                    </li>
                                )) : <p className="text-gray-500">Nenhum documento baixado.</p>}
                            </ul>
                        </section>
                    </div>
                )}
            </div>
        </div>
    );
};

// --- COMPONENTE PRINCIPAL ---

function App() {
    // Estados da Aplicação
    const [notificacoes, setNotificacoes] = useState([]);
    const [stats, setStats] = useState({});
    const [statusFiltro, setStatusFiltro] = useState('Pendente');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [isDateModalOpen, setIsDateModalOpen] = useState(false);
    
    // Estados para novas funcionalidades
    const [filtroBusca, setFiltroBusca] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'data_notificacao', direction: 'descending' });
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
    const [detailsData, setDetailsData] = useState({ andamentos: [], documentos: [], loading: false });
    const [activeActionMenu, setActiveActionMenu] = useState(null);
    const [isBulkMenuOpen, setIsBulkMenuOpen] = useState(false);
    const actionMenuRef = useRef(null);
    const bulkMenuRef = useRef(null);
    const API_URL = 'http://localhost:5001/api';

    // Funções de busca de dados
    const fetchStats = useCallback(async () => { try { const res = await fetch(`${API_URL}/dashboard-stats`); if(res.ok) setStats(await res.json()); } catch (err) { console.error("Erro em fetchStats:", err.message); } }, []);
    const fetchNotificacoes = useCallback(async () => { setLoading(true); setError(null); try { const res = await fetch(`${API_URL}/notificacoes?status=${statusFiltro}`); if(!res.ok) throw new Error(`HTTP error! status: ${res.status}`); setNotificacoes(await res.json()); } catch (err) { setError(err.message); setNotificacoes([]); } finally { setLoading(false); } }, [statusFiltro]);
    useEffect(() => { fetchStats(); fetchNotificacoes(); }, [fetchStats, fetchNotificacoes]);
    
    // Lógica de manipulação de dados (Filtro, Ordenação, Paginação)
    const processedNotificacoes = useMemo(() => { let items = [...notificacoes]; if (filtroBusca) { items = items.filter(n => n.NPJ.toLowerCase().includes(filtroBusca.toLowerCase())); } if (sortConfig.key) { items.sort((a, b) => { let aValue = a[sortConfig.key] || '', bValue = b[sortConfig.key] || ''; if (sortConfig.key === 'data_notificacao') { const parseDate = (dateStr) => { const [day, month, year] = dateStr.split('/'); return new Date(`${year}-${month}-${day}`); }; aValue = parseDate(aValue); bValue = parseDate(bValue); } if (aValue < bValue) return sortConfig.direction === 'ascending' ? -1 : 1; if (aValue > bValue) return sortConfig.direction === 'ascending' ? 1 : -1; return 0; }); } return items; }, [notificacoes, filtroBusca, sortConfig]);
    const totalPages = Math.ceil(processedNotificacoes.length / itemsPerPage);
    const currentTableData = processedNotificacoes.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    // Handlers
    const refreshData = () => { fetchStats(); fetchNotificacoes(); setSelectedIds(new Set()); };
    const handleAction = async (action, payload, successMsg) => { try { const response = await fetch(`${API_URL}/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), }); const result = await response.json(); if (!response.ok) throw new Error(result.message || 'Erro desconhecido'); alert(successMsg || result.message); refreshData(); } catch (err) { alert(`Erro: ${err.message}`); } };
    const handleUpdateStatus = (ids, novoStatus) => handleAction('atualizar-status', { ids, novo_status: novoStatus });
    const handleDateCorrection = (ids, novaData) => { handleAction('corrigir-data', { ids, nova_data: novaData }); setIsDateModalOpen(false); };
    const requestSort = (key) => { let direction = 'ascending'; if (sortConfig.key === key && sortConfig.direction === 'ascending') { direction = 'descending'; } else if (sortConfig.key === key && sortConfig.direction === 'descending') { direction = 'ascending'; } setSortConfig({ key, direction }); };
    
    const handleViewDetails = async (npj, data) => { setIsDetailsModalOpen(true); setDetailsData({ andamentos: [], documentos: [], loading: true }); try { const response = await fetch(`${API_URL}/notificacao-detalhes?npj=${encodeURIComponent(npj)}&data=${encodeURIComponent(data)}`); if(!response.ok) throw new Error('Falha ao buscar dados do servidor.'); const details = await response.json(); setDetailsData({ ...details, loading: false }); } catch (error) { console.error("Failed to fetch details", error); setDetailsData({ andamentos: [], documentos: [], loading: false, error: "Falha ao carregar detalhes." }); } };
    const handleDownload = (caminho) => { window.open(`${API_URL}/download-documento?caminho=${encodeURIComponent(caminho)}`, '_blank'); };

    // Handlers de Seleção
    const handleCheckboxChange = (grupo_ids, isChecked) => { setSelectedIds(prev => { const newSet = new Set(prev); if (isChecked) { grupo_ids.forEach(id => newSet.add(id)); } else { grupo_ids.forEach(id => newSet.delete(id)); } return newSet; }); };
    const handleSelectAllChange = (e) => { const isChecked = e.target.checked; const pageIds = currentTableData.flatMap(n => n.ids); setSelectedIds(prev => { const newSet = new Set(prev); if (isChecked) { pageIds.forEach(id => newSet.add(id)); } else { pageIds.forEach(id => newSet.delete(id)); } return newSet; }); };
    
    const pageSelectedIds = currentTableData.flatMap(n => n.ids);
    const isAllOnPageSelected = pageSelectedIds.length > 0 && pageSelectedIds.every(id => selectedIds.has(id));
    const isSomeOnPageSelected = pageSelectedIds.some(id => selectedIds.has(id));

    useEffect(() => {
        const handleClickOutside = (event) => { if (actionMenuRef.current && !actionMenuRef.current.contains(event.target)) setActiveActionMenu(null); if (bulkMenuRef.current && !bulkMenuRef.current.contains(event.target)) setIsBulkMenuOpen(false); };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);
    
    const SortableHeader = ({ label, columnKey, widthClass }) => { const isSorted = sortConfig.key === columnKey; return ( <th className={`p-4 text-sm font-semibold text-gray-300 cursor-pointer select-none ${widthClass}`} onClick={() => requestSort(columnKey)}> <div className="flex items-center space-x-1"> <span>{label}</span> {isSorted && (sortConfig.direction === 'ascending' ? <IconChevronUp className="w-4 h-4" /> : <IconChevronDown className="w-4 h-4" />)} </div> </th> ); };
    const StatusTab = ({ status, label }) => ( <button onClick={() => { setStatusFiltro(status); setSelectedIds(new Set()); }} className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors duration-200 ${statusFiltro === status ? 'bg-gray-800 border-b-2 border-blue-500 text-white' : 'text-gray-400 hover:bg-gray-700/50'}`}> {label} </button> );

    useEffect(() => { setCurrentPage(1); }, [statusFiltro, filtroBusca, itemsPerPage]);

    return (
        <div className="bg-gray-900 min-h-screen text-gray-200 font-sans p-4 sm:p-6 lg:p-8">
            <DateCorrectionModal isOpen={isDateModalOpen} onClose={() => setIsDateModalOpen(false)} onSubmit={(novaData) => handleDateCorrection(Array.from(selectedIds), novaData)} selectedCount={selectedIds.size} />
            <DetailsModal isOpen={isDetailsModalOpen} onClose={() => setIsDetailsModalOpen(false)} details={detailsData} onDownload={handleDownload} />

            <div className="max-w-7xl mx-auto">
                <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white">Painel OneNotify</h1>
                        <p className="text-gray-400 mt-1">Visão geral e gerenciamento das notificações da RPA.</p>
                    </div>
                    <button onClick={refreshData} className="mt-4 sm:mt-0 flex items-center space-x-2 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors shadow-md">
                        <IconRefresh className="w-5 h-5" />
                        <span>Atualizar</span>
                    </button>
                </header>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <StatCard title="Pendentes" value={stats.pendente ?? 0} icon={<IconClock className="w-6 h-6 text-white" />} colorClass="bg-yellow-500/80" />
                    <StatCard title="Em Processamento" value={stats.em_processamento ?? 0} icon={<IconBox className="w-6 h-6 text-white" />} colorClass="bg-blue-500/80" />
                    <StatCard title="Processados" value={stats.processado ?? 0} icon={<IconCheckCircle className="w-6 h-6 text-white" />} colorClass="bg-green-500/80" />
                    <StatCard title="Com Erro" value={stats.erro ?? 0} icon={<IconAlertTriangle className="w-6 h-6 text-white" />} colorClass="bg-red-500/80" />
                </div>
                
                <main className="bg-gray-800 rounded-lg shadow-2xl">
                    <div className="px-6 pt-4 border-b border-gray-700 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="flex items-center space-x-1">
                           <StatusTab status="Pendente" label="Pendentes" />
                           <StatusTab status="Em Processamento" label="Em Processamento" />
                           <StatusTab status="Processado" label="Processados" />
                           <StatusTab status="Erro" label="Com Erro" />
                           <StatusTab status="Arquivado" label="Arquivados" />
                        </div>
                        <div className="flex items-center gap-4">
                           <div className="relative" ref={bulkMenuRef}>
                                <button onClick={() => setIsBulkMenuOpen(prev => !prev)} disabled={selectedIds.size === 0} className="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-500 transition">
                                    Ações em Lote ({selectedIds.size}) <IconChevronDown className={`w-4 h-4 transition-transform ${isBulkMenuOpen ? 'rotate-180' : ''}`} />
                                </button>
                                {isBulkMenuOpen && (
                                    <div className="absolute right-0 mt-2 w-56 bg-gray-700 rounded-md shadow-lg z-10 border border-gray-600">
                                        {statusFiltro !== 'Pendente' && <button onClick={() => { handleUpdateStatus(Array.from(selectedIds), 'Pendente'); setIsBulkMenuOpen(false); }} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Marcar como Pendente</button>}
                                        {statusFiltro !== 'Arquivado' && <button onClick={() => { setIsDateModalOpen(true); setIsBulkMenuOpen(false); }} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Corrigir Data</button>}
                                        {statusFiltro !== 'Arquivado' && <button onClick={() => { handleUpdateStatus(Array.from(selectedIds), 'Arquivado'); setIsBulkMenuOpen(false); }} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Arquivar</button>}
                                    </div>
                                )}
                           </div>
                           <div className="relative w-full sm:w-64">
                                <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input type="text" placeholder="Buscar por NPJ..." value={filtroBusca} onChange={e => setFiltroBusca(e.target.value)} className="w-full bg-gray-700 text-white pl-10 pr-4 py-2 rounded-md border border-gray-600 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                            </div>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left table-fixed">
                            <thead className="bg-gray-700/50">
                                <tr>
                                    <th className="p-4 w-12 text-center">
                                        <input type="checkbox" ref={el => el && (el.indeterminate = isSomeOnPageSelected && !isAllOnPageSelected)} checked={isAllOnPageSelected} onChange={handleSelectAllChange} className="form-checkbox h-5 w-5 bg-gray-600 border-gray-500 rounded text-blue-500 focus:ring-blue-500" />
                                    </th>
                                    <SortableHeader label="Data" columnKey="data_notificacao" widthClass="w-[12%]" />
                                    <SortableHeader label="NPJ" columnKey="NPJ" widthClass="w-[18%]" />
                                    <SortableHeader label="Nº Processo" columnKey="numero_processo" widthClass="w-[20%]" />
                                    <th className="p-4 text-sm font-semibold text-gray-300 w-[35%]">Tipos de Notificação</th>
                                    <th className="p-4 text-sm font-semibold text-gray-300 text-center w-[10%]">Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && <tr><td colSpan="6" className="text-center p-8">Carregando dados...</td></tr>}
                                {error && <tr><td colSpan="6" className="text-center p-8 text-red-400">Erro ao carregar notificações: {error}</td></tr>}
                                {!loading && !error && currentTableData.length === 0 && ( <tr><td colSpan="6" className="text-center p-8 text-gray-500">{filtroBusca ? 'Nenhum resultado encontrado.' : 'Nenhuma notificação para este status.'}</td></tr> )}
                                {!loading && !error && currentTableData.map((n) => {
                                  const isRowSelected = n.ids.every(id => selectedIds.has(id));
                                  return (
                                    <tr key={n.NPJ + n.data_notificacao} className={`border-b border-gray-700 transition-colors ${isRowSelected ? 'bg-blue-900/40' : 'hover:bg-gray-700/50'}`}>
                                        <td className="p-4 text-center">
                                            <input type="checkbox" checked={isRowSelected} onChange={(e) => handleCheckboxChange(n.ids, e.target.checked)} className="form-checkbox h-5 w-5 bg-gray-600 border-gray-500 rounded text-blue-500 focus:ring-blue-500"/>
                                        </td>
                                        <td className="p-4 font-mono text-sm whitespace-nowrap">{n.data_notificacao}</td>
                                        <td className="p-4 font-mono text-sm whitespace-nowrap">{n.NPJ}</td>
                                        <td className="p-4 font-mono text-sm text-gray-400 whitespace-nowrap truncate">{n.numero_processo || <span className="text-gray-500">-</span>}</td>
                                        <td className="p-4 text-sm">
                                            <div className="flex flex-wrap gap-1">
                                                {n.tipos_notificacao.split('; ').map((tipo, index) => (
                                                    <span key={index} className="bg-gray-600 text-gray-300 text-xs font-medium px-2 py-0.5 rounded-full">{tipo}</span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <div className="flex items-center justify-center space-x-3">
                                                <button onClick={() => handleViewDetails(n.NPJ, n.data_notificacao)} className="text-gray-400 hover:text-blue-400" title="Ver Detalhes"><IconEye className="w-5 h-5"/></button>
                                                <div className="relative" ref={activeActionMenu === n.NPJ + n.data_notificacao ? actionMenuRef : null}>
                                                    <button onClick={() => setActiveActionMenu(n.NPJ + n.data_notificacao)} className="text-gray-400 hover:text-blue-400" title="Mais Ações"><IconMoreVertical className="w-5 h-5"/></button>
                                                    {activeActionMenu === n.NPJ + n.data_notificacao && (
                                                        <div className="absolute right-0 mt-2 w-48 bg-gray-700 rounded-md shadow-lg z-10 border border-gray-600">
                                                            {n.status !== 'Pendente' && <button onClick={() => {handleUpdateStatus(n.ids, 'Pendente'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Marcar como Pendente</button>}
                                                            {n.status !== 'Arquivado' && <button onClick={() => {setIsDateModalOpen(true); setSelectedIds(new Set(n.ids)); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Corrigir Data</button>}
                                                            {n.status !== 'Arquivado' && <button onClick={() => {handleUpdateStatus(n.ids, 'Arquivado'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-600">Arquivar</button>}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                  );
                                })}
                            </tbody>
                        </table>
                    </div>
                    <Pagination 
                        currentPage={currentPage} 
                        totalPages={totalPages} 
                        onPageChange={setCurrentPage}
                        itemsPerPage={itemsPerPage}
                        onItemsPerPageChange={(value) => {
                            setItemsPerPage(value);
                            setCurrentPage(1);
                        }}
                    />
                </main>
            </div>
        </div>
    );
}

export default App;
