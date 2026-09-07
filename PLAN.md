# Wheel Design Studio — PLAN

## Structure des assets

```
assets/
  images/        PNG des 6 roues (database drag-and-drop)
  stl/
    interpolations/  Dossiers A_to_B (15 fichiers interpolation_0.stl … interpolation_14.stl)
                     Meshes décimés à 90% (~3 MB/fichier au lieu de ~30 MB originaux)
  logo.jpg
  stellantis_logo.png
  styles.css

Note : les STL originaux (originals/) ont été supprimés — seuls les PNG sont utilisés
pour l'affichage des thumbnails. Les interpolations sont décimées pour rester < 10 MB
(limite de taille par fichier du déploiement Databricks Apps).
  logo.jpg
  stellantis_logo.png
  styles.css
data/
  rims.json      Manifest principal
```

## Identifiants lisibles (display_id / name)

| Clé interne (id)                                         | display_id | name           |
|----------------------------------------------------------|------------|----------------|
| 50_LB_Wheel_Rim_255_20by9_surface                        | W01        | 50 LB 255      |
| PRODUIT+4141B3D35C2129E44141B3D35C2250A7_--D__IN_WORK    | W02        | Produit 250A7  |
| PRODUIT+4141B2BD074708B84141B2BD09E85D41_---__SHARED     | W03        | Produit 5D41   |
| IB_6-36-2613_Complete_Rim                                | W04        | IB 36-2613     |
| 20_FC00ABF33420-005_NM_surface                           | W05        | FC00ABF33420   |
| IB_6-4580-252_Rim                                        | W06        | IB 4580-252    |

- `display_id` (W01…W06) est affiché en gros dans la card et la thumbnail.
- `name` (court, lisible) est affiché en sous-titre.
- L'`id` technique complet n'est jamais affiché dans l'UI.

## Logique d'interpolation

- Les dossiers s'appellent `A_to_B` (séparateur `_to_`).
- **Affichage principal** : PNG (`interpolation_0.png` … `interpolation_14.png`).
- **Visualisation 3D** : STL décimés (`interpolation_0.stl` … `interpolation_14.stl`),
  accessibles via le bouton "Voir le modèle" qui ouvre un popup `@st.dialog`.
- Le slider utilise les indices numériques extraits des noms de fichiers PNG.
- `interpolation_reverse` est stocké dans `st.session_state`.

## Interpolations disponibles (14 paires)

```
PRODUIT+...250A7_to_PRODUIT+...5D41
PRODUIT+...250A7_to_IB_6-4580-252_Rim
PRODUIT+...250A7_to_50_LB_Wheel_Rim_255_20by9_surface
PRODUIT+...250A7_to_20_FC00ABF33420-005_NM_surface
PRODUIT+...5D41_to_IB_6-4580-252_Rim
PRODUIT+...5D41_to_50_LB_Wheel_Rim_255_20by9_surface
PRODUIT+...5D41_to_20_FC00ABF33420-005_NM_surface
IB_6-36-2613_Complete_Rim_to_PRODUIT+...250A7
IB_6-36-2613_Complete_Rim_to_PRODUIT+...5D41
IB_6-36-2613_Complete_Rim_to_IB_6-4580-252_Rim
IB_6-36-2613_Complete_Rim_to_50_LB_Wheel_Rim_255_20by9_surface
IB_6-36-2613_Complete_Rim_to_20_FC00ABF33420-005_NM_surface
50_LB_Wheel_Rim_255_20by9_surface_to_IB_6-4580-252_Rim
50_LB_Wheel_Rim_255_20by9_surface_to_20_FC00ABF33420-005_NM_surface
```

## Conventions de code

- Nommage des fonctions : snake_case
- Données d'état dans `st.session_state` avec clés documentées
- Pas de noms complets de fichier exposés dans l'UI
- Streamlit + Plotly (pas matplotlib) pour la visu 3D
