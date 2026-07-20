"""
KRONOCOLOR — version Python (Flask)
Maison de négoce en pigments et peintures — boutique, grossiste, consultant, admin.

Lancer :
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...      (optionnel, sinon le diagnostic/chatbot IA sont désactivés)
    python app.py
Puis ouvrir http://127.0.0.1:5000
"""
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    g, jsonify, send_from_directory
)
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from ml_model import recommender as ml_recommender, lightness_bucket as ml_lightness_bucket
from language import LANGUAGES, LANGUAGE_LABELS, RTL_LANGUAGES, translate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kronocolor.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _upload_dir():
    # Comme _backup_dir() : dérivé de DB_PATH plutôt que figé, pour que les
    # tests (qui monkeypatchent DB_PATH vers une base temporaire) écrivent les
    # fichiers uploadés à côté de cette base temporaire au lieu de polluer le
    # static/uploads/ du vrai projet.
    if os.path.dirname(DB_PATH) == BASE_DIR:
        return UPLOAD_DIR
    upload_dir = os.path.join(os.path.dirname(DB_PATH), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir
BACKUP_MAX_KEEP = 10
BACKUP_MIN_INTERVAL_HOURS = 24

ADMIN_CODE = "kronocolor-admin"
CONSULTANT_CODE = "kronocolor-conseil"

# Paiement par carte réel (Stripe, mode test) si configuré — sinon paiement simulé
# comme le reste de la démo (aucune carte réelle n'est jamais débitée en mode test).
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")

CONTACT = {
    "phone": "+212 522 00 00 00",
    "whatsapp": "212522000000",  # format wa.me : indicatif + numéro, sans "+" ni espaces
    "email": "contact@kronocolor.ma",
    "address": "Rés. Galis, Imm 9, Rue El Araar, Casablanca, Maroc",
    "maps_url": "https://www.google.com/maps/search/?api=1&query=Rue+El+Araar+Res+Galis+Casablanca",
}

SHIPPING_ZONES = [
    {"id": "casa", "label": "Casablanca", "fee": 60, "days": "24–48h"},
    {"id": "national", "label": "Autres villes du Maroc", "fee": 120, "days": "3 à 5 jours"},
    {"id": "international", "label": "International", "fee": 450, "days": "7 à 14 jours"},
]
ZONES_BY_ID = {z["id"]: z for z in SHIPPING_ZONES}

FAQ = [
    (["livraison", "delai", "délai", "expedition", "expédition"],
     "Livraison sous 24–48h à Casablanca, 3 à 5 jours pour les autres villes du Maroc, "
     "7 à 14 jours à l'international. Frais offerts dès 800 MAD à Casablanca."),
    (["paiement", "payer", "carte"],
     "Le paiement se fait en ligne au moment de la commande, dans le panier ou depuis la boutique. "
     "C'est confirmé instantanément (paiement simulé en démo)."),
    (["stock", "disponible", "dispo"],
     "La disponibilité est indiquée sur chaque produit dans la boutique."),
    (["retour", "remboursement", "rembourser"],
     f"Pour un retour, contactez notre consultant ou appelez le {CONTACT['phone']}."),
    (["grossiste", "quantite", "quantité", "bulk"],
     "Pour les grandes quantités, connectez-vous avec le profil Grossiste : tarifs dégressifs et devis rapide."),
]

CATEGORIES = ["Murs", "Bois", "Voiture & Carrosserie", "Papier peint", "Outils de peinture"]
PAINT_CATEGORIES = ["Murs", "Bois", "Voiture & Carrosserie"]
LOW_STOCK_THRESHOLD = 20

# Rendement approximatif par catégorie, pour le calculateur de quantité de la
# fiche produit (m² couverts par unité vendue, pour 1 couche) et nombre de
# couches conseillé. Valeurs indicatives standard du secteur peinture/déco.
COVERAGE_M2_PER_UNIT = {
    "Murs": {"m2_per_unit": 10, "coats": 2, "waste": 1.0},
    "Bois": {"m2_per_unit": 12, "coats": 2, "waste": 1.0},
    "Voiture & Carrosserie": {"m2_per_unit": 5, "coats": 2, "waste": 1.0},
    "Papier peint": {"m2_per_unit": 5, "coats": 1, "waste": 1.1},
}
DEFAULT_PROMO_CODES = [
    ("BIENVENUE10", 10),
    ("GROS20", 20),
]

# Avis de démo affichés tant qu'aucun avis réel n'existe encore (table vide) —
# mis en avant sur l'accueil pour donner un aperçu réaliste de la fonctionnalité.
DEFAULT_REVIEWS = [
    ("p4", "Amine R.", 5, "Utilisée sur toute la façade de notre riad à Marrakech, la teinte a parfaitement "
                          "résisté à la saison des pluies. Rendu mat superbe, on recommande."),
    ("p3", "Salma B.", 5, "Exactement la couleur du nuancier, aucune mauvaise surprise à l'application. "
                          "Le conseil sur la finition satinée était parfait pour ma cuisine."),
    ("p6", "Youssef K.", 5, "Repeint ma voiture de collection avec cette laque, brillance incroyable et "
                            "tenue dans le temps malgré le soleil de Casablanca."),
    ("p2", "Karim T.", 4, "Qualité professionnelle, j'utilise cette laque pour tous mes chantiers de "
                          "menuiserie haut de gamme depuis un an."),
    ("w1", "Nadia El F.", 5, "Le motif est encore plus beau en vrai que sur les photos. Pose facile, "
                             "très satisfaite du rendu dans le salon."),
]

# Taux de change fixes pour la démo (pas d'API de change en temps réel).
# Base = MAD, tous les prix sont stockés en MAD en base de données.
CURRENCY_RATES = {"MAD": 1.0, "EUR": 0.092, "USD": 0.10}
CURRENCY_SYMBOLS = {"MAD": "MAD", "EUR": "€", "USD": "$"}

# Frais de douane/taxes à l'importation, appliqués sur les commandes livrées
# hors du Maroc (taux forfaitaires documentés pour la démo — vente export).
CUSTOMS_RATES = {
    "MA": {"label": "Maroc", "rate": 0.0},
    "FR": {"label": "France", "rate": 0.20},
    "ES": {"label": "Espagne", "rate": 0.21},
    "US": {"label": "États-Unis", "rate": 0.05},
    "AE": {"label": "Émirats arabes unis", "rate": 0.05},
    "OTHER": {"label": "Autre pays", "rate": 0.15},
}


def money_filter(amount):
    """Convertit un montant stocké en MAD vers la devise choisie en session (taux fixes de démo)."""
    currency = session.get("currency", "MAD")
    rate = CURRENCY_RATES.get(currency, 1.0)
    converted = (amount or 0) * rate
    if currency == "MAD":
        return f"{converted:,.0f} MAD".replace(",", " ")
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{converted:,.2f} {symbol}".replace(",", " ")

DEFAULT_PRODUCTS = [
    dict(id="p1", name="Oxyde de Merzouga", sub="peinture teinte terre ferrique, ocre rouge", category="Murs",
         hex="#9b3a2b", image=None, unit="L", price=420, wholesale_price=310, min_wholesale=25, stock=180,
         finish="Mat", binder="Silicate"),
    dict(id="p2", name="Or de Fès", sub="laque métallique pour boiseries", category="Bois",
         hex="#b08d3e", image=None, unit="L", price=690, wholesale_price=520, min_wholesale=15, stock=60,
         finish="Laqué", binder="Glycéro"),
    dict(id="p3", name="Vert Atlantique", sub="peinture malachite, finition satinée", category="Murs",
         hex="#3b5d56", image=None, unit="L", price=510, wholesale_price=380, min_wholesale=20, stock=95,
         finish="Satiné", binder="Acrylique"),
    dict(id="p4", name="Façade Extérieure Mat", sub="peinture prête, base acrylique", category="Murs",
         hex="#d8cdbb", image=None, unit="L", price=145, wholesale_price=95, min_wholesale=50, stock=300,
         finish="Mat", binder="Acrylique"),
    dict(id="p5", name="Vernis Teck Doré", sub="vernis bois, protection extérieure", category="Bois",
         hex="#8b5a2b", image=None, unit="L", price=350, wholesale_price=260, min_wholesale=15, stock=110,
         finish="Satiné", binder="Glycéro marine"),
    dict(id="p6", name="Laque Carrosserie Rouge Rallye", sub="laque auto, haute brillance", category="Voiture & Carrosserie",
         hex="#b3261e", image=None, unit="L", price=780, wholesale_price=610, min_wholesale=10, stock=40,
         finish="Laqué", binder="Polyuréthane"),
    dict(id="p7", name="Laque Carrosserie Noir Onyx", sub="laque auto, finition miroir", category="Voiture & Carrosserie",
         hex="#1b1b1e", image=None, unit="L", price=820, wholesale_price=640, min_wholesale=10, stock=35,
         finish="Laqué", binder="Polyuréthane"),
    dict(id="w1", name="Papier peint Indigo Chefchaouen", sub="motif tissé, rouleau 10m", category="Papier peint",
         hex="#2c2440", image=None, unit="rouleau", price=280, wholesale_price=210, min_wholesale=10, stock=70,
         finish=None, binder=None),
    dict(id="w2", name="Papier peint Ambre du Souk", sub="texture lin, rouleau 10m", category="Papier peint",
         hex="#c98a5e", image=None, unit="rouleau", price=260, wholesale_price=195, min_wholesale=10, stock=90,
         finish=None, binder=None),
    dict(id="t1", name="Kit de pinceaux professionnels", sub="set de 5, poils synthétiques", category="Outils de peinture",
         hex="#8a7a63", image=None, unit="kit", price=180, wholesale_price=130, min_wholesale=10, stock=120,
         finish=None, binder=None),
    dict(id="t2", name="Rouleau + bac de peinture", sub="rouleau laine 25cm + bac", category="Outils de peinture",
         hex="#b8ada0", image=None, unit="kit", price=95, wholesale_price=70, min_wholesale=15, stock=150,
         finish=None, binder=None),
    dict(id="p8", name="Safran de Taliouine", sub="peinture teinte safran, ocre doré lumineux", category="Murs",
         hex="#dfb92a", image=None, unit="L", price=380, wholesale_price=280, min_wholesale=20, stock=140,
         finish="Mat", binder="Acrylique"),
    dict(id="p9", name="Lavande de l'Atlas", sub="peinture teinte lavande, finition satinée", category="Murs",
         hex="#8a4fae", image=None, unit="L", price=420, wholesale_price=310, min_wholesale=20, stock=90,
         finish="Satiné", binder="Acrylique"),
    dict(id="p10", name="Rose de Kelaat M'Gouna", sub="peinture rose poudré, vallée des roses", category="Murs",
         hex="#b8547a", image=None, unit="L", price=440, wholesale_price=325, min_wholesale=20, stock=85,
         finish="Satiné", binder="Acrylique"),
    dict(id="p11", name="Bleu Majorelle", sub="peinture bleu profond, iconique jardins de Marrakech", category="Murs",
         hex="#1e5aa8", image=None, unit="L", price=460, wholesale_price=340, min_wholesale=20, stock=100,
         finish="Satiné", binder="Acrylique"),
    dict(id="p12", name="Vert Menthe Marocaine", sub="peinture vert menthe frais, finition mate", category="Murs",
         hex="#5f9b74", image=None, unit="L", price=400, wholesale_price=295, min_wholesale=20, stock=110,
         finish="Mat", binder="Acrylique"),
    dict(id="p13", name="Terre de Marrakech", sub="lasure terre cuite, protection bois extérieur", category="Bois",
         hex="#7a4a2e", image=None, unit="L", price=360, wholesale_price=265, min_wholesale=15, stock=95,
         finish="Satiné", binder="Glycéro"),
    dict(id="p14", name="Blanc Chaux d'Essaouira", sub="peinture blanc chaulé, façade traditionnelle", category="Murs",
         hex="#e8e4d8", image=None, unit="L", price=165, wholesale_price=110, min_wholesale=50, stock=220,
         finish="Mat", binder="Chaux"),
    dict(id="p15", name="Gris Pierre d'Agadir", sub="peinture gris pierre naturel, finition mate", category="Murs",
         hex="#8d8d85", image=None, unit="L", price=395, wholesale_price=290, min_wholesale=20, stock=105,
         finish="Mat", binder="Silicate"),
    dict(id="p16", name="Noir Ébène du Rif", sub="vernis noir ébène, bois massif haut de gamme", category="Bois",
         hex="#1a1a1a", image=None, unit="L", price=520, wholesale_price=390, min_wholesale=15, stock=55,
         finish="Laqué", binder="Glycéro"),
    dict(id="p17", name="Ocre du Sahara", sub="peinture ocre désertique, finition satinée", category="Murs",
         hex="#c9772e", image=None, unit="L", price=410, wholesale_price=305, min_wholesale=20, stock=130,
         finish="Satiné", binder="Silicate"),
]

SURFACES = ["Mur extérieur", "Mur intérieur", "Bois", "Métal", "Béton brut", "Carrosserie auto", "Plastique", "Plâtre"]
CLIMATES = [
    {"id": "chaud_sec", "label": "Chaud & sec"},
    {"id": "froid", "label": "Froid"},
    {"id": "humide", "label": "Humide"},
    {"id": "vent", "label": "Exposé au vent"},

]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kronocolor-dev-secret-change-me")
csrf = CSRFProtect(app)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT, sub TEXT, category TEXT, hex TEXT, image TEXT,
            unit TEXT, price REAL, wholesale_price REAL, min_wholesale INTEGER, stock INTEGER
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT, customer_email TEXT, customer_phone TEXT,
            customer_address TEXT, customer_city TEXT,
            items_json TEXT, total REAL,
            zone_id TEXT, shipping_fee REAL, payment_method TEXT,
            status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS wholesale (
            id TEXT PRIMARY KEY,
            company TEXT, contact TEXT, email TEXT,
            product_name TEXT, qty INTEGER, est_total REAL,
            status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_key TEXT, text TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT, author TEXT, rating INTEGER, message TEXT, created_at TEXT,
            photo TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL, email_verified INTEGER NOT NULL DEFAULT 0,
            verification_token TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS stock_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT, product_name TEXT, stock_at_alert INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            percent_off REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS training_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surface TEXT, climate TEXT, lightness_bucket TEXT,
            finish TEXT, binder TEXT, order_id TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_email TEXT, subject TEXT, body TEXT, order_id TEXT, created_at TEXT
        );
        """
    )
    try:
        db.execute("ALTER TABLE products ADD COLUMN old_price REAL")
    except sqlite3.OperationalError:
        pass  # column already exists
    for column_sql in ("ALTER TABLE orders ADD COLUMN promo_code TEXT",
                        "ALTER TABLE orders ADD COLUMN discount REAL DEFAULT 0",
                        "ALTER TABLE orders ADD COLUMN delivery_country TEXT DEFAULT 'MA'",
                        "ALTER TABLE orders ADD COLUMN customs_fee REAL DEFAULT 0",
                        "ALTER TABLE products ADD COLUMN finish TEXT",
                        "ALTER TABLE products ADD COLUMN binder TEXT",
                        "ALTER TABLE reviews ADD COLUMN photo TEXT"):
        try:
            db.execute(column_sql)
        except sqlite3.OperationalError:
            pass  # column already exists
    count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        for p in DEFAULT_PRODUCTS:
            db.execute(
                "INSERT INTO products (id,name,sub,category,hex,image,unit,price,wholesale_price,min_wholesale,stock,"
                "finish,binder) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (p["id"], p["name"], p["sub"], p["category"], p["hex"], p["image"], p["unit"],
                 p["price"], p["wholesale_price"], p["min_wholesale"], p["stock"], p["finish"], p["binder"]),
            )
        db.commit()
    promo_count = db.execute("SELECT COUNT(*) FROM promo_codes").fetchone()[0]
    if promo_count == 0:
        for code, percent_off in DEFAULT_PROMO_CODES:
            db.execute("INSERT INTO promo_codes (code,percent_off,active) VALUES (?,?,1)",
                       (code, percent_off))
        db.commit()
    review_count = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    if review_count == 0:
        for pid, author, rating, message in DEFAULT_REVIEWS:
            db.execute(
                "INSERT INTO reviews (product_id,author,rating,message,created_at) VALUES (?,?,?,?,?)",
                (pid, author, rating, message, datetime.utcnow().isoformat()),
            )
        db.commit()
    db.close()


def _backup_dir():
    # Dérivé de DB_PATH (pas d'une constante figée) pour que les tests, qui
    # monkeypatchent DB_PATH vers une base temporaire, sauvegardent aussi dans
    # un dossier temporaire au lieu de polluer le backups/ du vrai projet.
    return os.path.join(os.path.dirname(DB_PATH), "backups")


def backup_database():
    """Copie la base dans backups/ (via l'API de sauvegarde SQLite, donc
    sûre même pendant que l'app écrit dedans) et ne garde que les
    BACKUP_MAX_KEEP sauvegardes les plus récentes."""
    backup_dir = _backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backup_dir, f"kronocolor_{timestamp}.db")
    src = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(dest_path)
    with dest:
        src.backup(dest)
    src.close()
    dest.close()

    backups = sorted(
        f for f in os.listdir(backup_dir)
        if f.startswith("kronocolor_") and f.endswith(".db")
    )
    for old in backups[:-BACKUP_MAX_KEEP]:
        os.remove(os.path.join(backup_dir, old))

    return dest_path


def list_backups():
    backup_dir = _backup_dir()
    if not os.path.isdir(backup_dir):
        return []
    files = sorted(
        (f for f in os.listdir(backup_dir) if f.startswith("kronocolor_") and f.endswith(".db")),
        reverse=True,
    )
    result = []
    for f in files:
        path = os.path.join(backup_dir, f)
        size_kb = round(os.path.getsize(path) / 1024)
        result.append({"filename": f, "size_kb": size_kb})
    return result


def _maybe_auto_backup():
    """Déclenche une sauvegarde si aucune n'a été faite depuis BACKUP_MIN_INTERVAL_HOURS."""
    backups = list_backups()
    if not backups:
        backup_database()
        return
    latest = backups[0]["filename"]
    stamp = latest.replace("kronocolor_", "").replace(".db", "")
    try:
        last_time = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
    except ValueError:
        backup_database()
        return
    if datetime.utcnow() - last_time > timedelta(hours=BACKUP_MIN_INTERVAL_HOURS):
        backup_database()


def row_to_product(row):
    return dict(row)


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def attach_review_stats(db, products):
    stats = {
        r["product_id"]: {"avg": round(r["avg_rating"], 1), "count": r["cnt"]}
        for r in db.execute(
            "SELECT product_id, AVG(rating) AS avg_rating, COUNT(*) AS cnt FROM reviews GROUP BY product_id"
        ).fetchall()
    }
    for p in products:
        s = stats.get(p["id"], {"avg": 0, "count": 0})
        p["rating_avg"] = s["avg"]
        p["rating_count"] = s["count"]
    return products


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def current_user():
    return session.get("user")


def login_required(roles=None):
    def wrapper(fn):
        def inner(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if roles and user["role"] not in roles:
                flash("Accès non autorisé pour ce rôle.")
                return redirect(url_for("home_for_role", role=user["role"]))
            return fn(*args, **kwargs)
        inner.__name__ = fn.__name__
        return inner
    return wrapper


def home_for_role(role):
    return {
        "client": "client_home",
        "wholesale": "wholesale_view",
        "consultant": "consultant_list",
        "admin": "admin_stats",
    }.get(role, "login")


app.jinja_env.filters["money"] = money_filter


def current_lang():
    return session.get("lang", "fr")


@app.context_processor
def inject_globals():
    lang = current_lang()
    return dict(CONTACT=CONTACT, user=current_user(), NAV_CATEGORIES=CATEGORIES,
                current_currency=session.get("currency", "MAD"), currency_rates=CURRENCY_RATES,
                currency_symbols=CURRENCY_SYMBOLS,
                lang=lang, dir=("rtl" if lang in RTL_LANGUAGES else "ltr"),
                languages=LANGUAGES, language_labels=LANGUAGE_LABELS,
                t=lambda key: translate(key, lang),
                colorblind_mode=session.get("colorblind_mode", False))


@app.route("/accessibility/colorblind-mode", methods=["GET", "POST"])
def toggle_colorblind_mode():
    session["colorblind_mode"] = not session.get("colorblind_mode", False)
    return redirect(request.referrer or url_for("index"))


@app.route("/currency/<code>", methods=["POST"])
def set_currency(code):
    if code in CURRENCY_RATES:
        session["currency"] = code
    return redirect(request.referrer or url_for("index"))


@app.route("/lang/<code>", methods=["POST"])
def set_lang(code):
    if code in LANGUAGES:
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return redirect(url_for(home_for_role(user["role"])))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "client")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Merci de renseigner un email et un mot de passe.")
            return render_template("login.html", roles=ROLES)

        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if not row or not check_password_hash(row["password_hash"], password):
            flash("Email ou mot de passe incorrect.")
            return render_template("login.html", roles=ROLES)

        if row["role"] != role:
            role_label = next((r["label"] for r in ROLES if r["id"] == row["role"]), row["role"])
            flash(f"Ce compte est enregistré comme « {role_label} », pas comme le rôle sélectionné.")
            return render_template("login.html", roles=ROLES)

        if not row["email_verified"]:
            flash("Merci de vérifier votre adresse email avant de vous connecter "
                  "(lien de confirmation envoyé à l'inscription).")
            return render_template("login.html", roles=ROLES, unverified_email=email)

        session["user"] = {"name": row["name"] or email.split("@")[0], "email": email, "role": row["role"]}
        session["cart"] = session.get("cart", {})
        session["favorites"] = session.get("favorites", [])
        return redirect(url_for(home_for_role(row["role"])))

    return render_template("login.html", roles=ROLES)


ROLES = [
    {"id": "client", "label": "Client", "needs_code": False},
    {"id": "wholesale", "label": "Grossiste", "needs_code": False},
    {"id": "consultant", "label": "Consultant", "needs_code": True},
    {"id": "admin", "label": "Admin", "needs_code": True},
]


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = request.form.get("role", "client")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        code = request.form.get("code", "")

        if not name or not email or not password:
            flash("Merci de renseigner votre nom, votre email et un mot de passe.")
            return render_template("register.html", roles=ROLES)
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.")
            return render_template("register.html", roles=ROLES)
        if password != confirm:
            flash("Les deux mots de passe ne correspondent pas.")
            return render_template("register.html", roles=ROLES)
        if role == "admin" and code != ADMIN_CODE:
            flash("Code d'invitation invalide pour le rôle Admin.")
            return render_template("register.html", roles=ROLES)
        if role == "consultant" and code != CONSULTANT_CODE:
            flash("Code d'invitation invalide pour le rôle Consultant.")
            return render_template("register.html", roles=ROLES)

        db = get_db()
        exists = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if exists:
            flash("Un compte existe déjà avec cet email.")
            return render_template("register.html", roles=ROLES)

        token = secrets.token_urlsafe(24)
        db.execute(
            "INSERT INTO users (name,email,password_hash,role,email_verified,verification_token,created_at) "
            "VALUES (?,?,?,?,0,?,?)",
            (name, email, generate_password_hash(password), role, token, datetime.utcnow().isoformat()),
        )
        db.commit()
        verify_link = url_for("verify_email", token=token, _external=True)
        return render_template("register_done.html", email=email, verify_link=verify_link)

    return render_template("register.html", roles=ROLES)


@app.route("/verify-email/<token>")
def verify_email(token):
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE verification_token=?", (token,)).fetchone()
    if not row:
        flash("Lien de vérification invalide ou déjà utilisé.")
        return redirect(url_for("login"))
    db.execute("UPDATE users SET email_verified=1, verification_token=NULL WHERE id=?", (row["id"],))
    db.commit()
    flash("Email vérifié avec succès, vous pouvez vous connecter.")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Client — home
# ---------------------------------------------------------------------------
@app.route("/client")
@login_required(["client"])
def client_home():
    db = get_db()
    products = attach_review_stats(db, [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()])
    best_sellers = products[:4]
    testimonials = [dict(r) for r in db.execute(
        "SELECT reviews.author, reviews.rating, reviews.message, reviews.photo, reviews.created_at, "
        "products.name AS product_name, products.hex AS product_hex "
        "FROM reviews JOIN products ON products.id = reviews.product_id "
        "WHERE reviews.rating >= 4 AND length(reviews.message) > 8 "
        "ORDER BY reviews.rating DESC, reviews.created_at DESC LIMIT 6"
    ).fetchall()]
    return render_template("client/home.html", products=products, best_sellers=best_sellers,
                            favorites=session.get("favorites", []), compare=session.get("compare", []),
                            testimonials=testimonials)


# ---------------------------------------------------------------------------
# Client — shop / cart
# ---------------------------------------------------------------------------
def cart_items(db):
    cart = session.get("cart", {})
    items = []
    for pid, qty in cart.items():
        row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if row:
            p = row_to_product(row)
            qty = min(qty, p["stock"])
            items.append({**p, "qty": qty})
    return items


SAMPLE_PRICE = 35
SAMPLE_UNIT = "éch. 50ml"
SAMPLE_MAX_IN_CART = 3


def sample_cart_items():
    """Échantillons (pots d'essai 50ml) en attente dans le panier — stockés
    directement en session (pas en base) car ils peuvent représenter un
    mélange personnalisé du diagnostic, sans product_id existant."""
    return session.get("cart_samples", [])


COLOR_FAMILIES = ["rouge", "orange", "jaune", "vert", "bleu", "violet", "rose", "brun", "noir", "gris", "blanc"]
# Variantes de genre/nombre pour la reconnaissance par le chatbot (ex. "verte", "bleus", "blanche").
COLOR_FAMILY_VARIANTS = {
    "rouge": ["rouge", "rouges"],
    "orange": ["orange", "oranges"],
    "jaune": ["jaune", "jaunes"],
    "vert": ["vert", "verte", "verts", "vertes"],
    "bleu": ["bleu", "bleue", "bleus", "bleues"],
    "violet": ["violet", "violette", "violets", "violettes"],
    "rose": ["rose", "roses"],
    "brun": ["brun", "brune", "bruns", "brunes"],
    "noir": ["noir", "noire", "noirs", "noires"],
    "gris": ["gris", "grise", "grises"],
    "blanc": ["blanc", "blanche", "blancs", "blanches"],
}
COLOR_SWATCHES = {
    "rouge": "#b3261e", "orange": "#c98a5e", "jaune": "#d8b34a", "vert": "#3b5d56",
    "bleu": "#2c2440", "violet": "#6b3fa0", "rose": "#c0567a", "brun": "#8b5a2b",
    "noir": "#1b1b1e", "gris": "#8a7a63", "blanc": "#d8cdbb",
}


def _color_family(hex_color):
    """Regroupe une couleur hexadécimale en famille (rouge, bleu, brun...) pour le filtre boutique."""
    import colorsys
    hx = (hex_color or "").lstrip("#")
    if len(hx) != 6:
        return "gris"
    r, g, b = int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255, int(hx[4:6], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    deg = h * 360
    if l >= 0.75:
        return "blanc"
    if l <= 0.15:
        return "noir"
    if s <= 0.18:
        return "gris"
    if deg < 20 or deg >= 345:
        return "rouge"
    if deg < 45:
        return "brun" if l < 0.45 else "orange"
    if deg < 65:
        return "jaune"
    if deg < 190:
        return "vert"
    if deg < 270:
        return "bleu"
    if deg < 320:
        return "violet"
    return "rose"


app.jinja_env.filters["color_family"] = _color_family


@app.route("/client/shop")
@login_required(["client"])
def shop():
    db = get_db()
    active_category = request.args.get("cat")
    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "")
    price_range = request.args.get("price_range", "")
    color = request.args.get("color", "")
    in_stock_only = request.args.get("in_stock") == "1"
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if active_category:
        sql += " AND category=?"
        params.append(active_category)
    if query:
        sql += " AND (name LIKE ? OR sub LIKE ?)"
        like = f"%{query}%"
        params += [like, like]
    if price_range == "under_200":
        sql += " AND price < 200"
    elif price_range == "200_500":
        sql += " AND price >= 200 AND price <= 500"
    elif price_range == "over_500":
        sql += " AND price > 500"
    if in_stock_only:
        sql += " AND stock > 0"
    if sort == "price_asc":
        sql += " ORDER BY price ASC"
    elif sort == "price_desc":
        sql += " ORDER BY price DESC"
    products = attach_review_stats(db, [row_to_product(r) for r in db.execute(sql, params).fetchall()])
    for p in products:
        p["color_family"] = _color_family(p.get("hex"))
    if color:
        products = [p for p in products if p["color_family"] == color]

    viewed_ids = session.get("recently_viewed", [])
    recently_viewed = []
    if viewed_ids:
        placeholders = ",".join("?" * len(viewed_ids))
        rows = db.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", viewed_ids).fetchall()
        by_id = {r["id"]: row_to_product(r) for r in rows}
        recently_viewed = attach_review_stats(db, [by_id[i] for i in viewed_ids if i in by_id])

    return render_template("client/shop.html", products=products,
                            favorites=session.get("favorites", []), categories=CATEGORIES,
                            active_category=active_category, query=query, sort=sort,
                            price_range=price_range, product_count=len(products),
                            color=color, color_families=COLOR_FAMILIES, color_swatches=COLOR_SWATCHES,
                            in_stock_only=in_stock_only, recently_viewed=recently_viewed,
                            compare=session.get("compare", []))


@app.route("/client/nuancier")
@login_required(["client"])
def color_catalog():
    db = get_db()
    color = request.args.get("color", "")
    products = [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()]
    for p in products:
        p["color_family"] = _color_family(p.get("hex"))
    if color:
        products = [p for p in products if p["color_family"] == color]
    return render_template("client/nuancier.html", products=products, categories=CATEGORIES,
                            color=color, color_families=COLOR_FAMILIES, color_swatches=COLOR_SWATCHES)


RECENTLY_VIEWED_MAX = 8
COMPARE_MAX = 3


def _track_recently_viewed(pid):
    viewed = session.get("recently_viewed", [])
    viewed = [v for v in viewed if v != pid]
    viewed.insert(0, pid)
    session["recently_viewed"] = viewed[:RECENTLY_VIEWED_MAX]


@app.route("/client/product/<pid>")
@login_required(["client"])
def product_detail(pid):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not row:
        flash("Produit introuvable.")
        return redirect(url_for("shop"))
    product = attach_review_stats(db, [row_to_product(row)])[0]
    related = attach_review_stats(db, [row_to_product(r) for r in db.execute(
        "SELECT * FROM products WHERE category=? AND id<>? LIMIT 4", (product["category"], pid)
    ).fetchall()])
    reviews = [dict(r) for r in db.execute(
        "SELECT * FROM reviews WHERE product_id=? ORDER BY created_at DESC", (pid,)
    ).fetchall()]
    coverage = COVERAGE_M2_PER_UNIT.get(product["category"])
    _track_recently_viewed(pid)
    return render_template("client/product.html", p=product, related=related, reviews=reviews,
                            favorites=session.get("favorites", []), coverage=coverage,
                            compare=session.get("compare", []),
                            can_sample=product["category"] in PAINT_CATEGORIES,
                            sample_price=SAMPLE_PRICE)


@app.route("/client/product/<pid>/review", methods=["POST"])
@login_required(["client"])
def add_review(pid):
    db = get_db()
    row = db.execute("SELECT id FROM products WHERE id=?", (pid,)).fetchone()
    if not row:
        flash("Produit introuvable.")
        return redirect(url_for("shop"))

    try:
        rating = int(request.form.get("rating", 5))
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))
    message = request.form.get("message", "").strip()

    if not message:
        flash("Merci d'ajouter un message avec votre avis.")
        return redirect(url_for("product_detail", pid=pid))

    photo_path = None
    file = request.files.get("photo")
    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
            filename = secure_filename(f"review_{pid}_{new_id('R')}.{ext}")
            file.save(os.path.join(_upload_dir(), filename))
            photo_path = f"uploads/{filename}"
        else:
            flash("Photo ignorée : format non supporté (utilisez JPG, PNG, GIF ou WEBP).")

    user = current_user()
    db.execute(
        "INSERT INTO reviews (product_id, author, rating, message, created_at, photo) VALUES (?,?,?,?,?,?)",
        (pid, user["name"], rating, message, datetime.utcnow().isoformat(), photo_path),
    )
    db.commit()
    flash("Merci pour votre avis !")
    return redirect(url_for("product_detail", pid=pid))


