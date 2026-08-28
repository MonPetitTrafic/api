"""
Pour plus de facilité, on met toutes les fonctions annexes ici.

Le fourre-tout
"""
# IMPORTS =====
from custom_types import *
from base64 import b64decode as decoder
import feedparser, requests
import firebase_admin
from firebase_admin import messaging
import os,json
from dotenv import load_dotenv
from datetime import datetime

# UTILS =====


print("DEBUG::WARNING ! ExpectedFormat n'a pas été testé !")#<<<DEBUG was not tested

def format_rss_url(slug:str)-> str:
    """
    Transforme un slug (de feeds.json) en une URL de flux RSS Nitter
    directement exploitable
    """
    # RMQ : Nitter est uniquement exploitable par Python
    # les autres instances sont exploitables avec JavaScript
    return f"https://nitter.net/{slug}/rss"

def safe_import_sk()-> Any:
    """
    Importer la clé privée du projet Firebase
    de manière sécurisée (par .env et contrôlé par un try ... except)
    """
    try:
        load_dotenv()
        k_retrieve = os.getenv('ENCODED_FIREBASE_SERVICE_KEY')
        if k_retrieve is None:
            raise Exception
        k = decoder(k_retrieve.encode('utf-8')).decode('utf-8')
        return json.loads(k)
    except Exception as e:
        raise RuntimeError("Not found or unreadable Firebase service key")
    
def formatAsDate(d:str)-> FormattableDate|None:
    """
    Vérifie qu'une chaîne de caractères d respecte bien le format attendu
    pour les dates
    Si ce n'est pas le cas, renvoie None
    """
    try:
        dt = datetime.strptime(d,"%a, %d %b %Y %H:%M:%S GMT") #DAY, DD MON YYYY hh:mm:ss GMT
        return d # est de type FormattableDate
    except Exception:
        return None

def sanitize_search(L:list,w:Any,st:int=0)-> int:
    """
    Renvoie la première occurence de w dans la liste L à partir de l'indice st
    Si w n'est pas présent dans L, renvoie -1
    """
    try:
        return L.index(w,st)
    except ValueError:
        return -1

# FICHIERS =====

def import_feeds()-> Any|None:
    """
    Renvoie le contenu du fichier feeds.json
    """
    try:
        with open("feeds.json","r") as file:
            data = json.load(file)
        return data
    except Exception as e:
        raise e
    

# FIREBASE =====

def init_firebase(k:Any)-> firebase_admin.App:
    """
    Initialise une session Firebase avec la clé privée
    """
    try:
        return firebase_admin.initialize_app(firebase_admin.credentials.Certificate(k))
    except Exception as e:
        raise firebase_admin.DefaultCredentialsError("Cannot initialize a Firebase session with this private key")

def send_notifications(pr:list[postsReady]):
    """
    Envoie les posts prêts à Firebase pour lancer les notifications
    """
    msg_list = [
        messaging.Message(
            notification=messaging.Notification(elem['title'],elem['body']),
            android=messaging.AndroidConfig(priority='normal'),
            apns=messaging.APNSConfig(headers={"apns-priority":"5"}),
            topic=elem['line_slug'],
        )
        for elem in pr
    ]
    response = messaging.send_each(msg_list)
    print(f"{response.success_count}/{response.success_count+response.failure_count} notifications ont bien été envoyées !")
    return

# FETCH (Requests to Nitter) =====

