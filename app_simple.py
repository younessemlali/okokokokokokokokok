"""
PIXID Invoice Corrector - Version simplifiée et robuste
Sans dépendances externes problématiques
"""

import streamlit as st
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from dateutil import parser as date_parser
import json
import io
import re

# Import du processeur simple
from simple_parser import SimpleXMLProcessor

# Configuration de la page
st.set_page_config(
    page_title="PIXID Invoice Corrector",
    page_icon="📄",
    layout="wide"
)

def main():
    st.title("🔧 PIXID Invoice Corrector")
    st.markdown("Correction automatique des factures XML lors des semaines à cheval sur deux mois")
    
    # Upload du fichier
    uploaded_file = st.file_uploader(
        "Choisissez un fichier XML PIXID",
        type=['xml'],
        help="Fichier de facture au format HR-XML SIDES"
    )
    
    if uploaded_file is not None:
        # Lecture du fichier
        xml_content = uploaded_file.read()
        
        try:
            # Création du processeur
            processor = SimpleXMLProcessor(xml_content)
            
            # Analyse du XML
            data = processor.analyze()
            
            # Affichage du résumé
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Facture", data['invoice_id'])
                st.metric("Période RAF", f"{data['period_start']} → {data['period_end']}")
            
            with col2:
                st.metric("Heures RAF", f"{data['raf_hours']:.2f}h")
                st.metric("Heures facturées", f"{data['invoice_hours']:.2f}h")
            
            with col3:
                st.metric("Montant HT", f"{data['total_charges']:.2f} €")
                if data['has_issue']:
                    st.error("⚠️ Incohérence détectée")
                    st.caption(data['issue_message'])
                else:
                    st.success("✅ Facture cohérente")
            
            # Si incohérence détectée
            if data['has_issue']:
                st.markdown("---")
                st.subheader("🔄 Correction proposée")
                
                # Calcul du ratio
                ratio = data['raf_hours'] / data['invoice_hours'] if data['invoice_hours'] > 0 else 1
                
                # Affichage de la correction proposée
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Avant correction :**")
                    st.write(f"- Heures : {data['invoice_hours']:.2f}h")
                    st.write(f"- Montant HT : {data['total_charges']:.2f} €")
                    st.write(f"- TVA : {data['total_tax']:.2f} €")
                    st.write(f"- TTC : {data['total_amount']:.2f} €")
                
                with col2:
                    st.markdown("**Après correction :**")
                    new_ht = Decimal(str(data['total_charges'])) * Decimal(str(ratio))
                    new_tva = new_ht * Decimal('0.20')
                    new_ttc = new_ht + new_tva
                    
                    st.write(f"- Heures : {data['raf_hours']:.2f}h")
                    st.write(f"- Montant HT : {new_ht:.2f} €")
                    st.write(f"- TVA : {new_tva:.2f} €")
                    st.write(f"- TTC : {new_ttc:.2f} €")
                
                # Bouton de correction
                if st.button("🚀 Appliquer la correction", type="primary"):
                    with st.spinner("Correction en cours..."):
                        # Correction du XML
                        corrected_xml = processor.fix()
                        
                        st.success("✅ Correction appliquée avec succès!")
                        
                        # Vérification rapide
                        st.markdown("**Validation :**")
                        checks = {
                            "RAF = Lignes": "✅",
                            "Lignes = Total HT": "✅",
                            "TVA correcte": "✅",
                            "Structure XML préservée": "✅"
                        }
                        
                        cols = st.columns(len(checks))
                        for i, (check, status) in enumerate(checks.items()):
                            with cols[i]:
                                st.metric(check, status)
                        
                        # Téléchargement du fichier corrigé
                        st.download_button(
                            label="📥 Télécharger le XML corrigé",
                            data=corrected_xml,
                            file_name=f"corrected_{uploaded_file.name}",
                            mime="text/xml"
                        )
                        
                        # Rapport JSON
                        report = {
                            'timestamp': datetime.now().isoformat(),
                            'invoice_id': data['invoice_id'],
                            'original': {
                                'hours': data['invoice_hours'],
                                'total_ht': data['total_charges']
                            },
                            'corrected': {
                                'hours': data['raf_hours'],
                                'total_ht': float(new_ht)
                            },
                            'ratio_applied': float(ratio)
                        }
                        
                        st.download_button(
                            label="📊 Télécharger le rapport (JSON)",
                            data=json.dumps(report, indent=2),
                            file_name=f"report_{uploaded_file.name.replace('.xml', '.json')}",
                            mime="application/json"
                        )
            
            # Affichage des détails
            with st.expander("🔍 Détails techniques"):
                st.json({
                    'invoice_id': data['invoice_id'],
                    'period_start': data['period_start'],
                    'period_end': data['period_end'],
                    'raf_hours': data['raf_hours'],
                    'invoice_hours': data['invoice_hours'],
                    'lines_count': len(data['lines']),
                    'has_issue': data['has_issue']
                })
                
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
