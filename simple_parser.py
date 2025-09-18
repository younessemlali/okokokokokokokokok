"""
Parser XML simple et robuste pour PIXID
Utilise uniquement xml.etree.ElementTree (inclus dans Python)
"""

import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import re

class SimpleXMLProcessor:
    """Processeur XML tout-en-un pour les factures PIXID"""
    
    def __init__(self, xml_content):
        """Initialise le processeur avec le contenu XML"""
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8')
        
        self.xml_string = xml_content
        self.root = ET.fromstring(xml_content)
        self.data = {}
        
    def analyze(self):
        """Analyse le XML et détecte les problèmes"""
        self.data = {
            'invoice_id': self._get_invoice_id(),
            'period_start': None,
            'period_end': None,
            'raf_hours': 0,
            'invoice_hours': 0,
            'lines': [],
            'total_charges': 0,
            'total_tax': 0,
            'total_amount': 0,
            'vat_rate': 20,
            'has_issue': False,
            'issue_message': ''
        }
        
        # Extraction des TimeCards (RAF)
        self._extract_timecards()
        
        # Extraction des totaux et lignes
        self._extract_invoice_data()
        
        # Détection des incohérences
        self._detect_issues()
        
        return self.data
    
    def fix(self):
        """Corrige le XML pour la période détectée dans les TimeCards"""
        if not self.data.get('has_issue'):
            return self.xml_string
        
        # Parse le XML ligne par ligne pour préserver la structure
        lines = self.xml_string.split('\n')
        
        # Calculer le ratio de correction
        ratio = self.data['raf_hours'] / self.data['invoice_hours'] if self.data['invoice_hours'] > 0 else 1
        
        # Corrections à appliquer
        corrections = {
            'total_charges': Decimal(str(self.data['total_charges'])) * Decimal(str(ratio)),
            'hours_to_invoice': self.data['raf_hours'],
            'period': self.data['period_start']
        }
        
        # Appliquer les corrections ligne par ligne
        new_lines = []
        for line in lines:
            new_line = self._correct_line(line, corrections)
            new_lines.append(new_line)
        
        return '\n'.join(new_lines)
    
    def _get_invoice_id(self):
        """Extrait l'ID de la facture"""
        for elem in self.root.iter():
            if elem.tag.endswith('Id') or elem.tag == 'Id':
                parent = self._get_parent(elem)
                if parent and (parent.tag.endswith('DocumentIds') or parent.tag == 'DocumentIds'):
                    if elem.text:
                        return elem.text.strip()
        return "UNKNOWN"
    
    def _get_parent(self, element):
        """Trouve le parent d'un élément"""
        for parent in self.root.iter():
            for child in parent:
                if child == element:
                    return parent
        return None
    
    def _extract_timecards(self):
        """Extrait les informations des TimeCards (RAF)"""
        for elem in self.root.iter():
            if elem.tag.endswith('TimeCard') or elem.tag == 'TimeCard':
                for child in elem.iter():
                    if child.tag.endswith('PeriodStartDate') or child.tag == 'PeriodStartDate':
                        if child.text:
                            self.data['period_start'] = child.text
                    elif child.tag.endswith('PeriodEndDate') or child.tag == 'PeriodEndDate':
                        if child.text:
                            self.data['period_end'] = child.text
                    elif child.tag.endswith('TimeInterval') or child.tag == 'TimeInterval':
                        self._process_time_interval(child)
    
    def _process_time_interval(self, interval):
        """Traite un TimeInterval"""
        interval_type = interval.get('type', '')
        
        for child in interval:
            if child.tag.endswith('Duration') or child.tag == 'Duration':
                if child.text and 'heure' in interval_type.lower():
                    self.data['raf_hours'] += float(child.text)
    
    def _extract_invoice_data(self):
        """Extrait les données de la facture"""
        for elem in self.root.iter():
            # Totaux
            if elem.tag.endswith('TotalCharges') or elem.tag == 'TotalCharges':
                if elem.text:
                    self.data['total_charges'] = float(elem.text)
            elif elem.tag.endswith('TotalTax') or elem.tag == 'TotalTax':
                if elem.text:
                    self.data['total_tax'] = float(elem.text)
            elif elem.tag.endswith('TotalAmount') or elem.tag == 'TotalAmount':
                if elem.text:
                    self.data['total_amount'] = float(elem.text)
            
            # Lignes de facture
            elif elem.tag.endswith('Line') or elem.tag == 'Line':
                line_data = self._extract_line(elem)
                if line_data:
                    self.data['lines'].append(line_data)
                    # Accumulation des heures facturées
                    if line_data['unit'] in ['HUR', 'hur'] and 'heure' in line_data.get('description', '').lower():
                        self.data['invoice_hours'] += line_data['quantity']
    
    def _extract_line(self, line_elem):
        """Extrait les données d'une ligne"""
        line_data = {
            'description': '',
            'quantity': 0,
            'unit': '',
            'total': 0
        }
        
        for child in line_elem.iter():
            if child.tag.endswith('Description') or child.tag == 'Description':
                if not child.get('owner') and child.text:
                    line_data['description'] = child.text
            elif child.tag.endswith('ItemQuantity') or child.tag == 'ItemQuantity':
                if child.text:
                    line_data['quantity'] = float(child.text)
                    line_data['unit'] = child.get('uom', 'PCE')
            elif child.tag.endswith('Total') or child.tag == 'Total':
                parent = self._get_parent(child)
                if parent and (parent.tag.endswith('Charge') or parent.tag == 'Charge'):
                    if child.text:
                        line_data['total'] = float(child.text)
        
        return line_data if line_data['total'] > 0 else None
    
    def _detect_issues(self):
        """Détecte les incohérences RAF vs Facture"""
        # Vérifier l'écart entre heures RAF et heures facturées
        if abs(self.data['raf_hours'] - self.data['invoice_hours']) > 0.01:
            self.data['has_issue'] = True
            self.data['issue_message'] = f"Écart détecté: RAF {self.data['raf_hours']:.2f}h vs Facture {self.data['invoice_hours']:.2f}h"
        
        # Vérifier si c'est une semaine à cheval
        if self.data['period_start'] and self.data['period_end']:
            try:
                start = date_parser.parse(self.data['period_start']).date()
                end = date_parser.parse(self.data['period_end']).date()
                
                # Si période d'un jour mais facture complète
                if start == end and self.data['invoice_hours'] > 12:
                    self.data['has_issue'] = True
                    self.data['issue_message'] += " | Semaine à cheval détectée"
            except:
                pass
    
    def _correct_line(self, line, corrections):
        """Corrige une ligne XML"""
        # Patterns pour trouver et remplacer les valeurs
        patterns = [
            # Total HT
            (r'<TotalCharges>[\d.]+</TotalCharges>', 
             f'<TotalCharges>{corrections["total_charges"]:.2f}</TotalCharges>'),
            
            # TVA (20% du nouveau HT)
            (r'<TotalTax>[\d.]+</TotalTax>', 
             f'<TotalTax>{(corrections["total_charges"] * Decimal("0.20")):.2f}</TotalTax>'),
            
            # TTC
            (r'<TotalAmount>[\d.]+</TotalAmount>', 
             f'<TotalAmount>{(corrections["total_charges"] * Decimal("1.20")):.2f}</TotalAmount>'),
            
            # Heures facturées
            (r'owner="NbHeuresFacturees">[\d.]+<', 
             f'owner="NbHeuresFacturees">{corrections["hours_to_invoice"]:.2f}<'),
            
            # Dates de période
            (r'owner="DEB_PER">[^<]+<', 
             f'owner="DEB_PER">{corrections["period"]}<'),
            (r'owner="FIN_PER">[^<]+<', 
             f'owner="FIN_PER">{corrections["period"]}<'),
        ]
        
        new_line = line
        for pattern, replacement in patterns:
            new_line = re.sub(pattern, replacement, new_line)
        
        # Pour les lignes de détail, appliquer le ratio
        if 'ItemQuantity' in line and 'uom="HUR"' in line:
            # Extraire la quantité actuelle
            match = re.search(r'<ItemQuantity[^>]*>([\d.]+)</ItemQuantity>', line)
            if match:
                old_qty = float(match.group(1))
                new_qty = old_qty * float(corrections['total_charges'] / Decimal(str(self.data['total_charges'])))
                new_line = re.sub(
                    r'<ItemQuantity([^>]*)>[\d.]+</ItemQuantity>',
                    f'<ItemQuantity\\1>{new_qty:.2f}</ItemQuantity>',
                    new_line
                )
        
        # Supprimer les lignes HS/RTT si période d'un jour
        if corrections['period'] == self.data['period_start']:
            if any(x in line for x in ['Supplémentaire', 'RTT', 'HS 125']):
                # Si c'est une ligne de type HS/RTT, la vider ou la commenter
                if '<Line>' in line and any(x in line for x in ['Supplémentaire', 'RTT']):
                    return '<!-- Ligne supprimée: HS/RTT hors période -->'
        
        return new_line
    
    def get_summary(self):
        """Retourne un résumé de l'analyse"""
        return {
            'invoice_id': self.data.get('invoice_id', 'UNKNOWN'),
            'period': f"{self.data.get('period_start', 'N/A')} → {self.data.get('period_end', 'N/A')}",
            'raf_hours': self.data.get('raf_hours', 0),
            'invoice_hours': self.data.get('invoice_hours', 0),
            'total_ht': self.data.get('total_charges', 0),
            'has_issue': self.data.get('has_issue', False),
            'issue': self.data.get('issue_message', '')
        }
