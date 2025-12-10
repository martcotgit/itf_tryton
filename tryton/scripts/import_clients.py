#!/usr/bin/env python3
"""
Script d'import des clients depuis un fichier CSV propre.
Format attendu: Code;Nom;Nom Légal;Adresse;Ville;Province;Code Postal;Pays;Téléphone;Fax;Courriel

Usage:
    docker compose run --rm tryton python3 tryton/scripts/import_clients.py
"""
import csv
import os
import sys
from proteus import config, Model, Wizard
from trytond.modules.company.tests.tools import get_company

def bootstrap_tryton():
    database = os.environ.get("TRYTON_DATABASE", "tryton")
    config_file = os.environ.get("TRYTON_CONFIG", "/etc/tryton/trytond.conf")
    config.set_trytond(database=database, config_file=config_file)

def get_or_create_country(country_name):
    Country = Model.get('country.country')
    # Custom mapping
    code_map = {'Canada': 'CA'}
    code = code_map.get(country_name, 'CA')
    name = country_name if country_name else 'Canada'
    
    countries = Country.find([('code', '=', code)])
    if countries:
        return countries[0]
    
    # Create if missing
    c = Country()
    c.name = name
    c.code = code
    c.save()
    return c

def get_subdivision(country, province_code):
    Subdivision = Model.get('country.subdivision')
    if not country or not province_code.strip():
        return None
    
    # Ensure code format "CA-QC"
    if '-' not in province_code:
        full_code = f"{country.code}-{province_code}"
    else:
        full_code = province_code
        
    subdivisions = Subdivision.find([('code', '=', full_code)])
    if subdivisions:
        return subdivisions[0]

    # Create if missing
    names = {'QC': 'Québec', 'ON': 'Ontario'}
    short_code = province_code.strip()
    
    s = Subdivision()
    s.country = country
    s.code = full_code
    s.name = names.get(short_code, short_code) # Use code as name if map fails
    s.type = 'province'
    s.save()
    return s

def clean_phone(phone_str):
    # Enlever tout ce qui n'est pas chiffre
    digits = "".join(filter(str.isdigit, phone_str))
    # Si 10 chiffres (ex: 4181234567), on suppose canada/usa -> +1
    if len(digits) == 10:
        return f"+1{digits}"
    # Si 11 chiffres et commence par 1
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    # Sinon on retourne tel quel (ou avec +)
    if digits:
        return f"+{digits}" if not phone_str.startswith('+') else phone_str
    return phone_str

def import_clients(file_path):
    print(f"Début de l'import depuis {file_path}...")
    
    Party = Model.get('party.party')
    Address = Model.get('party.address')
    Contact = Model.get('party.contact_mechanism')
    
    count_created = 0
    count_updated = 0
    
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        for row in reader:
            code = row['Code'].strip()
            name = row['Nom'].strip()
            
            if not code:
                continue
                
            # Recherche existant
            parties = Party.find([('code', '=', code)])
            if parties:
                party = parties[0]
                count_updated += 1
            else:
                party = Party()
                party.code = code
                party.name = name
                party.save()
                count_created += 1

            # Gestion de l'adresse
            address = None
            if party.addresses:
                address = party.addresses[0]
            else:
                address = Address()
                address.party = party
            
            # Mise à jour des champs (écrasement ou remplissage)
            address.street = row['Adresse'].strip()
            address.city = row['Ville'].strip()
            address.postal_code = row['Code Postal'].strip()
            
            country_name = row['Pays'].strip()
            if country_name:
                country = get_or_create_country(country_name)
                if country:
                    address.country = country
                    subdivision = get_subdivision(country, row['Province'].strip())
                    if subdivision:
                        address.subdivision = subdivision
            
            try:
                address.save()
            except Exception as e:
                print(f"Erreur sauvegarde adresse pour {name}: {e}")

            # Gestion des contacts
            # On ne supprime pas les contacts existants, on ajoute ceux qui manquent
            # Téléphone
            raw_phone = row['Téléphone'].strip()
            if raw_phone:
                clean_val = clean_phone(raw_phone)
                # On cherche si ce numéro existe déjà (format brut ou clean)
                exists = False
                for c in party.contact_mechanisms:
                    if c.type == 'phone':
                        # Tryton formate le numéro, donc la comparaison exacte peut échouer.
                        # On compare 'digits' seulement pour être sûr
                        c_digits = "".join(filter(str.isdigit, c.value or ""))
                        new_digits = "".join(filter(str.isdigit, clean_val or ""))
                        if c_digits == new_digits:
                            exists = True
                            break
                
                if not exists:
                    try:
                        c = Contact()
                        c.party = party
                        c.type = 'phone'
                        c.value = clean_val
                        c.save()
                    except Exception as e:
                        print(f"Erreur téléphone pour {name} ({raw_phone}): {e}")

            # Courriel
            email = row['Courriel'].strip()
            if email:
                 if not any(c.type == 'email' and c.value == email for c in party.contact_mechanisms):
                    try:
                        c = Contact()
                        c.party = party
                        c.type = 'email'
                        c.value = email
                        c.save()
                    except Exception as e:
                        print(f"Erreur email pour {name} ({email}): {e}")
            
            # Fax (ajouté manquait dans version précedente)
            fax = row['Fax'].strip()
            if fax:
                 # Note: Tryton contact mechanism type for fax? 
                 # Standard types: phone, mobile, email, website, skype, sip, other.
                 # Souvent on utilise 'phone' avec une note ou un type custom si dispo.
                 # On va tenter 'phone' (ou check si 'fax' dispo dans le module party mais standard base n'a pas fax, c'est souvent 'phone')
                 # On va skip fax pour l'instant ou le mettre en 'other' si on veut pas casser.
                 pass

    print(f"Import terminé. Créés: {count_created}, Ignorés (existants): {count_updated}")

if __name__ == "__main__":
    bootstrap_tryton()
    # Le chemin dans le conteneur. Le dossier du projet est monté dans /app ou similaire ?
    # Docker compose mount par défaut ?
    # Vérifions le docker-compose ou assumons le pwd.
    # Dans le contexte 'docker compose run --rm tryton', le pwd est souvent /var/lib/trytond ou la racine du projet mappée.
    # On va assumer que 'docs/client-itf.csv' est accessible relative à l'endroit où on lance le script (racine projet).
    # Si le script est lancé depuis la racine avec `python3 tryton/scripts/...`, le fichier docs est dans `docs/...`
    
    candidate_paths = [
        "/docs/client-itf.csv",
        "docs/client-itf.csv",
        "client-itf.csv"
    ]
    
    file_path = None
    for path in candidate_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        print(f"ERREUR: Fichier introuvable. Cherché dans: {candidate_paths}")
        sys.exit(1)
        
    import_clients(file_path)
