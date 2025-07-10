#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "🚀 Installation des dépendances..."
pip install -r requirements.txt

echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --no-input

echo "🔍 Vérification connexion base NSIA..."
python manage.py check --database default

echo "🗃️ Application des migrations vers base NSIA..."
# ⚠️ ATTENTION : Utiliser --fake-initial car les tables NSIA existent déjà
python manage.py migrate --fake-initial || python manage.py migrate

echo "📊 Vérification des tables existantes..."
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \'public\';')
print(f'Tables trouvées: {cursor.fetchone()[0]}')
"

echo "🎉 Déploiement vers base NSIA terminé avec succès!"