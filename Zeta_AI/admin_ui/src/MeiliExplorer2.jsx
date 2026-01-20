import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8001";

function formatDate(dateStr) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString();
}

export default function MeiliExplorer2() {
  const [indexes, setIndexes] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [refreshFlag, setRefreshFlag] = useState(false);

  // Fetch indexes
  useEffect(() => {
    setLoading(true);
    axios
      .get(`${API_BASE}/meili/indexes`)
      .then((res) => {
        setIndexes(res.data.indexes || []);
        setLoading(false);
      })
      .catch((err) => {
        setError("Erreur chargement des indexes");
        setLoading(false);
      });
  }, [refreshFlag]);

  // Fetch documents of selected index
  useEffect(() => {
    if (!selectedIndex) return;
    setLoading(true);
    axios
      .get(`${API_BASE}/meili/index/${selectedIndex.uid}/documents`, {
        params: query ? { q: query } : {},
      })
      .then((res) => {
        setDocuments(res.data.documents || []);
        setLoading(false);
      })
      .catch((err) => {
        setError("Erreur chargement des documents");
        setLoading(false);
      });
  }, [selectedIndex, query, refreshFlag]);

  const handleDeleteDocs = async () => {
    if (!selectedDocs.length) return;
    if (!window.confirm("Supprimer les documents sélectionnés ?")) return;
    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/meili/index/${selectedIndex.uid}/documents`, {
        data: { ids: selectedDocs },
      });
      setRefreshFlag((f) => !f);
      setSelectedDocs([]);
    } catch (e) {
      setError("Erreur suppression documents");
    }
    setLoading(false);
  };

  const handleDeleteIndex = async () => {
    if (!window.confirm("Supprimer cet index ? (Action irréversible)")) return;
    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/meili/index/${selectedIndex.uid}`);
      setSelectedIndex(null);
      setRefreshFlag((f) => !f);
    } catch (e) {
      setError("Erreur suppression index");
    }
    setLoading(false);
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Meili Explorer 2.0</h2>
      {error && <div className="text-red-600 mb-2">{error}</div>}
      <div className="flex gap-8">
        {/* Liste des indexes */}
        <div className="w-1/3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">Indexes</span>
            <button
              className="bg-blue-500 text-white px-2 py-1 rounded"
              onClick={() => setRefreshFlag((f) => !f)}
            >
              Rafraîchir
            </button>
          </div>
          <ul className="border rounded divide-y">
            {indexes.length === 0 && <li className="p-2 text-gray-400">Aucun index</li>}
            {indexes.map((idx) => (
              <li
                key={idx.uid}
                className={`p-2 cursor-pointer hover:bg-blue-100 ${selectedIndex && idx.uid === selectedIndex.uid ? "bg-blue-200" : ""}`}
                onClick={() => setSelectedIndex(idx)}
              >
                <div className="font-mono text-sm">{idx.uid}</div>
                <div className="text-xs text-gray-500">{idx.primaryKey || "id"} | {idx.createdAt ? formatDate(idx.createdAt) : ""}</div>
              </li>
            ))}
          </ul>
        </div>
        {/* Documents de l'index sélectionné */}
        <div className="w-2/3">
          {selectedIndex ? (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold">Index : {selectedIndex.uid}</span>
                <button
                  className="bg-red-500 text-white px-2 py-1 rounded"
                  onClick={handleDeleteIndex}
                >
                  Supprimer l'index
                </button>
              </div>
              <div className="mb-2 flex gap-2">
                <input
                  type="text"
                  placeholder="Recherche..."
                  className="border px-2 py-1 rounded w-full"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button
                  className="bg-gray-200 px-2 py-1 rounded"
                  onClick={() => setQuery("")}
                >
                  Effacer
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full border text-sm">
                  <thead>
                    <tr>
                      <th>
                        <input
                          type="checkbox"
                          checked={selectedDocs.length === documents.length && documents.length > 0}
                          onChange={(e) =>
                            setSelectedDocs(
                              e.target.checked ? documents.map((doc) => doc.id) : []
                            )
                          }
                        />
                      </th>
                      <th>ID</th>
                      <th>Contenu</th>
                      <th>Company</th>
                      <th>Type</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc) => (
                      <tr key={doc.id} className="border-t">
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedDocs.includes(doc.id)}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedDocs([...selectedDocs, doc.id]);
                              else setSelectedDocs(selectedDocs.filter((id) => id !== doc.id));
                            }}
                          />
                        </td>
                        <td className="font-mono">{doc.id}</td>
                        <td>{doc.content?.slice(0, 60) || "-"}</td>
                        <td>{doc.company_id || "-"}</td>
                        <td>{doc.content_type || "-"}</td>
                        <td>{formatDate(doc.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  className="bg-red-500 text-white px-3 py-1 rounded disabled:opacity-50"
                  onClick={handleDeleteDocs}
                  disabled={selectedDocs.length === 0}
                >
                  Supprimer sélection
                </button>
                <button
                  className="bg-gray-200 px-3 py-1 rounded"
                  onClick={() => setRefreshFlag((f) => !f)}
                >
                  Rafraîchir
                </button>
              </div>
            </div>
          ) : (
            <div className="text-gray-500">Sélectionne un index pour afficher les documents</div>
          )}
        </div>
      </div>
      {loading && <div className="fixed bottom-4 right-4 bg-blue-100 px-4 py-2 rounded shadow">Chargement...</div>}
    </div>
  );
}
