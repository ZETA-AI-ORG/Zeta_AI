# WA Bridge - Incident, corrections et stabilisation production

## Objectif

Ce document résume :
- les problèmes rencontrés sur le WhatsApp Bridge
- les causes racines identifiées
- les corrections appliquées
- le fonctionnement cible désormais en production
- les vérifications à faire en cas de nouvel incident

## Contexte

Le WhatsApp Bridge sert d'interface entre WhatsApp Web, le backend Zeta AI, N8N et l'interface opérateur. Pendant l'incident, plusieurs symptômes ont empêché la réception correcte des messages et la remontée fiable des événements vers l'application.

Les problèmes n'étaient pas isolés. Ils se cumulaient :
- le bridge n'était pas correctement exposé derrière Nginx
- certaines routes `/wa-bridge` répondaient en `404`
- Chromium ne pouvait plus démarrer à cause d'un verrouillage de profil de session
- le webhook N8N n'était pas explicitement fiabilisé dans la configuration du bridge
- le frontend appelait parfois le backend en `http` depuis une page chargée en `https`, causant du Mixed Content
- la chaîne complète bridge -> backend -> N8N -> frontend n'était pas suffisamment explicite ni robuste

## Symptômes observés

### 1. Routes `/wa-bridge` en erreur 404
Les appels de production vers :
- `https://api.zetaapp.xyz/wa-bridge/...`

renvoyaient des `404`, ce qui empêchait :
- l'affichage de l'état du bridge
- la génération du QR code
- la reconnexion WhatsApp
- l'orchestration normale des messages entrants

### 2. QR code WhatsApp indisponible
Le QR code n'apparaissait plus alors que le service semblait démarré.

Effet concret :
- impossible de reconnecter le compte WhatsApp
- bridge inutilisable côté opérateur

### 3. Erreur de verrouillage Chromium / profile lock
Chromium ne pouvait plus utiliser le répertoire de session existant.

Effet concret :
- échec de lancement du navigateur headless/non-headless
- impossibilité de restaurer une session saine
- blocage du bridge même avec une configuration par ailleurs correcte

### 4. Webhook N8N non fiable ou mal propagé
Le bridge devait transmettre les événements entrants vers N8N, mais la cible webhook n'était pas suffisamment explicitement fixée dans l'exécution réelle du service.

Effet concret :
- des messages entrants pouvaient ne pas remonter correctement dans le workflow attendu
- l'orchestration aval devenait instable ou impossible à diagnostiquer

### 5. Mixed Content sur `incoming-signals`
Le frontend de production, servi en `https`, déclenchait des appels vers une URL backend en `http` pour le polling des signaux entrants.

Effet concret :
- warnings navigateur
- requêtes bloquées selon le contexte
- impression que les messages WhatsApp n'arrivaient pas dans l'interface alors que le problème se situait parfois côté URL frontend/backend

### 6. Dérive d'exploitation production
Le fonctionnement réel du bridge dépendait trop de manipulations implicites :
- configuration peu centralisée
- exposition réseau pas assez explicitée
- persistance de session fragile
- manque de séparation claire entre code, sessions et reverse proxy

## Causes racines identifiées

## Cause racine A - Reverse proxy Nginx incomplet ou incohérent
Le domaine `api.zetaapp.xyz` n'exposait pas correctement `/wa-bridge` vers le service du bridge.

Cela provoquait directement les `404` en production.

## Cause racine B - Conflit ou doublon de configuration Nginx
Un doublon autour de `server_name api.zetaapp.xyz` perturbait la configuration effective.

Conséquences :
- comportement non prévisible
- risque qu'une mauvaise définition prenne la main
- difficulté de diagnostic tant que la config active n'était pas clarifiée

## Cause racine C - Répertoire de session Chromium verrouillé/corrompu
Les fichiers de session WhatsApp/Chromium existants empêchaient un redémarrage propre.

Conséquences :
- impossibilité de relancer le navigateur
- QR code absent
- bridge bloqué dans un état partiellement vivant mais inutilisable

