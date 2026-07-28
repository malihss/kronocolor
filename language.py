"""
Traductions FR/EN/AR pour le parcours client (connexion → boutique → paiement).
Périmètre volontairement limité au tunnel d'achat visible par une clientèle
internationale (vente export) : les back-offices (admin/consultant/grossiste)
et les outils IA avancés (quiz, diagnostic) restent en français.
"""

LANGUAGES = ["fr", "en", "ar"]
LANGUAGE_LABELS = {"fr": "FR", "en": "EN", "ar": "AR"}
RTL_LANGUAGES = {"ar"}

TRANSLATIONS = {
    "role_client": {"fr": "Client", "en": "Client", "ar": "عميل"},
    "role_wholesale": {"fr": "Grossiste", "en": "Wholesale", "ar": "تاجر جملة"},
    "role_consultant": {"fr": "Consultant", "en": "Consultant", "ar": "مستشار"},
    "role_admin": {"fr": "Admin", "en": "Admin", "ar": "مدير"},

    "nav_home": {"fr": "Accueil", "en": "Home", "ar": "الرئيسية"},
    "nav_shop": {"fr": "Boutique", "en": "Shop", "ar": "المتجر"},
    "nav_shop_all": {"fr": "Tout voir", "en": "View all", "ar": "عرض الكل"},
    "nav_colors": {"fr": "Nuancier", "en": "Color chart", "ar": "دليل الألوان"},
    "nav_orders": {"fr": "Mes commandes", "en": "My orders", "ar": "طلباتي"},
    "nav_logout": {"fr": "Déconnexion", "en": "Log out", "ar": "تسجيل الخروج"},

    "footer_delivery_title": {"fr": "LIVRAISON", "en": "DELIVERY", "ar": "التوصيل"},
    "footer_delivery_line1": {
        "fr": "🌍 Expédition dans tout le Maroc et à l'international sur demande",
        "en": "🌍 Shipping across Morocco, and internationally on request",
        "ar": "🌍 التوصيل إلى جميع أنحاء المغرب ودوليًا عند الطلب",
    },
    "footer_delivery_line2": {
        "fr": "🚚 Suivi de commande dans l'espace client",
        "en": "🚚 Order tracking from your account",
        "ar": "🚚 تتبع الطلب من حسابك",
    },
    "footer_follow_title": {"fr": "SUIVEZ-NOUS", "en": "FOLLOW US", "ar": "تابعنا"},
    "footer_tagline": {
        "fr": "Pigments et peintures artisanales, pensés pour durer.",
        "en": "Artisan pigments and paints, made to last.",
        "ar": "أصباغ وطلاءات حرفية، مصممة لتدوم.",
    },
    "footer_shop_title": {"fr": "NAVIGATION", "en": "QUICK LINKS", "ar": "روابط سريعة"},
    "footer_back_to_top": {"fr": "Haut de page", "en": "Back to top", "ar": "العودة للأعلى"},

    "login_eyebrow": {"fr": "SE CONNECTER EN TANT QUE", "en": "LOG IN AS", "ar": "تسجيل الدخول كـ"},
    "login_title": {"fr": "Bon retour", "en": "Welcome back", "ar": "مرحبًا بعودتك"},
    "login_sub": {"fr": "Connectez-vous à votre espace", "en": "Sign in to your account", "ar": "سجّل الدخول إلى حسابك"},
    "email_placeholder": {"fr": "Email", "en": "Email", "ar": "البريد الإلكتروني"},
    "password_placeholder": {"fr": "Mot de passe", "en": "Password", "ar": "كلمة المرور"},
    "login_submit": {"fr": "Se connecter", "en": "Log in", "ar": "تسجيل الدخول"},
    "login_no_account": {"fr": "Pas encore de compte ?", "en": "No account yet?", "ar": "ليس لديك حساب؟"},
    "login_create_account": {"fr": "Créer un compte", "en": "Create an account", "ar": "إنشاء حساب"},

    "register_eyebrow": {"fr": "CRÉER UN COMPTE EN TANT QUE", "en": "CREATE AN ACCOUNT AS", "ar": "إنشاء حساب كـ"},
    "register_title": {"fr": "Bienvenue", "en": "Welcome", "ar": "أهلاً بك"},
    "register_sub": {"fr": "Créez votre espace KRONOCOLOR", "en": "Create your KRONOCOLOR account", "ar": "أنشئ حسابك في KRONOCOLOR"},
    "name_placeholder": {"fr": "Nom complet", "en": "Full name", "ar": "الاسم الكامل"},
    "register_password_placeholder": {
        "fr": "Mot de passe (6 caractères min.)", "en": "Password (6 characters min.)", "ar": "كلمة المرور (6 أحرف على الأقل)",
    },
    "register_confirm_placeholder": {"fr": "Confirmer le mot de passe", "en": "Confirm password", "ar": "تأكيد كلمة المرور"},
    "register_code_placeholder": {"fr": "Code d'invitation", "en": "Invitation code", "ar": "رمز الدعوة"},
    "register_submit": {"fr": "Créer mon compte", "en": "Create my account", "ar": "إنشاء حسابي"},
    "register_code_hint": {
        "fr": "Code d'invitation fourni par la maison KRONOCOLOR pour ce rôle.",
        "en": "Invitation code provided by KRONOCOLOR for this role.",
        "ar": "رمز الدعوة الذي تقدمه KRONOCOLOR لهذا الدور.",
    },
    "register_have_account": {"fr": "Déjà un compte ?", "en": "Already have an account?", "ar": "لديك حساب بالفعل؟"},

    "home_hero_line1": {"fr": "Chaque grand projet", "en": "Every great project", "ar": "كل مشروع عظيم"},
    "home_hero_line2": {"fr": "commence par", "en": "starts with", "ar": "يبدأ بـ"},
    "home_hero_line3": {"fr": "une couleur juste.", "en": "the right color.", "ar": "اللون الصحيح."},
    "home_cta_shop": {"fr": "Découvrir la boutique →", "en": "Discover the shop →", "ar": "اكتشف المتجر ←"},
    "home_cta_quiz": {"fr": "Quiz conseil →", "en": "Advice quiz →", "ar": "اختبار الاستشارة ←"},
    "home_bestseller_eyebrow": {"fr": "MEILLEURE VENTE", "en": "BESTSELLER", "ar": "الأكثر مبيعًا"},
    "home_catalog_eyebrow": {"fr": "CATALOGUE", "en": "CATALOG", "ar": "الكتالوج"},
    "home_catalog_title": {"fr": "La boutique par catégorie", "en": "Shop by category", "ar": "تسوق حسب الفئة"},
    "home_view_all_shop": {"fr": "Voir toute la boutique →", "en": "View the whole shop →", "ar": "عرض كل المتجر ←"},
    "home_tools_eyebrow": {"fr": "OUTILS EXCLUSIFS", "en": "EXCLUSIVE TOOLS", "ar": "أدوات حصرية"},
    "home_tools_title": {"fr": "Outils exclusifs KRONOCOLOR", "en": "Exclusive KRONOCOLOR tools", "ar": "أدوات KRONOCOLOR الحصرية"},
    "home_quiz_title": {"fr": "Quiz conseil", "en": "Advice quiz", "ar": "اختبار الاستشارة"},
    "home_quiz_text": {
        "fr": "Répondez à quelques questions et trouvez la teinte idéale pour votre projet.",
        "en": "Answer a few questions and find the ideal shade for your project.",
        "ar": "أجب عن بعض الأسئلة واعثر على اللون المثالي لمشروعك.",
    },
    "home_try": {"fr": "Essayer →", "en": "Try it →", "ar": "جرّب ←"},
    "home_diag_title": {"fr": "Diagnostic IA", "en": "AI diagnostic", "ar": "تشخيص بالذكاء الاصطناعي"},
    "home_diag_text": {
        "fr": "Mixez vos pigments et obtenez une analyse technique complète en temps réel.",
        "en": "Mix your pigments and get a full technical analysis in real time.",
        "ar": "امزج أصباغك واحصل على تحليل تقني كامل في الوقت الفعلي.",
    },
    "home_bestsellers_eyebrow": {"fr": "SÉLECTION", "en": "SELECTION", "ar": "الاختيارات"},
    "home_bestsellers_title": {"fr": "Meilleures ventes du mois", "en": "Best sellers this month", "ar": "الأكثر مبيعًا هذا الشهر"},
    "home_why_eyebrow": {"fr": "POURQUOI KRONOCOLOR", "en": "WHY KRONOCOLOR", "ar": "لماذا KRONOCOLOR"},
    "home_why_title": {"fr": "Une maison pensée pour durer", "en": "A house built to last", "ar": "دار صُممت لتدوم"},
    "home_why1_title": {"fr": "Une maison casablancaise", "en": "A Casablanca house", "ar": "دار من الدار البيضاء"},
    "home_why1_text": {
        "fr": "Fondée à Casablanca en 2020, KRONOCOLOR a démarré comme un petit négoce de pigments avant de devenir une référence pour les artisans et les marques exigeantes.",
        "en": "Founded in Casablanca in 2020, KRONOCOLOR started as a small pigment trading house before becoming a reference for craftsmen and demanding brands.",
        "ar": "تأسست KRONOCOLOR في الدار البيضاء عام 2020 كمتجر صغير للأصباغ قبل أن تصبح مرجعًا للحرفيين والعلامات التجارية المتميزة.",
    },
    "home_why2_title": {"fr": "Pensée pour l'usage réel", "en": "Built for real-world use", "ar": "مصممة للاستخدام الفعلي"},
    "home_why2_text": {
        "fr": "Chaque teinte est pensée pour son usage réel — climat, surface, exposition — pas seulement pour sa beauté sur un nuancier.",
        "en": "Every shade is designed for its real-world use — climate, surface, exposure — not just its beauty on a color chart.",
        "ar": "كل لون مصمم لاستخدامه الفعلي - المناخ والسطح والتعرض - وليس فقط لجماله على دليل الألوان.",
    },
    "home_why3_title": {"fr": "Livraison & service", "en": "Delivery & service", "ar": "التوصيل والخدمة"},
    "home_why3_text": {
        "fr": "Livraison, paiement sécurisé et devis grossiste : tout est pensé pour que le choix de couleur reste la seule décision difficile.",
        "en": "Delivery, secure payment and wholesale quotes: everything is designed so the color choice stays the only hard decision.",
        "ar": "التوصيل والدفع الآمن وعروض أسعار الجملة: كل شيء مصمم بحيث يبقى اختيار اللون هو القرار الصعب الوحيد.",
    },
    "stat_shades": {"fr": "Teintes disponibles", "en": "Shades available", "ar": "الألوان المتوفرة"},
    "stat_finishes": {"fr": "Finitions", "en": "Finishes", "ar": "التشطيبات"},
    "stat_experience": {"fr": "D'expertise", "en": "Of expertise", "ar": "من الخبرة"},
    "stat_satisfaction": {"fr": "Satisfaction client", "en": "Customer satisfaction", "ar": "رضا العملاء"},

    "shop_all_shades": {"fr": "Toutes nos teintes", "en": "All our shades", "ar": "جميع ألواننا"},
    "shop_sort_new": {"fr": "Trier par : Nouveautés", "en": "Sort by: New arrivals", "ar": "الترتيب حسب: الأحدث"},
    "shop_sort_price_asc": {"fr": "Prix croissant", "en": "Price: low to high", "ar": "السعر: من الأقل إلى الأعلى"},
    "shop_sort_price_desc": {"fr": "Prix décroissant", "en": "Price: high to low", "ar": "السعر: من الأعلى إلى الأقل"},
    "shop_filter_category": {"fr": "CATÉGORIE", "en": "CATEGORY", "ar": "الفئة"},
    "shop_all_categories": {"fr": "Toutes les catégories", "en": "All categories", "ar": "جميع الفئات"},
    "shop_filter_price": {"fr": "PRIX", "en": "PRICE", "ar": "السعر"},
    "shop_all_prices": {"fr": "Tous les prix", "en": "All prices", "ar": "جميع الأسعار"},
    "shop_under_200": {"fr": "Moins de 200 MAD", "en": "Under 200 MAD", "ar": "أقل من 200 درهم"},
    "shop_200_500": {"fr": "200 – 500 MAD", "en": "200 – 500 MAD", "ar": "200 – 500 درهم"},
    "shop_over_500": {"fr": "Plus de 500 MAD", "en": "Over 500 MAD", "ar": "أكثر من 500 درهم"},
    "shop_filter_color": {"fr": "COULEUR", "en": "COLOR", "ar": "اللون"},
    "shop_all_colors": {"fr": "Toutes les couleurs", "en": "All colors", "ar": "جميع الألوان"},
    "shop_filter_availability": {"fr": "DISPONIBILITÉ", "en": "AVAILABILITY", "ar": "التوفر"},
    "shop_all_products": {"fr": "Tous les produits", "en": "All products", "ar": "جميع المنتجات"},
    "shop_in_stock_only": {"fr": "En stock uniquement", "en": "In stock only", "ar": "المتوفر فقط"},
    "shop_no_products": {
        "fr": "Aucun produit ne correspond à ces filtres.",
        "en": "No product matches these filters.",
        "ar": "لا يوجد منتج يطابق هذه الفلاتر.",
    },
    "shop_view_all_cat": {"fr": "Voir tout →", "en": "View all →", "ar": "عرض الكل ←"},
    "shop_breadcrumb_home": {"fr": "Accueil", "en": "Home", "ar": "الرئيسية"},
    "shop_breadcrumb_shop": {"fr": "Boutique", "en": "Shop", "ar": "المتجر"},

    "cart_eyebrow": {"fr": "VOTRE SÉLECTION", "en": "YOUR SELECTION", "ar": "اختياراتك"},
    "cart_title": {"fr": "Panier", "en": "Cart", "ar": "السلة"},
    "cart_empty": {"fr": "Votre panier est vide pour le moment.", "en": "Your cart is currently empty.", "ar": "سلتك فارغة حاليًا."},
    "cart_remove": {"fr": "🗑 Retirer", "en": "🗑 Remove", "ar": "🗑 إزالة"},
    "cart_quantity": {"fr": "Quantité", "en": "Quantity", "ar": "الكمية"},
    "cart_update": {"fr": "Mettre à jour", "en": "Update", "ar": "تحديث"},
    "cart_clear": {"fr": "Vider le panier", "en": "Clear cart", "ar": "إفراغ السلة"},
    "cart_summary_eyebrow": {"fr": "RÉCAPITULATIF", "en": "SUMMARY", "ar": "الملخص"},
    "cart_subtotal": {"fr": "Sous-total", "en": "Subtotal", "ar": "المجموع الفرعي"},
    "cart_shipping_note": {
        "fr": "Frais de livraison calculés à l'étape suivante.",
        "en": "Shipping fees calculated at the next step.",
        "ar": "تُحسب رسوم الشحن في الخطوة التالية.",
    },
    "cart_checkout": {"fr": "Passer la commande →", "en": "Proceed to checkout →", "ar": "إتمام الطلب ←"},
    "cart_continue_shopping": {"fr": "Continuer mes achats", "en": "Continue shopping", "ar": "متابعة التسوق"},

    "checkout_eyebrow": {"fr": "LIVRAISON & PAIEMENT", "en": "DELIVERY & PAYMENT", "ar": "التوصيل والدفع"},
    "checkout_title": {"fr": "Finaliser la commande", "en": "Complete your order", "ar": "إتمام الطلب"},
    "checkout_promo_label": {"fr": "Code promo", "en": "Promo code", "ar": "رمز الخصم"},
    "checkout_promo_apply": {"fr": "Appliquer", "en": "Apply", "ar": "تطبيق"},
    "checkout_promo_applied_prefix": {"fr": "🏷️ Code promo «", "en": "🏷️ Promo code “", "ar": "🏷️ رمز الخصم «"},
    "checkout_promo_applied_suffix": {"fr": "» appliqué", "en": "” applied", "ar": "» مُطبَّق"},
    "checkout_promo_remove": {"fr": "Retirer", "en": "Remove", "ar": "إزالة"},
    "checkout_customs_label": {"fr": "Douane estimée", "en": "Estimated customs", "ar": "الجمارك المقدرة"},
    "checkout_country_label": {"fr": "Pays de livraison", "en": "Delivery country", "ar": "بلد التوصيل"},
    "checkout_country_note": {
        "fr": "Estimation forfaitaire pour la démo — les frais réels dépendent des accords douaniers en vigueur.",
        "en": "Flat-rate demo estimate — real fees depend on the customs agreements in force.",
        "ar": "تقدير إرشادي للعرض التوضيحي — تعتمد الرسوم الفعلية على الاتفاقيات الجمركية السارية.",
    },
    "checkout_address_placeholder": {"fr": "Adresse", "en": "Address", "ar": "العنوان"},
    "checkout_city_placeholder": {"fr": "Ville", "en": "City", "ar": "المدينة"},
    "checkout_phone_placeholder": {"fr": "Téléphone", "en": "Phone", "ar": "الهاتف"},
    "checkout_zone_label": {"fr": "Zone de livraison", "en": "Delivery zone", "ar": "منطقة التوصيل"},
    "checkout_payment_note": {
        "fr": "💳 Paiement simulé — démo, aucune carte réelle n'est débitée",
        "en": "💳 Simulated payment — demo, no real card is charged",
        "ar": "💳 دفع تجريبي — عرض توضيحي، لا يتم خصم أي بطاقة حقيقية",
    },
    "checkout_payment_label": {"fr": "Moyen de paiement", "en": "Payment method", "ar": "طريقة الدفع"},
    "checkout_card_option": {"fr": "💳 Carte bancaire", "en": "💳 Credit card", "ar": "💳 بطاقة بنكية"},
    "checkout_paypal_option": {"fr": "🅿️ PayPal", "en": "🅿️ PayPal", "ar": "🅿️ باي بال"},
    "checkout_card_placeholder": {
        "fr": "Numéro de carte ou email PayPal (démo)",
        "en": "Card number or PayPal email (demo)",
        "ar": "رقم البطاقة أو بريد PayPal (تجريبي)",
    },
    "checkout_submit": {"fr": "🛒 Payer et confirmer", "en": "🛒 Pay and confirm", "ar": "🛒 الدفع والتأكيد"},
}


def translate(key, lang):
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("fr") or key
