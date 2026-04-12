Analyse du Projet CHATBOT2.0 et Plan pour une PWA Complète (mise à jour)
Date : 2026-04-09
Auteur : Roo (Architect)
Projet : CHATBOT2.0 – RAG LLM Multi-Entreprise

1. Vue d'ensemble du projet
Le projet CHATBOT2.0 est une plateforme multi‑entreprise qui combine:

une application frontend (PWA) en React/TypeScript,
une API backend (FastAPI Python),
une couche data Supabase (PostgreSQL + PGVector),
une recherche full‑text via Meilisearch,
et un pipeline RAG (HyDE + dual search + cache) pour des réponses contextualisées.
Le système est conçu pour une utilisation multi‑tenant avec isolation logique par company_id à travers les tables, les requêtes, les indexes et les comportements IA.

1.1 Architecture actuelle (mise à jour)
┌─────────────────────────────────────────────────────────────┐
│                    Frontend PWA (React)                     │
│  zeta-ai-vercel – Vite, TypeScript, Tailwind, shadcn-ui     │
│  + Service Worker (push + polling incoming signals)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ (REST)
┌──────────────────────────────▼──────────────────────────────┐
│                   Backend FastAPI (Python)                  │
│  API zeta (ingestion, chat, notifications, etc.)            │
└──────────────┬────────────────────────────────┬─────────────┘
               │                                │
    ┌──────────▼──────────┐         ┌──────────▼──────────┐
    │   Base de données   │         │   Moteur de recherche│
    │   • Supabase        │         │   • Meilisearch      │
    │   • PostgreSQL      │         │   • Indexes          │
    │   • PGVector        │         └──────────────────────┘
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Pipeline RAG      │
    │   • HyDE structuré  │
    │   • Dual search     │
    │   • Cache multi-niveaux│
    └─────────────────────┘
