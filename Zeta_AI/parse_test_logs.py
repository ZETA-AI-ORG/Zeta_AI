#!/usr/bin/env python3
"""
📊 PARSER LOGS BOTLIVE - Extrait métriques des logs serveur
Analyse les logs pour récupérer les vraies métriques (tokens, coûts, timings)
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any

def parse_log_section(log_text: str) -> Dict[str, Any]:
    """
    Parse une section de log formatée pour extraire toutes les métriques
    
    Format attendu:
    🔵 QUESTION CLIENT:
    ...
    🟡 RAISONNEMENT LLM:
    ...
    🟢 RÉPONSE AU CLIENT:
    ...
    🔴 TOKENS RÉELS & COÛTS:
    ...
    ⏱️ TEMPS D'EXÉCUTION:
    ...
    """
    
    metrics = {
        'question': '',
        'thinking': '',
        'response': '',
        'model': 'inconnu',
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0,
        'llm_cost': 0.0,
        'router_cost': 0.0,
        'total_cost': 0.0,
        'router_tokens': 0,
        'timings': {},
        'total_time_ms': 0.0
    }
    
    # Extraire question
    question_match = re.search(r'🔵 QUESTION CLIENT:\s*\n(.+?)(?=\n\n|🟡|🟢)', log_text, re.DOTALL)
    if question_match:
        metrics['question'] = question_match.group(1).strip()
    
    # Extraire thinking (optionnel)
    thinking_match = re.search(r'🟡 RAISONNEMENT LLM:\s*\n(.+?)(?=\n\n|🟢|🔴)', log_text, re.DOTALL)
    if thinking_match:
        metrics['thinking'] = thinking_match.group(1).strip()
    else:
        # Pas de thinking, c'est normal
        metrics['thinking'] = ''
    
    # Extraire réponse
    response_match = re.search(r'🟢 RÉPONSE AU CLIENT:\s*\n(.+?)(?=\n\n|🔴|⏱️)', log_text, re.DOTALL)
    if response_match:
        metrics['response'] = response_match.group(1).strip()
    
    # Extraire modèle
    model_match = re.search(r'🤖 MODÈLE:\s*(\S+)', log_text)
    if model_match:
        metrics['model'] = model_match.group(1)
    
    # Extraire tokens
    tokens_match = re.search(r'Prompt:\s*(\d+)\s*\|\s*Completion:\s*(\d+)\s*\|\s*TOTAL:\s*(\d+)', log_text)
    if tokens_match:
        metrics['prompt_tokens'] = int(tokens_match.group(1))
        metrics['completion_tokens'] = int(tokens_match.group(2))
        metrics['total_tokens'] = int(tokens_match.group(3))
    
    # Extraire coût LLM
    llm_cost_match = re.search(r'💰 COÛT LLM:\s*\$([0-9.]+)', log_text)
    if llm_cost_match:
        metrics['llm_cost'] = float(llm_cost_match.group(1))
    
    # Extraire coût routeur HYDE
    router_cost_match = re.search(r'💰 COÛT ROUTEUR HYDE.*?:\s*\$([0-9.]+)\s*\((\d+)\s*tokens\)', log_text)
    if router_cost_match:
        metrics['router_cost'] = float(router_cost_match.group(1))
        metrics['router_tokens'] = int(router_cost_match.group(2))
    
    # Extraire coût total
    total_cost_match = re.search(r'💰 COÛT TOTAL:\s*\$([0-9.]+)', log_text)
    if total_cost_match:
        metrics['total_cost'] = float(total_cost_match.group(1))
    
    # Extraire timings détaillés
    routing_time_match = re.search(r'1\. Routage.*?:\s*([0-9.]+)ms', log_text)
    if routing_time_match:
        metrics['timings']['routing'] = float(routing_time_match.group(1))
    
    prompt_gen_match = re.search(r'2\. Génération prompt:\s*([0-9.]+)ms', log_text)
    if prompt_gen_match:
        metrics['timings']['prompt_generation'] = float(prompt_gen_match.group(1))
    
    llm_call_match = re.search(r'3\. Appel LLM.*?:\s*([0-9.]+)ms', log_text)
    if llm_call_match:
        metrics['timings']['llm_call'] = float(llm_call_match.group(1))
    
    tools_match = re.search(r'4\. Exécution outils:\s*([0-9.]+)ms', log_text)
    if tools_match:
        metrics['timings']['tools_execution'] = float(tools_match.group(1))
    
    # Temps total
    total_time_match = re.search(r'⏱️\s*TEMPS TOTAL REQUÊTE:\s*([0-9.]+)ms', log_text)
    if total_time_match:
        metrics['total_time_ms'] = float(total_time_match.group(1))
    
    return metrics

def parse_log_file(log_file_path: str) -> List[Dict[str, Any]]:
    """Parse un fichier de logs complet"""
    
    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        log_content = f.read()
    
    # Découper par sections (délimitées par ==== OU par 🔵)
    # Méthode 1: par ====
    sections = re.split(r'={80,}', log_content)
    
    all_metrics = []
    for section in sections:
        if '🔵 QUESTION CLIENT' in section or '🔵 QUESTION CLIENT' in section:
            metrics = parse_log_section(section)
            # Accepter même sans question si on a une réponse
            if metrics['question'] or metrics['response']:
                all_metrics.append(metrics)
    
    # Si rien trouvé, essayer découpage alternatif
    if not all_metrics:
        # Découper sur chaque occurrence de 🔵
        alt_sections = re.split(r'(?=🔵 QUESTION CLIENT)', log_content)
        for section in alt_sections:
            if '🔵' in section:
                metrics = parse_log_section(section)
                if metrics['question'] or metrics['response']:
                    all_metrics.append(metrics)
    
    return all_metrics

def generate_report(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Génère un rapport d'analyse complet"""
    
    if not metrics_list:
        return {'error': 'Aucune métrique trouvée'}
    
    total_requests = len(metrics_list)
    total_tokens = sum(m['total_tokens'] for m in metrics_list)
    total_cost = sum(m['total_cost'] for m in metrics_list)
    avg_time = sum(m['total_time_ms'] for m in metrics_list) / total_requests
    
    # Stats par modèle
    models = {}
    for m in metrics_list:
        model = m['model']
        if model not in models:
            models[model] = {'count': 0, 'tokens': 0, 'cost': 0.0}
        models[model]['count'] += 1
        models[model]['tokens'] += m['total_tokens']
        models[model]['cost'] += m['llm_cost']
    
    # Stats timings
    avg_timings = {}
    for m in metrics_list:
        for key, value in m['timings'].items():
            if key not in avg_timings:
                avg_timings[key] = []
            avg_timings[key].append(value)
    
    avg_timings = {k: sum(v)/len(v) for k, v in avg_timings.items()}
    
    return {
        'summary': {
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'total_cost_fcfa': total_cost * 600,
            'avg_time_ms': avg_time,
            'avg_cost_per_request': total_cost / total_requests if total_requests > 0 else 0
        },
        'models': models,
        'avg_timings': avg_timings,
        'details': metrics_list
    }

