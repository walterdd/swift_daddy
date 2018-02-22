import re

def preprocess_domain(domain):
    '''
    Transform uppercase letters to lowercase, strip domain zone
    '''
    name = domain.lower()
    zone = None
    m = re.search(r'(\.[a-z]*)$', name)
    if m:
        name = name[:-len(m.group())]
        zone = m.group()
    length = len(name)
    return name, length, zone