@app.route("/client/cart")
@login_required(["client"])
def cart_view():
    db = get_db()
    items = cart_items(db)
    samples = sample_cart_items()
    subtotal = sum(i["qty"] * i["price"] for i in items) + sum(s["qty"] * s["price"] for s in samples)
    return render_template("client/cart.html", cart=items, samples=samples, subtotal=subtotal)


@app.route("/client/cart/add/<pid>", methods=["POST"])
@login_required(["client"])
def cart_add(pid):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if row:
        p = row_to_product(row)
        cart = session.get("cart", {})
        next_qty = cart.get(pid, 0) + 1
        if next_qty > p["stock"]:
            flash(f"Stock maximum atteint pour {p['name']} ({p['stock']} {p['unit']}).")
        else:
            cart[pid] = next_qty
            session["cart"] = cart
    return redirect(request.referrer or url_for("shop"))


def _add_sample_to_cart(name, hex_color):
    samples = session.get("cart_samples", [])
    if len(samples) >= SAMPLE_MAX_IN_CART:
        flash(f"Vous pouvez commander au maximum {SAMPLE_MAX_IN_CART} échantillons à la fois.")
        return
    samples.append({
        "id": new_id("SAMPLE"),
        "name": f"{name} — Échantillon 50ml",
        "hex": hex_color,
        "price": SAMPLE_PRICE,
        "unit": SAMPLE_UNIT,
        "qty": 1,
    })
    session["cart_samples"] = samples
    flash(f"Échantillon 50ml ajouté au panier ({SAMPLE_PRICE} MAD).")