## Cause racine D - Configuration runtime insuffisamment explicite du bridge
Le bridge devait dépendre d'une configuration claire pour :
- le port
- les chemins de session
- les URLs webhook
- le comportement de persistance

Quand ces éléments sont implicites ou dispersés, la prod devient fragile.

## Cause racine E - URL backend frontend non normalisée
Le frontend pouvait construire un `baseUrl` non canonique, incluant du `http` en production.

Conséquences :
- Mixed Content
- polling `incoming-signals` non fiable
- perception de non-réception des messages alors qu'une partie du problème était purement d'URL

## Corrections appliquées

## 1. Exposition correcte de `/wa-bridge` derrière Nginx
La configuration Nginx a été reprise pour exposer explicitement le bridge derrière :
- `api.zetaapp.xyz`
- `api.myzeta.xyz`

Objectif :
- faire proxyfier correctement toutes les routes `/wa-bridge/...`
- supprimer les `404` de production
- garantir un point d'accès stable côté frontend et opérateur

Résultat :
- les routes `status`, `qr`, et autres endpoints du bridge redeviennent joignables via les domaines API

## 2. Correction du doublon `server_name`
La configuration parasite/dupliquée a été supprimée ou neutralisée afin de ne garder qu'une définition effective cohérente pour `api.zetaapp.xyz`.

Résultat :
- Nginx devient déterministe
- la route `/wa-bridge` est servie par la bonne configuration

## 3. Nettoyage du verrouillage de session Chromium
Les données de session problématiques ont été nettoyées pour repartir sur un état sain.

Objectif :
- permettre à Chromium de redémarrer proprement
- réafficher le QR code si nécessaire
- éviter qu'un vieux lock bloque toute la chaîne

Résultat :
- le bridge peut relancer Chromium sans rester bloqué sur le profil précédent

## 4. Mise en place d'une persistance stable des sessions
La persistance a été séparée proprement dans un répertoire dédié :
- `/srv/zeta-wa-bridge/sessions`

Objectif :
- éviter une persistance fragile ou mélangée au code
- rendre la maintenance plus claire
- préserver les sessions sur les redémarrages normaux

Résultat :
- les sessions ne dépendent plus d'un emplacement implicite ou temporaire

## 5. Isolation du code du bridge dans un emplacement dédié
Le bridge a été positionné dans un répertoire clair de service :
- `/opt/zeta-wa-bridge`

Objectif :
- distinguer clairement le code d'exécution
- faciliter l'exploitation
- réduire les dérives de configuration

## 6. Configuration explicite du bridge via environnement
La configuration du bridge a été rendue explicite dans son environnement d'exécution.

Elle inclut notamment :
- port d'écoute
- chemins de session
- URL du webhook N8N
- paramètres nécessaires au runtime

Objectif :
- supprimer les dépendances implicites
- fiabiliser le démarrage réel en prod
- rendre les diagnostics plus rapides

## 7. Exécution stable du bridge via PM2
Le service `wa-bridge` est désormais géré comme un process dédié, stable et redémarrable.

Objectif :
- avoir un process manager clair
- redémarrer facilement le bridge sans manipulation artisanale
- disposer d'un service identifiable en production

Résultat :
- le bridge est désormais traité comme un vrai service d'infrastructure applicative

## 8. Fix du webhook N8N côté configuration effective
Le webhook entrant/sortant attendu a été rendu explicite dans la configuration réellement utilisée par le bridge.

Objectif :
- éviter les écarts entre intention et runtime
- garantir que les messages entrants remontent vers le bon workflow

Résultat :
- l'intégration N8N devient plus lisible et beaucoup moins fragile

## 9. Fix frontend du Mixed Content sur `incoming-signals`
Le frontend a été corrigé pour normaliser l'URL backend en production vers une base `https` canonique.

Objectif :
- empêcher tout appel `http` depuis le frontend prod
- stabiliser le polling des signaux entrants
- supprimer les warnings Mixed Content

Résultat :
- le frontend n'utilise plus une URL non sécurisée en production pour `incoming-signals`

## Architecture production cible

