"""
Sauvegarde manuelle/planifiée de kronocolor.db.

Usage :
    python backup_db.py

À exécuter périodiquement via cron (Linux/Mac) ou le Planificateur de tâches
(Windows), par exemple tous les jours à 3h :
    0 3 * * * cd /chemin/vers/kronocolor-python && python3 backup_db.py

Utilise la même fonction que le bouton "Sauvegarder maintenant" de l'admin
(app.backup_database), donc les deux méthodes déposent leurs fichiers au même
endroit (backups/) et respectent la même limite de rétention.
"""
import sys

from app import backup_database

if __name__ == "__main__":
    path = backup_database()
    print(f"Sauvegarde créée : {path}")
    sys.exit(0)
