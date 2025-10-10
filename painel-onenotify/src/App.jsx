import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';

const API_URL = 'http://localhost:5001/api';

// --- Ícones ---
const EyeIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" /></svg>;
const DotsVerticalIcon = ({ onClick }) => <svg onClick={onClick} xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 cursor-pointer text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white" viewBox="0 0 20 20" fill="currentColor"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" /></svg>;
const DownloadIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2 inline-block" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
const ChevronDownIcon = ({ isOpen }) => <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
const SortIcon = ({ direction }) => {
    if (!direction) return <svg className="h-4 w-4 inline-block text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" /></svg>;
    if (direction === 'ascending') return <svg className="h-4 w-4 inline-block text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" /></svg>;
    return <svg className="h-4 w-4 inline-block text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>;
};
const SunIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>;
const MoonIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>;
const GearIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;
const XIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>;
const TaskIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V4a2 2 0 00-2-2H6zm1 2a1 1 0 000 2h6a1 1 0 100-2H7zm0 4a1 1 0 000 2h6a1 1 0 100-2H7zm0 4a1 1 0 000 2h4a1 1 0 100-2H7z" clipRule="evenodd" /></svg>;

// --- Helper Functions ---
const abbreviateTipo = (tipo) => {
    switch (tipo) {
        case 'Andamento de publicação em processo de condução terceirizada': return 'Andamento de Publicação';
        case 'Inclusão de Documentos no NPJ': return 'Inclusão de Doc NPJ';
        case 'Doc. anexado por empresa externa em processo terceirizado': return 'Doc Anexado Terceirizada';
        default: return tipo;
    }
};

// --- Componentes Reutilizáveis ---
const StatsCard = ({ title, value, color }) => (
  <div className={`p-4 rounded-lg shadow-md border-l-4 ${color} bg-white dark:bg-gray-800`}>
    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</h3>
    <p className="text-3xl font-bold text-gray-800 dark:text-gray-100">{value || 0}</p>
  </div>
);

const StatusTab = ({ status, label, activeStatus, setActiveStatus, count }) => (
  <button
    onClick={() => setActiveStatus(status)}
    className={`px-4 py-2 text-sm font-medium rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ${activeStatus === status ? 'bg-blue-600 text-white shadow' : 'bg-white text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}`}>
    {label} <span className={`text-xs rounded-full px-2 py-0.5 ml-1 ${activeStatus === status ? 'bg-blue-400 text-white' : 'bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200'}`}>{count || 0}</span>
  </button>
);

