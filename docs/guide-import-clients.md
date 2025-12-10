# Guide d'Import des Clients dans Tryton

Ce guide explique comment utiliser le script `import_clients.py` pour importer ou mettre à jour la liste des clients dans Tryton à partir d'un fichier CSV.

## 1. Prérequis

*   **Accès au serveur** : Vous devez avoir accès au terminal du serveur où Tryton est déployé via Docker.
*   **Fichier CSV** : Le fichier doit être au format CSV (séparateur point-virgule `;`, encodage UTF-8 recommandé).
    *   **Colonnes attendues** : `Code;Nom;Nom Légal;Adresse;Ville;Province;Code Postal;Pays;Téléphone;Fax;Courriel`
    *   Le fichier est généralement placé dans le dossier `docs/` à la racine du projet (ex: `docs/client-itf.csv`).

## 2. Fonctionnement du Script

Le script (`tryton/scripts/import_clients.py`) effectue les actions suivantes :
*   **Idempotence** : Il vérifie si un client existe déjà (par son `Code`).
    *   Si le client existe, ses informations (adresse, contacts) sont **mises à jour**.
    *   Si le client n'existe pas, il est **créé**.
*   **Pays et Provinces** : Il crée automatiquement le pays ("Canada") et la province (ex: "QC" -> "Québec") s'ils n'existent pas encore dans la base de données.
*   **Nettoyage** :
    *   Les numéros de téléphone sont nettoyés et formatés (ajout de `+1` si nécessaire).
    *   Les doublons d'adresses et de contacts sont évités.

## 3. Exécution sur Production

Le script s'exécute via `docker compose` en montant le dossier contenant votre CSV.

### Commande Standard

Depuis la racine du projet (là où se trouve le `docker-compose.yml`) :

```bash
docker compose run --rm -v $(pwd)/docs:/docs tryton python3 /opt/trytond/scripts/import_clients.py
```

### Explication de la commande
*   `docker compose run --rm tryton` : Lance un conteneur temporaire basé sur le service `tryton`.
*   `-v $(pwd)/docs:/docs` : Monte votre dossier local `docs/` (contenant le CSV) vers le dossier `/docs` à l'intérieur du conteneur.
*   `python3 /opt/trytond/scripts/import_clients.py` : Exécute le script Python situé dans le conteneur.

Le script cherchera automatiquement le fichier à `/docs/client-itf.csv`. Si votre fichier porte un autre nom ou est à un autre endroit, vous devrez modifier le script ou renommer votre fichier.

## 4. Résultats et Logs

Le script affichera la progression dans le terminal :
```text
Début de l'import depuis /docs/client-itf.csv...
...
Import terminé. Créés: 5, Ignorés (existants): 150
```

*   **Erreurs** : Les erreurs spécifiques (ex: format de téléphone impossible à corriger) seront affichées pour chaque ligne problématique, mais n'arrêteront pas l'import global.
