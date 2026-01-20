#!/usr/bin/env python3
"""
📊 ANALYSEUR LOGS JSON - Génère rapports à partir des logs JSON
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

def load_jsonl(file_path: str) -> List[Dict]:
    """Charge un fichier JSONL"""
    requests = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    requests.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Ligne invalide ignorée: {e}")
    return requests

def analyze_requests(requests: List[Dict]) -> Dict[str, Any]:
    """Analyse les requêtes et génère des statistiques"""
    
    if not requests:
        return {'error': 'Aucune requête trouvée'}
    
    total = len(requests)
    
    # Agrégations
    total_tokens = sum(r['metrics']['total_tokens'] for r in requests)
    total_cost = sum(r['metrics']['total_cost'] for r in requests)
    total_llm_cost = sum(r['metrics']['llm_cost'] for r in requests)
    total_router_cost = sum(r['metrics']['router_cost'] for r in requests)
    
    # Temps
    times = [r['timings']['total'] for r in requests]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    # Par modèle
    models = defaultdict(lambda: {'count': 0, 'tokens': 0, 'cost': 0.0, 'time': 0.0})
    for r in requests:
        model = r['model']
        models[model]['count'] += 1
        models[model]['tokens'] += r['metrics']['total_tokens']
        models[model]['cost'] += r['metrics']['llm_cost']
        models[model]['time'] += r['timings']['total']
    
    # Moyennes par modèle
    for model, stats in models.items():
        stats['avg_tokens'] = stats['tokens'] / stats['count']
        stats['avg_cost'] = stats['cost'] / stats['count']
        stats['avg_time'] = stats['time'] / stats['count']
    
    # Par user
    users = defaultdict(int)
    for r in requests:
        users[r['user_id']] += 1
    
    # Timings moyens
    avg_routing = sum(r['timings']['routing'] for r in requests) / total
    avg_prompt_gen = sum(r['timings']['prompt_generation'] for r in requests) / total
    avg_llm_call = sum(r['timings']['llm_call'] for r in requests) / total
    avg_tools = sum(r['timings']['tools_execution'] for r in requests) / total
    
    return {
        'summary': {
            'total_requests': total,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 6),
            'total_cost_fcfa': round(total_cost * 600, 2),
            'total_llm_cost': round(total_llm_cost, 6),
            'total_router_cost': round(total_router_cost, 6),
            'avg_tokens': round(total_tokens / total, 2),
            'avg_cost': round(total_cost / total, 6),
            'avg_time_ms': round(avg_time, 2),
            'min_time_ms': round(min_time, 2),
            'max_time_ms': round(max_time, 2)
        },
        'by_model': dict(models),
        'by_user': dict(users),
        'avg_timings': {
            'routing': round(avg_routing, 2),
            'prompt_generation': round(avg_prompt_gen, 2),
            'llm_call': round(avg_llm_call, 2),
            'tools_execution': round(avg_tools, 2)
        },
        'requests': requests
    }

def print_report(analysis: Dict, show_details: bool = True):
    """Affiche le rapport formaté"""
    
    if 'error' in analysis:
        print(f"❌ {analysis['error']}")
        return
    
    summary = analysis['summary']
    
    print("\n" + "="*80)
    print("📊 RAPPORT D'ANALYSE LOGS JSON")
    print("="*80)
    
    print(f"\n📈 STATISTIQUES GLOBALES:")
    print(f"   Total requêtes: {summary['total_requests']}")
    print(f"   Total tokens: {summary['total_tokens']:,}")
    print(f"   Tokens moyens: {summary['avg_tokens']}")
    print(f"   Coût total: ${summary['total_cost_usd']} ({summary['total_cost_fcfa']} FCFA)")
    print(f"   Coût moyen/req: ${summary['avg_cost']}")
    print(f"   Coût LLM: ${summary['total_llm_cost']}")
    print(f"   Coût Routeur: ${summary['total_router_cost']}")
    
    print(f"\n⏱️  TEMPS D'EXÉCUTION:")
    print(f"   Temps moyen: {summary['avg_time_ms']:.2f}ms")
    print(f"   Temps min: {summary['min_time_ms']:.2f}ms")
    print(f"   Temps max: {summary['max_time_ms']:.2f}ms")
    
    print(f"\n🤖 STATISTIQUES PAR MODÈLE:")
    for model, stats in analysis['by_model'].items():
        print(f"\n   {model}:")
        print(f"      Requêtes: {stats['count']} ({stats['count']/summary['total_requests']*100:.1f}%)")
        print(f"      Tokens: {stats['tokens']:,} (avg: {stats['avg_tokens']:.0f})")
        print(f"      Coût: ${stats['cost']:.6f} (avg: ${stats['avg_cost']:.6f})")
        print(f"      Temps: {stats['time']:.0f}ms (avg: {stats['avg_time']:.0f}ms)")
    
    print(f"\n⏱️  TEMPS MOYENS PAR ÉTAPE:")
    timings = analysis['avg_timings']
    print(f"   Routage HYDE: {timings['routing']:.2f}ms")
    print(f"   Génération prompt: {timings['prompt_generation']:.2f}ms")
    print(f"   Appel LLM: {timings['llm_call']:.2f}ms")
    print(f"   Exécution outils: {timings['tools_execution']:.2f}ms")
    
    print(f"\n👥 UTILISATEURS ({len(analysis['by_user'])} uniques):")
    for user, count in sorted(analysis['by_user'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {user}: {count} requêtes")
    
    print("\n" + "="*80)
    
    # AFFICHAGE DÉTAILLÉ DES CONVERSATIONS
    if show_details:
        print("\n" + "="*80)
        print("💬 DÉTAIL DES CONVERSATIONS")
        print("="*80)
        
        for i, req in enumerate(analysis['requests'], 1):
            print(f"\n{'─'*80}")
            print(f"📍 REQUÊTE #{i} | {req['timestamp']}")
            print(f"👤 User: {req['user_id']}")
            print(f"{'─'*80}")
            
            # Question
            print(f"\n🔵 QUESTION:")
            print(f"   {req['question']}")
            
            # Thinking (si présent)
            if req.get('thinking'):
                print(f"\n🟡 RAISONNEMENT:")
                for line in req['thinking'].split('\n'):
                    print(f"   {line}")
            
            # Réponse
            print(f"\n🟢 RÉPONSE:")
            print(f"   {req['response']}")
            
            # Métriques
            metrics = req['metrics']
            timings = req['timings']
            
            print(f"\n📊 MÉTRIQUES:")
            print(f"   🤖 Modèle: {req['model']}")
            print(f"   📝 Tokens: {metrics['prompt_tokens']} → {metrics['completion_tokens']} (total: {metrics['total_tokens']})")
            print(f"   💰 Coût: ${metrics['total_cost']:.6f} (LLM: ${metrics['llm_cost']:.6f} + Router: ${metrics['router_cost']:.6f})")
            print(f"   ⏱️  Temps: {timings['total']:.0f}ms (Routing: {timings['routing']:.0f}ms, LLM: {timings['llm_call']:.0f}ms)")
            
            if req.get('routing_reason'):
                print(f"\n🎯 Routage: {req['routing_reason'][:100]}...")
        
        print("\n" + "="*80)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_json_logs.py <json_log_file.jsonl> [--no-details]")
        print("\nExemples:")
        print("  python analyze_json_logs.py logs/requests_metrics_20251010.jsonl")
        print("  python analyze_json_logs.py logs/requests_metrics_20251010.jsonl --no-details")
        sys.exit(1)
    
    log_file = sys.argv[1]
    show_details = '--no-details' not in sys.argv
    
    if not Path(log_file).exists():
        print(f"❌ Fichier introuvable: {log_file}")
        sys.exit(1)
    
    print(f"📊 Chargement: {log_file}")
    requests = load_jsonl(log_file)
    
    if not requests:
        print("❌ Aucune requête trouvée dans le fichier")
        sys.exit(1)
    
    print(f"✅ {len(requests)} requêtes chargées")
    
    # Analyser
    analysis = analyze_requests(requests)
    
    # Afficher rapport
    print_report(analysis, show_details=show_details)
    
    # Sauvegarder rapport complet
    output_file = log_file.replace('.jsonl', '_report.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport complet sauvegardé: {output_file}")

if __name__ == "__main__":
    main()