1.2 Composants principaux (mise à jour)
Composant	Technologie	Description
Backend API	FastAPI (Python)	Endpoints chat/RAG/ingestion/notifications/push.
Frontend PWA	React + TypeScript + Vite	App multi‑contextes (AI / Flow / Partner), SW pour push + polling.
Base de données	Supabase (PostgreSQL + PGVector)	Données multi-tenant, subscriptions, balances, documents, embeddings.
Recherche full‑text	Meilisearch	Recherche textuelle, indexes par company/type.
Pipeline RAG	HyDE + Dual Search	Recherche sémantique + textuelle et fusion.
Système IA	(Jessica / Amanda / Botlive selon contextes)	Différents “modes” IA visibles selon le plan d’adhésion.
Cache	Redis + mémoire (selon env)	Accélération + déduplication RAG.
Notifications	Web Push + Service Worker	Abonnement push, sons, polling /api/incoming-signals.
Adhésion / abonnement	Supabase + logique frontend	Plans starter/pro/elite, essai PRO 15 jours, downgrade auto.
2. Points forts existants (mise à jour)
Multi‑tenant pragmatique – company_id est la clé pivot de la majorité des flux.
Pipeline RAG avancé – HyDE + dual search, logique anti‑hallucination.
PWA déjà en place – SW + manifest + base offline.
Push notifications + polling – Le SW peut poller /api/incoming-signals même app fermée (selon config).
Socle “adhésion” en cours de consolidation – Plans canoniques alignés côté frontend.
3. Points d'amélioration identifiés (mise à jour réaliste)
3.1 UX / Produit
Parcours d’adhésion: refacto en cours (noms de plans, pricing, features, FAQ, CTA).
Cohérence plan → UI: à finaliser (ce qu’on voit sur dashboard selon Starter vs Pro).
Clarté des bots: clarifier “Amanda vs Jessica” et s’assurer que hors PRO, un seul bot est visible.
3.2 Backend / Intégration
Problème CORS bloquant en dev: appels frontend → api.zetaapp.xyz depuis localhost bloqués (absence Access-Control-Allow-Origin).
Risque de drift DB: certaines colonnes utilisées par le frontend (ex: champs d’essai PRO dans subscriptions) peuvent ne pas exister partout ⇒ Supabase 400 Bad Request possible lors d’upsert.
Monolithisme: app.py et/ou certaines zones backend restent volumineuses (découpage recommandé).
3.3 PWA “complète”
Offline riche encore incomplet: file d’attente d’actions, cache structuré IndexedDB, sync au retour réseau.
Background sync: partiel / non systématique (surtout sur commandes/messages/uploads).
4. État actuel du chantier “Adhésion / Subscription / Dashboard” (nouvelle section)
4.1 Ce qui est déjà fait (côté code frontend)
Plans canoniques: starter, pro, elite.
Compatibilité DB: starter est mappé vers plan_name = "gratuit" en base pour éviter les incohérences.
Fix crash UI: plan.features peut être undefined, sécurisé.
Localisation des cartes bots dashboard: rendu dans ZetaFlowDashboardSection.tsx + Dashboard.tsx.
4.2 Ce qui reste à finaliser
Essai PRO 15 jours one-shot:
stockage fiable en DB,
badge “PRO J‑X jours” sur le dashboard,
downgrade auto vers Starter + toast.
Elite: doit ouvrir un modal “coming soon” (pas d’activation réelle).
CORS: correction côté backend ou via stratégie dev/proxy.
Robustesse Supabase 400: prévoir fallback d’upsert si colonnes non migrées (ou imposer migration unique/staging).
5. Plan d'action pour une PWA complète (mis à jour et priorisé)
Phase 0 (immédiate) : Stabilisation production/dev (2-5 jours)
Résoudre CORS pour localhost + domaines Vercel:
Autoriser explicitement les origins nécessaires.
Stabiliser l’adhésion:
unifier définitivement les IDs plans côté frontend,
vérifier la compatibilité DB (migrations subscriptions + RLS).
Mettre en place un “safe upsert” (ou imposer migration):
éviter les 400 si une colonne manque (fallback minimal) OU
appliquer la migration partout (staging/prod).
Phase 1 : Consolidation et découpage (1-2 semaines)
Refactor backend en routeurs thématiques (chat/ingestion/admin/notifications).
Unifier le RAG engine (réduire duplication).
Normaliser la configuration (env vars + conventions par environnements).
Documentation + client TS (OpenAPI → client).
Phase 2 : Offline & Sync (2-3 semaines)
Stratégie caching (Workbox) + données critiques.
Background sync (messages, commandes, uploads).
IndexedDB: historique, panier, préférences.
Fallback offline intelligent.
Phase 3 : Installation & expérience native (1-2 semaines)
Manifest enrichi (splash, shortcuts).
Prompt d’installation contrôlé.
Intégrations device (badge/vibration/share).
i18n (si nécessaire).
Phase 4 : Performance & monitoring (1 semaine)
Lazy loading routes (React.lazy).
Optimisation images (WebP, lazy).
Core Web Vitals.
Feature flags / A-B test minimal.
Phase 5 : Offline avancé (2-3 semaines)
Commande 100% offline + sync.
Notifications enrichies.
Résolution de conflits.
Export/import.
6. Recommandations immédiates (mise à jour)
Priorité #1: CORS + stabilité adhésion
Tant que CORS et la compat DB ne sont pas réglés, les tests “subscription → dashboard” resteront fragiles.
Priorité #2: cohérence plan → UI
Starter = Amanda only (par ex), Pro = Amanda + Jessica + badge trial, Elite = coming soon.
Priorité #3: environnement de staging
Pour tester migrations/adhésion/PWA sans toucher prod.
7. Conclusion (mise à jour)
CHATBOT2.0 a une base technique solide (RAG + multi‑tenant + PWA + push). Le chantier actuel le plus critique n’est pas “ajouter des features PWA”, mais de stabiliser la couche d’intégration (CORS + migrations + adhésion) afin que l’expérience utilisateur soit cohérente et testable. Une fois ce socle stable, le plan PWA complet (offline, sync, installation) peut avancer sans dette cachée.

Prochaine étape : valider Phase 0 (CORS + DB/migrations + adhésion), puis reprendre Phase 1.

Statut de la mise à jour
Document mis à jour selon l’état réel du chantier (Subscription/Dashboard, CORS, Supabase 400, essai PRO).