import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

// UI : couleurs/thème conservés (fond sombre, dégradés, boutons colorés)
export default function MeiliExplorer({ apiBase = "http://localhost:8001" }) {
  const [indexes, setIndexes] = useState([]);
  const [selectedUid, setSelectedUid] = useState("");
  const [filterable, setFilterable] = useState([]);
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState("");
  const [selectedFacets, setSelectedFacets] = useState({});
  const [facetDist, setFacetDist] = useState(null);
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // états manquants
  const [loadingIdx, setLoadingIdx] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [companyHint, setCompanyHint] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportJson, setExportJson] = useState("");
  const [exportError, setExportError] = useState("");
  const [fullView, setFullView] = useState(true);
  const [simpleMode, setSimpleMode] = useState(true);

  // Helper copier dans le presse-papiers
  const copyToClipboard = async (text) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return;
      }
      // fallback
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (e) {
      console.warn("Clipboard error", e);
    }
  };

  const exportAllForCompany = async () => {
    if (!companyHint) {
      setExportError("Veuillez saisir un company_id");
      return;
    }
    setExportError("");
    setExportJson("");
    setExporting(true);
    try {
      const res = await axios.get(`${apiBase}/meili/export-company`, {
        params: { company_id: companyHint, page_size: 1000 },
      });
      setExportJson(JSON.stringify(res.data, null, 2));
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur export";
      setExportError(msg);
    } finally {
      setExporting(false);
    }
  };

  const snippet = (val, max = 160) => {
    if (!val) return "";
    const s = String(val).replace(/\s+/g, " ").trim();
    return s.length > max ? s.slice(0, max - 1) + "…" : s;
  };

  const deleteSelected = async () => {
    if (!selectedUid) return;
    if (!window.confirm(`Supprimer l'index "${selectedUid}" ?`)) return;
    setError("");
    try {
      await axios.delete(`${apiBase}/meili/index/${encodeURIComponent(selectedUid)}`);
      // rafraîchir la liste et nettoyer la sélection si supprimée
      await fetchIndexes();
      setSelectedUid("");
      setStats(null);
      setDocs([]);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur suppression index";
      setError(msg);
    }
  };

  const deleteAll = async () => {
    if (!window.confirm("SUPPRIMER TOUS LES INDEX ? Action destructive.")) return;
    setError("");
    try {
      await axios.delete(`${apiBase}/meili/indexes`);
      await fetchIndexes();
      setSelectedUid("");
      setStats(null);
      setDocs([]);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur suppression de tous les indexes";
      setError(msg);
    }
  };

  useEffect(() => {
    fetchIndexes();
  }, []);

  const fetchIndexes = async () => {
    setLoadingIdx(true);
    setError("");
    try {
      const res = await axios.get(`${apiBase}/meili/indexes`);
      setIndexes(res.data.indexes || []);
    } catch (e) {
      setError("Erreur chargement des indexes");
    } finally {
      setLoadingIdx(false);
    }
  };

  useEffect(() => {
    if (!selectedUid) return;
    // reset pagination
    setOffset(0);
    setSelectedFacets({});
    setFacetDist(null);
    if (simpleMode) {
      // Mode simple: liste brute des documents
      setTimeout(() => { fetchDocs(selectedUid, { limit, offset: 0 }); }, 0);
    } else {
      // Mode avancé: stats, settings, recherche
      fetchStats(selectedUid);
      fetchSettings(selectedUid);
      setTimeout(() => { search(); }, 0);
    }
  }, [selectedUid, simpleMode]);

  // Charger les attributs filterables de l'index
  const fetchSettings = async (uid) => {
    try {
      const res = await axios.get(`${apiBase}/meili/index/${encodeURIComponent(uid)}/settings`);
      setFilterable(res.data.filterableAttributes || []);
    } catch (e) {
      setFilterable([]);
    }
  };

  const fetchStats = async (uid) => {
    try {
      const res = await axios.get(`${apiBase}/meili/index/${encodeURIComponent(uid)}/stats`);
      setStats(res.data.stats || null);
    } catch (e) {
      setStats(null);
    }
  };

  const fetchDocs = async (uid, { limit, offset }) => {
    setLoadingData(true);
    setError("");
    try {
      const res = await axios.get(`${apiBase}/meili/index/${encodeURIComponent(uid)}/documents`, {
        params: { limit, offset },
      });
      setDocs(res.data.hits || []);
      setTotal(null); // inconnu en liste brut
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur chargement documents";
      setError(msg);
    } finally {
      setLoadingData(false);
    }
  };

  const search = async () => {
    if (!selectedUid) return;
    setLoadingData(true);
    setError("");
    try {
      const body = {
        q: query,
        limit,
        offset,
        filter: filter || undefined,
        // backend acceptera string ou array et normalise si besoin
        sort: sort || undefined,
        facets: filterable || undefined,
      };
      const res = await axios.post(`${apiBase}/meili/index/${encodeURIComponent(selectedUid)}/search`, body, {
        headers: { 'Content-Type': 'application/json' }
      });
      setDocs(res.data.hits || []);
      setTotal(res.data.estimatedTotalHits ?? null);
      setFacetDist(res.data.facetDistribution || null);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur recherche";
      setError(msg);
    } finally {
      setLoadingData(false);
    }
  };

  const searchDelivery = async () => {
    if (!companyHint) {
      setError("Veuillez saisir un company_id (champ en haut à droite)");
      return;
    }
    setLoadingData(true);
    setError("");
    try {
      const body = {
        company_id: companyHint,
        q: query,
        limit,
        offset,
        filter: filter || undefined,
        sort: sort || undefined,
        facets: filterable || undefined,
      };
      const res = await axios.post(`${apiBase}/meili/delivery/search`, body, {
        headers: { 'Content-Type': 'application/json' }
      });
      setDocs(res.data.hits || []);
      setTotal(res.data.estimatedTotalHits ?? null);
      setFacetDist(res.data.facetDistribution || null);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Erreur recherche delivery";
      setError(msg);
    } finally {
      setLoadingData(false);
    }
  };

  const escapeValue = (v) => String(v).replace(/"/g, '\\"');
  const buildFilterFromSelection = (selObj) => {
    // OU intra-facette, ET inter-facettes: (f = "a" OR f = "b") AND (g = "x")
    const parts = Object.entries(selObj)
      .map(([facetName, setValues]) => {
        const values = Array.from(setValues || []);
        if (!values.length) return null;
        const orClause = values
          .map((val) => `${facetName} = \"${escapeValue(val)}\"`)
          .join(" OR ");
        return values.length > 1 ? `(${orClause})` : orClause;
      })
      .filter(Boolean);
    return parts.join(" AND ");
  };

  const toggleFacet = (facetName, value) => {
    setSelectedFacets((prev) => {
      const next = { ...prev };
      const currentSet = new Set(next[facetName] || []);
      if (currentSet.has(value)) currentSet.delete(value); else currentSet.add(value);
      if (currentSet.size === 0) delete next[facetName]; else next[facetName] = currentSet;
      // génère et applique le filtre
      const newFilter = buildFilterFromSelection(next);
      setFilter(newFilter);
      // reset pagination et relance recherche
      setOffset(0);
      setTimeout(search, 0);
      return next;
    });
  };

  const onRefresh = () => {
    if (!selectedUid) return;
    if (simpleMode) {
      fetchDocs(selectedUid, { limit, offset });
    } else {
      search();
    }
  };

  const canPrev = useMemo(() => offset > 0, [offset]);
  const canNext = useMemo(() => {
    if (total == null) return true; // en mode liste brut, on ne connait pas le total
    return offset + limit < total;
  }, [offset, limit, total]);

  const nextPage = () => {
    const newOffset = offset + limit;
    setOffset(newOffset);
    if (simpleMode) setTimeout(() => fetchDocs(selectedUid, { limit, offset: newOffset }), 0);
    else setTimeout(search, 0);
  };

  const prevPage = () => {
    const newOffset = Math.max(0, offset - limit);
    setOffset(newOffset);
    if (simpleMode) setTimeout(() => fetchDocs(selectedUid, { limit, offset: newOffset }), 0);
    else setTimeout(search, 0);
  };

  return (
    <div className="text-gray-100 min-h-[85vh] p-6 rounded-lg"
         style={{background: "linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%)"}}>
      <div className="flex items-center justify-between mb-6 sticky top-0 z-10 py-2"
           style={{backdropFilter: 'blur(16px)'}}>
        <h2 className="text-2xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">Meili Explorer</h2>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="px-3 py-2 rounded bg-gray-800 text-sm"
            placeholder="company_id (hint)"
            value={companyHint}
            onChange={(e) => setCompanyHint(e.target.value)}
            title="Utilisé pour les presets ci‑dessous"
          />
          <button onClick={() => setSelectedUid(companyHint ? `company_${companyHint}` : selectedUid)} className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600">company_*</button>
          <button onClick={() => setSelectedUid(companyHint ? `products_${companyHint}` : selectedUid)} className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600">products_*</button>
          <button onClick={() => setSelectedUid(companyHint ? `delivery_${companyHint}` : selectedUid)} className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600">delivery_*</button>
          <button onClick={() => setSelectedUid(companyHint ? `support_${companyHint}` : selectedUid)} className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600">support_*</button>
          <button onClick={() => setSelectedUid(companyHint ? `company_docs_${companyHint}` : selectedUid)} className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600">company_docs_*</button>

          <div className="w-px h-6 bg-gray-700 mx-1" />
          <label className="flex items-center gap-2 text-xs text-gray-300">
            <input type="checkbox" className="accent-green-500" checked={simpleMode} onChange={() => setSimpleMode(v => !v)} />
            Mode simple
          </label>
          <button
            onClick={fetchIndexes}
            className="px-3 py-2 rounded border border-white/20 bg-white/10 hover:bg-white/15 transition shadow-md"
            disabled={loadingIdx}
          >
            Rafraîchir
          </button>
          {!simpleMode && (
            <button
              onClick={exportAllForCompany}
              className="px-3 py-2 rounded bg-gradient-to-tr from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50 shadow-md"
              title="Exporter tous les documents pour ce company_id"
              disabled={!companyHint || exporting}
            >
              {exporting ? 'Export…' : 'Exporter tout (company_id)'}
            </button>
          )}
          <button
            onClick={deleteSelected}
            className="px-3 py-2 rounded bg-gradient-to-tr from-rose-500 to-red-500 hover:from-rose-400 hover:to-red-400 disabled:opacity-50 shadow-md"
            disabled={!selectedUid}
            title="Supprimer l'index sélectionné"
          >
            Supprimer sélection
          </button>
          <button
            onClick={deleteAll}
            className="px-3 py-2 rounded bg-gradient-to-tr from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 shadow-md"
            title="Supprimer tous les indexes"
          >
            Supprimer TOUS
          </button>
        </div>
      </div>

      {error && <div className="text-red-400 mb-3">{error}</div>}
      {exportError && <div className="text-red-400 mb-3">{exportError}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 max-w-[1400px] mx-auto">
        {/* Colonne gauche: liste indexes */}
        <div className="rounded-2xl p-5 border border-white/10 bg-white/10" style={{backdropFilter: 'blur(20px)'}}>
          <div className="text-sm text-gray-400 mb-2">Indexes</div>
          {loadingIdx ? (
            <div className="text-gray-400">Chargement…</div>
          ) : (
            <ul className="space-y-2">
              {indexes.map((it) => (
                <li key={it.uid} className="flex gap-2 items-stretch">
                  <button
                    onClick={() => setSelectedUid(it.uid)}
                    className={`w-full text-left px-3 py-2 rounded border transition ${selectedUid === it.uid ? 'bg-gradient-to-r from-indigo-500/30 to-purple-500/30 border-indigo-400/50' : 'bg-white/10 hover:bg-white/15 border-white/10'}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{it.uid}</span>
                      <div className="flex items-center gap-2">
                        {it.primaryKey && (
                          <div className="text-xs text-gray-400">PK: {it.primaryKey}</div>
                        )}
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`Supprimer l'index "${it.uid}" ?`)) return;
                      try {
                        await axios.delete(`${apiBase}/meili/index/${encodeURIComponent(it.uid)}`);
                        await fetchIndexes();
                        if (selectedUid === it.uid) {
                          setSelectedUid("");
                          setStats(null);
                          setDocs([]);
                        }
                      } catch (e) {
                        const msg = e?.response?.data?.detail || e?.message || "Erreur suppression index";
                        setError(msg);
                      }
                    }}
                    className="px-2 py-1 text-xs rounded bg-gradient-to-tr from-rose-500 to-red-500 hover:from-rose-400 hover:to-red-400"
                    title="Supprimer cet index"
                  >
                    ✖
                  </button>
                </li>
              ))}
              {indexes.length === 0 && (
                <div className="text-gray-400 text-sm">
                  Aucun index.
                </div>
              )}
            </ul>
          )}

          {/* Presets & Deletes */}
          <div className="mt-6 space-y-3">
            <input
              className="w-full px-3 py-2 rounded bg-white/10 border border-white/20 placeholder-white/60"
              placeholder="company_id (hint)"
              value={companyHint}
              onChange={(e) => setCompanyHint(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-2">
              {['company_','products_','delivery_','support_','company_docs_'].map(p => (
                <button key={p}
                        className="px-3 py-2 rounded border border-white/20 bg-white/10 hover:bg-white/15 text-sm"
                        onClick={() => companyHint && setSelectedUid(`${p}${companyHint}`)}>
                  {p}*
                </button>
              ))}
            </div>
            <div className="grid grid-cols-1 gap-2 pt-2">
              <button onClick={deleteSelected}
                      disabled={!selectedUid}
                      className="px-3 py-2 rounded bg-gradient-to-tr from-rose-500 to-red-500 hover:from-rose-400 hover:to-red-400 disabled:opacity-50">
                Supprimer sélection
              </button>
              <button onClick={deleteAll}
                      className="px-3 py-2 rounded bg-gradient-to-tr from-red-600 to-red-700 hover:from-red-500 hover:to-red-600">
                Supprimer TOUS
              </button>
            </div>
          </div>
        </div>

        {/* Colonne droite: recherche + stats + résultats */}

        {/* Affichage contextuel */}
      <section className="flex-1 flex flex-col gap-2 overflow-auto p-3">
        {error && <div className="text-red-400 mb-1 text-sm">{error}</div>}
        {/* Recherche rapide + stats (masquées en mode simple) */}
        {!simpleMode && (
        <div className="flex flex-wrap items-end gap-2 mb-2">
          <input
            className="px-2 py-1 rounded bg-[#1e2530] border border-[#2c3848] text-sm w-[180px]"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Recherche…"
            onKeyDown={e => { if (e.key === "Enter") search(); }}
          />
          <input
            type="number"
            className="px-2 py-1 rounded bg-[#1e2530] border border-[#2c3848] text-sm w-[70px]"
            value={limit}
            min={1}
            max={1000}
            onChange={e => setLimit(Number(e.target.value || 20))}
            title="Limit"
          />
          <button onClick={search} className="px-3 py-1 rounded bg-gradient-to-tr from-green-500 to-teal-500 hover:from-green-400 hover:to-teal-400 text-xs font-bold">Rechercher</button>
          {stats && (
            <span className="ml-2 text-xs text-gray-300">Docs: {stats.numberOfDocuments ?? "?"} | Indexing: {String(stats.isIndexing ?? false)}</span>
          )}
          <label className="ml-2 flex items-center gap-1 text-xs text-gray-300">
            <input type="checkbox" className="accent-green-500" checked={fullView} onChange={() => setFullView(v => !v)} />
            Affichage complet
          </label>
        </div>
        )}

        {/* Facettes dynamiques (masquées en mode simple) */}
        {!simpleMode && facetDist && filterable.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {filterable.map(facetName => {
              const items = Object.entries(facetDist?.[facetName] || {}).sort((a, b) => b[1] - a[1]);
              const selectedSet = new Set(selectedFacets[facetName] || []);
              return (
                <div key={facetName} className="bg-[#1d232c] border border-[#2c3848] rounded p-2 flex flex-col min-w-[130px] max-w-[180px]">
                  <div className="font-medium text-xs mb-1 text-green-300 truncate" title={facetName}>{facetName}</div>
                  <ul className="space-y-1 max-h-36 overflow-auto pr-1">
                    {items.map(([val, count]) => (
                      <li key={String(val)} className="flex items-center justify-between gap-2">
                        <label className="flex items-center gap-2 cursor-pointer text-xs">
                          <input
                            type="checkbox"
                            className="accent-green-500"
                            checked={selectedSet.has(val)}
                            onChange={() => toggleFacet(facetName, val)}
                          />
                          <span className="truncate max-w-[90px]" title={String(val)}>{String(val)}</span>
                        </label>
                        <span className="text-xs text-gray-400">{count}</span>
                      </li>
                    ))}
                    {items.length === 0 && (
                      <li className="text-xs text-gray-500">Aucune valeur</li>
                    )}
                  </ul>
                </div>
              );
            })}
            {filterable.length === 0 && (
              <div className="text-gray-400 text-xs px-2 py-3">Aucune facette disponible.</div>
            )}
            <button
              onClick={() => { setSelectedFacets({}); setOffset(0); setTimeout(search, 0); }}
              className="px-2 py-1 text-xs rounded border border-green-400 bg-green-900/20 hover:bg-green-800/40 self-end mt-2"
              disabled={Object.keys(selectedFacets).length === 0}
            >Réinitialiser filtres</button>
          </div>
        )}

        {/* Résultats paginés (compact) */}
        <div className="flex flex-col gap-1 bg-[#1d232c] border border-[#2c3848] rounded p-2 min-h-[180px]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-300">
              Offset {offset} • Limit {limit} {total != null && <>• Total {total}</>}
            </span>
            <span className="flex gap-1">
              <button onClick={prevPage} disabled={!canPrev || loading} className="px-2 py-1 rounded border border-green-400 bg-green-900/20 hover:bg-green-800/40 text-xs disabled:opacity-50">◀</button>
              <button onClick={nextPage} disabled={!canNext || loading} className="px-2 py-1 rounded border border-green-400 bg-green-900/20 hover:bg-green-800/40 text-xs disabled:opacity-50">▶</button>
            </span>
          </div>
          {loading ? (
            <div className="text-gray-400 text-xs">Chargement…</div>
          ) : docs.length > 0 ? (
            <table className="min-w-full text-xs">
              <thead className="bg-[#202832] text-green-200">
                <tr>
                  <th className="text-left px-2 py-1">ID</th>
                  <th className="text-left px-2 py-1">document_id</th>
                  <th className="text-left px-2 py-1">content</th>
                  <th className="text-left px-2 py-1">created_at</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d, i) => (
                  <tr key={d.id || i} className="border-b border-[#273040]">
                    <td className="px-2 py-1 font-mono break-all align-top">{String(d.id || `doc_${i}`)}</td>
                    <td className="px-2 py-1 font-mono break-all align-top">{String(d.document_id || d.file_name || "")}</td>
                    <td className="px-2 py-1 align-top">
                      <div className={fullView ? "text-gray-200 whitespace-pre-wrap break-words" : "text-gray-200 truncate max-w-[220px]"}>
                        {fullView ? String(d.content || "") : String(d.content || "").slice(0, 80)}
                      </div>
                      {d.level && <div className="text-xs text-gray-400 mt-1">level: {d.level}{typeof d.chunk_index !== 'undefined' ? ` • chunk ${d.chunk_index}` : ''}</div>}
                    </td>
                    <td className="px-2 py-1 align-top text-gray-300">{d.created_at ? String(d.created_at).slice(0, 24) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-4 text-gray-400 text-xs">
              <div className="text-2xl mb-1 opacity-60">📄</div>
              <div className="font-medium">Aucun résultat</div>
              <div className="text-xs">Lancez une recherche pour afficher les résultats</div>
            </div>
          )}
        </div>
      </section>
    </div>
  </div>
);
}