const Paginacao = ({ currentPage, totalPages, onPageChange, itemsPerPage, onItemsPerPageChange, totalItems }) => {
    if (totalPages <= 1) return null;
    return (
        <div className="flex flex-col sm:flex-row justify-between items-center mt-4 text-sm text-gray-600 dark:text-gray-400 gap-4">
            <div className="flex items-center gap-2">
                <span>Itens por página:</span>
                <select value={itemsPerPage} onChange={e => onItemsPerPageChange(Number(e.target.value))} className="border rounded-md p-1 bg-white dark:bg-gray-700 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value={10}>10</option><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option>
                </select>
            </div>
            <span>Página {currentPage} de {totalPages} ({totalItems} itens)</span>
            <div>
                <button onClick={() => onPageChange(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 border rounded-md bg-white dark:bg-gray-700 dark:border-gray-600 disabled:opacity-50">Anterior</button>
                <button onClick={() => onPageChange(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 border rounded-md bg-white dark:bg-gray-700 dark:border-gray-600 ml-2 disabled:opacity-50">Próxima</button>
            </div>
        </div>
    );
};

const ConfirmationModal = ({ isOpen, onClose, onConfirm, message }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex justify-center items-center z-[60] p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md" onClick={e => e.stopPropagation()}>
                <div className="p-6">
                    <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">Confirmação</h3>
                    <p className="text-gray-600 dark:text-gray-300">{message}</p>
                </div>
                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 flex justify-end gap-4">
                    <button onClick={onClose} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 font-semibold">Cancelar</button>
                    <button onClick={onConfirm} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold">Confirmar</button>
                </div>
            </div>
        </div>
    );
};

const ModalDetalhes = ({ isOpen, onClose, item, executeUpdateStatus, legalOneUsers, legalOneTasks }) => {
    const [step, setStep] = useState('details');
    const [activeAndamento, setActiveAndamento] = useState(null);
    const [detalhes, setDetalhes] = useState(null);
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        responsavel_name: '',
        responsavel_id: null,
        tarefa_name: '',
        tarefa_parent_id: null,
        tarefa_external_id: null,
        data_agendamento: ''
    });
    
    const { NPJ: npj, data_notificacao, numero_processo, ids, status } = item || {};

    useEffect(() => {
        if (isOpen) {
            setStep('details');
            setFormData({ responsavel_name: '', responsavel_id: null, tarefa_name: '', tarefa_parent_id: null, tarefa_external_id: null, data_agendamento: '' });
            if (npj && data_notificacao) {
                setLoading(true);
                setActiveAndamento(null);
                const fetchDetalhes = async () => {
                    try {
                        const url = `${API_URL}/detalhes?npj=${encodeURIComponent(npj)}&data=${encodeURIComponent(data_notificacao)}`;
                        const res = await fetch(url);
                        if (!res.ok) throw new Error('Falha ao buscar detalhes');
                        const data = await res.json();
                        setDetalhes(data);
                    } catch (err) { console.error("Erro ao buscar detalhes:", err); } 
                    finally { setLoading(false); }
                };
                fetchDetalhes();
            }
        }
    }, [isOpen, npj, data_notificacao]);
    
    if (!isOpen || !item) return null;

    const handleDownload = async (path) => {
        try {
            const response = await fetch(`${API_URL}/download?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error('Falha no download');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = path.split(/[\\/]/).pop();
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (error) { console.error("Erro no download:", error); }
    };

    const handleFinalizarSemTarefa = () => {
        executeUpdateStatus([ids], 'Tratada', 0);
        onClose();
    };

    const handleCriarTarefa = async (e) => {
        e.preventDefault();

        const [year, month, day] = formData.data_agendamento.split('-');
        const formattedDate = `${day}/${month}/${year}`;

        const finalJson = {
            fonte: "Onenotify",
            processos: [
                {
                    id_responsavel: formData.responsavel_id,
                    numero_processo: numero_processo ? numero_processo.replace(/\D/g, '') : '',
                    parent_type_external_id: formData.tarefa_parent_id,
                    external_id: formData.tarefa_external_id,
                    "data agendamento": formattedDate,
                    observacao: formData.tarefa_name
                }
            ]
        };
        
        try {
            const response = await fetch(`${API_URL}/tarefas`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalJson),
            });
            if (!response.ok) throw new Error("Falha ao salvar a tarefa.");
            
            executeUpdateStatus([ids], 'Tratada', 1);
            onClose();

        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleResponsavelChange = (name) => {
        const selectedUser = legalOneUsers.find(user => user.name === name);
        setFormData({
            ...formData,
            responsavel_name: name,
            responsavel_id: selectedUser ? selectedUser.external_id : null
        });
    };
    
    const handleTarefaChange = (name) => {
        const selectedTask = legalOneTasks.find(task => task.name === name);
        setFormData({
            ...formData,
            tarefa_name: name,
            tarefa_parent_id: selectedTask ? selectedTask.parent_type_external_id : null,
            tarefa_external_id: selectedTask ? selectedTask.external_id : null
        });
    };
    
    const renderContent = () => {
        switch (step) {
            case 'decision':
                return (
                    <div className="p-6 text-center flex-grow flex flex-col justify-center">
                        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">Esta notificação vai gerar uma tarefa?</h3>
                        <div className="flex justify-center gap-4 mt-6">
                            <button onClick={() => setStep('form')} className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold">Sim</button>
                            <button onClick={handleFinalizarSemTarefa} className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-semibold">Não</button>
                        </div>
                    </div>
                );
            case 'form':
                return (
                    <div className="p-6 flex-grow overflow-y-auto">
                        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-6">Agendar Nova Tarefa</h3>
                        <form onSubmit={handleCriarTarefa} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Responsável</label>
                                <input list="legal-one-users" value={formData.responsavel_name} onChange={e => handleResponsavelChange(e.target.value)} className="mt-1 block w-full border rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600" required />
                                <datalist id="legal-one-users">
                                    {legalOneUsers.map(user => <option key={user.external_id} value={user.name} />)}
                                </datalist>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Tipo de Tarefa</label>
                                <input list="legal-one-tasks" value={formData.tarefa_name} onChange={e => handleTarefaChange(e.target.value)} className="mt-1 block w-full border rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600" required />
                                <datalist id="legal-one-tasks">
                                    {legalOneTasks.map(task => <option key={task.external_id} value={task.name} />)}
                                </datalist>
                            </div>
                             <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Data do Agendamento</label>
                                <input type="date" value={formData.data_agendamento} onChange={e => setFormData({...formData, data_agendamento: e.target.value})} className="mt-1 block w-full border rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600" required />
                            </div>
                            <div className="pt-4 flex justify-end gap-4">
                                <button type="button" onClick={() => setStep('decision')} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 font-semibold">Voltar</button>
                                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold">Criar Tarefa</button>
                            </div>
                        </form>
                    </div>
                );
            case 'details':
            default:
                return (
                     <main className="p-4 flex-grow overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-6">
                        {loading ? <p className="text-center col-span-2 dark:text-gray-300">Carregando detalhes...</p> :
                            <>
                                <div className="flex flex-col">
                                    <h3 className="font-bold mb-2 text-gray-700 dark:text-gray-200">Andamentos Capturados</h3>
                                    <div className="border rounded-md p-2 overflow-y-auto flex-grow h-96 dark:border-gray-700">
                                        {detalhes?.andamentos?.length > 0 ? (
                                            detalhes.andamentos.map((andamento, index) => (
                                                <div key={index} className="border-b last:border-b-0 dark:border-gray-700">
                                                    <button onClick={() => setActiveAndamento(activeAndamento === index ? null : index)} className="w-full text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-700 flex justify-between items-center">
                                                        <span className="font-medium text-sm text-gray-800 dark:text-gray-200">{andamento.data} - {andamento.descricao}</span>
                                                        <ChevronDownIcon isOpen={activeAndamento === index} />
                                                    </button>
                                                    {activeAndamento === index && (
                                                        <div className="p-3 bg-gray-50 dark:bg-gray-900 text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{andamento.detalhes}</div>
                                                    )}
                                                </div>
                                            ))
                                        ) : <p className="text-sm text-gray-500 dark:text-gray-400 p-2">Nenhum andamento capturado.</p>}
                                    </div>
                                </div>
                                <div className="flex flex-col">
                                    <h3 className="font-bold mb-2 text-gray-700 dark:text-gray-200">Documentos Baixados</h3>
                                    <div className="border rounded-md p-2 overflow-y-auto flex-grow h-96 dark:border-gray-700">
                                       {detalhes?.documentos?.length > 0 ? (
                                            detalhes.documentos.map((doc, index) => (
                                                <button key={index} onClick={() => handleDownload(doc.caminho)} className="w-full text-left p-2 border-b last:border-b-0 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center text-sm text-blue-600 dark:text-blue-400">
                                                    <DownloadIcon /> {doc.nome}
                                                </button>
                                            ))
                                       ) : <p className="text-sm text-gray-500 dark:text-gray-400 p-2">Nenhum documento baixado.</p>}
                                    </div>
                                </div>
                            </>
                        }
                     </main>
                );
        }
    };
    
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 p-4" onClick={onClose}>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col relative" onClick={e => e.stopPropagation()}>
                <header className="p-4 border-b dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10">
                    <button onClick={onClose} className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                        <XIcon />
                    </button>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">Detalhes do Processamento</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        {numero_processo ? `Nº Processo: ${numero_processo} | ` : ''}NPJ: {npj} | Data: {data_notificacao}
                    </p>
                    {item.responsavel && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Responsável: {item.responsavel}</p>}
                </header>
                
                {renderContent()}

                {step === 'details' && (
                    <footer className="p-3 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex justify-end sticky bottom-0">
                        <button onClick={() => setStep('decision')} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold">
                            Finalizar
                        </button>
                    </footer>
                )}
            </div>
        </div>
    );
};


// --- Componente Principal ---
function App() {
    const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
    useEffect(() => {
        const root = window.document.documentElement;
        root.classList.remove(theme === 'light' ? 'dark' : 'light');
        root.classList.add(theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(theme === 'light' ? 'dark' : 'light');

    const [stats, setStats] = useState({ pendente: 0, processado: 0, erro: 0, erro_data_invalida: 0, arquivado: 0, tratada: 0 });
    const [notificacoes, setNotificacoes] = useState([]);
    const [statusFiltro, setStatusFiltro] = useState('Processado');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [filtroBusca, setFiltroBusca] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'data_notificacao', direction: 'descending' });
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const [selectedIds, setSelectedIds] = useState([]);
    const [modalDetalhes, setModalDetalhes] = useState({ isOpen: false, item: null });
    const [showUserManagement, setShowUserManagement] = useState(false);
    const [listaUsuarios, setListaUsuarios] = useState([]);
    const [responsavelFiltro, setResponsavelFiltro] = useState('Todos');
    const [activeActionMenu, setActiveActionMenu] = useState(null);
    const menuRef = useRef(null);
    const [confirmationModal, setConfirmationModal] = useState({ isOpen: false, onConfirm: () => {}, message: '' });

    const [legalOneUsers, setLegalOneUsers] = useState([]);
    const [legalOneTasks, setLegalOneTasks] = useState([]);

    const fetchAllData = useCallback(async () => {
        setLoading(true);
        setError('');
        setSelectedIds([]);
        try {
            const [statsRes, usersRes, legalOneUsersRes, legalOneTasksRes] = await Promise.all([
                fetch(`${API_URL}/stats`), 
                fetch(`${API_URL}/usuarios`),
                fetch(`${API_URL}/legalone/users`),
                fetch(`${API_URL}/legalone/tasks`),
            ]);
            if (!statsRes.ok || !usersRes.ok || !legalOneUsersRes.ok || !legalOneTasksRes.ok) throw new Error('Falha ao carregar dados iniciais');

            const statsData = await statsRes.json();
            const usersData = await usersRes.json();
            const legalOneUsersData = await legalOneUsersRes.json();
            const legalOneTasksData = await legalOneTasksRes.json();

            setStats(statsData);
            setListaUsuarios(usersData);
            setLegalOneUsers(legalOneUsersData);
            setLegalOneTasks(legalOneTasksData);

            let url = `${API_URL}/notificacoes?status=${statusFiltro}`;
            if (responsavelFiltro !== 'Todos') url += `&responsavel=${encodeURIComponent(responsavelFiltro)}`;

            const notificacoesRes = await fetch(url);
            if (!notificacoesRes.ok) throw new Error('Falha ao carregar notificações');

            const notificacoesData = await notificacoesRes.json();
            setNotificacoes(notificacoesData);
        } catch (err) { setError(err.message); } 
        finally { setLoading(false); }
    }, [statusFiltro, responsavelFiltro]);

    useEffect(() => { fetchAllData(); }, [fetchAllData]);
    
    const sortedItems = useMemo(() => {
        let sortableItems = [...notificacoes];
        if (sortConfig.key) {
            sortableItems.sort((a, b) => {
                let aValue = a[sortConfig.key] || '';
                let bValue = b[sortConfig.key] || '';
                if (sortConfig.key === 'data_notificacao') {
                    aValue = aValue.split('/').reverse().join('');
                    bValue = bValue.split('/').reverse().join('');
                }
                if (aValue < bValue) return sortConfig.direction === 'ascending' ? -1 : 1;
                if (aValue > bValue) return sortConfig.direction === 'ascending' ? 1 : -1;
                return 0;
            });
        }
        return sortableItems;
    }, [notificacoes, sortConfig]);

    const filteredItems = useMemo(() => sortedItems.filter(item =>
        (item.NPJ?.toLowerCase() || '').includes(filtroBusca.toLowerCase()) ||
        (item.adverso_principal?.toLowerCase() || '').includes(filtroBusca.toLowerCase())
    ), [sortedItems, filtroBusca]);

    const currentTableData = useMemo(() => {
        const firstPageIndex = (currentPage - 1) * itemsPerPage;
        return filteredItems.slice(firstPageIndex, firstPageIndex + itemsPerPage);
    }, [filteredItems, currentPage, itemsPerPage]);

    const requestSort = (key) => {
        let direction = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') direction = 'descending';
        setSortConfig({ key, direction });
    };

    const handleStatusChange = (newStatus) => {
        setStatusFiltro(newStatus);
        setCurrentPage(1);
        setFiltroBusca('');
        setResponsavelFiltro('Todos');
    };

    const executeUpdateStatus = async (ids, novo_status, gerou_tarefa) => {
        const flatIds = ids.flatMap(idStr => idStr.split(';'));
        try {
          const body = { ids: flatIds, novo_status };
          if (novo_status === 'Tratada') {
            body.gerou_tarefa = gerou_tarefa;
          }
          const response = await fetch(`${API_URL}/acoes/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          if (!response.ok) throw new Error("Falha ao executar ação.");
          fetchAllData();
        } catch (err) {
          console.error(err);
        }
        setConfirmationModal({ isOpen: false, onConfirm: () => {}, message: '' });
    };

    const handleAction = (ids, action) => {
        if (!ids || ids.length === 0) return;
        
        if (action === 'Tratada') {
            setConfirmationModal({
                isOpen: true,
                onConfirm: () => executeUpdateStatus(ids, 'Tratada', 0),
                message: "Você confirma que esta(s) notificação(ões) será(ão) marcada(s) como 'Tratada(s)' sem a criação de novas tarefas?"
            });
        } else {
            executeUpdateStatus(ids, action);
        }
    };
    
    const handleSelectAll = (e) => {
        if (e.target.checked) {
          const allIdsOnPage = currentTableData.map(item => item.ids);
          setSelectedIds(allIdsOnPage);
        } else {
          setSelectedIds([]);
        }
    };
    
    const handleSelectOne = (e, ids) => {
        if (e.target.checked) {
          setSelectedIds(prev => [...prev, ids]);
        } else {
          setSelectedIds(prev => prev.filter(id => id !== ids));
        }
    };

    const allOnPageSelected = useMemo(() => 
        currentTableData.length > 0 && currentTableData.every(item => selectedIds.includes(item.ids)),
        [currentTableData, selectedIds]
    );
      
    const someOnPageSelected = useMemo(() => 
        currentTableData.some(item => selectedIds.includes(item.ids)),
        [currentTableData, selectedIds]
    );
    
    const masterCheckboxRef = useRef(null);
    useEffect(() => {
        if (masterCheckboxRef.current) {
          masterCheckboxRef.current.indeterminate = someOnPageSelected && !allOnPageSelected;
        }
    }, [someOnPageSelected, allOnPageSelected]);
    
    
    useEffect(() => {
        const handleClickOutside = (event) => {
          if (menuRef.current && !menuRef.current.contains(event.target)) {
            setActiveActionMenu(null);
          }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className="bg-gray-100 dark:bg-gray-900 min-h-screen p-4 sm:p-6 lg:p-8 font-sans">
          <header className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">OneNotify</h1>
            <div className="flex items-center gap-4">
                <button onClick={toggleTheme} className="p-2 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {theme === 'light' ? <MoonIcon /> : <SunIcon />}
                </button>
                <button onClick={() => setShowUserManagement(!showUserManagement)} className="bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-semibold py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-sm">
                    {showUserManagement ? 'Ver Notificações' : 'Gerenciar Responsáveis'}
                </button>
            </div>
          </header>
    
          {showUserManagement ? ( <UserManagement users={listaUsuarios} onUserChange={fetchAllData} /> ) : (
            <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
                    <StatsCard title="Pendentes" value={stats.pendente} color="border-yellow-400" />
                    <StatsCard title="Processados" value={stats.processado} color="border-green-400" />
                    <StatsCard title="Tratadas" value={stats.tratada} color="border-blue-400" />
                    <StatsCard title="Com Erro" value={stats.erro} color="border-red-400" />
                    <StatsCard title="Erro de Dados" value={stats.erro_data_invalida} color="border-orange-400" />
                    <StatsCard title="Arquivados" value={stats.arquivado} color="border-gray-400" />
                </div>
                <div className="flex flex-wrap gap-2 mb-4">
                    <StatusTab status="Pendente" label="Pendentes" activeStatus={statusFiltro} setActiveStatus={handleStatusChange} count={stats.pendente} />
                    <StatusTab status="Processado" label="Processados" activeStatus={statusFiltro} setActiveStatus={handleStatusChange} count={stats.processado} />
                    <StatusTab status="Tratada" label="Tratadas" activeStatus={statusFiltro} setActiveStatus={handleStatusChange} count={stats.tratada} />
                    <StatusTab status="Erro" label="Erro" activeStatus={statusFiltro} setActiveStatus={handleStatusChange} count={stats.erro} />
                    <StatusTab status="Arquivado" label="Arquivados" activeStatus={statusFiltro} setActiveStatus={handleStatusChange} count={stats.arquivado} />
                </div>
                
                <div className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-lg shadow-md">
                    <div className="flex flex-col sm:flex-row justify-between items-center mb-4 gap-4">
                        <div className="flex items-center gap-2 md:gap-4 flex-wrap">
                          <input type="text" placeholder="Buscar por NPJ ou Adverso..." value={filtroBusca} onChange={e => setFiltroBusca(e.target.value)} className="border rounded-md py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-auto bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600" />
                          <select value={responsavelFiltro} onChange={e => setResponsavelFiltro(e.target.value)} className="border rounded-md py-2 px-3 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-auto">
                            <option value="Todos">Todos os Responsáveis</option>
                            <option value="Sem Responsável">Sem Responsável</option>
                            {listaUsuarios.map(user => <option key={user.id} value={user.nome}>{user.nome}</option>)}
                          </select>
                        </div>
                        <div className="relative" ref={menuRef}>
                            <button onClick={() => setActiveActionMenu(activeActionMenu === 'batch' ? null : 'batch')} disabled={selectedIds.length === 0} className="bg-blue-500 text-white font-bold py-2 px-4 rounded-md text-sm disabled:bg-gray-400 dark:disabled:bg-gray-600 flex items-center gap-2">
                               <GearIcon /> 
                               <span>({selectedIds.length})</span>
                            </button>
                            {activeActionMenu === 'batch' && (
                                 <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-700 rounded-md shadow-lg z-20">
                                    {statusFiltro !== 'Tratada' && <button onClick={() => {handleAction(selectedIds, 'Tratada'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Marcar como Tratada</button>}
                                    {statusFiltro !== 'Pendente' && <button onClick={() => {handleAction(selectedIds, 'Pendente'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Marcar como Pendente</button>}
                                    {statusFiltro !== 'Arquivado' && <button onClick={() => {handleAction(selectedIds, 'Arquivado'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Arquivar</button>}
                                </div>
                            )}
                        </div>
                    </div>
    
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 table-fixed">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                               <tr>
                                    <th className="p-4 w-12 text-left">
                                        <input type="checkbox" ref={masterCheckboxRef} checked={allOnPageSelected} onChange={handleSelectAll} className="rounded" />
                                    </th>
                                    <th className="w-[10%] px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer" onClick={() => requestSort('data_notificacao')}>Data <SortIcon direction={sortConfig.key === 'data_notificacao' ? sortConfig.direction : null}/></th>
                                    <th className="w-[25%] px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer" onClick={() => requestSort('NPJ')}>NPJ <SortIcon direction={sortConfig.key === 'NPJ' ? sortConfig.direction : null}/></th>
                                    <th className="w-[15%] px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Nº Processo</th>
                                    <th className="w-[25%] px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Tipos de Notificação</th>
                                    <th className="w-[15%] px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer" onClick={() => requestSort('responsavel')}>Responsável <SortIcon direction={sortConfig.key === 'responsavel' ? sortConfig.direction : null}/></th>
                                    <th className="w-[5%] px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Detalhes</th>
                                    <th className="w-[5%] px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                {loading ? <tr><td colSpan="8" className="text-center p-4 dark:text-gray-300">Carregando...</td></tr> :
                                 error ? <tr><td colSpan="8" className="text-center p-4 text-red-500">{error}</td></tr> :
                                 currentTableData.map(item => {
                                    const itemKey = item.NPJ + item.data_notificacao;
                                    return (
                                    <tr key={itemKey} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                        <td className="p-4">
                                            <input type="checkbox" checked={selectedIds.includes(item.ids)} onChange={(e) => handleSelectOne(e, item.ids)} className="rounded" />
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{item.data_notificacao}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
                                            {item.NPJ}
                                            {item.gerou_tarefa === 1 && <TaskIcon />}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300 truncate">{item.numero_processo || '-'}</td>
                                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
                                            <div className="flex flex-wrap gap-1">
                                                {item.tipos_notificacao.split('; ').map(tipo => (
                                                    <span key={tipo} className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-2 py-0.5 rounded-full">{abbreviateTipo(tipo)}</span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{item.responsavel || '-'}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                                            <button onClick={() => setModalDetalhes({ isOpen: true, item })} className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-200"><EyeIcon /></button>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                                             <div className="relative" ref={activeActionMenu === itemKey ? menuRef : null}>
                                                <DotsVerticalIcon onClick={() => setActiveActionMenu(activeActionMenu === itemKey ? null : itemKey)} />
                                                {activeActionMenu === itemKey && (
                                                    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-700 rounded-md shadow-lg z-20">
                                                        {item.status !== 'Tratada' && <button onClick={() => {handleAction([item.ids], 'Tratada'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Marcar como Tratada</button>}
                                                        {item.status !== 'Pendente' && <button onClick={() => {handleAction([item.ids], 'Pendente'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Marcar como Pendente</button>}
                                                        {item.status !== 'Arquivado' && <button onClick={() => {handleAction([item.ids], 'Arquivado'); setActiveActionMenu(null);}} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600">Arquivar</button>}
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                )})}
                            </tbody>
                        </table>
                    </div>
    
                    <Paginacao
                        currentPage={currentPage} totalPages={Math.ceil(filteredItems.length / itemsPerPage)}
                        onPageChange={setCurrentPage} itemsPerPage={itemsPerPage}
                        onItemsPerPageChange={(value) => { setItemsPerPage(value); setCurrentPage(1); }}
                        totalItems={filteredItems.length}
                    />
                </div>
            </>
          )}
    
          <ConfirmationModal
            isOpen={confirmationModal.isOpen}
            onClose={() => setConfirmationModal({ isOpen: false, onConfirm: () => {}, message: '' })}
            onConfirm={confirmationModal.onConfirm}
            message={confirmationModal.message}
          />
          <ModalDetalhes 
            isOpen={modalDetalhes.isOpen} 
            onClose={() => setModalDetalhes({ isOpen: false, item: null })}
            item={modalDetalhes.item}
            executeUpdateStatus={executeUpdateStatus}
            legalOneUsers={legalOneUsers}
            legalOneTasks={legalOneTasks}
          />
        </div>
      );
}

// --- Gerenciador de Usuários ---
const UserManagement = ({ users, onUserChange }) => {
    const [newUserName, setNewUserName] = useState('');
    const [error, setError] = useState('');

    const handleAddUser = async (e) => {
        e.preventDefault();
        setError('');
        if (!newUserName.trim()) { setError('O nome não pode ser vazio.'); return; }
        try {
            const response = await fetch(`${API_URL}/usuarios`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: newUserName }),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Falha ao adicionar usuário');
            }
            setNewUserName('');
            onUserChange();
        } catch (err) { setError(err.message); }
    };
    
    const handleDeleteUser = async (userId) => {
            try {
                const response = await fetch(`${API_URL}/usuarios/${userId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Falha ao remover usuário');
                onUserChange();
            } catch (err) { setError(err.message); }
    };

    return (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md max-w-2xl mx-auto">
            <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-gray-100">Gerenciar Responsáveis</h2>
            {error && <p className="text-red-500 mb-4">{error}</p>}
            <form onSubmit={handleAddUser} className="flex items-center gap-2 mb-6">
                <input type="text" value={newUserName} onChange={e => setNewUserName(e.target.value)} placeholder="Nome do novo responsável" className="border rounded-md py-2 px-3 flex-grow focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600" />
                <button type="submit" className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md">Adicionar</button>
            </form>
            <div className="space-y-2">
                {users.map(user => (
                    <div key={user.id} className="flex justify-between items-center p-3 border rounded-md bg-gray-50 dark:bg-gray-700 dark:border-gray-600">
                        <span className="font-medium text-gray-700 dark:text-gray-200">{user.nome}</span>
                        <button onClick={() => handleDeleteUser(user.id)} className="text-red-500 hover:text-red-700 font-semibold text-sm">Remover</button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default App;

