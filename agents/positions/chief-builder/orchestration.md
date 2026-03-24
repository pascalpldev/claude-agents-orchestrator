---
name: orchestration
description: Protocole d'orchestration complet du chief-builder — de l'idée brute au code déployé
scope: chief-builder only
---

# Orchestration — Chief Builder

## Pipeline full-lifecycle

```
[Entrée]  Idée / besoin (ticket GitHub ou conversation directe)
              ↓
[Phase 1] Discovery        — Product Builder
              ↓
[Phase 2] Conception       — Tech Lead + UX Expert + Artistic Director
              ↓
[Phase 3] Challenge        — Bounded Revision Loop
              ↓
[Phase 4] Plan enrichi     — Publié sur ticket ou résumé en conversation
              ↓
        ★ GATE HUMAINE ★   — tu valides → label "to-dev" (ou confirmation en chat)
              ↓
[Phase 5] Fabrication      — Dev persona
              ↓
[Phase 6] Mise en place    — Dev persona
```

---

## Entrées : deux modes de déclenchement

### Mode Ticket (GitHub)

Déclenché par `cao-process-tickets` sur un ticket labelisé `to-enrich` ou `to-dev`.

```bash
TICKET_N="<N>"
gh issue view "$TICKET_N" --repo "$OWNER/$REPO" \
  --json number,title,body,labels,comments,assignees
```

- Phases 1–4 : ticket labelisé `to-enrich` → produit le plan en commentaire GitHub → label `enriched`
- Phases 5–6 : ticket labelisé `to-dev` → implémentation → PR → label `to-test`

### Mode Conversation (direct)

Déclenché en chat : *"j'ai besoin de X"*, *"je veux construire Y"*, *"idée : Z"*.

- Phases 1–4 : dialogue interactif — questions de cadrage si nécessaire, plan présenté en conversation
- Gate humaine : *"Je valide — on part en fabrication ?"* ou *"Pas encore — tu ajustes X d'abord ?"*
- Phases 5–6 : déclenchées sur confirmation explicite en chat

L'agent détecte le mode automatiquement : présence d'un `TICKET_N` = mode ticket, sinon = mode conversation.

---

## Phase 1 — Discovery (Product Builder)

**Objectif** : comprendre le vrai besoin avant toute conception.

1. Charger la persona : `Read agents/positions/chief-builder/personas/product-builder.md`
2. Charger les behaviors : `jtbd.md` (toujours) + `five-whys.md` (si solution prescrite sans problème)
3. Produire :
   - JTBD statement : *"Quand X, l'utilisateur veut Y pour Z."*
   - Version YAGNI du scope
   - Questions de cadrage si scope insuffisant (max 3, une par message en mode conversation)

**Output de phase** : JTBD statement validé + scope minimal défini.

**Règle** : ne pas passer en Phase 2 si le JTBD statement est flou ou si des contradictions dans le scope persistent.

---

## Phase 2 — Conception (waves parallèles)

**Objectif** : produire un plan d'implémentation complet, informé par Phase 1.

Les trois rôles s'activent **en parallèle**, nourris par le JTBD statement et le scope YAGNI de Phase 1.

### Wave Tech Lead
1. Charger : `Read agents/positions/chief-builder/personas/tech-lead.md`
2. Charger behaviors conditionnels :
   - `boy-scout-rule.md` — toujours
   - `stride.md` — si auth / APIs / données sensibles
   - `fmea.md` — si chemin critique prod
3. Produire : architecture, fichiers concernés, patterns réutilisables, risques

### Wave UX Expert
1. Charger : `Read agents/positions/chief-builder/personas/ux-expert.md`
2. Charger behaviors conditionnels :
   - `four-states-ui.md` — si interface impliquée
   - `cognitive-load.md` — si interface impliquée
   - `progressive-disclosure.md` — si formulaire > 4 champs ou flow multi-étapes
3. Produire : flows utilisateur, états d'interaction, checklist UX

### Wave Artistic Director
1. Charger : `Read agents/positions/chief-builder/personas/artistic-director.md`
2. Actif uniquement si interface visuelle impliquée — silencieux sinon
3. Produire : direction visuelle, opportunités distinctives, contraintes design system

**Output de phase** : trois positions distinctes, prêtes pour la synthèse.

---

## Phase 3 — Challenge (Bounded Revision Loop)

**Objectif** : détecter les conflits entre phases/waves et les résoudre avant de produire le plan final.

Charger : `Read agents/behaviors/challenge-amplify.md`

### Filtre par wave

Chaque wave applique le filtre Challenge/Amplify sur les outputs des autres waves :

| Source | Peut challenger | Peut amplifier |
|--------|----------------|----------------|
| Tech Lead | Scope Phase 1, UX Phase 2 | Réutilisation, Boy Scout |
| UX Expert | Architecture Phase 2, Scope Phase 1 | Flow simplifié, état couvert |
| Artistic Director | UX flows Phase 2 | Touche distinctive gratuite |
| Product Builder | Toute wave si complexity > scope | Valeur adjacente détectée |

### Classification du challenge

