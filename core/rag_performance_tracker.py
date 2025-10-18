#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⏱️ SYSTÈME DE TRACKING PERFORMANCE RAG
Mesure temps d'exécution et tokens réels de chaque étape
✅ OPTIMISATION: Mode production avec tracking minimal
"""

import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# ✅ OPTIMISATION: Désactiver tracking détaillé en production
ENABLE_DETAILED_TRACKING = os.getenv("ENABLE_DETAILED_TRACKING", "false").lower() == "true"


@dataclass
class StepTiming:
    """Timing d'une étape du RAG"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self):
        """Termine le timing"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class LLMUsage:
    """Usage tokens et coût LLM"""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float


class RAGPerformanceTracker:
    """
    Tracker de performance pour pipeline RAG complet
    Mesure chaque étape et calcule coûts réels
    """
    
    # Coûts par modèle ($/1M tokens)
    MODEL_COSTS = {
        "llama-3.3-70b-versatile": {
            "input": 0.59,
            "output": 0.79
        },
        "llama-3.1-8b-instant": {
            "input": 0.05,
            "output": 0.08
        },
        "openai/gpt-oss-120b": {
            "input": 0.50,
            "output": 0.70
        }
    }
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.steps: List[StepTiming] = []
        self.current_step: Optional[StepTiming] = None
        self.llm_usage: Optional[LLMUsage] = None
        self.total_duration_ms: Optional[float] = None
    
    def start_step(self, name: str, **metadata):
        """Démarre une nouvelle étape"""
        # ✅ OPTIMISATION: Skip si tracking désactivé
        if not ENABLE_DETAILED_TRACKING:
            return
            
        # Finir l'étape précédente si existe
        if self.current_step and self.current_step.end_time is None:
            self.current_step.finish()
        
        # Créer nouvelle étape
        self.current_step = StepTiming(
            name=name,
            start_time=time.time(),
            metadata=metadata
        )
        self.steps.append(self.current_step)
        
        logger.debug(f"⏱️ [{self.request_id}] Début: {name}")
    
    def end_step(self, **metadata):
        """Termine l'étape courante"""
        # ✅ OPTIMISATION: Skip si tracking désactivé
        if not ENABLE_DETAILED_TRACKING:
            return
            
        if self.current_step:
            self.current_step.metadata.update(metadata)
            self.current_step.finish()
            logger.debug(
                f"⏱️ [{self.request_id}] Fin: {self.current_step.name} "
                f"({self.current_step.duration_ms:.2f}ms)"
            )
            self.current_step = None
    
    def record_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        """Enregistre l'usage LLM avec calcul de coût"""
        total_tokens = prompt_tokens + completion_tokens
        
        # Récupérer les coûts du modèle
        costs = self.MODEL_COSTS.get(model, {"input": 0, "output": 0})
        
        # Calculer coûts ($/1M tokens)
        prompt_cost = (prompt_tokens / 1_000_000) * costs["input"]
        completion_cost = (completion_tokens / 1_000_000) * costs["output"]
        total_cost = prompt_cost + completion_cost
        
        self.llm_usage = LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost
        )
        
        logger.info(
            f"💰 [{self.request_id}] LLM: {model} | "
            f"{prompt_tokens}+{completion_tokens}={total_tokens} tokens | "
            f"${total_cost:.6f}"
        )
    
    def finish(self):
        """Termine le tracking complet"""
        # Finir l'étape courante si existe
        if self.current_step and self.current_step.end_time is None:
            self.current_step.finish()
        
        # Calculer durée totale
        self.total_duration_ms = (time.time() - self.start_time) * 1000
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé complet"""
        return {
            "request_id": self.request_id,
            "total_duration_ms": round(self.total_duration_ms, 2) if self.total_duration_ms else None,
            "steps": [
                {
                    "name": step.name,
                    "duration_ms": round(step.duration_ms, 2) if step.duration_ms else None,
                    "metadata": step.metadata
                }
                for step in self.steps
            ],
            "llm_usage": {
                "model": self.llm_usage.model,
                "prompt_tokens": self.llm_usage.prompt_tokens,
                "completion_tokens": self.llm_usage.completion_tokens,
                "total_tokens": self.llm_usage.total_tokens,
                "prompt_cost_usd": round(self.llm_usage.prompt_cost, 6),
                "completion_cost_usd": round(self.llm_usage.completion_cost, 6),
                "total_cost_usd": round(self.llm_usage.total_cost, 6)
            } if self.llm_usage else None
        }
    
    def print_summary_red(self):
        """Affiche le résumé en ROUGE dans les logs"""
        # ✅ OPTIMISATION: Skip si tracking désactivé
        if not ENABLE_DETAILED_TRACKING:
            return
            
        RED = '\033[91m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
        
        summary = self.get_summary()
        
        print(f"\n{RED}{BOLD}{'='*80}{RESET}")
        print(f"{RED}{BOLD}⏱️  PERFORMANCE TRACKING - {self.request_id}{RESET}")
        print(f"{RED}{BOLD}{'='*80}{RESET}")
        
        # Durée totale
        if summary['total_duration_ms']:
            print(f"{RED}🕐 DURÉE TOTALE: {summary['total_duration_ms']:.2f}ms ({summary['total_duration_ms']/1000:.2f}s){RESET}")
        
        # Étapes
        print(f"\n{RED}{BOLD}📊 ÉTAPES DU PIPELINE:{RESET}")
        for step in summary['steps']:
            duration = step['duration_ms'] if step['duration_ms'] else 'N/A'
            metadata_str = ""
            if step['metadata']:
                metadata_str = f" | {step['metadata']}"
            print(f"{RED}  ├─ {step['name']}: {duration}ms{metadata_str}{RESET}")
        
        # LLM Usage
        if summary['llm_usage']:
            llm = summary['llm_usage']
            print(f"\n{RED}{BOLD}🤖 USAGE LLM:{RESET}")
            print(f"{RED}  ├─ Modèle: {llm['model']}{RESET}")
            print(f"{RED}  ├─ Tokens prompt: {llm['prompt_tokens']:,}{RESET}")
            print(f"{RED}  ├─ Tokens completion: {llm['completion_tokens']:,}{RESET}")
            print(f"{RED}  ├─ Tokens total: {llm['total_tokens']:,}{RESET}")
            print(f"{RED}  ├─ Coût prompt: ${llm['prompt_cost_usd']:.6f}{RESET}")
            print(f"{RED}  ├─ Coût completion: ${llm['completion_cost_usd']:.6f}{RESET}")
            print(f"{RED}  └─ COÛT TOTAL: ${llm['total_cost_usd']:.6f}{RESET}")
        
        # Analyse performance
        print(f"\n{RED}{BOLD}📈 ANALYSE:{RESET}")
        if summary['steps']:
            slowest = max(summary['steps'], key=lambda x: x['duration_ms'] or 0)
            print(f"{RED}  ├─ Étape la plus lente: {slowest['name']} ({slowest['duration_ms']:.2f}ms){RESET}")
            
            total_steps_time = sum(s['duration_ms'] or 0 for s in summary['steps'])
            overhead = (summary['total_duration_ms'] or 0) - total_steps_time
            if overhead > 0:
                print(f"{RED}  └─ Overhead système: {overhead:.2f}ms{RESET}")
        
        print(f"{RED}{BOLD}{'='*80}{RESET}\n")


# ============================================================================
# SINGLETON GLOBAL PAR REQUÊTE
# ============================================================================

_trackers: Dict[str, RAGPerformanceTracker] = {}


def get_tracker(request_id: str) -> RAGPerformanceTracker:
    """Récupère ou crée un tracker pour une requête"""
    if request_id not in _trackers:
        _trackers[request_id] = RAGPerformanceTracker(request_id)
    return _trackers[request_id]


def cleanup_tracker(request_id: str):
    """Nettoie un tracker après utilisation"""
    if request_id in _trackers:
        del _trackers[request_id]


def get_all_trackers() -> Dict[str, RAGPerformanceTracker]:
    """Retourne tous les trackers actifs"""
    return _trackers.copy()