def fetch_nitter(url:str,etag:str|None=None,modified:FormattableDate|str|None=None,timeout:int=20):
    """
    Fetche les instances de Nitter pour un compte X et renvoie le contenu obtenu après la requête

    Le fetch utilise la méthode If-None-Match/If-Modified-Since afin d'éviter de spammer
    les instances de Nitter
    """
    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MonPetitTrafic/1.0(+https://github.com/MonPetitTrafic)"
    headers["Accept"] = "application/rss+xml, application/xml, text/xml"
    # headers["From"] ## nécessaire pour l'automatisation par GitHub Actions

    if etag: # If-None-Match a la priorité 
        headers["If-None-Match"] = etag

    if modified is not None:
        modified_corrected:FormattableDate|None = formatAsDate(modified)
        if modified_corrected is not None:
            headers["If-Modified-Since"] = modified_corrected

    try:
        req = requests.get(url,headers=headers,timeout=timeout)
    except Exception as e:
        raise e
    else:
        if req.status_code==304:
            return {"status": 304, "headers": req.headers, "rawcontent": None}
        if req.status_code>=400:
            return {"status": req.status_code, "text": req.text, "headers": req.headers, "rawcontent":None}
        return {"status": req.status_code, "text":req.text,"rawcontent": req.content, "headers": req.headers}

def parsing(ctxt:Any,line_slug:str)-> list[postsReady]:
    """
    Filtre les posts X en ne conservant que les posts intéressants

    Fonctionne à partir d'un dico du type {"status": req.status_code, "text":req.text,"rawcontent": req.content, "headers": req.headers}
    Ce qui nous intéresse, c'est "text"
    Et renvoie une liste des posts prêts à être envoyés sur FCM (formattés en un dico)

    Perso, je trouve la méthode de parsing actuellement utilisée pourrie mais on l'améliorera plus tard...
    """
    KEPT:list[postsReady] = []
    try:
        if ctxt['status']!=200:
            raise ValueError
        feed = feedparser.parse(ctxt['text'])
    except Exception as e:
        raise ValueError(f"Invalid value for ctxt. Found {ctxt}.\nRemember that parsing works only for successful fetching !")

    # récupérer les posts
    waitingPosts = feed["entries"]

    # création de l'ETag (/!\ prendre véritablement le dernier message même si non intéressant)
    ### à compléter
    # sauvagarde de l'ETag et du last_modified

    # TRAITEMENT
    for post in waitingPosts:
        dico:postsReady = {}
        dico["line_slug"] = line_slug
        content:str = post["summary"]
        words = content.split(" ")

        # éjection des posts cultures de la RATP + travaux
        if "[culture]" in words or content.find("TRAVAUX")!=-1 or content.find("🚧")!=-1:
            continue
        # éjection des posts travaux (un verbe au futur)
        if "sera" in words or "seront" in words:
            continue


        # emojis distinctifs
        i_emoji = content.find('⚠️')
        if i_emoji!=-1:
            dico["title"] = f"{line_slug} : Trafic perturbé"
            dico["body"] = content
            KEPT.append(dico)
            continue
        i_emoji = [content.find('❌'),content.find('🔴'),content.find('⛔')]
        if set(i_emoji)!={-1}:
            dico["title"] = f"{line_slug} : Trafic interrompu"
            dico["body"] = content
            KEPT.append(dico)
            continue
        i_emoji = content.find('✅')
        if i_emoji!=-1:
            dico["title"] = f"{line_slug} : Reprise progressive"
            dico["body"] = content
            KEPT.append(dico)
            continue

        # images distinctives (à implémenter plus tard et si possible)

        # phrases type "(le) trafic (est) ..."
        i_trafic = sanitize_search(words,"trafic")
        if i_trafic==-1:
            i_trafic = sanitize_search(words,"Trafic")
        if i_trafic != -1:

            # ... perturbé
            ib = sanitize_search(words,"perturbé",i_trafic)
            if ib!=-1 and ib-i_trafic<=2:
                dico["title"] = f"{line_slug} : Trafic perturbé"
                dico["body"] = content
                KEPT.append(dico)
                continue
            ib = sanitize_search(words,"ralenti",i_trafic)
            if ib!=-1 and ib-i_trafic<=3:
                dico["title"] = f"{line_slug} : Trafic perturbé"
                dico["body"] = content
                KEPT.append(dico)
                continue

            # ... interrompu
            ib = sanitize_search(words,"interrompu",i_trafic)
            if ib!=-1 and ib-i_trafic<=2:
                dico["title"] = f"{line_slug} : Trafic interrompu"
                dico["body"] = content
                KEPT.append(dico)
                continue        

        # stationnements
        ib = content.find(" stationne")
        if ib!=-1:
            ic = [content.find("fin de"),content.find("Fin de")]
            if 0<=ic[0]<ib or 0<=ic[1]<ib: # fin de/du stationnement
                dico["title"] = f"{line_slug} : Reprise progressive"
                dico["body"] = content
                KEPT.append(dico)
                continue
            else:
                dico["title"] = f"{line_slug} : Stationnement(s)"
                dico["body"] = content
                KEPT.append(dico)
                continue

        # reprise du trafic
        ibx = [content.find("in d'incident"),content.find("ncident terminé"),content.find("etour à la normale")]
        if set(ibx)!={-1}:
            dico["title"] = f"{line_slug} : Reprise progressive"
            dico["body"] = content
            KEPT.append(dico)
            continue
        ib = content.find("e trafic reprend mais reste")
        if ib!=-1:
            dico["title"] = f"{line_slug} : Reprise progressive"
            dico["body"] = content
            KEPT.append(dico)
            continue

        # phrase clé SNCF : retards, modifications de desserte et suppressions à prévoir
        ibx = [content.find("retard"),content.find('desserte'),content.find("suppression")]
        if ibx[0]<ibx[1]<ibx[2] and ibx[0]!=-1:
            dico["title"] = f"{line_slug} : Trafic perturbé"
            dico["body"] = content
            KEPT.append(dico)
            continue

        # retards
        ib = content.find("retardé")
        if content.find("train")!=-1 or content.find("rame")!=-1:
            dico["title"] = f"{line_slug} : Trafic perturbé"
            dico["body"] = content
            KEPT.append(dico)
            continue

        # arrêts non desservis
        ib = content.find("non desservi")
        if ib!=-1:
            dico["title"] = f"{line_slug} : Trafic perturbé"
            dico["body"] = content
            KEPT.append(dico)
            continue

        ### normalement, tous les posts intéréssants ont été traités à ce stade
        ### on récupère à partir de maintenant tous les posts intéressants qui seraient mal formattés

        # train spécifique concerné
        ib = sanitize_search(words,"départ") #départ - arrivée
        ic = sanitize_search(words,"arrivée")
        if ib<ic and ib!=-1:
            dico["title"] = f"{line_slug} : Course(s) impactée(s)"
            dico["body"] = content
            KEPT.append(dico)
            continue
        ibx = [re.search(RATP_codes,content),re.search(SNCF_codes,content)]
        if ibx!=[None,None]:
            dico["title"] = f"{line_slug} : Course(s) impactée(s)"
            dico["body"] = content
            KEPT.append(dico)
            continue
        
        # causes possibles
        ibx = [
            content.find("bus de remplacement"),
            content.find("panne de"),content.find("panne d'un"),
            content.find("Motif :"),content.find("Motif:"),
            content.find('Message automatique'), # propre à la SNCF en dehors des sessions
            content.find("ndisponibilité du personnel"),
            content.find("en répercussion d"),content.find('en raison d'),
            content.find('❗')
        ]
        if set(ibx)!={-1}:
            dico["title"] = f"{line_slug} : Problème détecté"
            dico["body"] = content
            KEPT.append(dico)
            continue

        # arrivé à ce stade, le post est considéré comme inintéressant et inutile !

    return KEPT