@app.route("/client/product/<pid>/sample", methods=["POST"])
@login_required(["client"])
def add_product_sample(pid):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not row:
        flash("Produit introuvable.")
        return redirect(url_for("shop"))
    p = row_to_product(row)
    _add_sample_to_cart(p["name"], p["hex"])
    return redirect(request.referrer or url_for("product_detail", pid=pid))


@app.route("/client/diagnostic/sample", methods=["POST"])
@login_required(["client"])
def add_diagnostic_sample():
    hex_color = request.form.get("hex_color", "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_color or ""):
        flash("Couleur de mélange invalide.")
        return redirect(url_for("diagnostic"))
    _add_sample_to_cart("Mélange personnalisé", hex_color)
    return redirect(url_for("diagnostic"))


@app.route("/client/cart/samples/remove/<sample_id>", methods=["POST"])
@login_required(["client"])
def remove_sample(sample_id):
    samples = session.get("cart_samples", [])
    session["cart_samples"] = [s for s in samples if s["id"] != sample_id]
    return redirect(request.referrer or url_for("cart_view"))


@app.route("/client/cart/update/<pid>", methods=["POST"])
@login_required(["client"])
def cart_update(pid):
    db = get_db()
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1
    row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    cart = session.get("cart", {})
    if row and qty > 0:
        p = row_to_product(row)
        qty = min(qty, p["stock"])
        cart[pid] = qty
    elif pid in cart:
        del cart[pid]
    session["cart"] = cart
    return redirect(url_for("cart_view"))


@app.route("/client/cart/remove/<pid>", methods=["POST"])
@login_required(["client"])
def cart_remove(pid):
    cart = session.get("cart", {})
    cart.pop(pid, None)
    session["cart"] = cart
    return redirect(url_for("cart_view"))


@app.route("/client/cart/clear", methods=["POST"])
@login_required(["client"])
def cart_clear():
    session["cart"] = {}
    return redirect(url_for("cart_view"))


def _active_promo(db):
    """Renvoie le code promo actif en session (dict code/percent_off) ou None."""
    promo = session.get("promo")
    if not promo:
        return None
    row = db.execute(
        "SELECT code, percent_off FROM promo_codes WHERE code=? AND active=1", (promo["code"],)
    ).fetchone()
    return dict(row) if row else None


@app.route("/client/checkout/promo", methods=["POST"])
@login_required(["client"])
def apply_promo():
    db = get_db()
    code = request.form.get("promo_code", "").strip().upper()
    row = db.execute(
        "SELECT code, percent_off FROM promo_codes WHERE code=? AND active=1", (code,)
    ).fetchone()
    if row:
        session["promo"] = {"code": row["code"], "percent_off": row["percent_off"]}
        flash(f"Code promo « {row['code']} » appliqué : -{row['percent_off']:.0f}%.")
    else:
        flash("Code promo invalide ou expiré.")
    return redirect(url_for("checkout"))


@app.route("/client/checkout/promo/remove", methods=["POST"])
@login_required(["client"])
def remove_promo():
    session.pop("promo", None)
    return redirect(url_for("checkout"))


@app.route("/client/checkout", methods=["GET", "POST"])
@login_required(["client"])
def checkout():
    db = get_db()
    items = cart_items(db)
    samples = sample_cart_items()
    if not items and not samples:
        return redirect(url_for("shop"))
    all_items = items + samples
    subtotal = sum(i["qty"] * i["price"] for i in all_items)
    promo = _active_promo(db)
    discount = round(subtotal * promo["percent_off"] / 100, 2) if promo else 0
    country = (request.form.get("country") if request.method == "POST" else request.args.get("country")) or "MA"
    customs = CUSTOMS_RATES.get(country, CUSTOMS_RATES["OTHER"])
    customs_fee = round((subtotal - discount) * customs["rate"], 2)

    if request.method == "POST":
        zone_id = request.form.get("zone", "casa")
        zone = ZONES_BY_ID.get(zone_id, ZONES_BY_ID["casa"])
        fee = 0 if (subtotal > 800 and zone_id == "casa") else zone["fee"]
        user = current_user()
        payment_method = request.form.get("payment_method", "card")
        order_data = {
            "id": new_id("KC"),
            "name": request.form.get("name", user["name"]),
            "email": request.form.get("email", user["email"]),
            "phone": request.form.get("phone", ""),
            "address": request.form.get("address", ""),
            "city": request.form.get("city", ""),
            "items_json": _items_to_json(all_items),
            "total": subtotal - discount + customs_fee + fee,
            "zone_id": zone_id,
            "shipping_fee": fee,
            "payment_method": payment_method,
            "promo_code": promo["code"] if promo else None,
            "discount": discount,
            "country": country,
            "customs_fee": customs_fee,
        }

        if payment_method == "card" and STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY:
            try:
                checkout_session = _create_stripe_checkout_session(order_data)
            except Exception as e:
                # Trace technique complète dans les logs serveur (utile pour diagnostiquer un
                # vrai souci Stripe/réseau) ; message court et non technique pour le client.
                print(f"[STRIPE ERROR] Échec de création de session pour la commande "
                      f"{order_data['id']} : {e}")
                flash("Le paiement par carte est temporairement indisponible. Réessayez dans "
                      "quelques instants, ou choisissez PayPal.")
                return redirect(url_for("checkout"))
            session["pending_order"] = order_data
            return render_template("client/checkout_payment.html", order_id=order_data["id"],
                                    client_secret=checkout_session.client_secret,
                                    stripe_publishable_key=STRIPE_PUBLISHABLE_KEY)

        _finalize_order(db, order_data, items)
        estimate = (datetime.utcnow() + timedelta(days=_max_days(zone["days"]))).strftime("%d %B %Y")
        return render_template("client/order_done.html", order_id=order_data["id"], zone=zone, estimate=estimate,
                                payment_method=payment_method, paid_via_stripe=False)

    user = current_user()
    return render_template("client/checkout.html", items=all_items, subtotal=subtotal, zones=SHIPPING_ZONES,
                            user=user, promo=promo, discount=discount, country=country,
                            customs=customs, customs_fee=customs_fee, customs_rates=CUSTOMS_RATES,
                            stripe_enabled=bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY))


