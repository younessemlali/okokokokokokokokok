# 📄 PIXID Invoice Corrector

Application Streamlit pour corriger automatiquement les factures XML PIXID lors des semaines à cheval sur deux mois.

## 🔴 Le problème que cette application résout

### Situation problématique

Votre entreprise utilise un ERP pour générer des factures envoyées à PIXID. Lorsqu'une semaine de travail chevauche deux mois :

- **Exemple** : Semaine du 26 août au 1er septembre
- **Vous voulez facturer** : Seulement le 26-31 août (fin du mois)
- **Le PDF généré** : ✅ Correct (affiche uniquement la période à facturer)
- **Le XML envoyé à PIXID** : ❌ Contient TOUTE la semaine (38h au lieu de 8h)

### Conséquence

PIXID rejette la facture avec une erreur du type :
```
Ecart -- Montants total (RAF): 240.12 - Montants total (RCV):1145.60
```

Les RAF (TimeCards) indiquent 8h mais la facture contient 38h → incohérence !

## ✅ Comment l'application résout le problème

### 1. Détection automatique

L'application :
- Lit les TimeCards (RAF) dans le XML pour identifier la vraie période à facturer
- Détecte l'écart entre heures RAF (8h) et heures facturées (38h)
- Identifie automatiquement les semaines à cheval

### 2. Corrections appliquées

| Élément | Avant | Après |
|---------|-------|-------|
| **Heures travaillées** | 35h (semaine) | 8h (lundi seul) |
| **Heures supplémentaires** | 1h | 0h (supprimées) |
| **RTT** | 2h | 0h (supprimées) |
| **Prime 13e mois** | 35 unités | 8 unités (prorata) |
| **Paniers chantier** | 5 | 1 (jour travaillé) |
| **Transport** | 5 | 1 (jour travaillé) |
| **Total HT** | 1145.60€ | 240.13€ |
| **TVA (20%)** | 229.12€ | 48.03€ |
| **Total TTC** | 1374.72€ | 288.16€ |

### 3. Garanties

- ✅ **RAF = Lignes = TotalCharges** : L'égalité exigée par PIXID est respectée
- ✅ **Structure XML préservée** : Même format, même ordre, mêmes attributs
- ✅ **Dates cohérentes** : DEB_PER = FIN_PER = jour facturé
- ✅ **Encodage UTF-8** : Préservé sans modification

## 🚀 Installation et utilisation

### Prérequis

- Python 3.8+
- Accès à Streamlit Cloud ou installation locale

### Installation locale

```bash
# Cloner le repository
git clone https://github.com/[votre-compte]/pixid-corrector.git
cd pixid-corrector

# Installer les dépendances (seulement 2 !)
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

### Utilisation

1. **Uploadez** votre fichier XML problématique
2. **L'application détecte** automatiquement le problème
3. **Visualisez** la correction proposée (avant/après)
4. **Cliquez** sur "Appliquer la correction"
5. **Téléchargez** le XML corrigé prêt pour PIXID

## 📊 Exemple concret

### Fichier original (problématique)
```xml
<!-- RAF indique 1 jour (30/06) -->
<TimeCard>
  <PeriodStartDate>2025-06-30</PeriodStartDate>
  <PeriodEndDate>2025-06-30</PeriodEndDate>
  <TimeInterval type="Heures travaillées">
    <Duration>8</Duration>
  </TimeInterval>
</TimeCard>

<!-- Mais la facture contient toute la semaine -->
<Line>
  <Description>Heures travaillées</Description>
  <ItemQuantity uom="HUR">35.00</ItemQuantity> <!-- Problème ! -->
  <Charges><Charge><Total>854.76</Total></Charge></Charges>
</Line>
```

### Fichier corrigé
```xml
<!-- RAF toujours 1 jour (30/06) -->
<TimeCard>
  <PeriodStartDate>2025-06-30</PeriodStartDate>
  <PeriodEndDate>2025-06-30</PeriodEndDate>
  <TimeInterval type="Heures travaillées">
    <Duration>8</Duration>
  </TimeInterval>
</TimeCard>

<!-- La facture ne contient que le jour facturé -->
<Line>
  <Description>Heures travaillées</Description>
  <ItemQuantity uom="HUR">8.00</ItemQuantity> <!-- Corrigé ! -->
  <Charges><Charge><Total>195.37</Total></Charge></Charges>
</Line>
```

## 🔧 Architecture technique

### Simplicité maximale

- **1 seul module Python** : `simple_parser.py` fait tout
- **0 dépendance externe** : Utilise `xml.etree.ElementTree` (inclus dans Python)
- **2 packages pip** : streamlit + python-dateutil seulement
- **Pas de compilation** : Fonctionne partout, immédiatement

### Pourquoi cette simplicité ?

1. **Robustesse** : Moins de code = moins de bugs
2. **Compatibilité** : Fonctionne avec Python 3.8 à 3.13+
3. **Maintenance** : Tout le code métier dans un seul fichier
4. **Performance** : Plus rapide sans surcouches

## 📝 Configuration

Aucune configuration nécessaire ! L'application :
- Détecte automatiquement le format PIXID
- Trouve les TimeCards qu'ils soient en Header ou Line
- Calcule automatiquement les ratios de correction
- Applique la TVA standard (20%)

## ❓ FAQ

**Q : L'application modifie-t-elle la structure XML ?**
R : Non, seules les valeurs sont modifiées. La structure reste identique.

**Q : Que faire si j'ai plusieurs factures à corriger ?**
R : Traitez-les une par une. Une version batch pourrait être développée.

**Q : L'application gère-t-elle tous les cas ?**
R : Elle gère le cas principal (semaine → jour). D'autres cas peuvent être ajoutés.

**Q : Puis-je vérifier avant d'appliquer ?**
R : Oui, l'application montre toujours un aperçu avant/après.

## 🤝 Support et contribution

- **Issues** : Signalez les problèmes sur GitHub
- **Pull Requests** : Les améliorations sont bienvenues
- **Contact** : [Votre email]

## 📜 Licence

MIT - Utilisez librement cette application

---

**Note importante** : Cette application corrige le XML AVANT l'envoi à PIXID. Elle ne peut pas corriger des factures déjà envoyées.
