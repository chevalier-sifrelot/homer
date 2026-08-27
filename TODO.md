# TODO

Questions de conception et prochaines étapes pour le projet Homer.
Ces points sont des sujets de réflexion à trancher, pas encore des tâches figées.

## 1. Prise en compte de différents types de fichiers en entrée

Aujourd'hui les sources sont uniquement du `.txt` (traduction en prose de Butler,
découpée en `BOOK I`…`BOOK XXIV`).

- Étudier l'ingestion d'autres formats : PDF, EPUB, HTML, XML/TEI, scans + OCR.
- Introduire une étape de **normalisation vers un format pivot** (texte brut segmenté par livre) pour découpler l'extraction du format source.
- Gérer la segmentation quand le découpage en livres n'existe pas nativement dans le fichier.
- Conserver la **traçabilité de la source** (page / ligne / offset) pour fiabiliser l'attribution des citations.
- Prévoir la coexistence de plusieurs sources/éditions d'une même œuvre.

## 2. Bonnes pratiques de réflexion et de vérification (fiches non triviales)

Quand la création d'une fiche n'est pas simple : personnage ambigu, sources
contradictoires ou lacunaires, homonymes, noms romains vs grecs, figures mineures.

- Définir une **méthode reproductible** : collecte des passages → tri → sélection des citations → rédaction → vérification.
- Documenter les cas limites et les décisions prises (ex. quel nom retenir, quelle affiliation).
- Prévoir un **mode brouillon** où les incertitudes sont explicites et doivent être levées avant validation.
- Décider du comportement quand une information attendue est absente des sources (champ vide ? note ? fiche partielle ?).
- Envisager une **relecture croisée** (second regard humain et/ou agent) pour les fiches sensibles.

## 3. Insertion de l'approche dans un processus existant

Où et comment brancher cette base dans un flux de travail réel.

- **Traduction** : gérer plusieurs traductions/éditions, versionnage, cohérence des noms d'une source à l'autre.
- **Partage de fichiers** : format d'export, publication (site statique ?), gestion des droits et des accès.
- **Capitalisation** : réutilisation des fiches, interconnexion avec d'autres bases de connaissances, pérennité.
- **Outillage** : hook pre-commit / CI exécutant `verif/verify.py`, génération automatique d'index et de vues.

## 4. Vérification / contrôle de la qualité et de la couverture

Au-delà de la conformité au template (déjà assurée par `verif/verify.py`).

- **Qualité du contenu** : vérifier automatiquement que chaque citation est réellement présente dans les sources (contrôle du verbatim) et que le livre cité est le bon.
- **Couverture** : comparer la liste des personnages/lieux attendus à ceux réellement présents, pour détecter les manques.
- **Cohérence transversale** : liens bidirectionnels (`Ruler` ↔ `Inhabitants`, `Origin` ↔ personnages), absence de liens cassés, cohérence des affiliations.
- **Faire vérifier** : définir un protocole de relecture humaine (échantillonnage) et/ou une vérification adversariale par agents.