## Backend / Bridge
- backend principal : VPS Contabo
- bridge WhatsApp : service dédié sur VPS
- code bridge : `/opt/zeta-wa-bridge`
- sessions persistantes : `/srv/zeta-wa-bridge/sessions`
- supervision process : PM2
- reverse proxy : Nginx

## Exposition réseau
- `https://api.zetaapp.xyz/wa-bridge/...`
- `https://api.myzeta.xyz/wa-bridge/...`

## Orchestration des messages
Flux cible :
1. message reçu sur WhatsApp
2. bridge le capte via la session WhatsApp Web active
3. bridge transmet l'événement au webhook configuré
4. N8N orchestre le traitement
5. backend/frontend récupèrent les signaux utiles
6. l'interface Discussions/Chat peut refléter l'activité sans erreur de protocole

## Ce qui rend maintenant le bridge robuste

## 1. Configuration explicite
Le comportement de prod ne repose plus sur des hypothèses implicites.

## 2. Séparation code / sessions / proxy
Chaque responsabilité a un emplacement clair.

## 3. Process manager dédié
Le service peut être observé, relancé et maintenu plus proprement.

## 4. URL de production canonique
Les appels critiques passent désormais par des URLs cohérentes et sécurisées.

## 5. Proxy Nginx unifié
Les domaines API pointent correctement vers le bridge.

## 6. Réduction du risque de dérive
Le système est plus proche d'une exploitation de prod stable que d'un assemblage manuel fragile.

## Vérifications de routine recommandées

## Vérifier le bridge
Exemples d'URL de contrôle :
- `https://api.zetaapp.xyz/wa-bridge/status?merchant_id=...`
- `https://api.myzeta.xyz/wa-bridge/status?merchant_id=...`

Attendu :
- réponse HTTP valide
- état cohérent du bridge
- absence de `404`

## Vérifier le process manager
Contrôler que le process `wa-bridge` est bien présent et stable dans PM2.

## Vérifier Nginx
Contrôler qu'aucun doublon de config ne réintroduit un conflit de `server_name`.

## Vérifier les sessions
Confirmer que le répertoire de session reste accessible et non verrouillé de manière anormale.

## Vérifier le frontend
Depuis le navigateur :
- inspecter les requêtes `incoming-signals`
- confirmer qu'elles passent bien en `https`
- confirmer l'absence de Mixed Content

## Procédure en cas de régression

## Si `/wa-bridge` repasse en 404
Vérifier en priorité :
- la configuration Nginx active
- les doublons `server_name`
- le `location /wa-bridge` réellement chargé
- la cible `proxy_pass`

## Si le QR code n'apparaît plus
Vérifier en priorité :
- le process `wa-bridge`
- les logs PM2
- l'état du répertoire de sessions
- un éventuel verrou Chromium

## Si les messages WhatsApp n'arrivent plus dans l'interface
Vérifier la chaîne complète :
- bridge actif
- webhook N8N correct
- backend joignable
- frontend sans Mixed Content
- polling `incoming-signals` bien en `https`

## Points de vigilance

## Ne pas réintroduire d'implicite dans la config bridge
Toute variable critique doit rester explicite.

## Ne pas casser la config Nginx active
Les routes de prod doivent rester centralisées et lisibles.

## Ne pas mélanger code et données de session
Les sessions doivent rester dans leur emplacement dédié.

## Ne pas laisser le frontend dériver vers des URLs non canoniques
La prod doit rester en `https` sur l'API canonique.

## Conclusion

Le problème du WA Bridge n'était pas un bug unique mais une accumulation de fragilités de production : proxy incomplet, doublon Nginx, sessions Chromium verrouillées, configuration runtime trop implicite et URL frontend non normalisée.

Les corrections appliquées ont permis de :
- supprimer les `404` sur `/wa-bridge`
- restaurer un lancement Chromium sain
- rendre la reconnexion WhatsApp à nouveau possible
- fiabiliser le lien avec N8N
- supprimer le Mixed Content côté frontend
- poser une base de production plus robuste et plus maintenable

Le bridge est maintenant stabilisé autour d'un modèle plus propre :
- service dédié
- configuration explicite
- persistance stable
- reverse proxy correct
- URLs de prod cohérentes
- exploitation plus sûre