def _finalize_order(db, order_data, items):
    """Insère la commande en base et déclenche tous les effets de bord d'une commande
    confirmée : décrément de stock, alerte stock bas, apprentissage ML, email de
    confirmation. Utilisé aussi bien par le paiement simulé (immédiat) que par le
    retour de paiement Stripe (après confirmation réelle du paiement par carte)."""
    db.execute(
        "INSERT INTO orders (id,customer_name,customer_email,customer_phone,customer_address,"
        "customer_city,items_json,total,zone_id,shipping_fee,payment_method,status,created_at,"
        "promo_code,discount,delivery_country,customs_fee) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            order_data["id"], order_data["name"], order_data["email"], order_data["phone"],
            order_data["address"], order_data["city"], order_data["items_json"], order_data["total"],
            order_data["zone_id"], order_data["shipping_fee"], order_data["payment_method"],
            "Confirmée", datetime.utcnow().isoformat(), order_data["promo_code"], order_data["discount"],
            order_data["country"], order_data["customs_fee"],
        ),
    )
    _decrement_stock_and_alert(db, items)
    _capture_training_samples(db, items, order_data["id"])
    _send_order_status_email(db, {
        "id": order_data["id"], "customer_email": order_data["email"],
        "customer_name": order_data["name"], "total": order_data["total"],
    }, "Confirmée")
    session.pop("promo", None)
    session.pop("quiz_context", None)
    db.commit()
    session["cart"] = {}
    session["cart_samples"] = []


def _create_stripe_checkout_session(order_data):
    """Session Stripe Checkout en mode "embedded" : le formulaire de carte s'affiche dans
    un iframe sécurisé directement sur notre page, sans redirection vers stripe.com."""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    amount_cents = max(50, int(round(order_data["total"] * 100)))
    return stripe.checkout.Session.create(
        ui_mode="embedded_page",
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mad",
                "product_data": {"name": f"Commande KRONOCOLOR {order_data['id']}"},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        customer_email=order_data["email"],
        return_url=url_for("stripe_checkout_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
    )


@app.route("/client/checkout/stripe/success")
@login_required(["client"])
def stripe_checkout_success():
    order_data = session.get("pending_order")
    session_id = request.args.get("session_id")
    if not order_data or not session_id:
        flash("Session de paiement introuvable.")
        return redirect(url_for("cart_view"))

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        flash("Impossible de vérifier le paiement Stripe.")
        return redirect(url_for("cart_view"))

    if checkout_session.payment_status != "paid":
        flash("Le paiement n'a pas été confirmé.")
        return redirect(url_for("cart_view"))

    db = get_db()
    items = cart_items(db)
    _finalize_order(db, order_data, items)
    session.pop("pending_order", None)
    zone = ZONES_BY_ID.get(order_data["zone_id"], ZONES_BY_ID["casa"])
    estimate = (datetime.utcnow() + timedelta(days=_max_days(zone["days"]))).strftime("%d %B %Y")
    return render_template("client/order_done.html", order_id=order_data["id"], zone=zone, estimate=estimate,
                            payment_method="card", paid_via_stripe=True)


@app.route("/client/checkout/stripe/cancel")
@login_required(["client"])
def stripe_checkout_cancel():
    session.pop("pending_order", None)
    flash("Paiement annulé — votre panier a été conservé.")
    return redirect(url_for("checkout"))


def _capture_training_samples(db, items, order_id):
    """Relie une commande réelle au contexte (surface/climat) exprimé lors du
    quiz conseil ou du diagnostic IA juste avant, et enregistre un échantillon
    d'entraînement réel pour chaque article "peinture" acheté (les articles
    sans finition/liant connus — outils, papier peint — sont ignorés).
    Déclenche ensuite un ré-entraînement du modèle ML sur les commandes réelles."""
    context = session.get("quiz_context")
    if not context:
        return
    new_samples = False
    for item in items:
        if not item.get("finish") or not item.get("binder"):
            continue
        bucket = ml_lightness_bucket(item["hex"])
        db.execute(
            "INSERT INTO training_samples (surface,climate,lightness_bucket,finish,binder,order_id,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (context["surface"], context["climate"], bucket, item["finish"], item["binder"],
             order_id, datetime.utcnow().isoformat()),
        )
        new_samples = True
    if new_samples:
        _retrain_ml_from_db(db)


