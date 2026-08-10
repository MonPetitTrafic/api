"""
À utiliser uniquement en mode production ou développement

Ce script permet d'encoder votre clé privée Firebase pour la placer dans un fichier .env
"""

import json
from base64 import b64encode as encoder

# Pour le mode production ou développement,
# Merci de changer la référence pour éviter de surcharger le projet Firebase de l'appli en mode déployé
REFERENCE = "monpetittrafic-secret-key.json"

with open(REFERENCE,'r') as file:
    k = json.load(file)
    k = json.dumps(k)
    kbuff = k.encode("utf-8")
encoded_buff = encoder(kbuff)
encoded = encoded_buff.decode('utf-8')

# Copier le résultat dans le fichier .env
# en tant que variable ENCODED_FIREBASE_SERVICE_KEY
print(encoded)