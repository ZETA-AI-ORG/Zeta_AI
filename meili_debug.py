import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import aiohttp
import meilisearch
from meilisearch.errors import MeilisearchApiError, MeilisearchError


class DebugLevel(Enum):
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"


@dataclass
class DiagnosticResult:
    test_name: str
    success: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None
    recommendations: Optional[List[str]] = None


def mask(s: Optional[str], keep: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "***" + s[-keep:]


class MeiliSearchDebugger:
    def __init__(
        self,
        meili_url: str,
        meili_key: Optional[str],
        company_id: str,
        fastapi_base: str = "http://127.0.0.1:8001",
    ):
        self.meili_url = meili_url.rstrip("/")
        self.meili_key = meili_key
        self.company_id = company_id
        self.index_name = f"products_{company_id}"
        self.fastapi_base = fastapi_base.rstrip("/")

        try:
            self.client = meilisearch.Client(self.meili_url, self.meili_key)
        except Exception as e:
            self.client = None
            logging.error(f"Failed to init Meilisearch client: {e}")

        self.logger = logging.getLogger(__name__)

    async def run_full_diagnostic(self, debug_level: DebugLevel = DebugLevel.DETAILED) -> Dict[str, DiagnosticResult]:
        print("🔍 DIAGNOSTIC MEILISEARCH - DÉBUT")
        print("=" * 70)
        print(f"URL: {self.meili_url}")
        print(f"API KEY: {mask(self.meili_key)}")
        print(f"Index attendu: {self.index_name}")
        print()

        diagnostics: Dict[str, DiagnosticResult] = {}

        diagnostics["connectivity"] = await self._test_connectivity()
        diagnostics["list_indexes"] = await self._list_indexes()
        diagnostics["index"] = await self._test_index_access()
        diagnostics["documents"] = await self._test_documents()
        diagnostics["search_queries"] = await self._test_search_queries()
        diagnostics["hyde_queries"] = await self._test_hyde_problematic_queries()
        diagnostics["fastapi_comparison"] = await self._test_fastapi_vs_direct()

        if debug_level in [DebugLevel.DETAILED, DebugLevel.VERBOSE]:
            diagnostics["config_analysis"] = await self._analyze_configuration()
        if debug_level == DebugLevel.VERBOSE:
            diagnostics["performance"] = await self._test_performance()

        self._print_diagnostic_summary(diagnostics)
        return diagnostics

    async def _test_connectivity(self) -> DiagnosticResult:
        print("🌐 Test de connectivité...")
        try:
            if not self.client:
                return DiagnosticResult(
                    test_name="Connectivité",
                    success=False,
                    details={},
                    error_message="Client Meilisearch non initialisé",
                    recommendations=["Vérifier MEILI_URL et MEILI_API_KEY"],
                )
            health = self.client.health()
            version = self.client.get_version()
            return DiagnosticResult(
                test_name="Connectivité",
                success=True,
                details={"health": health, "version": version, "url": self.meili_url},
                recommendations=["✅ Connectivité OK"],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Connectivité",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur de connexion: {e}",
                recommendations=[
                    "Vérifier que Meilisearch est démarré",
                    "Vérifier l'URL (port 7700)",
                    "Vérifier la clé API et les permissions",
                ],
            )

    async def _list_indexes(self) -> DiagnosticResult:
        print("📜 Liste des index...")
        try:
            indexes = self.client.get_indexes()
            # meilisearch 0.37 may return a dict with 'results' or a list of model objects
            arr = []
            if isinstance(indexes, dict) and "results" in indexes:
                arr = indexes["results"]
            elif isinstance(indexes, list):
                arr = indexes
            uids: List[str] = []
            for item in arr:
                if isinstance(item, dict):
                    uid = item.get("uid")
                else:
                    uid = getattr(item, "uid", None)
                if uid:
                    uids.append(uid)
            exists = self.index_name in uids
            recs = []
            if not exists:
                recs.append(
                    f"Index attendu '{self.index_name}' introuvable. Vérifier company_id et convention de nommage. UIDs trouvés: {uids[:10]}"
                )
            return DiagnosticResult(
                test_name="Indexes",
                success=True,
                details={"count": len(uids), "uids": uids, "expected_present": exists},
                recommendations=recs or ["✅ Index listé"],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Indexes",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur en listant les index: {e}",
            )

    async def _test_index_access(self) -> DiagnosticResult:
        print(f"📚 Test d'accès à l'index '{self.index_name}'...")
        try:
            index = self.client.index(self.index_name)
            try:
                stats = index.get_stats()
                settings = index.get_settings()
                # Compatible dict or model objects
                def sget(obj, name, default=None):
                    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
                return DiagnosticResult(
                    test_name="Index Access",
                    success=True,
                    details={
                        "index_name": self.index_name,
                        "document_count": sget(stats, "numberOfDocuments", 0),
                        "isIndexing": sget(stats, "isIndexing", False),
                        "searchable_attributes": sget(settings, "searchableAttributes", []),
                        "filterable_attributes": sget(settings, "filterableAttributes", []),
                        "sortable_attributes": sget(settings, "sortableAttributes", []),
                    },
                    recommendations=["✅ Index accessible"],
                )
            except MeilisearchApiError as me:
                code = getattr(me, "code", str(me))
                if code == "index_not_found":
                    payload = json.dumps({"uid": self.index_name})
                    cmd_create = (
                        f"curl -H 'Authorization: Bearer {self.meili_key}' "
                        f"-H 'Content-Type: application/json' "
                        f"-X POST '{self.meili_url}/indexes' -d '{payload}'"
                    )
                    cmd_list = (
                        f"curl -H 'Authorization: Bearer {self.meili_key}' "
                        f"'{self.meili_url}/indexes'"
                    )
                    return DiagnosticResult(
                        test_name="Index Access",
                        success=False,
                        details={"index_name": self.index_name},
                        error_message=f"Index '{self.index_name}' n'existe pas",
                        recommendations=[
                            cmd_create,
                            "Vérifier le company_id exact",
                            cmd_list,
                        ],
                    )
                raise
        except Exception as e:
            return DiagnosticResult(
                test_name="Index Access",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur d'accès à l'index: {e}",
                recommendations=["Vérifier permissions/clé sur l'index"],
            )

    async def _test_documents(self) -> DiagnosticResult:
        print("📄 Test des documents (échantillon)...")
        try:
            index = self.client.index(self.index_name)
            documents = index.get_documents({"limit": 5})
            results = (
                documents.get("results")
                if isinstance(documents, dict)
                else getattr(documents, "results", None)
            )
            if not results:
                return DiagnosticResult(
                    test_name="Documents",
                    success=False,
                    details={"document_count": 0},
                    error_message="Aucun document dans l'index",
                    recommendations=[
                        "Indexer des documents",
                        "Vérifier les logs d'indexation",
                    ],
                )
            sample_doc = results[0]
            doc_fields = list(sample_doc.keys()) if isinstance(sample_doc, dict) else []
            critical_fields = ["name", "product_name", "title", "description", "color"]
            available_text_fields = [
                f for f in doc_fields if any(cf in f.lower() for cf in critical_fields)
            ]
            return DiagnosticResult(
                test_name="Documents",
                success=True,
                details={
                    "document_count_sample": len(results),
                    "sample_document": sample_doc,
                    "available_fields": doc_fields,
                    "text_fields": available_text_fields,
                },
                recommendations=["✅ Documents présents"],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Documents",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur documents: {e}",
            )

    async def _test_search_queries(self) -> DiagnosticResult:
        print("🔎 Test des requêtes de recherche...")
        test_queries = [
            "casque",
            "moto",
            "rouge",
            "casque moto",
            "casque rouge",
            "moto rouge",
        ]
        try:
            index = self.client.index(self.index_name)
            results: Dict[str, Any] = {}
            for query in test_queries:
                try:
                    start = time.time()
                    sr = index.search(query, {"limit": 5})  # returns dict
                    elapsed_ms = int((time.time() - start) * 1000)
                    hits = sr.get("hits", [])
                    results[query] = {
                        "hit_count": len(hits),
                        "processing_time_ms": sr.get("processingTimeMs", elapsed_ms),
                        "hits_preview": hits[:2],
                    }
                except Exception as e:
                    results[query] = {"error": str(e)}
            successful = [q for q, r in results.items() if r.get("hit_count", 0) > 0 and "error" not in r]
            failed = [q for q, r in results.items() if ("error" in r) or r.get("hit_count", 0) == 0]
            return DiagnosticResult(
                test_name="Search Queries",
                success=len(successful) > 0,
                details={
                    "total_queries": len(test_queries),
                    "successful_queries": successful,
                    "failed_queries": failed,
                    "detailed_results": results,
                },
                recommendations=[
                    f"✅ {len(successful)}/{len(test_queries)} requêtes avec hits" if successful else "❌ 0 hit sur toutes les requêtes",
                    "Vérifier searchableAttributes (name, product_name, description, color)",
                ],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Search Queries",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur tests recherche: {e}",
            )

    async def _test_hyde_problematic_queries(self) -> DiagnosticResult:
        print("⚠️  Test des requêtes HyDE problématiques...")
        problematic_queries = [
            "casque moto",
            "moto rouge",
            "casque rouge",
        ]
        try:
            index = self.client.index(self.index_name)
            results: Dict[str, Any] = {}
            total_hits = 0
            for query in problematic_queries:
                try:
                    sr = index.search(query, {"limit": 5})
                    hits = sr.get("hits", [])
                    count = len(hits)
                    total_hits += count
                    results[query] = {"hit_count": count, "hits_preview": hits[:2]}
                    print(f"   🔍 '{query}' → {count} résultat(s)")
                except Exception as e:
                    results[query] = {"error": str(e)}
                    print(f"   ❌ '{query}' → Erreur: {e}")
            return DiagnosticResult(
                test_name="HyDE Problematic Queries",
                success=total_hits > 0,
                details={"queries_tested": problematic_queries, "results": results, "total_hits": total_hits},
                recommendations=[
                    "❌ 0 hit sur ces requêtes: vérifier index/data vs FastAPI" if total_hits == 0 else "⚠️ Hits partiels: comparer avec résultats FastAPI",
                ],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="HyDE Problematic Queries",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur: {e}",
            )

    async def _test_fastapi_vs_direct(self) -> DiagnosticResult:
        print("⚖️  Comparaison FastAPI vs Direct...")
        test_query = "casque moto rouge"
        try:
            index = self.client.index(self.index_name)
            direct = index.search(test_query, {"limit": 5})
            direct_hits = len(direct.get("hits", []))

            fastapi_result = await self._simulate_fastapi_call(test_query)
            return DiagnosticResult(
                test_name="FastAPI vs Direct",
                success=True,
                details={
                    "test_query": test_query,
                    "direct_hits": direct_hits,
                    "fastapi_result": fastapi_result,
                    "direct_response_preview": {k: direct.get(k) for k in ("estimatedTotalHits", "processingTimeMs")} ,
                },
                recommendations=[
                    f"Direct Meilisearch hits: {direct_hits}",
                    f"FastAPI status: {fastapi_result.get('status', 'unknown')} ({fastapi_result.get('status_code')})",
                    "Si divergents: vérifier URL/clé/index côté FastAPI",
                ],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="FastAPI vs Direct",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur comparaison: {e}",
            )

    async def _simulate_fastapi_call(self, query: str) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "company_id": self.company_id,
                    "user_id": "debugtest01",
                    "message": query,
                }
                url = f"{self.fastapi_base}/chat"
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    txt = await resp.text()
                    try:
                        data = json.loads(txt)
                    except Exception:
                        data = {"raw": txt}
                    return {"status": "success" if resp.status == 200 else "error", "status_code": resp.status, "body": data}
        except Exception as e:
            return {"status": "connection_error", "error": str(e)}

    async def _analyze_configuration(self) -> DiagnosticResult:
        print("⚙️  Analyse de configuration...")
        try:
            index = self.client.index(self.index_name)
            settings = index.get_settings()
            stats = index.get_stats()
            def sget(obj, name, default=None):
                return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
            searchable = sget(settings, "searchableAttributes", [])
            filterable = sget(settings, "filterableAttributes", [])
            sortable = sget(settings, "sortableAttributes", [])
            issues = []
            recs: List[str] = []
            if not searchable:
                issues.append("searchableAttributes non définis")
                recs.append("Définir name, product_name, description, color comme searchables")
            if (stats.get("numberOfDocuments") if isinstance(stats, dict) else getattr(stats, "numberOfDocuments", 0)) == 0:
                issues.append("Index vide")
                recs.append("Indexer des documents")
            return DiagnosticResult(
                test_name="Configuration Analysis",
                success=len(issues) == 0,
                details={
                    "settings": settings,
                    "stats": stats,
                    "searchable": searchable,
                    "filterable": filterable,
                    "sortable": sortable,
                    "issues": issues,
                },
                recommendations=recs or ["✅ Configuration OK"],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Configuration Analysis",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur d'analyse: {e}",
            )

    async def _test_performance(self) -> DiagnosticResult:
        print("🚀 Test de performance...")
        test_queries = ["casque", "moto rouge", "prix casque moto"]
        performance: Dict[str, Any] = {}
        try:
            index = self.client.index(self.index_name)
            for q in test_queries:
                times: List[float] = []
                last_hits = 0
                for _ in range(5):
                    start = time.time()
                    r = index.search(q, {"limit": 10})
                    last_hits = len(r.get("hits", []))
                    times.append((time.time() - start) * 1000)
                performance[q] = {
                    "average_time_ms": round(sum(times) / len(times), 2),
                    "times_ms": [round(t, 2) for t in times],
                    "hit_count": last_hits,
                }
            return DiagnosticResult(
                test_name="Performance",
                success=True,
                details={"results": performance},
                recommendations=[
                    f"Temps moyen global: {round(sum(v['average_time_ms'] for v in performance.values())/len(performance), 2)}ms",
                ],
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="Performance",
                success=False,
                details={"error": str(e)},
                error_message=f"Erreur performance: {e}",
            )

    def _print_diagnostic_summary(self, diagnostics: Dict[str, DiagnosticResult]):
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ DU DIAGNOSTIC")
        print("=" * 70)
        ok = sum(1 for d in diagnostics.values() if d.success)
        total = len(diagnostics)
        print(f"✅ Tests réussis: {ok}/{total}\n")
        for name, res in diagnostics.items():
            status = "✅" if res.success else "❌"
            print(f"{status} {res.test_name}")
            if res.error_message:
                print(f"   💥 {res.error_message}")
            if res.recommendations:
                for rec in res.recommendations:
                    print(f"   💡 {rec}")
            print()