def _retrain_ml_from_db(db):
    rows = db.execute(
        "SELECT surface, climate, lightness_bucket, finish, binder FROM training_samples"
    ).fetchall()
    samples = [(r["surface"], r["climate"], r["lightness_bucket"], r["finish"], r["binder"]) for r in rows]
    ml_recommender.retrain(samples)


def _send_email(db, to_email, subject, body, order_id=None):
    """Envoi d'email simulé — cohérent avec le reste de la démo (paiement,
    vérification de compte) : aucun SMTP n'est configuré, l'email est
    journalisé en base (visible dans l'admin) et sur la console au lieu
    d'être réellement délivré."""
    db.execute(
        "INSERT INTO sent_emails (to_email,subject,body,order_id,created_at) VALUES (?,?,?,?,?)",
        (to_email, subject, body, order_id, datetime.utcnow().isoformat()),
    )
    print(f"[EMAIL SIMULÉ] À: {to_email} | Objet: {subject}\n{body}")


ORDER_STATUS_EMAIL_TEMPLATES = {
    "Confirmée": (
        "Confirmation de votre commande {order_id}",
        "Bonjour {name},\n\nVotre commande {order_id} d'un montant de {total:.0f} MAD a bien été "
        "enregistrée. Nous vous tiendrons informé(e) de son expédition.\n\nL'équipe KRONOCOLOR",
    ),
    "Expédiée": (
        "Votre commande {order_id} a été expédiée",
        "Bonjour {name},\n\nVotre commande {order_id} vient d'être expédiée et est en route.\n\n"
        "L'équipe KRONOCOLOR",
    ),
    "Livrée": (
        "Votre commande {order_id} a été livrée",
        "Bonjour {name},\n\nVotre commande {order_id} a été livrée. Merci pour votre confiance, "
        "n'hésitez pas à laisser un avis sur les produits reçus.\n\nL'équipe KRONOCOLOR",
    ),
}


def _send_order_status_email(db, order, status):
    template = ORDER_STATUS_EMAIL_TEMPLATES.get(status)
    if not template or not order["customer_email"]:
        return
    subject_tpl, body_tpl = template
    subject = subject_tpl.format(order_id=order["id"])
    body = body_tpl.format(order_id=order["id"], name=order["customer_name"] or "",
                            total=order["total"] or 0)
    _send_email(db, order["customer_email"], subject, body, order_id=order["id"])


def _decrement_stock_and_alert(db, items):
    """Décrémente le stock après une commande et journalise une alerte
    (email simulé) la première fois qu'un produit passe sous le seuil critique."""
    for item in items:
        before = db.execute("SELECT stock FROM products WHERE id=?", (item["id"],)).fetchone()
        if not before:
            continue
        old_stock = before["stock"]
        new_stock = max(0, old_stock - item["qty"])
        db.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, item["id"]))
        if old_stock >= LOW_STOCK_THRESHOLD > new_stock:
            db.execute(
                "INSERT INTO stock_alerts (product_id,product_name,stock_at_alert,created_at) "
                "VALUES (?,?,?,?)",
                (item["id"], item["name"], new_stock, datetime.utcnow().isoformat()),
            )
            print(f"[ALERTE STOCK BAS - email simulé] {item['name']} (id={item['id']}) "
                  f"est passé sous le seuil de {LOW_STOCK_THRESHOLD} unités (reste: {new_stock}).")


def _items_to_json(items):
    import json
    return json.dumps([{"id": i["id"], "name": i["name"], "qty": i["qty"], "price": i["price"]} for i in items])


def _max_days(days_label):
    nums = re.findall(r"\d+", days_label)
    return int(nums[-1]) if nums else 3


@app.route("/client/orders")
@login_required(["client"])
def my_orders():
    db = get_db()
    user = current_user()
    rows = db.execute(
        "SELECT * FROM orders WHERE customer_email=? ORDER BY created_at DESC", (user["email"],)
    ).fetchall()
    import json
    orders = []
    for r in rows:
        o = dict(r)
        o["items"] = json.loads(o["items_json"])
        orders.append(o)
    return render_template("client/orders.html", orders=orders)


