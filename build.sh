#!/usr/bin/env bash
set -o errexit

echo "🚀 Installation des dépendances..."
pip install -r requirements.txt

echo "📁 Création forcée du dossier staticfiles..."
mkdir -p staticfiles

echo "🎨 Collecte FORCÉE des fichiers statiques..."
python manage.py collectstatic --no-input --clear --verbosity 2

echo "📋 Vérification du contenu staticfiles..."
ls -la staticfiles/ || echo "Dossier staticfiles vide"

echo "🔍 Vérification Django..."
python manage.py check

echo "🗃️ Migrations (si base NSIA accessible)..."
python manage.py migrate --fake-initial || echo "Migration ignorée"

echo "🎉 Build terminé!"