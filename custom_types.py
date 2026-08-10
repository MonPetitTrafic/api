"""
Séparation pour les types

NE METTRE QUE DES DÉFINITIONS DE TYPES ICI, MERCI !
"""
from typing import TypeAlias, Any, TypedDict
import re

# DATE au format ?nom?
FormattableDate: TypeAlias = str# format attendu : DAY, DD MON YYYY hh:mm:ss GMT
ExpectedFormat = re.compile(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), '
    r'(0[1-9]|[12][0-9]|3[01]) '
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) '
    r'\d{4} '
    r'([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9] '
    r'(GMT|UTC|[A-Z]{3})$'
)

# DICO des posts prêts
class postsReady(TypedDict):
    line_slug: str
    title: str
    body: str

# CODE MISSION
RATP_codes = re.compile(r' [A-Z]{4}[0-9]{2} ')
SNCF_codes = re.compile(r' [A-Z]{4} ')