@app.route("/client/orders/<order_id>/invoice.pdf")
@login_required(["client"])
def order_invoice_pdf(order_id):
    import json
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    db = get_db()
    user = current_user()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND customer_email=?", (order_id, user["email"])
    ).fetchone()
    if not order:
        flash("Facture introuvable.")
        return redirect(url_for("my_orders"))

    items = json.loads(order["items_json"])
    subtotal = sum(i["qty"] * i["price"] for i in items)

    pdf = FPDF(format="A4", unit="mm")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "KRONOCOLOR", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Peintures & pigments d'exception - Maroc", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Facture - Commande {order['id']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date : {order['created_at'][:10]}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Statut : {order['status']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Facturé à :", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, order["customer_name"] or "", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, order["customer_email"] or "", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"{order['customer_address'] or ''}, {order['customer_city'] or ''}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    pdf.set_fill_color(230, 220, 200)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "Article", border=1, fill=True)
    pdf.cell(25, 8, "Qté", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Prix unit.", border=1, fill=True, align="R")
    pdf.cell(35, 8, "Total", border=1, fill=True, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    for it in items:
        pdf.cell(90, 8, it["name"][:45], border=1)
        pdf.cell(25, 8, str(it["qty"]), border=1, align="C")
        pdf.cell(35, 8, f"{it['price']:.2f} MAD", border=1, align="R")
        pdf.cell(35, 8, f"{it['price'] * it['qty']:.2f} MAD", border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(150, 7, "Sous-total", align="R")
    pdf.cell(35, 7, f"{subtotal:.2f} MAD", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if order["discount"]:
        label = f"Réduction ({order['promo_code']})" if order["promo_code"] else "Réduction"
        pdf.cell(150, 7, label, align="R")
        pdf.cell(35, 7, f"-{order['discount']:.2f} MAD", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if order["customs_fee"]:
        country_label = CUSTOMS_RATES.get(order["delivery_country"], CUSTOMS_RATES["OTHER"])["label"]
        pdf.cell(150, 7, f"Frais de douane ({country_label})", align="R")
        pdf.cell(35, 7, f"{order['customs_fee']:.2f} MAD", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(150, 7, "Frais de livraison", align="R")
    pdf.cell(35, 7, f"{order['shipping_fee']:.2f} MAD", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(150, 9, "Total payé", align="R")
    pdf.cell(35, 9, f"{order['total']:.2f} MAD", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, "Paiement simulé - démo, aucune carte réelle n'a été débitée. Facture générée automatiquement par KRONOCOLOR.")

    pdf_bytes = bytes(pdf.output())
    return app.response_class(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=facture_{order['id']}.pdf"},
    )


# ---------------------------------------------------------------------------
# Client — favorites
# ---------------------------------------------------------------------------
@app.route("/client/favorites")
@login_required(["client"])
def favorites_view():
    db = get_db()
    fav_ids = session.get("favorites", [])
    products = attach_review_stats(db, [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall() if r["id"] in fav_ids])
    return render_template("client/favorites.html", products=products, favorites=fav_ids,
                            compare=session.get("compare", []))


@app.route("/client/favorites/toggle/<pid>", methods=["POST"])
@login_required(["client"])
def toggle_favorite(pid):
    favs = session.get("favorites", [])
    if pid in favs:
        favs.remove(pid)
    else:
        favs.append(pid)
    session["favorites"] = favs
    return redirect(request.referrer or url_for("shop"))


@app.route("/client/compare/toggle/<pid>", methods=["POST"])
@login_required(["client"])
def toggle_compare(pid):
    compare = session.get("compare", [])
    if pid in compare:
        compare.remove(pid)
    elif len(compare) >= COMPARE_MAX:
        flash(f"Vous pouvez comparer au maximum {COMPARE_MAX} produits à la fois — retirez-en un d'abord.")
    else:
        compare.append(pid)
    session["compare"] = compare
    return redirect(request.referrer or url_for("shop"))


@app.route("/client/compare")
@login_required(["client"])
def compare_view():
    db = get_db()
    ids = session.get("compare", [])
    rows = [row_to_product(r) for r in db.execute("SELECT * FROM products WHERE id IN ({})".format(
        ",".join("?" * len(ids))
    ), ids).fetchall()] if ids else []
    products = attach_review_stats(db, rows)
    products.sort(key=lambda p: ids.index(p["id"]))
    return render_template("client/compare.html", products=products, compare_max=COMPARE_MAX)


# ---------------------------------------------------------------------------
# Client — diagnostic IA (color mixing + technical recommendation)
# ---------------------------------------------------------------------------
def mix_colors(items):
    total = sum(i["pct"] for i in items) or 1
    r = g_ = b = 0
    for i in items:
        hexv = i["hex"].lstrip("#")
        rr, gg, bb = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)
        r += rr * i["pct"] / total
        g_ += gg * i["pct"] / total
        b += bb * i["pct"] / total
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g_), int(b))


def _color_distance(hex_a, hex_b):
    """Distance euclidienne pondérée (redmean) entre deux couleurs hexadécimales
    — assez proche de la perception humaine sans dépendance externe."""
    ha, hb = hex_a.lstrip("#"), hex_b.lstrip("#")
    r1, g1, b1 = int(ha[0:2], 16), int(ha[2:4], 16), int(ha[4:6], 16)
    r2, g2, b2 = int(hb[0:2], 16), int(hb[2:4], 16), int(hb[4:6], 16)
    rmean = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return ((2 + rmean / 256) * dr**2 + 4 * dg**2 + (2 + (255 - rmean) / 256) * db**2) ** 0.5


def closest_products(db, hex_color, limit=3, exclude_ids=None):
    """Les produits du catalogue dont la teinte est la plus proche d'une couleur donnée
    — utilisé pour relier un mélange du diagnostic IA à des teintes déjà en vente."""
    exclude_ids = exclude_ids or set()
    rows = [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()
            if r["id"] not in exclude_ids and r["hex"]]
    rows.sort(key=lambda p: _color_distance(hex_color, p["hex"]))
    return rows[:limit]


@app.route("/client/diagnostic", methods=["GET", "POST"])
@login_required(["client"])
def diagnostic():
    db = get_db()
    placeholders = ",".join("?" * len(PAINT_CATEGORIES))
    pigments = [row_to_product(r) for r in db.execute(
        f"SELECT * FROM products WHERE category IN ({placeholders})", PAINT_CATEGORIES
    ).fetchall()]

    result_color = None
    ai_text = None
    error = None
    mix_selection = []
    ml_prediction = None
    similar_products = []

    if request.method == "POST":
        surface = request.form.get("surface")
        climate_id = request.form.get("climate")
        climate_label = next((c["label"] for c in CLIMATES if c["id"] == climate_id), climate_id)

        for p in pigments:
            pct = request.form.get(f"pct_{p['id']}", "0")
            try:
                pct = int(pct)
            except ValueError:
                pct = 0
            if pct > 0:
                mix_selection.append({"name": p["name"], "hex": p["hex"], "pct": pct})

        if mix_selection:
            result_color = mix_colors(mix_selection)
            # 1) local machine learning prediction — instant, no network call
            ml_prediction = ml_recommender.predict(surface, climate_id, result_color)
            session["quiz_context"] = {"surface": surface, "climate": climate_id}
            # 2) Claude AI — detailed technical explanation in natural language, ancrée sur
            # la prédiction ML locale pour que les deux analyses restent cohérentes entre elles
            ai_text, error = call_diagnostic_ai(mix_selection, result_color, surface, climate_label, ml_prediction)
            # 3) relie le mélange obtenu aux teintes déjà en vente les plus proches
            similar_products = closest_products(db, result_color)

    return render_template("client/diagnostic.html", pigments=pigments, surfaces=SURFACES,
                            climates=CLIMATES, result_color=result_color, ai_text=ai_text,
                            error=error, mix_selection=mix_selection, ml_prediction=ml_prediction,
                            sample_price=SAMPLE_PRICE, similar_products=similar_products)


def call_diagnostic_ai(mix_selection, result_color, surface, climate_label, ml_prediction=None):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "Diagnostic IA désactivé : définissez ANTHROPIC_API_KEY pour l'activer."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        mix_desc = ", ".join(f"{m['name']} ({m['pct']}%)" for m in mix_selection)
        # Ancre la réponse de Claude sur la prédiction du modèle ML local (déjà affichée sur la
        # même page) pour que les deux analyses se complètent au lieu de risquer de se contredire.
        ml_context = ""
        if ml_prediction:
            ml_context = (
                f"Notre modèle de Machine Learning local recommande déjà une finition "
                f"{ml_prediction['finish']} avec un liant {ml_prediction['binder']} "
                f"(confiance {ml_prediction['confidence']}%) pour cette surface et ce climat. "
                "Base ton explication sur cette recommandation (ne la contredis pas), et développe le "
                "raisonnement technique derrière ce choix plutôt que d'en proposer un autre. "
            )
        prompt = (
            "Tu es un conseiller technique en peinture et pigments pour la maison KRONOCOLOR. "
            f"Un client prépare ce mélange de pigments : {mix_desc}, couleur résultante approximative {result_color}. "
            f"Surface visée : {surface}. Condition climatique : {climate_label}. "
            f"{ml_context}"
            "Réponds en français, en 4 sections courtes avec des titres en gras suivis de ':' : "
            "1. Finition recommandée. 2. Type de liant/peinture adapté et pourquoi vu le climat. "
            "3. Précautions techniques liées à la surface et au climat. 4. Durée de séchage estimée. "
            "Sois concret et technique. Maximum 130 mots au total."
        )
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        return text, None
    except Exception as e:
        return None, f"Analyse indisponible ({e})."


# ---------------------------------------------------------------------------
# Client — quiz QCM (assistant "sois-disant place" : quelques questions -> ML)
# ---------------------------------------------------------------------------
LIGHTNESS_SAMPLE_HEX = {
    "clair": "#e8e2d5",
    "moyen": "#9b7b5a",
    "sombre": "#2c2440",
}
QUIZ_LIGHTNESS_OPTIONS = [
    {"id": "clair", "label": "Plutôt claire"},
    {"id": "moyen", "label": "Ton moyen"},
    {"id": "sombre", "label": "Plutôt foncée"},
]
QUIZ_BUDGET_OPTIONS = [
    {"id": "eco", "label": "Économique", "icon": "💰", "max_price": 200},
    {"id": "standard", "label": "Standard", "icon": "💳", "max_price": 450},
    {"id": "premium", "label": "Premium", "icon": "💎", "max_price": None},
]
QUIZ_SURFACE_SIZE_OPTIONS = [
    {"id": "petite", "label": "Petite — moins de 10 m²", "icon": "🔹", "liters": 2},
    {"id": "moyenne", "label": "Moyenne — 10 à 30 m²", "icon": "🔸", "liters": 5},
    {"id": "grande", "label": "Grande — plus de 30 m²", "icon": "🔶", "liters": 10},
]


@app.route("/client/quiz", methods=["GET", "POST"])
@login_required(["client"])
def quiz():
    db = get_db()
    result = None
    suggestions = []
    answers = {}

    if request.method == "POST":
        surface = request.form.get("surface", SURFACES[0])
        climate_id = request.form.get("climate", CLIMATES[0]["id"])
        lightness = request.form.get("lightness", "moyen")
        budget = request.form.get("budget", "standard")
        surface_size = request.form.get("surface_size", "moyenne")
        answers = {"surface": surface, "climate": climate_id, "lightness": lightness,
                   "budget": budget, "surface_size": surface_size}

        sample_hex = LIGHTNESS_SAMPLE_HEX.get(lightness, "#9b7b5a")
        result = ml_recommender.predict(surface, climate_id, sample_hex)
        # Mémorisé pour relier cette recherche à un éventuel achat plus tard
        # (voir _capture_training_samples), afin de ré-entraîner le modèle sur du réel.
        session["quiz_context"] = {"surface": surface, "climate": climate_id}
        size_option = next((o for o in QUIZ_SURFACE_SIZE_OPTIONS if o["id"] == surface_size),
                            QUIZ_SURFACE_SIZE_OPTIONS[1])
        result["estimated_liters"] = size_option["liters"]

        budget_option = next((o for o in QUIZ_BUDGET_OPTIONS if o["id"] == budget), QUIZ_BUDGET_OPTIONS[1])
        placeholders = ",".join("?" * len(PAINT_CATEGORIES))
        sql = f"SELECT * FROM products WHERE category IN ({placeholders})"
        params = list(PAINT_CATEGORIES)
        if budget_option["max_price"] is not None:
            sql += " AND price <= ?"
            params.append(budget_option["max_price"])
        elif budget == "premium":
            sql += " AND price > ?"
            params.append(QUIZ_BUDGET_OPTIONS[1]["max_price"])
        rows = db.execute(sql, params).fetchall()
        if not rows:
            rows = db.execute(
                f"SELECT * FROM products WHERE category IN ({placeholders})", PAINT_CATEGORIES
            ).fetchall()
        suggestions = attach_review_stats(db, [row_to_product(r) for r in rows][:3])

    return render_template("client/quiz.html", surfaces=SURFACES, climates=CLIMATES,
                            lightness_options=QUIZ_LIGHTNESS_OPTIONS, lightness_hex=LIGHTNESS_SAMPLE_HEX,
                            budget_options=QUIZ_BUDGET_OPTIONS, surface_size_options=QUIZ_SURFACE_SIZE_OPTIONS,
                            result=result, suggestions=suggestions, answers=answers,
                            favorites=session.get("favorites", []), compare=session.get("compare", []))


@app.route("/api/surface-recommendation", methods=["POST"])
@login_required(["client"])
def api_surface_recommendation():
    data = request.get_json(force=True, silent=True) or {}
    surface = data.get("surface") or SURFACES[0]
    climate_id = data.get("climate") or CLIMATES[0]["id"]
    hex_color = data.get("hex") or "#9b7b5a"
    if surface not in SURFACES:
        surface = SURFACES[0]
    if climate_id not in [c["id"] for c in CLIMATES]:
        climate_id = CLIMATES[0]["id"]
    result = ml_recommender.predict(surface, climate_id, hex_color)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Wholesale
# ---------------------------------------------------------------------------
@app.route("/wholesale", methods=["GET", "POST"])
@login_required(["wholesale"])
def wholesale_view():
    db = get_db()
    products = [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()]

    if request.method == "POST":
        action = request.form.get("action")
        pid = request.form.get("product_id")
        qty = int(request.form.get("qty", 0) or 0)
        row = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        product = row_to_product(row) if row else None

        if not product or qty < product["min_wholesale"]:
            flash("Quantité inférieure au minimum grossiste pour cette référence.")
            return redirect(url_for("wholesale_view"))

        est_total = qty * product["wholesale_price"]
        wid = new_id("WS")

        if action == "quote":
            db.execute(
                "INSERT INTO wholesale (id,company,contact,email,product_name,qty,est_total,status,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (wid, request.form.get("company", ""), request.form.get("contact", ""),
                 request.form.get("email", ""), product["name"], qty, est_total,
                 "En attente", datetime.utcnow().isoformat()),
            )
            db.commit()
            flash(f"Demande de devis {wid} envoyée à notre équipe commerciale.")
        else:  # direct payment
            shipping_fee = 0 if est_total > 5000 else 250
            db.execute(
                "INSERT INTO wholesale (id,company,contact,email,product_name,qty,est_total,status,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (wid, request.form.get("company", ""), request.form.get("contact", ""),
                 request.form.get("email", ""), product["name"], qty, est_total + shipping_fee,
                 "Payée", datetime.utcnow().isoformat()),
            )
            db.commit()
            flash(f"Commande grossiste {wid} payée et confirmée. Livraison sous 5 à 10 jours ouvrés.")
        return redirect(url_for("wholesale_view"))

    return render_template("wholesale.html", products=products)


# ---------------------------------------------------------------------------
# Consultant
# ---------------------------------------------------------------------------
@app.route("/consultant")
@login_required(["consultant"])
def consultant_list():
    import json
    db = get_db()
    rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    clients = {}
    for r in rows:
        o = dict(r)
        key = (o["customer_phone"] or o["customer_name"] or "inconnu").lower()
        c = clients.setdefault(key, {"key": key, "name": o["customer_name"], "phone": o["customer_phone"],
                                      "city": o["customer_city"], "orders": [], "total": 0})
        o["items"] = json.loads(o["items_json"])
        c["orders"].append(o)
        c["total"] += o["total"]
    client_list = sorted(clients.values(), key=lambda c: -c["total"])
    return render_template("consultant.html", clients=client_list, selected=None)


@app.route("/consultant/client/<key>")
@login_required(["consultant"])
def consultant_client(key):
    import json
    db = get_db()
    rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    clients = {}
    for r in rows:
        o = dict(r)
        k = (o["customer_phone"] or o["customer_name"] or "inconnu").lower()
        c = clients.setdefault(k, {"key": k, "name": o["customer_name"], "phone": o["customer_phone"],
                                    "city": o["customer_city"], "orders": [], "total": 0})
        o["items"] = json.loads(o["items_json"])
        c["orders"].append(o)
        c["total"] += o["total"]
    client_list = sorted(clients.values(), key=lambda c: -c["total"])
    selected = clients.get(key)
    feedback_rows = db.execute(
        "SELECT * FROM feedback WHERE client_key=? ORDER BY created_at ASC", (key,)
    ).fetchall()
    return render_template("consultant.html", clients=client_list, selected=selected,
                            feedback=[dict(f) for f in feedback_rows])


@app.route("/consultant/client/<key>/feedback", methods=["POST"])
@login_required(["consultant"])
def consultant_feedback(key):
    text = request.form.get("text", "").strip()
    if text:
        db = get_db()
        db.execute(
            "INSERT INTO feedback (client_key, text, created_at) VALUES (?,?,?)",
            (key, text, datetime.utcnow().isoformat()),
        )
        db.commit()
    return redirect(url_for("consultant_client", key=key))


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@app.route("/admin")
@login_required(["admin"])
def admin_stats():
    import json
    db = get_db()
    orders = [dict(r) for r in db.execute("SELECT * FROM orders").fetchall()]
    wholesale = [dict(r) for r in db.execute("SELECT * FROM wholesale").fetchall()]

    revenue = sum(o["total"] for o in orders) + sum(w["est_total"] for w in wholesale)
    unique_clients = len({(o["customer_email"] or o["customer_name"]) for o in orders})

    tally = {}
    for o in orders:
        for item in json.loads(o["items_json"]):
            tally[item["name"]] = tally.get(item["name"], 0) + item["qty"]
    for w in wholesale:
        tally[w["product_name"]] = tally.get(w["product_name"], 0) + w["qty"]
    best_sellers = sorted(tally.items(), key=lambda x: -x[1])[:5]
    max_qty = best_sellers[0][1] if best_sellers else 1

    # Ventes des 14 derniers jours (regroupées par date) pour le graphique d'évolution.
    days = [(datetime.utcnow() - timedelta(days=n)).strftime("%Y-%m-%d") for n in range(13, -1, -1)]
    daily_revenue = {d: 0.0 for d in days}
    for o in orders:
        day = (o["created_at"] or "")[:10]
        if day in daily_revenue:
            daily_revenue[day] += o["total"]
    max_daily = max(daily_revenue.values()) if any(daily_revenue.values()) else 1
    sales_over_time = [
        {"date": d, "label": d[5:], "amount": daily_revenue[d],
         "pct": round(daily_revenue[d] / max_daily * 100) if max_daily else 0}
        for d in days
    ]

    low_stock = [dict(r) for r in db.execute(
        "SELECT id, name, stock FROM products WHERE stock < ? ORDER BY stock ASC",
        (LOW_STOCK_THRESHOLD,)
    ).fetchall()]
    recent_alerts = [dict(r) for r in db.execute(
        "SELECT * FROM stock_alerts ORDER BY id DESC LIMIT 10"
    ).fetchall()]

    ml_sample_count = db.execute("SELECT COUNT(*) FROM training_samples").fetchone()[0]
    ml_recent_samples = [dict(r) for r in db.execute(
        "SELECT * FROM training_samples ORDER BY id DESC LIMIT 8"
    ).fetchall()]

    return render_template("admin/stats.html", revenue=revenue, unique_clients=unique_clients,
                            total_orders=len(orders) + len(wholesale), best_sellers=best_sellers,
                            max_qty=max_qty, sales_over_time=sales_over_time,
                            low_stock=low_stock, recent_alerts=recent_alerts,
                            low_stock_threshold=LOW_STOCK_THRESHOLD,
                            ml_sample_count=ml_sample_count, ml_recent_samples=ml_recent_samples,
                            ml_real_samples_in_model=ml_recommender.n_real_samples,
                            backups=list_backups())


@app.route("/admin/ml/retrain", methods=["POST"])
@login_required(["admin"])
def admin_ml_retrain():
    db = get_db()
    _retrain_ml_from_db(db)
    flash(f"Modèle ré-entraîné sur {ml_recommender.n_real_samples} commande(s) réelle(s) "
          f"(+ le jeu de règles de base).")
    return redirect(url_for("admin_stats"))


@app.route("/admin/backup", methods=["POST"])
@login_required(["admin"])
def admin_backup_now():
    path = backup_database()
    flash(f"Sauvegarde créée : {os.path.basename(path)}")
    return redirect(url_for("admin_stats"))


@app.route("/admin/orders/export.csv")
@login_required(["admin"])
def admin_orders_export_csv():
    import csv
    import io
    import json
    db = get_db()
    orders = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "date", "client", "email", "ville", "pays_livraison", "articles", "total_dhs",
                      "frais_livraison", "frais_douane", "paiement", "statut"])
    for o in orders:
        items = json.loads(o["items_json"])
        articles = "; ".join(f"{i['name']} x{i['qty']}" for i in items)
        writer.writerow([o["id"], o["created_at"], o["customer_name"], o["customer_email"],
                          o["customer_city"], o["delivery_country"], articles, o["total"], o["shipping_fee"],
                          o["customs_fee"], o["payment_method"], o["status"]])

    csv_data = buf.getvalue()
    filename = f"commandes_kronocolor_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return app.response_class(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/admin/products", methods=["GET", "POST"])
