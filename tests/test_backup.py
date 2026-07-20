"""Sauvegarde automatique/manuelle de la base de données."""
import os

import app as kronocolor_app
from conftest import register_and_login


def test_backup_database_creates_file_next_to_test_db(client, tmp_path):
    with kronocolor_app.app.app_context():
        path = kronocolor_app.backup_database()
    assert os.path.exists(path)
    assert path.startswith(str(tmp_path))  # jamais dans le vrai dossier du projet
    assert "backups" in path


def test_list_backups_reports_created_file(client):
    with kronocolor_app.app.app_context():
        kronocolor_app.backup_database()
        backups = kronocolor_app.list_backups()
    assert len(backups) == 1
    assert backups[0]["filename"].startswith("kronocolor_")
    assert backups[0]["size_kb"] > 0


def test_backup_prunes_old_files_beyond_max_keep(client, monkeypatch):
    monkeypatch.setattr(kronocolor_app, "BACKUP_MAX_KEEP", 2)
    with kronocolor_app.app.app_context():
        for _ in range(4):
            kronocolor_app.backup_database()
            import time
            time.sleep(1.1)  # les noms de fichiers sont horodatés à la seconde près
        backups = kronocolor_app.list_backups()
    assert len(backups) == 2


def test_admin_can_trigger_backup_manually(client):
    register_and_login(client, email="backup-admin@test.ma", name="Backup Admin",
                        role="admin", code="kronocolor-admin")
    resp = client.post("/admin/backup", follow_redirects=True)
    assert resp.status_code == 200
    assert "Sauvegarde cr".encode("utf-8") in resp.data

    with kronocolor_app.app.app_context():
        backups = kronocolor_app.list_backups()
    assert len(backups) >= 1


def test_backup_section_visible_on_admin_stats_page(client):
    register_and_login(client, email="backup-admin2@test.ma", name="Backup Admin2",
                        role="admin", code="kronocolor-admin")
    resp = client.get("/admin").get_data(as_text=True)
    assert "Sauvegarde de la base de données" in resp
