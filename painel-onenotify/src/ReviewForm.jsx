import React, { useEffect, useState } from 'react';

const STORAGE_KEY = 'notify-review-2026-10-v1';
const RELATIONS = [
  ['mesmo_ato', 'Mesmo ato de outro item do dossiê'],
  ['complemento', 'Complementa outro item'],
  ['assunto_proprio', 'Outro ato ou assunto que merece análise própria'],
  ['janela', 'Apareceu na janela, mas não se relaciona a esta notificação'],
  ['unico', 'Único conteúdo relevante neste dossiê'],
  ['incerto', 'Não consegui determinar'],
];
const ACTIONS = [
  ['nova_providencia', 'Exigiu ou exigiria nova providência'],
  ['ja_coberto', 'Já estava coberto por outra providência'],
  ['sem_providencia', 'Não exigiu providência'],
  ['conferir', 'Precisa de mais conferência'],
  ['incerto', 'Não sei dizer'],
];

const label = (options, value) => options.find(([key]) => key === value)?.[1] || 'Não respondido';

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const field = document.createElement('textarea');
  field.value = value;
  field.style.position = 'fixed';
  field.style.opacity = '0';
  document.body.appendChild(field);
  field.select();
  const copied = document.execCommand('copy');
  field.remove();
  if (!copied) throw new Error('O navegador bloqueou a área de transferência.');
}

function loadDraft() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function formatAnswers(cases, details, draft) {
  const lines = [
    'Revisão de casos reais do Notify — outubro/2026',
    `Operadora: ${draft.reviewer || 'não informado'}`,
    'A seleção de casos não representa uma conclusão automática sobre os documentos.',
  ];
  cases.forEach((entry, position) => {
    const item = details[entry.id];
    const answer = draft.answers?.[entry.id] || {};
    lines.push('', `CASO ${position + 1} — NPJ ${entry.npj || '?'} — ${entry.data_notificacao || '?'}`);
    if (!item) {
      lines.push('Caso não carregado na tela.');
      return;
    }
    lines.push(`Notificações do portal: ${item.notificacoes.map(n => n.tipo).join('; ')}`);
    item.documentos.forEach((doc, index) => {
      const response = answer.documents?.[doc.index] || {};
      lines.push(
        `Documento ${index + 1}: ${doc.nome}`,
        `Relação: ${label(RELATIONS, response.relation)}`,
        `Providência: ${label(ACTIONS, response.action)}`,
        `Sinais usados: ${response.reason?.trim() || 'não respondido'}`,
      );
    });
    lines.push(
      `Conclusão do dossiê: ${answer.conclusion?.trim() || 'não respondido'}`,
      `Consultou o portal do BB: ${answer.portal || 'não respondido'}`,
      `Motivo da consulta ou do dispensá-la: ${answer.portalReason?.trim() || 'não respondido'}`,
    );
  });
  return lines.join('\n');
}