def main():
    """Point d'entrée principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parse_test_logs.py <log_file.txt>")
        print("\nExemple:")
        print("  python parse_test_logs.py test_logs.txt")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    print(f"📊 Parsing logs: {log_file}")
    metrics_list = parse_log_file(log_file)
    
    if not metrics_list:
        print("❌ Aucune métrique trouvée dans les logs")
        sys.exit(1)
    
    print(f"✅ {len(metrics_list)} requêtes analysées")
    
    # Générer rapport
    report = generate_report(metrics_list)
    
    # Sauvegarder JSON
    output_file = log_file.replace('.txt', '_analysis.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Rapport sauvegardé: {output_file}")
    
    # Afficher résumé
    print("\n" + "="*80)
    print("📈 RÉSUMÉ ANALYSE")
    print("="*80)
    
    summary = report['summary']
    print(f"\n📊 STATISTIQUES GLOBALES:")
    print(f"   Total requêtes: {summary['total_requests']}")
    print(f"   Total tokens: {summary['total_tokens']:,}")
    print(f"   Coût total: ${summary['total_cost_usd']:.6f} ({summary['total_cost_fcfa']:.2f} FCFA)")
    print(f"   Temps moyen: {summary['avg_time_ms']:.2f}ms")
    print(f"   Coût moyen/req: ${summary['avg_cost_per_request']:.6f}")
    
    print(f"\n🤖 PAR MODÈLE:")
    for model, stats in report['models'].items():
        print(f"   {model}:")
        print(f"      Requêtes: {stats['count']}")
        print(f"      Tokens: {stats['tokens']:,}")
        print(f"      Coût: ${stats['cost']:.6f}")
    
    print(f"\n⏱️  TEMPS MOYENS:")
    for step, time_ms in report['avg_timings'].items():
        print(f"   {step}: {time_ms:.2f}ms")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
