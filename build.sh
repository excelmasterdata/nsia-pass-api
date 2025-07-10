#!/usr/bin/env bash
set -o errexit

echo "🚀 Installation des dépendances..."
pip install -r requirements.txt

echo "📁 Collecte des fichiers statiques Django..."
python manage.py collectstatic --no-input --clear

echo "🔍 Vérification connexion base NSIA..."
python manage.py check --database default

echo "🗃️ Application des migrations..."
python manage.py migrate --fake-initial || python manage.py migrate

echo "🎉 Déploiement terminé avec succès!"