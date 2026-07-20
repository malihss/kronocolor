"""
Modèle de Machine Learning KRONOCOLOR
--------------------------------------
Un RandomForestClassifier scikit-learn entraîné sur un jeu de règles techniques
(surface, climat, luminosité de la teinte) pour prédire la finition et le liant
recommandés. Complète (ne remplace pas) l'explication détaillée générée par l'IA
Claude : ce modèle donne une prédiction rapide, déterministe et locale, sans appel
réseau.

Entraînement fait en mémoire au démarrage de l'app (dataset synthétique, petit
volume => quelques millisecondes), pas de fichier modèle à charger.
"""
import random

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

SURFACES = ["Mur extérieur", "Mur intérieur", "Bois", "Métal", "Béton brut",
            "Carrosserie auto", "Plastique", "Plâtre"]
CLIMATES = ["chaud_sec", "froid", "humide", "vent"]

# (surface, climate, lightness_bucket) -> (finish, binder)
# lightness_bucket: "clair" (>170), "moyen" (90-170), "sombre" (<90)
RULES = {
    ("Mur extérieur", "chaud_sec"): ("Mat", "Silicate"),
    ("Mur extérieur", "froid"): ("Satiné", "Acrylique"),
    ("Mur extérieur", "humide"): ("Satiné", "Silicate"),
    ("Mur extérieur", "vent"): ("Mat", "Chaux"),
    ("Mur intérieur", "chaud_sec"): ("Mat", "Acrylique"),
    ("Mur intérieur", "froid"): ("Satiné", "Acrylique"),
    ("Mur intérieur", "humide"): ("Satiné", "Acrylique anti-humidité"),
    ("Mur intérieur", "vent"): ("Mat", "Acrylique"),
    ("Bois", "chaud_sec"): ("Satiné", "Glycéro"),
    ("Bois", "froid"): ("Laqué", "Glycéro"),
    ("Bois", "humide"): ("Laqué", "Glycéro marine"),
    ("Bois", "vent"): ("Satiné", "Glycéro"),
    ("Métal", "chaud_sec"): ("Laqué", "Époxy"),
    ("Métal", "froid"): ("Laqué", "Époxy"),
    ("Métal", "humide"): ("Laqué", "Époxy anti-corrosion"),
    ("Métal", "vent"): ("Laqué", "Époxy"),
    ("Béton brut", "chaud_sec"): ("Mat", "Silicate"),
    ("Béton brut", "froid"): ("Mat", "Acrylique"),
    ("Béton brut", "humide"): ("Satiné", "Silicate hydrofuge"),
    ("Béton brut", "vent"): ("Mat", "Silicate"),
    ("Carrosserie auto", "chaud_sec"): ("Laqué", "Polyuréthane"),
    ("Carrosserie auto", "froid"): ("Laqué", "Polyuréthane"),
    ("Carrosserie auto", "humide"): ("Laqué", "Polyuréthane anti-corrosion"),
    ("Carrosserie auto", "vent"): ("Laqué", "Polyuréthane"),
    ("Plastique", "chaud_sec"): ("Satiné", "Acrylique adhérence plastique"),
    ("Plastique", "froid"): ("Satiné", "Acrylique adhérence plastique"),
    ("Plastique", "humide"): ("Laqué", "Époxy adhérence plastique"),
    ("Plastique", "vent"): ("Satiné", "Acrylique adhérence plastique"),
    ("Plâtre", "chaud_sec"): ("Mat", "Acrylique"),
    ("Plâtre", "froid"): ("Mat", "Acrylique"),
    ("Plâtre", "humide"): ("Satiné", "Acrylique anti-humidité"),
    ("Plâtre", "vent"): ("Mat", "Acrylique"),
}

LIGHTNESS_BUCKETS = ["sombre", "moyen", "clair"]


def lightness_bucket(hex_color):
    hexv = hex_color.lstrip("#")
    r, g, b = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum > 170:
        return "clair"
    if lum > 90:
        return "moyen"
    return "sombre"