class FastAPIConfigChecker:
    def check_environment_variables(self) -> Dict[str, Any]:
        critical = [
            "MEILI_URL",
            "MEILI_API_KEY",
        ]
        status: Dict[str, Any] = {}
        for var in critical:
            val = os.getenv(var)
            status[var] = {"value": mask(val), "is_set": val is not None}
        return status

    def generate_debug_curl_commands(self, company_id: str, base_url: str, api_key: Optional[str]) -> List[str]:
        idx = f"products_{company_id}"
        auth = f"-H 'Authorization: Bearer {api_key}' " if api_key else ""
        payload1 = json.dumps({"q": "casque", "limit": 5})
        payload2 = json.dumps({"q": "casque moto rouge", "limit": 5})
        cmds = [
            f"curl {auth}{base_url}/health",
            f"curl {auth}{base_url}/indexes",
            f"curl {auth}{base_url}/indexes/{idx}/stats",
            f"curl {auth}{base_url}/indexes/{idx}/settings",
            f"curl {auth}-X POST {base_url}/indexes/{idx}/search -H 'Content-Type: application/json' -d '{payload1}'",
            f"curl {auth}-X POST {base_url}/indexes/{idx}/search -H 'Content-Type: application/json' -d '{payload2}'",
        ]
        return cmds


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    print("🚀 DÉMARRAGE DU DIAGNOSTIC MEILISEARCH")
    print("=" * 70)

    meili_url = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
    meili_key = os.getenv("MEILI_API_KEY") or os.getenv("MEILISEARCH_API_KEY") or os.getenv("MEILISEARCH_KEY")
    company_id = os.getenv("DEBUG_COMPANY_ID", "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3")
    fastapi_base = os.getenv("FASTAPI_BASE", "http://127.0.0.1:8001")

    # Print env quick view
    print("🔧 Variables d'environnement critiques:")
    env_checker = FastAPIConfigChecker()
    env_status = env_checker.check_environment_variables()
    for var, st in env_status.items():
        symbol = "✅" if st["is_set"] else "❌"
        print(f"  {symbol} {var}: {st['value']}")
    print()

    debugger = MeiliSearchDebugger(meili_url, meili_key, company_id, fastapi_base)
    results = await debugger.run_full_diagnostic(DebugLevel.DETAILED)

    print("🛠️  COMMANDES CURL DE DEBUG:")
    print("-" * 40)
    for i, cmd in enumerate(env_checker.generate_debug_curl_commands(company_id, meili_url, meili_key), 1):
        print(f"{i}. {cmd}")

    print("\n" + "=" * 70)
    print("🎯 DIAGNOSTIC TERMINÉ")
    return results


if __name__ == "__main__":
    asyncio.run(main())