| Type | Critère | Traitement |
|------|---------|------------|
| **Mineur** | Désaccord sur un choix, pas sur la direction | Wave 4 synthèse absorbe — pas de re-run |
| **Bloquant** | Invalide une décision structurante (scope, faisabilité, sécurité critique) | Revision Arc — re-run ciblé de la wave affectée, une fois |

### Revision Arc (challenges bloquants uniquement)

```
Challenge bloquant détecté par Wave N sur Wave M
  → Re-run ciblé de Wave M avec le nouveau contexte
  → Si le challenge persiste après re-run → Synthesizer tranche
  → Documenter comme "Tension non résolue" dans le plan
```

**Règle absolue** : maximum 1 révision par wave. Pas de boucle infinie.

### Tensions non résolues

Si un challenge bloquant persiste après révision :

```markdown
### Tensions non résolues
- [Rôle A] vs [Rôle B] : [description du désaccord]
  Retenu : [décision du synthesizer + justification]
  Risque accepté : [description]
```

---

## Phase 4 — Plan enrichi (Synthèse)

**Objectif** : produire le plan final qui sera validé par l'humain.

Le synthesizer combine tous les outputs des phases 1–3 en un plan structuré.

### Format du plan (mode ticket)

Publié en commentaire GitHub via :
```bash
gh issue comment "$TICKET_N" --repo "$OWNER/$REPO" --body "$(cat <<'COMMENT'
## Plan d'enrichissement
[voir template dans agent.md section 3c]
COMMENT
)"
gh issue edit "$TICKET_N" --repo "$OWNER/$REPO" \
  --remove-label "enriching" --add-label "enriched"
```

### Format du plan (mode conversation)

Présenté directement en chat avec la conclusion :

> *"Plan prêt. Je m'arrête ici pour validation. Dis-moi 'go' pour lancer la fabrication, ou indique ce que tu veux ajuster."*

### ★ GATE HUMAINE ★

Vérifier le label `autonomous` sur le ticket (mode ticket) ou l'intention explicite (mode conversation) :

```
Mode ticket :
  ticket a le label "autonomous"
    → LOG gate_bypassed + continuer Phase 5 immédiatement
  ticket n'a PAS le label "autonomous"
    → LOG gate_active + s'arrêter
    → label "enriched" posé, attendre que le label passe à "to-dev"

Mode conversation :
  utilisateur a dit "autonome", "sans gate", "go direct", "enchaîne"
    → continuer Phase 5 immédiatement
  sinon
    → s'arrêter, présenter le plan, attendre confirmation explicite
    → ("go", "c'est bon", "lance", "to-dev")
```

**Règle absolue** : sans le label `autonomous` ou une instruction explicite, l'agent ne passe jamais en Phase 5 de sa propre initiative.

---

## Phase 5 — Fabrication (Dev persona)

Déclenchée par :
- Mode ticket : label `to-dev` détecté
- Mode conversation : confirmation explicite de l'humain

1. Charger : `Read agents/positions/chief-builder/personas/dev.md`
2. Suivre le processus complet du persona dev :
   - Créer branch feature
   - Implémenter selon le plan Phase 4
   - Respecter les patterns identifiés en Phase 2 (Tech Lead)
   - Appliquer les flows définis en Phase 2 (UX Expert)
   - Respecter la direction visuelle Phase 2 (Artistic Director) si applicable
3. Lancer les tests
4. Créer PR via `gh pr create`
5. Mode ticket → label `dev-in-progress` → `to-test`
6. Mode conversation → résumé du travail effectué

---

## Phase 6 — Mise en place (Dev persona)

Déclenchée par :
- Mode ticket : label `godeploy` sur ticket `to-test`
- Mode conversation : *"merge"*, *"déploie"*, confirmation explicite

1. Dev persona reste actif
2. Vérifier mergeable via `gh pr view`
3. Merger via `gh pr merge`
4. Mode ticket → label `deployed`
5. Mode conversation → confirmation de déploiement

---

## Synergies cross-phases

Certaines combinaisons de contenu déclenchent des activations supplémentaires :

| Signal détecté | Synergie déclenchée |
|----------------|---------------------|
| Ticket touche auth / permissions | Tech Lead (STRIDE) → active aussi UX Expert (cognitive-load sur l'UI de permissions) |
| Nouveau flow onboarding / premier usage | UX Expert (four-states-ui) → active aussi Product Builder (JTBD — l'empty state IS le job) |
| Migration / refacto de données | Tech Lead (FMEA) → active aussi Product Builder (YAGNI — revalider le scope face au risque) |
| Nouvelle page / composant UI riche | UX Expert (progressive-disclosure) → active aussi Artistic Director |
| Complexité estimée XL | Product Builder re-s'active → challenge YAGNI sur le scope final |

---

## Règles globales

- **Phase 1 bloque Phase 2** : pas de conception sans JTBD clair
- **Gate humaine bloque Phase 5** : pas de fabrication sans validation explicite
- **1 révision max** par wave dans la Bounded Revision Loop
- **Silence = valeur** : un rôle sans contribution concrète ne parle pas
- **Mode autonome interdit sur Phase 5-6** sans signal explicite — même en mode conversation
