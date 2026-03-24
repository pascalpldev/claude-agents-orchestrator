---
name: test-discipline
description: Bonnes pratiques de test — nommage, isolation, couverture, ce qu'on ne teste pas
scope: dev persona (always)
reference: Growing Object-Oriented Software (Freeman & Pryce), TDD by Example (Kent Beck)
---

# Test Discipline

## Philosophie

**Tester le comportement, pas l'implémentation.** Un test qui échoue quand on renomme une variable privée est un mauvais test. Un test qui échoue quand on casse un contrat public est un bon test.

La couverture de lignes est un indicateur, pas un objectif. 80% de couverture sur les chemins critiques vaut mieux que 100% sur les getters.

## Nommage

Le nom d'un test est sa documentation. Il doit être lisible par un humain non-technique.

**Format** : `test_<quand>_<alors>` ou `<sujet>_<condition>_<résultat attendu>`

```python
# ✅ Bon — décrit un comportement
def test_login_with_expired_token_returns_401():
def test_cart_total_applies_discount_when_code_is_valid():
def test_user_creation_fails_when_email_already_exists():

# ❌ Mauvais — décrit l'implémentation
def test_check_token():
def test_calculate():
def test_create_user_error():
```

## Structure AAA (Arrange / Act / Assert)

Chaque test suit ce pattern, séparé visuellement :

```python
def test_order_total_includes_tax():
    # Arrange
    cart = Cart(items=[Item(price=100)])
    tax_rate = 0.2

    # Act
    total = cart.calculate_total(tax_rate=tax_rate)

    # Assert
    assert total == 120
```

Un seul `Assert` logique par test. Si tu as besoin de plusieurs assertions pour décrire un comportement, c'est acceptable — si tu as besoin de plusieurs assertions pour tester des comportements *différents*, c'est un test à découper.

## Isolation

Chaque test doit être indépendant : il ne doit pas dépendre de l'ordre d'exécution, de l'état laissé par un autre test, ni d'une ressource externe non contrôlée.

**Règles** :
- Pas de state partagé entre tests (pas de variables globales modifiées)
- Chaque test crée ses propres fixtures / données
- Les tests doivent passer dans n'importe quel ordre
- Nettoyer après soi : teardown ou fixtures scoped

**Mocks — usage limité** :
- Mocker les dépendances externes réelles (API tierce, email, clock système)
- Ne pas mocker ce qu'on possède (nos propres modules) — tester l'intégration à la place
- Un test qui mocke tout ce qu'il appelle ne teste rien

## Ce qu'on teste

| ✅ Tester | ❌ Ne pas tester |
|-----------|-----------------|
| Logique métier (calculs, règles, transformations) | Getters/setters triviaux |
| Chemins d'erreur (input invalide, ressource manquante) | Framework internals (ORM, routing) |
| Contrats d'API (status codes, format de réponse) | Code généré automatiquement |
| Cas limites (zéro, vide, null, max) | Constantes et configuration statique |
| Comportement des intégrations (DB, cache) | Code de logging pur |

## Types de tests et quand les écrire

**Unit tests** — pour la logique pure, sans dépendance externe :
- Fonctions de transformation, calcul, validation
- Classes avec règles métier
- Rapides, nombreux, isolés

**Integration tests** — pour les interactions entre composants :
- Endpoints API (happy path + au moins un error path)
- Interactions avec la DB sur les requêtes non-triviales
- Un test d'intégration remplace N unit tests sur des mocks fragiles

**Ne pas écrire de e2e tests** sauf si le plan d'enrichissement l'exige explicitement.

## Mapping enrichissement → tests

Chaque critère de validation du plan d'enrichissement doit avoir un test correspondant. Vérifier 1:1 avant d'ouvrir la PR :

```
Critère de validation            → Test
─────────────────────────────────────────────────
☑ Behaviour A works              → test_behaviour_a_returns_expected_result()
☑ Edge case B is handled         → test_behaviour_a_with_edge_case_b_returns_X()
☑ Error path C returns 404       → test_behaviour_a_missing_resource_returns_404()
☑ No regression on D             → test_existing_d_still_works_after_change()
```

Si un critère de validation ne peut pas être traduit en test automatisé : noter explicitement dans le PR body sous `## Testing` avec la procédure de vérification manuelle.

## Placement des fichiers de test

Suivre la convention existante du projet (lire CLAUDE.md). En l'absence de convention :

```
src/
  users/
    user_service.py
    test_user_service.py    ← colocalisé, même dossier

# OU

tests/
  unit/
    test_user_service.py
  integration/
    test_user_api.py
```

Ne pas créer une nouvelle structure si une convention existe déjà — la cohérence prime.
