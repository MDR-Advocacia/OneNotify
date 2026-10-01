import React, { useEffect, useState } from 'react';
import ReviewPdf from './ReviewPdf';

const STORAGE_KEY = 'notify-review-2026-10-v2';
const PREVIOUS_STORAGE_KEY = 'notify-review-2026-10-v1';
const MIN_REASON_CHARS = 120;
const MIN_CONCLUSION_CHARS = 120;
const MIN_SOURCE_CHARS = 80;

// As perguntas descrevem os arquivos da amostra, sem antecipar a conclusão.
const CASE_GUIDES = {
  164455: {
    navLabel: 'TJRN · custas finais',
    title: 'TJRN: publicação e PDF da intimação sobre custas finais',
    intro: 'A publicação menciona comprovação das custas finais em 30 dias. Compare esse comando com o PDF da intimação.',
    conclusionQuestion: 'Neste caso, uma tarefa sobre as custas finais cobriria publicação e PDF? Descreva exatamente o que você faria e qual prazo registraria.',
    sourceQuestion: 'Para decidir sobre custas e prazo, você precisaria sair do Notify? Diga qual informação buscaria.',
    documents: {
      0: {
        relationQuestion: 'O PDF traz a mesma intimação da publicação de 24/09 para comprovar as custas finais?',
        relationOptions: [['mesmo_ato', 'Sim, é a mesma intimação'], ['complemento', 'É a mesma intimação, mas o PDF acrescenta informação relevante'], ['assunto_proprio', 'Não, o PDF contém outro ato'], ['incerto', 'Não consigo concluir']],
        actionQuestion: 'Se a publicação já tiver uma tarefa de custas finais, o PDF exige outra providência?',
        actionOptions: [['ja_coberto', 'Não, a tarefa da publicação cobre o PDF'], ['nova_providencia', 'Sim, exige providência adicional'], ['sem_providencia', 'Nenhuma providência é necessária'], ['conferir', 'Preciso conferir outra fonte para decidir']],
        reasonQuestion: 'Cite o trecho da publicação e a página/trecho do PDF sobre custas e prazo. Explique o que é igual ou diferente e por que a providência escolhida cobre o risco.',
      },
    },
  },
  164118: {
    navLabel: 'TJRN · 15 dias + TXT',
    title: 'TJRN: intimação de 15 dias, PDF e alerta TXT',
    intro: 'A publicação pede manifestação em 15 dias. O PDF contém uma intimação; o TXT diz que arquivos adicionais podem ter falhado na captura. Julgue os dois arquivos separadamente.',
    conclusionQuestion: 'A intimação de 15 dias fica totalmente coberta pelo PDF e pela publicação? O alerta TXT deixa alguma pendência concreta? Descreva o encaminhamento de cada item.',
    sourceQuestion: 'Você abriria o link do TXT ou consultaria o tribunal/BB neste caso? Explique o que tentaria confirmar.',
    documents: {
      0: {
        relationQuestion: 'O alerta TXT indica que falta um arquivo necessário, mesmo com o PDF da intimação disponível?',
        relationOptions: [['alerta_resolvido', 'Não, o PDF já contém o ato necessário'], ['precisa_buscar', 'Sim, pode faltar arquivo essencial'], ['assunto_proprio', 'O TXT aponta outro ato ou assunto'], ['incerto', 'Não consigo concluir']],
        actionQuestion: 'O que você faria especificamente com o link indicado no TXT?',
        actionOptions: [['ja_coberto', 'Dispensaria a consulta; o PDF resolve'], ['conferir', 'Abriria o link para verificar outro arquivo'], ['nova_providencia', 'Abriria uma pendência própria pela falta do arquivo'], ['incerto', 'Não consigo decidir']],
        reasonQuestion: 'Explique o que o TXT afirma que não foi obtido, o que o PDF já oferece e por que isso basta ou não basta. Se abriria o link, diga o que procuraria.',
      },
      1: {
        relationQuestion: 'O PDF contém o mesmo ato ordinatório publicado em 23/09 para requerer o prosseguimento em 15 dias?',
        relationOptions: [['mesmo_ato', 'Sim, reproduz o mesmo ato'], ['complemento', 'É o mesmo ato, com detalhe que muda a análise'], ['assunto_proprio', 'Não, refere-se a outro ato'], ['incerto', 'Não consigo concluir']],
        actionQuestion: 'O PDF exige algo além da providência ligada à publicação de 15 dias?',
        actionOptions: [['ja_coberto', 'Não, a providência da publicação cobre o PDF'], ['nova_providencia', 'Sim, há outra providência'], ['sem_providencia', 'Não há providência a tomar'], ['conferir', 'Preciso conferir outra fonte']],
        reasonQuestion: 'Compare o comando e o prazo escritos na publicação e no PDF. Indique o trecho/página que sustenta sua resposta e a tarefa que seria registrada.',
      },
    },
  },
  163811: {
    navLabel: 'TJAP · seguro',
    title: 'TJAP: publicação e documento de restituição de seguro',
    intro: 'Há uma publicação de intimação do TJAP e, na janela do NPJ, um PDF de restituição de seguro. A presença no mesmo dossiê não resolve a relação entre eles.',
    conclusionQuestion: 'Você trataria a publicação e o PDF de seguro juntos, separadamente ou deixaria o PDF fora desta notificação? Descreva o trabalho que cada um exige.',
    sourceQuestion: 'Você precisaria consultar os autos ou o portal para ligar o PDF de seguro à publicação? Diga exatamente o que verificaria.',
    documents: {
      0: {
        relationQuestion: 'O PDF de restituição de seguro integra o ato comunicado pela publicação do TJAP?',
        relationOptions: [['mesmo_ato', 'Sim, é documento do mesmo ato'], ['complemento', 'Complementa o assunto da publicação'], ['assunto_proprio', 'É outro assunto que exige avaliação própria'], ['janela', 'Só apareceu na janela; não se relaciona à publicação'], ['incerto', 'Não consigo concluir']],
        actionQuestion: 'Esse PDF de seguro exige providência própria?',
        actionOptions: [['nova_providencia', 'Sim, providência própria'], ['ja_coberto', 'Não, já está coberto pela publicação'], ['sem_providencia', 'Não exige providência'], ['conferir', 'Preciso conferir os autos ou outra fonte']],
        reasonQuestion: 'Aponte o assunto/comando da publicação e o conteúdo do PDF que você comparou. Explique por que há ou não vínculo e qual risco ficaria sem tratamento.',
      },
    },
  },
  167236: {
    navLabel: 'TXT · arquivo não obtido',
    title: 'TJRN: só um TXT com link para documento não obtido',
    intro: 'Neste dossiê não há publicação capturada. O TXT relata falha na obtenção de arquivo adicional e oferece um link do PJe.',
    conclusionQuestion: 'Sem publicação e sem o documento final no Notify, que status ou pendência você deixaria para este NPJ? O que precisa ser conhecido antes de encerrar?',
    sourceQuestion: 'Você conseguiu ou conseguiria abrir o link do TXT? Se não, qual fonte usaria e como acompanharia a pendência?',
    documents: {
      0: {
        relationQuestion: 'O TXT permite identificar o conteúdo e a importância do documento que o robô não obteve?',
        relationOptions: [['texto_suficiente', 'Sim, o TXT basta para decidir'], ['precisa_buscar', 'Não, preciso abrir o link ou buscar o documento'], ['sem_acesso', 'Tentei, mas o link não dá acesso'], ['incerto', 'Não consigo concluir']],
        actionQuestion: 'Qual é o próximo passo concreto para esta notificação?',
        actionOptions: [['conferir', 'Abrir link/portal e examinar o documento'], ['nova_providencia', 'Registrar pendência para obter o documento'], ['sem_providencia', 'Nenhuma providência é necessária'], ['incerto', 'Não consigo decidir']],
        reasonQuestion: 'Descreva o que o TXT efetivamente informa, o que ainda falta saber sobre o ato e como você obteria essa informação. Se tentou o link, relate o resultado.',
      },
    },
  },
  168581: {
    navLabel: 'PDF · protesto',
    title: 'PDF em imagem: intimação de protesto do tabelionato',
    intro: 'Neste dossiê não há publicação capturada. A primeira página do PDF é uma intimação de protesto dirigida ao BB; a segunda contém informações do tabelionato. Examine as duas páginas.',
    conclusionQuestion: 'A intimação de protesto deve gerar providência, ficar pendente para conferência ou ser dispensada? Diga qual prazo consideraria e para quem encaminharia.',
    sourceQuestion: 'Para avaliar o protesto, o PDF incorporado foi suficiente? Se não, que informação precisaria obter no NPJ, no portal ou por OCR?',
    documents: {
      0: {
        relationQuestion: 'A intimação de protesto do PDF está ligada ao assunto deste NPJ?',
        relationOptions: [['identificado_relevante', 'Sim, identifiquei conteúdo relevante ao NPJ'], ['identificado_irrelevante', 'Sim, mas não se relaciona a esta notificação'], ['ilegivel', 'Não, o original está ilegível ou incompleto'], ['incerto', 'Não consigo concluir sem outra fonte']],
        actionQuestion: 'A intimação de protesto aponta alguma providência ou prazo a controlar?',
        actionOptions: [['nova_providencia', 'Sim, há providência ou prazo'], ['sem_providencia', 'Não há providência'], ['conferir', 'Preciso de leitura/OCR ou outra fonte'], ['incerto', 'Não consigo decidir']],
        reasonQuestion: 'Indique a página e os dados do título que usou para ligar ou não o protesto ao NPJ. Explique o prazo, o comando e o risco de agir ou encerrar sem conferir.',
      },
    },
  },
};

