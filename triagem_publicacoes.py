"""Triagem local, sem efeitos colaterais, dos atos de publicação do BB.

O dossiê do Notify é uma janela de consulta por NPJ/data. Um documento presente
nessa janela não pertence necessariamente à notificação de publicação.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any


SCHEMA_VERSION = "onenotify.publication-triage.v1"
MIN_EQUIVALENT_TOKENS = 20
MAX_COMPARE_TOKENS = 2500
CNJ_PATTERN = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
EXTRA_DECISION_WORDS = {"defiro", "indefiro", "julgo", "condeno", "determino", "homologo"}
CRITICAL_WORDS = {
    "defiro", "indefiro", "deferido", "indeferido", "procedente", "improcedente",
    "julgo", "condeno", "determino", "homologo", "acolho", "rejeito", "nego",
    "concedo", "revogo", "suspensao", "arquivamento",
    "cinco", "dez", "quinze", "trinta", "sessenta", "noventa", "prazo", "dias",
}


def _tokens(value: Any) -> list[str]:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", text)


def _document_text(document: dict[str, Any]) -> str:
    extraction = document.get("extraction") or {}
    return "\n\n".join(
        str(page.get("text") or "")
        for page in extraction.get("pages") or []
        if isinstance(page, dict)
    ).strip()


def _deadline_signatures(value: str) -> set[str]:
    tokens = _tokens(value)
    return {
        tokens[index + 2]
        for index in range(len(tokens) - 3)
        if tokens[index:index + 2] == ["prazo", "de"] and tokens[index + 3] == "dias"
    }


def _is_publication(andamento: dict[str, Any]) -> bool:
    title = " ".join(_tokens(andamento.get("descricao")))
    return "publicacao" in title and ("dj do" in title or "djen" in title)


def _candidate_overlap(publication: list[str], document: list[str]) -> dict[str, Any]:
    if not publication or not document:
        return {"longest_common_tokens": 0, "publication_coverage": 0.0, "document_coverage": 0.0}
    blocks = SequenceMatcher(None, publication, document, autojunk=False).get_matching_blocks()
    common = sum(block.size for block in blocks)
    return {
        "longest_common_tokens": max(block.size for block in blocks),
        "publication_coverage": round(common / len(publication), 3),
        "document_coverage": round(common / len(document), 3),
    }


def _same_core(publication_text: str, document_text: str, evidence: dict[str, Any]) -> bool:
    """Reconhece o mesmo corpo final com cabeçalhos diferentes, sem decidir por score só."""
    publication = _tokens(publication_text)
    document = _tokens(document_text)
    if not publication or not document:
        return False
    publication_cnjs = set(CNJ_PATTERN.findall(publication_text))
    document_cnjs = set(CNJ_PATTERN.findall(document_text))
    if len(publication_cnjs) != 1 or publication_cnjs != document_cnjs:
        return False
    block = max(
        SequenceMatcher(None, publication, document, autojunk=False).get_matching_blocks(),
        key=lambda item: item.size,
    )
    if (block.size < 80 or len(publication) - block.a - block.size > 5
            or len(document) - block.b - block.size > 50):
        return False
    if evidence["publication_coverage"] < 0.6 or evidence["document_coverage"] < 0.5:
        return False
    publication_critical = Counter(token for token in publication if token in CRITICAL_WORDS)
    document_critical = Counter(token for token in document if token in CRITICAL_WORDS)
    if publication_critical != document_critical:
        return False
    if _deadline_signatures(publication_text) != _deadline_signatures(document_text):
        return False
    unmatched_document = document[:block.b] + document[block.b + block.size:]
    return not EXTRA_DECISION_WORDS.intersection(unmatched_document)


def analisar_dossie(
    andamentos: Any,
    documentos_json: Any,
    documentos_originais: Any = None,
) -> dict[str, Any]:
    """Separa publicação e documentos; só libera repetição textual demonstrável.

    Não envia ao Flow, altera status, descarta arquivo nem toma decisão jurídica.
    `documentos_originais` detecta arquivos ainda sem extração estruturada.
    """
    andamentos = andamentos if isinstance(andamentos, list) else []
    originais = documentos_originais if isinstance(documentos_originais, list) else []
    envelope = documentos_json if isinstance(documentos_json, dict) else {}
    items = envelope.get("items") if isinstance(envelope.get("items"), list) else []

    publications: dict[str, dict[str, Any]] = {}
    other_movements = []
    for index, andamento in enumerate(andamentos):
        if not isinstance(andamento, dict):
            other_movements.append(index)
            continue
        if not _is_publication(andamento):
            other_movements.append(index)
            continue
        text = str(andamento.get("detalhes") or "").strip()
        tokens = _tokens(text)
        identity = hashlib.sha256(
            (str(andamento.get("data") or "") + "|" + " ".join(tokens)).encode("utf-8")
        ).hexdigest()[:20]
        if identity not in publications:
            publications[identity] = {
                "id": identity,
                "data": andamento.get("data"),
                "texto": text,
                "indices_andamentos": [],
                "texto_util": len(tokens) >= MIN_EQUIVALENT_TOKENS,
            }
        publications[identity]["indices_andamentos"].append(index)

    publication_list = list(publications.values())
    reference_tokens = _tokens(publication_list[0]["texto"]) if len(publication_list) == 1 else []
    documents = []
    total_documents = max(len(items), len(originais))
    for index in range(total_documents):
        item = items[index] if index < len(items) and isinstance(items[index], dict) else {}
        original = originais[index] if index < len(originais) and isinstance(originais[index], dict) else {}
        extraction = item.get("extraction") or {}
        text = _document_text(item)
        tokens = _tokens(text)
        relation = "NAO_ANALISADO"
        reason = "sem_publicacao_unica"
        evidence = None
        if reference_tokens:
            if not item or extraction.get("status") != "ok" or extraction.get("truncated") or extraction.get("ocr_required"):
                relation, reason = "INCONCLUSIVO", "texto_ausente_incompleto_ou_imagem"
            elif len(tokens) < MIN_EQUIVALENT_TOKENS:
                relation, reason = "INCONCLUSIVO", "texto_curto_ou_insuficiente"
            elif tokens == reference_tokens:
                relation, reason = "REPETE_PUBLICACAO", "texto_integral_normalizado_igual"
            elif len(reference_tokens) > MAX_COMPARE_TOKENS or len(tokens) > MAX_COMPARE_TOKENS:
                relation, reason = "INCONCLUSIVO", "texto_longo_sem_comparacao_segura"
            else:
                evidence = _candidate_overlap(reference_tokens, tokens)
                if _same_core(publication_list[0]["texto"], text, evidence):
                    relation, reason = "REPETE_PUBLICACAO", "nucleo_final_identico_com_cnj_compartilhado"
                elif evidence["longest_common_tokens"] >= 40:
                    relation, reason = "CANDIDATO_MESMO_ATO", "trecho_longo_em_comum_sem_equivalencia_integral"
                else:
                    relation, reason = "INCONCLUSIVO", "conteudo_nao_equivalente"
        documents.append({
            "indice": index,
            "nome": item.get("nome") or original.get("nome"),
            "sha256": item.get("sha256"),
            "relacao": relation,
            "motivo": reason,
            "evidencia": evidence,
        })

    reasons = []
    if not publication_list:
        reasons.append("sem_publicacao_dj_do")
    elif len(publication_list) > 1:
        reasons.append("multiplas_publicacoes_distintas")
    elif not publication_list[0]["texto_util"]:
        reasons.append("texto_publicacao_ausente_ou_curto")
    if other_movements:
        reasons.append("outros_andamentos_na_janela")
    if any(doc["relacao"] != "REPETE_PUBLICACAO" for doc in documents):
        reasons.append("documentos_sem_equivalencia_comprovada")

    automatic = not reasons
    if not publication_list:
        status = "SEM_PUBLICACAO"
    elif automatic and documents:
        status = "PUBLICACAO_COM_REPETICOES_COMPROVADAS"
    elif automatic:
        status = "PUBLICACAO_ISOLADA"
    else:
        status = "REVISAO_NECESSARIA"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "apto_para_etapa_publicacao": automatic,
        "publicacoes": publication_list,
        "documentos": documents,
        "outros_andamentos": other_movements,
        "motivos_revisao": reasons,
    }
