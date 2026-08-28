from functions import *

# ========= CONSTANTES DE CONTRÔLE ============
MAX_PARALLEL_FETCHES = 1 #=à changer plus tard
PER_HOST_CONCURRENCY = 2 #=à voir si on le change
PER_HOST_INTERVAL = 1.0 # temps minimum avant nouvel essai #=à changer plus tard

#=I DON'T KNOW !!!!!!!!!!!!!!!!!!!!!!!!!
#BACKOFF_BASE = 2.0
#MAX_BACKOFF = 600              # seconds (10 min)
#COOLDOWN_AFTER_ERRORS = 3
#COOLDOWN_MIN = 60   

# ========= INITIALISATION ============
print("<> Nouvelle session initiée <>")

# la clé privée de Firebase
FIREBASE_SERVICE_KEY = safe_import_sk()

# la session Firebase
FIREBASE_SESSION = init_firebase(FIREBASE_SERVICE_KEY)

# ========= MAIN FUNCTION ============
print("<> Lancement <>")

# chargement des infos
feeds = import_feeds()

# -- à améliorer (core, cœurs, optimisat°, etc) --
if feeds is None:
    print(">>> INTERRUPTION INOPINÉE : les infos n'ont pas été trouvées !")
else:
    for linekey in feeds:
        # fetching de Nitter
        dresp = fetch_nitter(format_rss_url(feeds[linekey]["slug"]),feeds[linekey]["etag"],feeds[linekey]['last_modified'])
        if dresp is not None and dresp["status"]==200:
            # tri des posts
            posts = parsing(dresp,feeds[linekey]['slug'])
            # envoi à FCM
            send_notifications(posts)
print("<> Session Terminée <>")

# TESTS
"""
print(c:=parsing(fetch_nitter(format_rss_url("RER_A")),"RER_A"))
# maintenant, ajouter la logique des "ne pas envoyer les posts déjà envoyés"
# +++ attention : les évolutions sont souvent des Reply à des anciens posts !
send_notifications(c)
"""
