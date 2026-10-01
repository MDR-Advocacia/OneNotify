import React, { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/webpack';

export default function ReviewPdf({ url, name }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [pdf, setPdf] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const task = pdfjs.getDocument(url);
    setLoading(true);
    setError('');
    setPdf(null);
    setPageNumber(1);
    task.promise.then(document => {
      if (!active) return;
      setPdf(document);
      setPageCount(document.numPages);
    }).catch(() => {
      if (active) setError('Não foi possível exibir o PDF aqui. Abra o original em nova aba.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
      task.destroy();
    };
  }, [url]);

  useEffect(() => {
    if (!pdf || !canvasRef.current || !containerRef.current) return;
    let active = true;
    let renderTask;
    setLoading(true);
    pdf.getPage(pageNumber).then(page => {
      if (!active) return;
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      const original = page.getViewport({ scale: 1 });
      const fittedScale = Math.max(0.25, (container.clientWidth - 24) / original.width) * zoom;
      const viewport = page.getViewport({ scale: fittedScale });
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.ceil(viewport.width * pixelRatio);
      canvas.height = Math.ceil(viewport.height * pixelRatio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext('2d');
      renderTask = page.render({ canvasContext: context, viewport, transform: [pixelRatio, 0, 0, pixelRatio, 0, 0] });
      return renderTask.promise;
    }).then(() => {
      if (active) setLoading(false);
    }).catch(err => {
      if (active && err?.name !== 'RenderingCancelledException') {
        setError('Não foi possível renderizar esta página. Abra o original em nova aba.');
        setLoading(false);
      }
    });
    return () => {
      active = false;
      renderTask?.cancel();
    };
  }, [pdf, pageNumber, zoom]);

  return <div className="flex h-[34rem] flex-col">
    <div className="flex flex-wrap items-center gap-2 border-b bg-gray-50 px-2 py-1 text-sm">
      <button type="button" disabled={pageNumber <= 1} onClick={() => setPageNumber(value => value - 1)} className="rounded border px-2 py-1 disabled:opacity-40">Anterior</button>
      <span>Página {pageNumber} de {pageCount || '…'}</span>
      <button type="button" disabled={pageNumber >= pageCount} onClick={() => setPageNumber(value => value + 1)} className="rounded border px-2 py-1 disabled:opacity-40">Próxima</button>
      <button type="button" disabled={zoom <= 0.75} onClick={() => setZoom(value => Math.max(0.75, value - 0.25))} className="ml-auto rounded border px-2 py-1 disabled:opacity-40" aria-label="Diminuir zoom">−</button>
      <span>{Math.round(zoom * 100)}%</span>
      <button type="button" disabled={zoom >= 2.5} onClick={() => setZoom(value => Math.min(2.5, value + 0.25))} className="rounded border px-2 py-1 disabled:opacity-40" aria-label="Aumentar zoom">+</button>
    </div>
    <div ref={containerRef} className="min-h-0 flex-1 overflow-auto bg-gray-200 p-3 text-center">
      {error && <p role="alert" className="rounded bg-amber-50 p-3 text-amber-900">{error}</p>}
      {loading && !error && <p role="status">Carregando PDF…</p>}
      <canvas ref={canvasRef} aria-label={`Página ${pageNumber} do PDF ${name}`} className="mx-auto bg-white shadow" />
    </div>
  </div>;
}