@login_required(["admin"])
def admin_products():
    db = get_db()

    if request.method == "POST":
        pid = request.form.get("id") or new_id("P")
        image_path = request.form.get("existing_image") or None
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(f"{pid}_{file.filename}")
            file.save(os.path.join(_upload_dir(), filename))
            image_path = f"uploads/{filename}"

        exists = db.execute("SELECT id FROM products WHERE id=?", (pid,)).fetchone()
        old_price_raw = request.form.get("old_price", "").strip()
        fields = (
            request.form.get("name", ""), request.form.get("sub", ""),
            request.form.get("category", "Murs"), request.form.get("hex", "#9b3a2b"),
            image_path, request.form.get("unit", "kg"),
            float(request.form.get("price", 0) or 0), float(request.form.get("wholesale_price", 0) or 0),
            int(request.form.get("min_wholesale", 10) or 10), int(request.form.get("stock", 0) or 0),
            float(old_price_raw) if old_price_raw else None,
        )
        if exists:
            db.execute(
                "UPDATE products SET name=?,sub=?,category=?,hex=?,image=?,unit=?,price=?,"
                "wholesale_price=?,min_wholesale=?,stock=?,old_price=? WHERE id=?",
                fields + (pid,),
            )
        else:
            db.execute(
                "INSERT INTO products (name,sub,category,hex,image,unit,price,wholesale_price,"
                "min_wholesale,stock,old_price,id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                fields + (pid,),
            )
        db.commit()
        return redirect(url_for("admin_products"))

    products = [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()]
    return render_template("admin/products.html", products=products)


@app.route("/admin/products/<pid>/delete", methods=["POST"])
@login_required(["admin"])
def admin_product_delete(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (pid,))
    db.commit()
    return redirect(url_for("admin_products"))


@app.route("/admin/orders")
@login_required(["admin"])
def admin_orders():
    import json
    db = get_db()
    rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    orders = []
    for r in rows:
        o = dict(r)
        o["items"] = json.loads(o["items_json"])
        orders.append(o)
    recent_emails = [dict(r) for r in db.execute(
        "SELECT * FROM sent_emails ORDER BY id DESC LIMIT 10"
    ).fetchall()]
    return render_template("admin/orders.html", orders=orders, recent_emails=recent_emails)


@app.route("/admin/orders/<oid>/status", methods=["POST"])
@login_required(["admin"])
def admin_order_status(oid):
    db = get_db()
    new_status = request.form.get("status")
    db.execute("UPDATE orders SET status=? WHERE id=?", (new_status, oid))
    order = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if order:
        _send_order_status_email(db, order, new_status)
    db.commit()
    return redirect(url_for("admin_orders"))


