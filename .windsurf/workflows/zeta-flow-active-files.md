---
description: Référence des vrais fichiers actifs à modifier pour /zeta-flow
---
Toujours vérifier cette référence avant toute modification liée à Zeta Flow.

## Cible active unique
- Application active : `zeta-ai-vercel/`
- Flow actif : `/zeta-flow`
- Ne pas appliquer les corrections métier directement dans `zeta-ai-vercel-deploy/`.
- `zeta-ai-vercel-deploy/` sert de clone de déploiement séparé pour pousser vers Vercel staging sans toucher au dépôt de travail principal.
- Ne pas utiliser `/zeta-flow-v2` comme cible par défaut.

## Fichiers autoritaires par zone
- Domaines & Pages dans l'app active : `zeta-ai-vercel/src/pages/ZetaFlowDomains.tsx`
- Intégration du sous-écran Domaines dans l'app active : `zeta-ai-vercel/src/pages/ZetaFlow.tsx`
- **Page Commande / Formulaire client de Zeta Flow (prod)** : `zeta-ai-vercel/src/pages/ZetaFlow.tsx` — contient le formulaire avec champ libre "Adresse de livraison * — COMMUNE / QUARTIER" (pas de select commune)
- Page Commande pour `/zeta-flow-v2` (non utilisée par défaut) : `zeta-ai-vercel/src/pages/ZetaflowCommandes.tsx` — version alternative avec select commune
- Catalogue admin React utilisé par `/zeta-flow` : `zeta-ai-vercel/src/pages/ZetaFlowCatalogueRedirect.tsx`
- Écran catalogue / upload / crop réellement travaillé : `zeta-ai-vercel/src/pages/ZetaFlowCatalogue.tsx`
- Hook catalogue utilisé par `/zeta-flow` : `zeta-ai-vercel/src/hooks/useCatalog.ts`
- Hook société / slug utilisé par `/zeta-flow` : `zeta-ai-vercel/src/hooks/useCompany.ts`
- Admin catalogue HTML réellement servi : `zeta-ai-vercel/public/admincatalogue.html`
- Catalogue public réellement servi : `zeta-ai-vercel/public/publiccatalogue.html`

## Vérification obligatoire avant édition
1. Identifier si la demande concerne `/zeta-flow`, le catalogue admin HTML, le catalogue public ou un hook partagé.
2. Ouvrir le fichier autoritaire dans `zeta-ai-vercel/` avant toute modification.
3. Vérifier qu'aucune modification n'est faite par erreur dans `zeta-ai-vercel-deploy/` ou dans un prototype racine.
4. Si un fichier racine sert seulement de référence visuelle, reporter ensuite les changements dans le fichier actif de `zeta-ai-vercel/`.

## Procédure de déploiement staging validée
1. Faire toutes les modifications source dans `zeta-ai-vercel/`.
2. Valider localement le frontend depuis `zeta-ai-vercel/` avec un build ciblé si la modification est significative.
3. Ne pas faire le commit/push de staging depuis `zeta-ai-vercel/` si on veut éviter toute répercussion sur le dépôt de travail principal.
4. Utiliser `zeta-ai-vercel-deploy/` comme clone de déploiement isolé.
5. Synchroniser le contenu de `zeta-ai-vercel/` vers `zeta-ai-vercel-deploy/` en excluant les dossiers et fichiers locaux sensibles comme `.git`, `node_modules`, `dist`, `.vercel` et les `.env`.
6. Vérifier que `zeta-ai-vercel-deploy/` est bien sur la branche `dev`.
7. Faire le `git add`, `git commit` et `git push origin dev` depuis `zeta-ai-vercel-deploy/`.
8. Laisser Vercel staging se déclencher depuis la branche `dev` du repo de déploiement.
9. Considérer `zeta-ai-vercel/` comme la source de vérité pour le code, et `zeta-ai-vercel-deploy/` comme un véhicule de publication staging.

## Références non autoritaires sauf demande explicite
- `admincatalogue.html` à la racine : référence/source possible, pas la cible de prod Vite.
- `parametrefinal.jsx` : prototype visuel uniquement.
- `zeta-ai-vercel-deploy/` : ne pas considérer comme cible principale de développement, seulement comme clone de déploiement.

## Contrôle final
- Relire le fichier réellement utilisé.
- Si c'est une modification frontend Vite significative, lancer une validation ciblée ou un build local.
- Avant push staging, vérifier la branche du clone de déploiement et le remote visé.

