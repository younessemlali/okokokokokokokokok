"""
Module de détection et conversion d'encodage pour les fichiers XML PIXID
"""

import chardet
import re

def detect_and_decode(content):
    """
    Détecte automatiquement l'encodage d'un fichier et le décode
    
    Args:
        content: bytes ou string
    
    Returns:
        tuple: (contenu_décodé, encodage_détecté)
    """
    if isinstance(content, str):
        return content, 'already_string'
    
    # Méthode 1: Chercher la déclaration XML
    encoding_from_xml = None
    try:
        # Recherche de <?xml version="1.0" encoding="XXX"?>
        first_line = content[:200].decode('ascii', errors='ignore')
        match = re.search(r'encoding=["\']([^"\']+)["\']', first_line)
        if match:
            encoding_from_xml = match.group(1).lower()
            # Normaliser les noms d'encodage
            encoding_map = {
                'utf8': 'utf-8',
                'latin1': 'latin-1',
                'iso-8859-1': 'latin-1',
                'iso8859-1': 'latin-1',
                'windows-1252': 'cp1252',
                'cp-1252': 'cp1252'
            }
            encoding_from_xml = encoding_map.get(encoding_from_xml, encoding_from_xml)
    except:
        pass
    
    # Méthode 2: Essayer l'encodage déclaré dans le XML
    if encoding_from_xml:
        try:
            return content.decode(encoding_from_xml), encoding_from_xml
        except:
            pass
    
    # Méthode 3: Détection automatique avec chardet (si disponible)
    try:
        import chardet
        detected = chardet.detect(content)
        if detected['confidence'] > 0.7:
            try:
                return content.decode(detected['encoding']), detected['encoding']
            except:
                pass
    except ImportError:
        pass
    
    # Méthode 4: Essayer les encodages courants
    common_encodings = [
        'utf-8',
        'latin-1',
        'iso-8859-1',
        'windows-1252',
        'cp1252',
        'utf-16',
        'utf-32'
    ]
    
    for encoding in common_encodings:
        try:
            decoded = content.decode(encoding)
            # Vérifier que le décodage a produit du XML valide
            if '<?xml' in decoded or '<Envelope' in decoded:
                return decoded, encoding
        except:
            continue
    
    # Méthode 5: Forcer en latin-1 (décode toujours sans erreur)
    return content.decode('latin-1', errors='replace'), 'latin-1_forced'

def ensure_utf8_xml(xml_content):
    """
    Assure que le contenu XML est en UTF-8 avec la bonne déclaration
    
    Args:
        xml_content: string XML
    
    Returns:
        string: XML avec déclaration UTF-8
    """
    # Remplacer la déclaration d'encodage si elle existe
    xml_content = re.sub(
        r'(<\?xml[^>]+encoding=)["\'][^"\']+["\']',
        r'\1"UTF-8"',
        xml_content
    )
    
    # Ajouter la déclaration si elle n'existe pas
    if not xml_content.startswith('<?xml'):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    
    return xml_content
