# Roadmap Zeta AI : Expérience PWA "Elite" 2026

Ce document récapitule les technologies et stratégies pour transformer Zeta AI en une extension native du système, dépassant le simple cadre d'une application web.

---

## 1. Couche Haptique (Micro-vibrations)
Donner une consistance physique aux pixels.
- **Bibliothèque** : `web-haptics`
- **Patterns** : 
  - Clic : Light (10ms)
  - Succès : Double pulse léger
  - Erreur : Triple pulse rapide
- **Usage** : Intégration dans les boutons, les notifications (toasts) et le pull-to-refresh.

## 2. Sécurité Biométrique (Passkeys / Face ID)
La révolution ultime pour le login. Plus de mots de passe, plus d'OTP.
- **Mécanisme** : WebAuthn (Face ID sur iOS, Empreinte sur Android).
- **Fallback** : Géré par l'OS (Code PIN de l'iPhone).
- **Intégration** : via Supabase Auth (`mfa.enroll`, `mfa.challenge`).

## 3. Navigation & Fluidité (Zéro Latence Perçue)
- **Navigation Prédictive** : Speculative Rules API (`speculationrules`). Pré-chargement des pages au survol.
- **View Transitions** : Faire "voler" les éléments d'une page à l'autre (ex: photo produit du catalogue vers le détail).

## 4. Audio Spatial & "Earcons"
- **Earcons** : Logos sonores courts (50ms) pour les validations d'actions.
- **Audio Spatial** : Sons directionnels selon le positionnement de l'alerte.

## 5. Sensibilité Environnementale
- **Ambient Light Sensor** : Ajuster contraste/saturation en plein soleil.
- **Proximity Sensor** : Couper l'écran et basculer sur l'écouteur interne quand le téléphone est à l'oreille.

## 6. Intégration Système Profonde
- **Share Target API** : Apparaître dans le menu "Partager" natif (ex: Reçu Wave depuis WhatsApp).
- **File Handling** : Ouvrir les fichiers `.pdf` ou `.json` directement dans Zeta AI.
- **App Shortcuts** : Menu contextuel sur l'icône de l'écran d'accueil.

## 7. Local-First (Sync Optimiste)
- **IndexedDB + CRDTs** : Écriture instantanée en local, synchronisation Supabase en arrière-plan. Zéro Spinner.

---

*Note : Ces technologies transforment la perception de qualité et positionnent Zeta AI comme une référence technologique de premier plan.*

Pour le Face ID (Passkeys), voici à quoi va ressembler le cœur du système dans ton projet. C'est l'API de MFA de Supabase qui va piloter le scan natif du téléphone :

typescript
// Extrait de ce qu'on va implémenter dans ton AuthContext
const enrollPasskey = async () => {
  // 1. On demande à Supabase de préparer l'enrôlement WebAuthn
  const { data, error } = await supabase.auth.mfa.enroll({
    factorType: 'webauthn',
    issuer: 'Zeta AI',
    friendlyName: 'Mon Appareil Principal'
  });
  if (error) throw error;
  // 2. C'est ICI que la popup native Face ID / Touch ID apparaît
  // Le navigateur prend le relais avec navigator.credentials.create
  const challengeResponse = await supabase.auth.mfa.challenge({ factorId: data.id });
  
  // 3. Une fois scanné, on valide l'enrôlement
  return await supabase.auth.mfa.verify({
    factorId: data.id,
    challengeId: challengeResponse.data.id,
    code: challengeResponse.data.challenge // Le "code" est ici la signature biométrique
  });
};