const getGuide = id => CASE_GUIDES[id];
const getDocumentGuide = (id, index) => getGuide(id)?.documents?.[index];

function courtLinks(text) {
  return [...new Set((text.match(/https?:\/\/[^\s]+/g) || []).map(value => value.replace(/[),.;]+$/, '')))]
    .filter(value => {
      try { return /(^|\.)jus\.br$/i.test(new URL(value).hostname); } catch { return false; }
    })
    .slice(0, 3);
}

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
    const current = localStorage.getItem(STORAGE_KEY);
    if (current) return JSON.parse(current);
    const previous = JSON.parse(localStorage.getItem(PREVIOUS_STORAGE_KEY) || '{}');
    if (!previous.answers) return previous;
    // As perguntas mudaram: preserve os textos escritos, mas peça novas escolhas.
    return {
      reviewer: previous.reviewer,
      answers: Object.fromEntries(Object.entries(previous.answers).map(([caseId, answer]) => [caseId, {
        conclusion: answer.conclusion,
        portalReason: answer.portalReason,
        documents: Object.fromEntries(Object.entries(answer.documents || {}).map(([index, doc]) => [index, { reason: doc.reason }])),
      }])),
    };
  } catch {
    return {};
  }
}

function firstMissingAnswer(cases, details, draft) {
  if (!draft.reviewer?.trim()) return { caseId: cases[0]?.id, message: 'Informe seu nome antes de copiar as respostas.' };
  for (const [position, entry] of cases.entries()) {
    if (!entry.available) continue;
    const item = details[entry.id];
    const answer = draft.answers?.[entry.id] || {};
    for (const [index, doc] of item.documentos.entries()) {
      const response = answer.documents?.[doc.index] || {};
      const guide = getDocumentGuide(entry.id, doc.index);
      if (!guide?.relationOptions.some(([value]) => value === response.relation)) {
        return { caseId: entry.id, message: `Caso ${position + 1}, documento ${index + 1}: responda à primeira pergunta.` };
      }
      if (!guide?.actionOptions.some(([value]) => value === response.action)) {
        return { caseId: entry.id, message: `Caso ${position + 1}, documento ${index + 1}: escolha a providência.` };
      }
      if ((response.reason || '').trim().length < MIN_REASON_CHARS) {
        return { caseId: entry.id, message: `Caso ${position + 1}, documento ${index + 1}: explique sua decisão com ao menos ${MIN_REASON_CHARS} caracteres, incluindo o trecho ou página consultado.` };
      }
    }
    if ((answer.conclusion || '').trim().length < MIN_CONCLUSION_CHARS) {
      return { caseId: entry.id, message: `Caso ${position + 1}: descreva o encaminhamento do dossiê com ao menos ${MIN_CONCLUSION_CHARS} caracteres.` };
    }
    if (!['Sim', 'Não', 'Não consigo decidir'].includes(answer.portal)) {
      return { caseId: entry.id, message: `Caso ${position + 1}: responda se precisaria sair do Notify.` };
    }
    if ((answer.portalReason || '').trim().length < MIN_SOURCE_CHARS) {
      return { caseId: entry.id, message: `Caso ${position + 1}: detalhe a consulta externa ou por que o Notify bastou, com ao menos ${MIN_SOURCE_CHARS} caracteres.` };
    }
  }
  return null;
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
    const guide = getGuide(entry.id);
    lines.push('', `CASO ${position + 1} — ${guide?.title || 'Dossiê'} — NPJ ${entry.npj || '?'} — ${entry.data_notificacao || '?'}`);
    if (!item) {
      lines.push('Caso não carregado na tela.');
      return;
    }
    lines.push(`Notificações do portal: ${item.notificacoes.map(n => n.tipo).join('; ')}`);
    item.documentos.forEach((doc, index) => {
      const response = answer.documents?.[doc.index] || {};
      const questions = getDocumentGuide(entry.id, doc.index);
      lines.push(
        `Documento ${index + 1}: ${doc.nome}`,
        `${questions.relationQuestion} ${label(questions.relationOptions, response.relation)}`,
        `${questions.actionQuestion} ${label(questions.actionOptions, response.action)}`,
        `${questions.reasonQuestion} ${response.reason?.trim() || 'não respondido'}`,
      );
    });
    lines.push(
      `${guide.conclusionQuestion} ${answer.conclusion?.trim() || 'não respondido'}`,
      `Precisaria sair do Notify: ${answer.portal || 'não respondido'}`,
      `${guide.sourceQuestion} ${answer.portalReason?.trim() || 'não respondido'}`,
    );
  });
  return lines.join('\n');
}