def _build_dataset(n_per_rule=12, seed=42):
    rng = random.Random(seed)
    X, y = [], []
    for (surface, climate), (finish, binder) in RULES.items():
        for _ in range(n_per_rule):
            bucket = rng.choice(LIGHTNESS_BUCKETS)
            # dark + humid metal/car surfaces skew slightly more toward glossier finish
            label = f"{finish}|{binder}"
            if bucket == "sombre" and climate == "humide" and finish == "Satiné":
                label = f"Laqué|{binder}"
            X.append([surface, climate, bucket])
            y.append(label)
    return X, y


class KronocolorRecommender:
    """Wraps a RandomForestClassifier with simple categorical encoders.

    Starts trained on the hand-coded rule dataset. As real orders come in
    (see retrain() below), it is periodically refit on the rule dataset PLUS
    the real (surface, climate, lightness_bucket) -> (finish, binder) samples
    captured from actual quiz-then-purchase journeys, so recommendations
    gradually reflect real customer behaviour instead of only the rules.
    """

    def __init__(self):
        self.surface_enc = LabelEncoder().fit(SURFACES)
        self.climate_enc = LabelEncoder().fit(CLIMATES)
        self.bucket_enc = LabelEncoder().fit(LIGHTNESS_BUCKETS)
        self.n_real_samples = 0
        self._fit(_build_dataset())

    def _fit(self, dataset):
        X_raw, y = dataset
        X = self._encode_rows(X_raw)
        self.label_enc = LabelEncoder().fit(y)
        y_enc = self.label_enc.transform(y)
        self.model = RandomForestClassifier(n_estimators=60, max_depth=6, random_state=42)
        self.model.fit(X, y_enc)

    def retrain(self, real_samples):
        """Refit the model on the synthetic rule dataset plus real usage samples.

        real_samples: iterable of (surface, climate, lightness_bucket, finish, binder).
        Real samples are duplicated a few times so a growing number of real
        orders can gradually outweigh the synthetic rules without needing a
        large volume of data to move the model at all.
        """
        X_raw, y = _build_dataset()
        real_list = list(real_samples)
        weight = 4
        for surface, climate, bucket, finish, binder in real_list:
            for _ in range(weight):
                X_raw.append([surface, climate, bucket])
                y.append(f"{finish}|{binder}")
        self.n_real_samples = len(real_list)
        self._fit((X_raw, y))

    def _encode_rows(self, rows):
        return [
            [self.surface_enc.transform([s])[0], self.climate_enc.transform([c])[0],
             self.bucket_enc.transform([b])[0]]
            for s, c, b in rows
        ]

    def predict(self, surface, climate, hex_color):
        if surface not in SURFACES:
            surface = SURFACES[0]
        if climate not in CLIMATES:
            climate = CLIMATES[0]
        bucket = lightness_bucket(hex_color)

        X = self._encode_rows([(surface, climate, bucket)])
        probs = self.model.predict_proba(X)[0]
        order = probs.argsort()[::-1]
        best_idx = order[0]
        label = self.label_enc.inverse_transform([best_idx])[0]
        finish, binder = label.split("|")
        confidence = round(float(probs[best_idx]) * 100)

        result = {
            "finish": finish,
            "binder": binder,
            "confidence": confidence,
            "lightness_bucket": bucket,
            "alternative": None,
        }

        # Recommandation alternative : utile quand le modèle hésite entre deux options
        # plutôt que d'afficher une seule réponse qui masquerait cette incertitude.
        if len(order) > 1:
            alt_idx = order[1]
            alt_confidence = round(float(probs[alt_idx]) * 100)
            if alt_confidence >= 15:
                alt_label = self.label_enc.inverse_transform([alt_idx])[0]
                alt_finish, alt_binder = alt_label.split("|")
                result["alternative"] = {
                    "finish": alt_finish, "binder": alt_binder, "confidence": alt_confidence,
                }
        return result


# single shared instance, trained once at import time
recommender = KronocolorRecommender()
