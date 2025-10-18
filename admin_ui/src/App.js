import React, { useEffect, useState } from "react";
import axios from "axios";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";
import MeiliExplorer2 from "./MeiliExplorer2";
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const API = "http://localhost:8001";

function StatCard({ label, value, icon }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex items-center gap-4">
      <div className="text-3xl">{icon}</div>
      <div>
        <div className="text-gray-500 text-xs uppercase">{label}</div>
        <div className="text-2xl font-bold">{value}</div>
      </div>
    </div>
  );
}

function Dashboard() {
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [flushMsg, setFlushMsg] = useState("");

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const res = await axios.get(`${API}/metrics`);
      const lines = res.data.split("\n");
      const stats = {};
      lines.forEach((line) => {
        if (!line.startsWith("#") && line.includes(" ")) {
          const [k, v] = line.split(" ");
          stats[k] = Number(v);
        }
      });
      setMetrics(stats);
      setLoading(false);
    } catch (e) {
      setLoading(false);
    }
  };

  const flushCache = async () => {
    setFlushMsg("");
    try {
      await axios.post(`${API}/admin/cache/flush`);
      setFlushMsg("Cache vidé !");
      fetchMetrics();
    } catch {
      setFlushMsg("Erreur flush cache.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 p-6">
      <h1 className="text-3xl font-bold mb-6">CHATBOT2.0 Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard label="Requêtes RAG" value={metrics.rag_requests_total || 0} icon="📊" />
        <StatCard label="Cache hits" value={metrics.rag_cache_hits || 0} icon="⚡" />
        <StatCard label="Erreurs" value={metrics.rag_errors_total || 0} icon="❌" />
        <StatCard label="Réponses (s)" value={(metrics.rag_response_duration_seconds_sum || 0).toFixed(2)} icon="⏱️" />
      </div>
      <div className="flex flex-wrap gap-6 mb-8">
        <button onClick={flushCache} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Flush cache</button>
        {flushMsg && <span className="ml-4 text-green-500">{flushMsg}</span>}
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Métriques temps réel</h2>
        <Bar
          data={{
            labels: ["Requêtes", "Cache", "Erreurs"],
            datasets: [
              {
                label: "Compteur",
                data: [metrics.rag_requests_total || 0, metrics.rag_cache_hits || 0, metrics.rag_errors_total || 0],
                backgroundColor: ["#2563eb", "#f59e42", "#dc2626"],
              },
            ],
          }}
          options={{
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
          }}
        />
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Logs & Feedbacks récents</h2>
        <div className="text-gray-400 text-sm">(À venir : affichage live, export, analyse, etc.)</div>
      </div>
    </div>
  );
}

function App() {
  const [tab, setTab] = useState("dashboard");
  return (
    <div className="min-h-screen">
      <div className="bg-gray-900 text-gray-100 px-6 py-4 flex items-center justify-between">
        <div className="text-xl font-semibold">CHATBOT2.0 Admin</div>
        <div className="flex gap-2">
          <button
            onClick={() => setTab("dashboard")}
            className={`px-3 py-2 rounded ${tab === "dashboard" ? "bg-blue-600" : "bg-gray-700 hover:bg-gray-600"}`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setTab("meili")}
            className={`px-3 py-2 rounded ${tab === "meili" ? "bg-blue-600" : "bg-gray-700 hover:bg-gray-600"}`}
          >
            Meili Explorer
          </button>
        </div>
      </div>
      {tab === "dashboard" ? <Dashboard /> : <MeiliExplorer2 />}
    </div>
  );
}

export default App;
