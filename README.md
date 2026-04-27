# A2PRACTICE - Plateforme QCM A2SUP

![Version](https://img.shields.io/badge/version-1.0.0-red)
![Flask](https://img.shields.io/badge/Flask-3.0+-blue?logo=flask)

A2PRACTICE est un outil d'entraînement aux QCM développé pour le tutorat A2SUP. Il permet de s'exercer sur la base de données de questions avec un suivi des performances et une interface optimisée.

---

## Fonctionnalités

- Authentification simple par identifiant session.
- Navigation par Unité d'Enseignement (UE).
- Sessions personnalisables :
  - Sélection de chapitres multiples.
  - Modes de tirage : nouvelles questions, focus erreurs, ou aléatoire.
  - Paramétrage de la durée.
- Interface de quiz :
  - Correction immédiate avec affichage des badges Vrai/Faux.
  - Justificatifs détaillés après chaque question.
  - Sauvegarde automatique et cumulative des résultats.
- Statistiques : Historique des tentatives, calcul de moyenne pondérée et progression par chapitre.

---

## Installation et Lancement

### Prérequis
- Python 3.8+
- Flask
- Waitress (recommandé pour la production)

### Procédure
1. Cloner le dépôt :
   ```bash
   git clone https://github.com/DocteurWu/A2SUP-QCM.git
   cd A2SUP-QCM
   ```
2. Installer les dépendances :
   ```bash
   pip install flask waitress
   ```
3. Lancer le serveur :
   ```bash
   python app.py
   ```
   L'application détecte automatiquement la présence de Waitress pour basculer en mode production sur le port 5000.

---

## Structure du Projet

```text
A2SUP/
├── app.py              # Logique serveur Flask et API
├── db.json             # Base de données questions (format JSON)
├── data_sp6.csv        # Source de données initiale (CSV)
├── history.json        # Stockage local de l'historique utilisateurs
├── templates/          # Templates Jinja2
│   ├── login.html      # Connexion
│   ├── dashboard.html  # Sélection UE et stats globales
│   ├── ue.html         # Configuration session et stats chapitres
│   └── quiz.html       # Interface de test et calcul scores
└── README.md           # Documentation technique
```

---

## Mise à jour des questions

Pour intégrer de nouvelles données :
1. Déposer le fichier CSV dans le répertoire racine.
2. Utiliser le script de conversion pour mettre à jour `db.json`.
3. Redémarrer l'application.

---

## Gestion des Utilisateurs

Les identifiants sont actuellement définis dans `app.py`. Pour une gestion externe :
1. Créer un fichier `users.json` (format `{"id": {"name": "Nom"}}`).
2. Charger le fichier dans `app.py` via une fonction `load_users()`.

---

## Authentification par Jeton (URL)

Le site principal `a2sup.fr` peut rediriger vers la plateforme QCM via un jeton sécurisé :
1. Redirection vers `qcm.a2sup.fr/login/sso?token=TOKEN`.
2. Validation du jeton côté serveur pour ouvrir la session.

---

## Maintenance

Projet maintenu par Louaï. Conçu pour être léger, auto-hébergé et résilient.