export default function ReviewForm() {
  const [cases, setCases] = useState([]);
  const [details, setDetails] = useState({});
  const [draft, setDraft] = useState(loadDraft);
  const [selectedId, setSelectedId] = useState(null);
  const [viewModes, setViewModes] = useState({});
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
      const missingAnswer = firstMissingAnswer(cases, loaded, draft);
      if (missingAnswer) {
        setSelectedId(missingAnswer.caseId);
        setError(missingAnswer.message);
        return;
      }
      await copyText(formatAnswers(cases, loaded, draft));
      setCopied(true);
    } catch (err) {
      setError(`Não foi possível copiar: ${err.message}`);
    }
  };

  const item = details[selectedId];
  const answer = draft.answers?.[selectedId] || {};
  const guide = getGuide(selectedId);
  const publications = item?.andamentos?.filter(andamento => andamento.descricao?.toUpperCase().includes('PUBLICACAO DJ/DO')) || [];
  const inputClass = 'w-full rounded-md border border-gray-300 bg-white p-2 text-gray-900 focus:border-blue-600 focus:outline-none';

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <header className="border-b bg-white px-5 py-4">
        <div className="mx-auto max-w-screen-2xl flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">Revisão de casos do Notify</h1>
            <p className="text-sm text-gray-600">Amostra para entender seu raciocínio. Esta página não altera o tratamento dos casos.</p>
          </div>
          <a className="text-sm text-blue-700 underline" href="/">Voltar ao painel</a>
        </div>
      </header>
      <main className="mx-auto max-w-screen-2xl p-5">
        <div className="mb-5 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
          Compare a publicação com cada documento. Escreva respostas completas: cite o trecho ou página, indique prazo ou comando quando houver, explique a providência e o motivo da decisão. Se não conseguir concluir, descreva exatamente o que falta verificar. O rascunho fica neste navegador; ao terminar, copie as respostas para o Teams.
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
                  <strong>Caso {index + 1} · {getGuide(entry.id)?.navLabel || 'Indisponível'}</strong><br />
                  <span>{entry.data_notificacao || 'Indisponível'} · {entry.andamentos} andamento(s) · {entry.documentos} documento(s)</span>
                </button>
              ))}
            </div>
            <button type="button" onClick={copyAnswers} className="mt-5 w-full rounded-md bg-blue-700 px-4 py-3 font-semibold text-white hover:bg-blue-800">Copiar respostas para o Teams</button>
            {error && <p role="alert" className="mt-2 text-sm text-red-800">{error}</p>}
            {copied && <p role="status" className="mt-2 text-sm text-green-700">Copiado. Cole na conversa do Teams.</p>}
          </aside>

          <section className="space-y-5">
            {!item && <div className="rounded-lg bg-white p-5 shadow-sm">{selectedId ? 'Carregando caso...' : 'Nenhum caso disponível.'}</div>}
            {item && <>
              <div className="rounded-lg bg-white p-5 shadow-sm">
                <h2 className="text-lg font-semibold">{guide?.title}</h2>
                <p className="mt-1 text-sm text-gray-700">{guide?.intro}</p>
                <p className="mt-3 text-sm font-medium">NPJ {item.npj} · {item.data_notificacao}</p>
                {item.numero_processo && <p className="text-sm text-gray-600">Processo: {item.numero_processo}</p>}
                <h3 className="mb-1 mt-4 font-medium">Notificações recebidas</h3>
                <ul className="list-inside list-disc text-sm">{item.notificacoes.map(n => <li key={n.id}>{n.tipo}</li>)}</ul>
                <p className="mt-3 text-sm text-gray-600">Os documentos vêm da janela de conferência do NPJ. Julgue cada relação pelo conteúdo exibido, não pela proximidade da data.</p>
              </div>

              {item.documentos.map((doc, position) => {
                const response = answer.documents?.[doc.index] || {};
                const questions = getDocumentGuide(selectedId, doc.index);
                const modeKey = `${selectedId}-${doc.index}`;
                const hasText = Boolean(doc.text_preview?.trim());
                const viewMode = viewModes[modeKey] || (hasText ? 'text' : 'original');
                const originalUrl = `/api/documentos/view?path=${encodeURIComponent(doc.caminho)}`;
                const links = doc.mime_type === 'text/plain' ? courtLinks(doc.text_preview || '') : [];
                return <div key={doc.index} className="rounded-lg bg-white p-5 shadow-sm">
                  <h3 className="font-semibold">Documento {position + 1}: <span className="break-all font-normal">{doc.nome}</span></h3>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
                    {hasText && <button type="button" aria-pressed={viewMode === 'text'} onClick={() => setViewModes(previous => ({ ...previous, [modeKey]: 'text' }))} className={`rounded px-3 py-1.5 ${viewMode === 'text' ? 'bg-blue-700 text-white' : 'bg-gray-100 text-blue-700'}`}>Comparar textos</button>}
                    <button type="button" aria-pressed={viewMode === 'original'} onClick={() => setViewModes(previous => ({ ...previous, [modeKey]: 'original' }))} className={`rounded px-3 py-1.5 ${viewMode === 'original' ? 'bg-blue-700 text-white' : 'bg-gray-100 text-blue-700'}`}>Ver original incorporado</button>
                    <a className="text-blue-700 underline" href={originalUrl} target="_blank" rel="noopener noreferrer">Abrir em nova aba</a>
                  </div>
                  {links.length > 0 && <div className="mt-3 text-sm">{links.map((url, index) => <a key={url} className="mr-4 text-blue-700 underline" href={url} target="_blank" rel="noopener noreferrer">Abrir link do tribunal {index + 1}</a>)}</div>}
                  <div className={`mt-4 grid gap-4 ${publications.length ? 'xl:grid-cols-2' : 'grid-cols-1'}`}>
                    {publications.length > 0 && <div className="min-w-0 rounded border border-gray-200">
                      <h4 className="border-b bg-gray-50 px-3 py-2 font-medium">Publicação capturada</h4>
                      <div className="h-[34rem] overflow-y-auto p-3 text-sm leading-6">
                        {publications.map((publication, index) => <div key={index} className="mb-5">
                          <p className="mb-2 font-medium">{publication.data} · {publication.descricao}</p>
                          <pre className="whitespace-pre-wrap break-words font-sans">{publication.detalhes}</pre>
                        </div>)}
                      </div>
                    </div>}
                    <div className="min-w-0 rounded border border-gray-200">
                      <h4 className="border-b bg-gray-50 px-3 py-2 font-medium">{viewMode === 'text' ? 'Texto extraído do documento' : 'Documento original'}</h4>
                      {viewMode === 'text' && hasText
                        ? <div className="h-[34rem] overflow-y-auto p-3 text-sm leading-6"><pre className="whitespace-pre-wrap break-words font-sans">{doc.text_preview}{doc.text_preview_truncated ? '\n\n[Prévia limitada: confira o original]' : ''}</pre></div>
                        : doc.mime_type === 'text/plain' || doc.nome.toLowerCase().endsWith('.txt')
                          ? <iframe title={`Original do documento ${position + 1}: ${doc.nome}`} src={originalUrl} className="h-[34rem] w-full" />
                          : <ReviewPdf url={originalUrl} name={doc.nome} />}
                    </div>
                  </div>
                  {!hasText && <p className="mt-2 text-sm text-amber-800">Este arquivo não tem texto extraído. Examine o original incorporado.</p>}
                  <label className="mb-1 mt-6 block text-sm font-semibold" htmlFor={`relation-${doc.index}`}>{questions.relationQuestion}</label>
                  <select id={`relation-${doc.index}`} className={inputClass} value={response.relation || ''} onChange={e => updateDocument(doc.index, { relation: e.target.value })}>
                    <option value="">Selecione uma resposta</option>
                    {questions.relationOptions.map(([value, text]) => <option value={value} key={value}>{text}</option>)}
                  </select>
                  <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor={`action-${doc.index}`}>{questions.actionQuestion}</label>
                  <select id={`action-${doc.index}`} className={inputClass} value={response.action || ''} onChange={e => updateDocument(doc.index, { action: e.target.value })}>
                    <option value="">Selecione uma resposta</option>
                    {questions.actionOptions.map(([value, text]) => <option value={value} key={value}>{text}</option>)}
                  </select>
                  <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor={`reason-${doc.index}`}>{questions.reasonQuestion}</label>
                  <textarea id={`reason-${doc.index}`} rows={5} className={inputClass} value={response.reason || ''} onChange={e => updateDocument(doc.index, { reason: e.target.value })} placeholder="Descreva em algumas frases: o que leu, em qual página/trecho, qual prazo ou efeito encontrou e por que essa resposta é segura. Se houver dúvida, explique exatamente o que falta." />
                  <p className="mt-1 text-xs text-gray-600">Descrição detalhada: {(response.reason || '').trim().length}/{MIN_REASON_CHARS} caracteres mínimos.</p>
                </div>;
              })}

              <div className="rounded-lg bg-white p-5 shadow-sm">
                <h3 className="font-semibold">Fechamento do dossiê</h3>
                <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor="conclusion">{guide.conclusionQuestion}</label>
                <textarea id="conclusion" rows={5} className={inputClass} value={answer.conclusion || ''} onChange={e => updateCase({ conclusion: e.target.value })} placeholder="Descreva a providência, eventual prazo, o que você marcaria como coberto e o que deixaria pendente." />
                <p className="mt-1 text-xs text-gray-600">Descrição detalhada: {(answer.conclusion || '').trim().length}/{MIN_CONCLUSION_CHARS} caracteres mínimos.</p>
                <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor="portal">Para concluir, você precisaria sair do Notify (portal BB, tribunal ou autos)?</label>
                <select id="portal" className={inputClass} value={answer.portal || ''} onChange={e => updateCase({ portal: e.target.value })}>
                  <option value="">Selecione</option><option value="Sim">Sim</option><option value="Não">Não</option><option value="Não consigo decidir">Não consigo decidir</option>
                </select>
                <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor="portal-reason">{guide.sourceQuestion}</label>
                <textarea id="portal-reason" rows={3} className={inputClass} value={answer.portalReason || ''} onChange={e => updateCase({ portalReason: e.target.value })} placeholder="Diga qual informação falta, onde buscaria e como essa verificação muda sua decisão; ou por que o Notify já foi suficiente." />
                <p className="mt-1 text-xs text-gray-600">Descrição detalhada: {(answer.portalReason || '').trim().length}/{MIN_SOURCE_CHARS} caracteres mínimos.</p>
              </div>
            </>}
          </section>
        </div>
      </main>
    </div>
  );
}
