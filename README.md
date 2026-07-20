# KRONOCOLOR — version Python (Flask)

Maison de négoce en pigments et peintures — boutique, grossiste, consultant, admin.
Persistance réelle en base SQLite (`kronocolor.db`, créée automatiquement au premier lancement).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration (optionnelle, pour l'IA)

```bash
export ANTHROPIC_API_KEY=sk-ant-...     # Windows : set ANTHROPIC_API_KEY=sk-ant-...
```

Sans cette clé, le site fonctionne normalement (boutique, panier, paiement simulé,
livraison, favoris, grossiste, consultant, admin, statistiques, prédiction Machine
Learning) — seule l'explication technique détaillée générée par Claude est désactivée
(un message l'indique). La prédiction Machine Learning (scikit-learn) fonctionne
toujours, elle est locale et ne dépend d'aucune clé.

## Lancer le site

```bash
python app.py
```

Puis ouvrir **http://127.0.0.1:5000**

## Comptes de connexion

À la connexion, choisissez le rôle puis renseignez n'importe quel email/mot de passe :

| Rôle       | Code d'accès requis   |
|------------|------------------------|
| Client     | aucun                  |
| Grossiste  | aucun                  |
| Consultant | `kronocolor-conseil`   |
| Admin      | `kronocolor-admin`     |

## Ce que contient chaque rôle

- **Client** : accueil (meilleures ventes, favoris), boutique organisée en 3 compartiments
  (Peinture, Papier peint, Outils de peinture) avec panier et paiement (Carte ou PayPal,
  simulés) et livraison par zone, quiz QCM de conseil (Machine Learning), diagnostic
  détaillé (mélange de pigments + prédiction ML locale + explication IA Claude), test
  caméra en direct (superposition de couleur façon réalité augmentée + détection de la
  nature de la surface par IA vision), mes commandes, chatbot flottant (réponses
  instantanées sur les questions fréquentes, sinon IA).
- **Grossiste** : devis ou paiement direct en grande quantité.
- **Consultant** ("advisor") : liste des clients, historique d'achat de chacun, notes/avis.
- **Admin** : statistiques (CA, clients uniques, meilleures ventes), gestion des
  produits par compartiment (ajout manuel avec photo uploadée, prix, stock), suivi des
  commandes, demandes grossiste.

## Quiz QCM et caméra AR

- `/client/quiz` : trois questions (surface, climat, teinte souhaitée) transformées en
  entrée du modèle scikit-learn, qui renvoie une recommandation de finition et de liant
  avec un score de confiance — sans appel réseau.
- `/client/camera` : active la caméra du navigateur (`getUserMedia`), superpose une
  couleur choisie sur le flux vidéo en direct (aperçu façon réalité augmentée), et permet
  de capturer une image pour l'envoyer à Claude (vision) afin d'identifier la nature de
  la surface (mur, bois, métal, béton…) et son état apparent.

## Machine Learning

`ml_model.py` entraîne un `RandomForestClassifier` (scikit-learn) au démarrage sur un
jeu de règles techniques (surface × climat × luminosité de la teinte → finition +
liant recommandés). C'est un vrai modèle appris, pas une simple table de correspondance
codée en dur : il généralise via ses arbres de décision et donne un score de confiance.
Il tourne localement, sans appel réseau, et complète (sans la remplacer) l'explication
en langage naturel générée par Claude.

## Structure du projet

```
app.py                  routes Flask + logique métier
ml_model.py             modèle scikit-learn (prédiction finition/liant)
requirements.txt
templates/              pages Jinja2 (login, client, wholesale, consultant, admin)
static/style.css        thème chic, chaud, clair
static/uploads/         photos de produits uploadées par l'admin
kronocolor.db           base SQLite (créée automatiquement)
```

## Notes

- Le paiement est **simulé** (aucune carte réelle n'est débitée) : pour un vrai
  paiement, il faudrait intégrer un prestataire (Stripe, CMI au Maroc, etc.).
- Les photos produits sont stockées sur disque dans `static/uploads/`.
- Le panier et les favoris sont stockés dans la session Flask (par utilisateur connecté).
