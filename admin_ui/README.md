# CHATBOT2.0 - Interface d'administration et de monitoring

Cette interface React permet de tout piloter et monitorer sur votre backend FastAPI :

- Dashboard temps réel (stats, logs, cache, feedbacks)
- Gestion des prompts versionnés (CRUD, rollback, test A/B)
- Feedbacks utilisateurs (tableau, export, analyse)
- Monitoring Prometheus (graphiques, alertes)
- Chatbot playground (tester, scorer, logs, contexte)
- Ingestion de documents (upload, purge, statut)
- Paramètres avancés (flush cache, choix embedding, etc.)

## Lancement

```bash
cd admin_ui
npm install
npm start
```

L'interface sera accessible sur http://localhost:3000

## Prérequis
- Node.js >= 18
- Backend FastAPI lancé sur http://localhost:8000 (ou adapter l'URL dans le code)

## Roadmap UI
- [x] Dashboard (stats, actions rapides)
- [ ] Pages prompts, feedbacks, monitoring, chat, ingestion, settings
- [ ] Authentification admin (optionnel)

---

**Tout est pilotable via cette UI : impressionne-toi !**
