# AI Wheel Design Studio

> Démonstrateur IA — marketplace de jantes 3D avec interpolation précalculée

## Description

Application interactive de marketplace de jantes 3D avec interpolation précalculée entre designs.
Le visiteur peut sélectionner deux modèles de jantes et explorer visuellement la transition géométrique entre les deux.

## Stack technique

- **Python** + **Streamlit** pour l'interface web
- **Plotly** pour la visualisation 3D interactive
- **trimesh** pour le chargement des fichiers STL
- **NumPy** pour le traitement numérique

## Structure du projet

```
app_jpo/
├── app.py                  # Application Streamlit principale
├── requirements.txt        # Dépendances Python
├── README.md               # Ce fichier
├── data/
│   └── rims.json           # Manifeste des jantes
└── assets/
    ├── styles.css          # CSS personnalisé
    ├── logo.jpg
    ├── stellantis_logo.png
    ├── images/             # Aperçus PNG des jantes
    └── stl/
        └── interpolations/ # Interpolations précalculées
            ├── rim_XX__rim_YY/
            │   ├── step_00.stl
            │   └── ...
            └── ...
```

## Installation locale

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Ajout de données

### Images de prévisualisation

Placez des fichiers PNG (carrés, 512x512 px recommandé) dans `assets/images/` nommés selon le format `rim_XX.png`.

### Interpolations précalculées

Pour chaque paire de jantes `(rim_XX, rim_YY)` avec XX < YY :

1. Créez un dossier `assets/stl/interpolations/rim_XX__rim_YY/`
2. Placez-y les fichiers `step_00.stl`, `step_01.stl`, ..., `step_NN.stl`
3. Le nombre de steps peut varier de 10 à 20 selon la paire

L'application découvre dynamiquement les fichiers disponibles.

## Mode démo (sans assets)

L'application démarre même sans fichiers STL ou images :
- Les images manquantes affichent un placeholder élégant
- Les STL manquants affichent un message d'erreur explicite
- Aucune géométrie de substitution n'est générée

## Note sur le mode autoplay

Le mode autoplay (animation automatique du slider) n'est pas implémenté car Streamlit ne supporte pas nativement les boucles d'animation côté serveur sans rerun répétitif, ce qui rendrait l'application instable lors d'une démonstration publique. Pour un autoplay fiable, une solution serait d'intégrer un composant JavaScript custom.

## Contraintes de la démo

- Aucune IA exécutée au runtime
- Aucune connexion GPU requise
- Aucun accès internet requis
- Aucune connexion à un endpoint de modèle
- Toutes les interpolations sont précalculées
- Application optimisée pour une utilisation répétée