export default function ReviewForm() {
  const [cases, setCases] = useState([]);
  const [details, setDetails] = useState({});
  const [draft, setDraft] = useState(loadDraft);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch('/api/revisao/casos')
      .then(response => {
        if (!response.ok) throw new Error('Não foi possível carregar a amostra.');
        return response.json();
      })
      .then(items => {
        setCases(items);
        setSelectedId(items.find(item => item.available)?.id || null);
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedId || details[selectedId]) return;
    fetch(`/api/revisao/casos/${selectedId}`)
      .then(response => {
        if (!response.ok) throw new Error('Não foi possível abrir este caso.');
        return response.json();
      })
      .then(item => setDetails(previous => ({ ...previous, [selectedId]: item })))
      .catch(err => setError(err.message));
  }, [selectedId, details]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  }, [draft]);

  const updateCase = patch => setDraft(previous => ({
    ...previous,
    answers: {
      ...previous.answers,
      [selectedId]: { ...previous.answers?.[selectedId], ...patch },
    },
  }));

  const updateDocument = (index, patch) => {
    const answer = draft.answers?.[selectedId] || {};
    updateCase({
      documents: {
        ...answer.documents,
        [index]: { ...answer.documents?.[index], ...patch },
      },
    });
  };

  const copyAnswers = async () => {
    setError('');
    setCopied(false);
    try {
      const missing = cases.filter(entry => entry.available && !details[entry.id]);
      const loaded = { ...details };
      for (const entry of missing) {
        const response = await fetch(`/api/revisao/casos/${entry.id}`);
        if (!response.ok) throw new Error(`Não foi possível carregar o caso ${entry.id}.`);
        loaded[entry.id] = await response.json();
      }
      setDetails(loaded);
      await copyText(formatAnswers(cases, loaded, draft));
      setCopied(true);
    } catch (err) {
      setError(`Não foi possível copiar: ${err.message}`);
    }
  };

  const item = details[selectedId];
  const answer = draft.answers?.[selectedId] || {};
  const inputClass = 'w-full rounded-md border border-gray-300 bg-white p-2 text-gray-900 focus:border-blue-600 focus:outline-none';

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <header className="border-b bg-white px-5 py-4">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">Revisão de casos do Notify</h1>
            <p className="text-sm text-gray-600">Amostra para entender seu raciocínio. Esta página não altera o tratamento dos casos.</p>
          </div>
          <a className="text-sm text-blue-700 underline" href="/">Voltar ao painel</a>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-5">
        <div className="mb-5 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
          A janela de documentos do NPJ pode conter itens do mesmo ato, de outro assunto ou apenas documentos próximos no tempo. Examine cada caso como faria no trabalho. Se uma opção não servir, explique no campo livre. Seu rascunho fica salvo neste navegador; ao terminar, copie as respostas e cole no Teams.
        </div>
        {error && <p role="alert" className="mb-4 rounded bg-red-100 p-3 text-red-800">{error}</p>}
        <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
          <aside className="rounded-lg bg-white p-4 shadow-sm h-fit">
            <label className="mb-2 block text-sm font-medium" htmlFor="reviewer">Seu nome</label>
            <input id="reviewer" className={inputClass} value={draft.reviewer || ''} onChange={e => setDraft(previous => ({ ...previous, reviewer: e.target.value }))} />
            <h2 className="mb-2 mt-6 font-semibold">Casos selecionados</h2>
            <div className="space-y-2">
              {cases.map((entry, index) => (
                <button key={entry.id} type="button" disabled={!entry.available} onClick={() => { setSelectedId(entry.id); setError(''); }} className={`w-full rounded-md border p-3 text-left text-sm ${selectedId === entry.id ? 'border-blue-600 bg-blue-50' : 'border-gray-200'} disabled:opacity-50`}>
                  <strong>Caso {index + 1}</strong><br />
                  <span>{entry.data_notificacao || 'Indisponível'} · {entry.andamentos} andamento(s) · {entry.documentos} documento(s)</span>
                </button>
              ))}
            </div>
            <button type="button" onClick={copyAnswers} className="mt-5 w-full rounded-md bg-blue-700 px-4 py-3 font-semibold text-white hover:bg-blue-800">Copiar respostas para o Teams</button>
            {copied && <p role="status" className="mt-2 text-sm text-green-700">Copiado. Cole na conversa do Teams.</p>}
          </aside>

          <section className="space-y-5">
            {!item && <div className="rounded-lg bg-white p-5 shadow-sm">{selectedId ? 'Carregando caso...' : 'Nenhum caso disponível.'}</div>}
            {item && <>
              <div className="rounded-lg bg-white p-5 shadow-sm">
                <h2 className="text-lg font-semibold">NPJ {item.npj} · {item.data_notificacao}</h2>
                {item.numero_processo && <p className="text-sm text-gray-600">Processo: {item.numero_processo}</p>}
                <h3 className="mb-1 mt-4 font-medium">Notificações recebidas</h3>
                <ul className="list-inside list-disc text-sm">{item.notificacoes.map(n => <li key={n.id}>{n.tipo}</li>)}</ul>
                <p className="mt-3 text-sm text-gray-600">Os documentos abaixo vêm da janela de conferência do NPJ. A presença na lista não prova que pertençam à mesma publicação.</p>
              </div>

              <div className="rounded-lg bg-white p-5 shadow-sm">
                <h3 className="font-semibold">Andamentos capturados</h3>
                {!item.andamentos.length && <p className="mt-2 text-sm text-gray-600">Nenhum andamento capturado neste dossiê.</p>}
                {item.andamentos.map((andamento, index) => <details key={index} className="mt-3 rounded border p-3">
                  <summary className="cursor-pointer font-medium">{andamento.data} · {andamento.descricao}</summary>
                  <pre className="mt-3 whitespace-pre-wrap break-words text-sm font-sans">{andamento.detalhes}</pre>
                </details>)}
              </div>

              {item.documentos.map((doc, position) => {
                const response = answer.documents?.[doc.index] || {};
                return <div key={doc.index} className="rounded-lg bg-white p-5 shadow-sm">
                  <h3 className="font-semibold">Documento {position + 1}: <span className="break-all font-normal">{doc.nome}</span></h3>
                  <div className="mt-2 flex flex-wrap gap-3 text-sm">
                    <a className="text-blue-700 underline" href={`/api/documentos/view?path=${encodeURIComponent(doc.caminho)}`} target="_blank" rel="noopener noreferrer">Abrir original</a>
                    {doc.text_preview && <details><summary className="cursor-pointer text-blue-700 underline">Ver texto extraído</summary><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-50 p-3 font-sans text-gray-800">{doc.text_preview}{doc.text_preview_truncated ? '\n\n[Prévia limitada; confira o original]' : ''}</pre></details>}
                    {!doc.text_preview && <span className="text-gray-600">Sem texto extraído; confira o original.</span>}
                  </div>
                  <label className="mb-1 mt-5 block text-sm font-medium" htmlFor={`relation-${doc.index}`}>O que este documento representa no dossiê?</label>
                  <select id={`relation-${doc.index}`} className={inputClass} value={response.relation || ''} onChange={e => updateDocument(doc.index, { relation: e.target.value })}>
                    <option value="">Selecione ou explique abaixo</option>
                    {RELATIONS.map(([value, text]) => <option value={value} key={value}>{text}</option>)}
                  </select>
                  <label className="mb-1 mt-4 block text-sm font-medium" htmlFor={`action-${doc.index}`}>Qual foi ou seria a providência?</label>
                  <select id={`action-${doc.index}`} className={inputClass} value={response.action || ''} onChange={e => updateDocument(doc.index, { action: e.target.value })}>
                    <option value="">Selecione ou explique abaixo</option>
                    {ACTIONS.map(([value, text]) => <option value={value} key={value}>{text}</option>)}
                  </select>
                  <label className="mb-1 mt-4 block text-sm font-medium" htmlFor={`reason-${doc.index}`}>Que sinal ou informação levou você a essa conclusão?</label>
                  <textarea id={`reason-${doc.index}`} rows={3} className={inputClass} value={response.reason || ''} onChange={e => updateDocument(doc.index, { reason: e.target.value })} placeholder="Pode apontar um trecho, a data, outro documento ou o que precisaria conferir." />
                </div>;
              })}

              <div className="rounded-lg bg-white p-5 shadow-sm">
                <h3 className="font-semibold">Fechamento do dossiê</h3>
                <label className="mb-1 mt-4 block text-sm font-medium" htmlFor="conclusion">O que você fez ou faria com este conjunto?</label>
                <textarea id="conclusion" rows={3} className={inputClass} value={answer.conclusion || ''} onChange={e => updateCase({ conclusion: e.target.value })} />
                <label className="mb-1 mt-4 block text-sm font-medium" htmlFor="portal">Precisou consultar o portal do BB?</label>
                <select id="portal" className={inputClass} value={answer.portal || ''} onChange={e => updateCase({ portal: e.target.value })}>
                  <option value="">Selecione</option><option value="Sim">Sim</option><option value="Não">Não</option><option value="Não lembro">Não lembro</option>
                </select>
                <label className="mb-1 mt-4 block text-sm font-medium" htmlFor="portal-reason">Por quê? O que faltou ou o que foi suficiente no Notify?</label>
                <textarea id="portal-reason" rows={2} className={inputClass} value={answer.portalReason || ''} onChange={e => updateCase({ portalReason: e.target.value })} />
              </div>
            </>}
          </section>
        </div>
      </main>
    </div>
  );
}