@app.route("/admin/wholesale")
@login_required(["admin"])
def admin_wholesale():
    db = get_db()
    rows = db.execute("SELECT * FROM wholesale ORDER BY created_at DESC").fetchall()
    return render_template("admin/wholesale.html", requests=[dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Chatbot API (static FAQ fast-path + local domain expertise + AI fallback)
# ---------------------------------------------------------------------------
SURFACE_KEYWORDS = {
    "mur exterieur": "Mur extérieur", "facade": "Mur extérieur",
    "mur interieur": "Mur intérieur",
    "bois": "Bois", "boiserie": "Bois", "boiseries": "Bois",
    "metal": "Métal", "fer": "Métal", "acier": "Métal",
    "beton": "Béton brut",
    "carrosserie": "Carrosserie auto", "voiture": "Carrosserie auto", "auto": "Carrosserie auto",
    "plastique": "Plastique",
    "platre": "Plâtre",
}
CLIMATE_KEYWORDS = {
    "chaud": "chaud_sec", "sec": "chaud_sec", "secheresse": "chaud_sec",
    "froid": "froid", "hiver": "froid", "gel": "froid",
    "humide": "humide", "humidite": "humide", "pluie": "humide",
    "vent": "vent", "venteux": "vent",
}
CATEGORY_KEYWORDS = {
    "bois": "Bois", "carrosserie": "Voiture & Carrosserie", "voiture": "Voiture & Carrosserie",
    "mur": "Murs", "papier peint": "Papier peint", "outil": "Outils de peinture", "pinceau": "Outils de peinture",
}
GREETING_KEYWORDS = ["bonjour", "salut", "bonsoir", "coucou", "hello", "hey"]
THANKS_KEYWORDS = ["merci", "cool merci", "top merci"]
ORDER_STATUS_KEYWORDS = ["ou est ma commande", "mes commandes", "suivi de commande", "statut de ma commande",
                         "ou en est ma commande"]

# Glossaire jargon peinture : finitions, liants, préparation, pathologies, outils, rendement.
PAINT_JARGON = [
    (["mat", "matte", "mate", "mats", "mates"],
     "Le mat offre un rendu sans reflet, idéal pour masquer les petites imperfections d'un mur. "
     "Moins résistant aux frottements qu'un satiné ou un laqué."),
    (["satine", "satin", "satinee", "satines", "satinees"],
     "Le satiné offre un léger reflet, plus résistant et lessivable que le mat — un bon compromis pour "
     "les pièces de vie et la cuisine."),
    (["brillant", "laque", "gloss", "brillante", "brillants", "brillantes", "laquee", "laques", "laquees"],
     "Le brillant (laqué) offre un rendu très réfléchissant et une excellente résistance — utilisé sur "
     "boiseries, métal et carrosserie pour un fini miroir."),
    (["veloute", "velour", "veloutee", "veloutes", "veloutees"],
     "Le velouté se situe entre mat et satiné : toucher doux, peu de reflet, bonne tenue au quotidien."),
    (["acrylique"],
     "L'acrylique est un liant en phase aqueuse, écologique, séchage rapide — idéal pour murs intérieurs "
     "et extérieurs standards."),
    (["glycero"],
     "Le glycéro (phase solvant) offre une excellente tenue et un beau tendu, surtout utilisé sur boiseries "
     "et métal — séchage plus long, odeur plus marquée que l'acrylique."),
    (["epoxy"],
     "L'époxy est un liant bi-composant à très haute résistance chimique et mécanique — recommandé pour "
     "métal, sols et carrosserie."),
    (["silicate"],
     "Le silicate est un liant minéral très respirant, parfait pour les façades extérieures et le béton, "
     "résistant aux intempéries."),
    (["chaux"],
     "La chaux est un liant traditionnel et respirant, souvent utilisé en extérieur et sur supports anciens "
     "ou en pierre."),
    (["polyurethane"],
     "Le polyuréthane offre une résistance mécanique et chimique élevée — le choix de référence pour "
     "carrosserie et surfaces très sollicitées."),
    (["sous-couche", "sous couche", "primaire", "appret"],
     "Une sous-couche (primaire/apprêt) améliore l'accroche et l'uniformité de la couleur, surtout sur "
     "surface poreuse, bois brut ou changement de teinte marqué. Toujours recommandée avant la finition."),
    (["poncage", "poncer"],
     "Un ponçage léger (grain fin) avant application assure une meilleure adhérence, surtout sur bois ou "
     "une ancienne peinture brillante."),
    (["diluant", "solvant", "white spirit"],
     "Le diluant (eau pour l'acrylique, white spirit pour le glycéro) ajuste la fluidité de la peinture et "
     "sert au nettoyage des outils."),
    (["cloque", "cloques", "boursouflure", "boursouflures"],
     "Des cloques indiquent souvent un problème d'humidité sous le film de peinture ou une application sur "
     "support mal préparé/humide. Grattez, assécher, puis reprenez avec une sous-couche adaptée."),
    (["ecaillage", "ecaillages", "s'ecaille"],
     "L'écaillage vient généralement d'un manque d'accroche (surface non préparée) ou d'une incompatibilité "
     "de liants entre couches. Un ponçage et une sous-couche adaptée règlent le problème."),
    (["moisissure", "moisissures", "champignon", "champignons", "salpetre"],
     "Contre la moisissure, traitez le support avec un anti-fongique avant de repeindre, et privilégiez un "
     "liant respirant (silicate, chaux) en cas d'humidité persistante."),
    (["rouille", "rouilles", "rouillee", "rouillees", "corrosion"],
     "Sur métal rouillé, un traitement antirouille puis une laque époxy anti-corrosion est recommandée pour "
     "une tenue durable."),
    (["craquelure", "craquelures", "craquele"],
     "Les craquelures apparaissent souvent avec une couche trop épaisse ou un séchage trop rapide. Respectez "
     "le temps de séchage entre couches et l'épaisseur recommandée."),
    (["couvrance", "rendement", "combien de m2", "combien de metre"],
     "Comptez environ 10 m² par litre et par couche (deux couches recommandées pour une couverture homogène) "
     "— variable selon la surface et la teinte."),
    (["nombre de couches", "combien de couches"],
     "Deux couches sont généralement recommandées pour une couleur homogène et durable, trois sur une teinte "
     "très contrastée ou un support neuf."),
    (["sechage", "temps de sechage"],
     "Comptez environ 2 à 4h de séchage au toucher pour un acrylique, 8 à 24h pour un glycéro — et 24 à 48h "
     "avant la seconde couche selon le climat."),
    (["pinceau"],
     "Un pinceau à poils synthétiques convient à l'acrylique, un pinceau à poils naturels au glycéro. "
     "Retrouvez nos kits dans la catégorie Outils de peinture."),
    (["rouleau"],
     "Un rouleau à poils courts convient aux finitions lisses (laqué/satiné), un poil plus long aux surfaces "
     "texturées ou au mat extérieur."),
    (["ral", "code couleur"],
     "Nous ne suivons pas les codes RAL directement, mais chaque teinte KRONOCOLOR a son propre code "
     "hexadécimal — consultez notre Nuancier pour explorer toutes nos couleurs."),
]


def _strip_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


PRODUCT_WORD_STOPLIST = {"papier", "peint", "peinture", "outils", "outil"}


def domain_answer(message, db):
    """Answer domain-specific questions (products, technical surface/climate advice,
    category browsing, painting jargon) from local data, without needing the Claude API."""
    lower = _strip_accents(message.lower())
    words_count = len(lower.split())
    products = [row_to_product(r) for r in db.execute("SELECT * FROM products").fetchall()]

    def has_word(keyword):
        return re.search(r"\b" + re.escape(keyword) + r"\b", lower) is not None

    def has_phrase(phrase):
        return _strip_accents(phrase) in lower

    # 0a) Suivi de commande : intention très spécifique, dépend de l'utilisateur connecté —
    # vérifiée en premier avant que les tiers plus génériques ne puissent interférer.
    if any(has_phrase(p) for p in ORDER_STATUS_KEYWORDS):
        user = current_user()
        if not user:
            return "Connectez-vous à votre compte pour que je puisse retrouver vos commandes."
        row = db.execute(
            "SELECT * FROM orders WHERE customer_email=? ORDER BY created_at DESC LIMIT 1", (user["email"],)
        ).fetchone()
        if not row:
            return "Je ne trouve aucune commande associée à votre compte pour le moment."
        return (f"Votre dernière commande {row['id']} ({row['created_at'][:10]}) est actuellement "
                f"« {row['status']} ». Retrouvez le détail dans « Mes commandes ».")

    # 0b) Politesses : ne répond ainsi que pour un message court et essentiellement une
    # salutation/un remerciement, pour ne pas ignorer une vraie question qui commence par « bonjour ».
    if words_count <= 4:
        if any(has_word(k) for k in THANKS_KEYWORDS):
            return "Avec plaisir ! N'hésitez pas si vous avez d'autres questions sur nos peintures et pigments."
        if any(has_word(k) for k in GREETING_KEYWORDS):
            return ("Bonjour 👋 Je peux vous renseigner sur un produit, une couleur, la livraison, le paiement, "
                    "ou vous conseiller une finition selon votre surface et votre climat. Que puis-je faire pour vous ?")

    # 1) Jargon technique (finitions, liants, pathologies...) : signal le plus intentionnel,
    # prioritaire sur un simple mot de surface qui apparaîtrait aussi dans un nom de produit.
    for keywords, answer in PAINT_JARGON:
        if any(has_word(k) for k in keywords):
            return answer

    # 2) Correspondance produit sur un mot distinctif (on exclut les mots génériques de
    # surface/catégorie pour éviter qu'un mot comme "façade" ne déclenche un produit au hasard).
    generic_words = set(SURFACE_KEYWORDS) | set(CATEGORY_KEYWORDS) | PRODUCT_WORD_STOPLIST
    for p in products:
        name_norm = _strip_accents(p["name"].lower())
        words = [w for w in name_norm.split() if len(w) >= 4 and w not in generic_words]
        if has_word(name_norm) or any(has_word(w) for w in words):
            stock_txt = "en stock" if p["stock"] > 0 else "épuisée"
            return (f"{p['name']} ({p['category']}) — {p['sub']}. "
                    f"{p['price']} MAD/{p['unit']}, {stock_txt} ({p['stock']} {p['unit']}). "
                    f"Retrouvez-la dans la boutique, catégorie « {p['category']} ».")

    # 3) Surface + climat explicitement mentionnés ensemble : question technique ("quelle
    # peinture pour du bois en climat humide ?") -> recommandation finition/liant.
    surface = next((v for k, v in SURFACE_KEYWORDS.items() if has_word(k)), None)
    climate_id = next((v for k, v in CLIMATE_KEYWORDS.items() if has_word(k)), None)
    if surface and climate_id:
        climate_label = next((c["label"] for c in CLIMATES if c["id"] == climate_id), climate_id)
        result = ml_recommender.predict(surface, climate_id, "#9b7b5a")
        return (f"Pour du {surface.lower()} en climat {climate_label.lower()}, je recommande une finition "
                f"{result['finish'].lower()} avec un liant {result['binder'].lower()} "
                f"(confiance du modèle : {result['confidence']}%). "
                f"Essayez notre Diagnostic IA pour affiner avec votre propre mélange de pigments.")

    # 4) Couleur mentionnée (« vous avez du rouge ? ») -> produits du catalogue dont la teinte
    # appartient à cette famille de couleur (même logique que le filtre couleur de la boutique).
    color_family = next(
        (fam for fam, variants in COLOR_FAMILY_VARIANTS.items() if any(has_word(v) for v in variants)), None
    )
    if color_family:
        matches = [p for p in products if _color_family(p["hex"]) == color_family][:3]
        if matches:
            items = ", ".join(f"{p['name']} ({p['price']} MAD)" for p in matches)
            return (f"En {color_family}, nous avons par exemple : {items}. Filtrez par couleur dans la boutique "
                    f"ou le nuancier pour voir toutes les teintes {color_family}s.")
        return (f"Je n'ai pas de teinte {color_family} en stock actuellement, mais essayez notre Diagnostic IA "
                f"pour composer un mélange personnalisé dans cette teinte.")

    # 5) Simple mention de catégorie/surface sans climat : intention de navigation
    # ("vous avez de la peinture carrosserie ?") -> liste de produits disponibles.
    for kw, cat in CATEGORY_KEYWORDS.items():
        if has_word(kw):
            matches = [p for p in products if p["category"] == cat][:3]
            if matches:
                items = ", ".join(f"{p['name']} ({p['price']} MAD)" for p in matches)
                return f"Dans la catégorie « {cat} », nous avons par exemple : {items}. Voir tout dans la boutique."

    # 6) Filet de sécurité : une surface était mentionnée mais sans catégorie ni climat détecté.
    if surface:
        result = ml_recommender.predict(surface, "chaud_sec", "#9b7b5a")
        return (f"Pour du {surface.lower()}, je recommande une finition {result['finish'].lower()} avec un "
                f"liant {result['binder'].lower()}. Précisez le climat (chaud, froid, humide, venteux) pour "
                f"affiner la recommandation.")

    return None


@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Pouvez-vous préciser votre question ?"})

    # domain_answer() est vérifié en premier : c'est un moteur à paliers qui peut répondre
    # de façon précise (produit, stock, commande...) alors que la FAQ ci-dessous ne fait que
    # des correspondances génériques sur des mots-clés larges (ex. "stock", "carte").
    domain_reply = domain_answer(message, get_db())
    if domain_reply:
        return jsonify({"reply": domain_reply, "source": "domain"})

    lower = _strip_accents(message.lower())

    def has_word(keyword):
        return re.search(r"\b" + re.escape(_strip_accents(keyword)) + r"\b", lower) is not None

    for keywords, answer in FAQ:
        if any(has_word(k) for k in keywords):
            return jsonify({"reply": answer, "source": "faq"})

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"reply": "Je peux répondre sur la livraison, le paiement, le stock, les retours, le "
                                  "grossiste, un produit précis, ou vous conseiller une finition selon la surface "
                                  "et le climat (ex : « quelle peinture pour du bois en climat humide ? »). "
                                  "Pour le reste, contactez notre consultant.",
                         "source": "fallback"})
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[
                {"role": "user", "content": "Tu es l'assistant de chat de KRONOCOLOR, maison de pigments et "
                                             "peintures. Réponds en français, court (max 60 mots), chaleureux."},
                {"role": "assistant", "content": "Compris."},
                {"role": "user", "content": message},
            ],
        )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        return jsonify({"reply": text or "Pouvez-vous reformuler ?", "source": "ai"})
    except Exception:
        return jsonify({"reply": "Je suis indisponible pour le moment, réessayez.", "source": "error"})


# ---------------------------------------------------------------------------
# Lazily initialise the database on first request, so the schema/seed data
# exist whether the app is started via `python app.py` or under a production
# WSGI server (gunicorn, Docker) where the __main__ guard below never runs.
_db_initialized = False


@app.before_request
def _ensure_db_ready():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _retrain_ml_from_db(get_db())
        _maybe_auto_backup()
        _db_initialized = True


if __name__ == "__main__":
    init_db()
    with app.app_context():
        _retrain_ml_from_db(get_db())
        _maybe_auto_backup()
    _db_initialized = True
    app.run(debug=True)
