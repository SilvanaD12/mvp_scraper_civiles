"""Historial inmutable de consultas y descargas; conexión por operación/hilo."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .connection import DatabaseConnection


def identity(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def procedure_identity(row: dict) -> str:
    return identity({k: row.get(k) for k in ('nomenclatura', 'entidad', 'publicado_en', 'descripcion', 'objeto_contratacion', 'cui_texto')})


class ReferencesRepository:
    def __init__(self, path: Path):
        self.path = path
        with DatabaseConnection(path) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS reference_events (
                    id INTEGER PRIMARY KEY, source TEXT NOT NULL,
                    kind TEXT NOT NULL, subject TEXT NOT NULL,
                    created_at TEXT NOT NULL, payload_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS seace_procedures (
                    identity TEXT PRIMARY KEY, nomenclatura TEXT NOT NULL,
                    entidad TEXT, publicado_en TEXT, descripcion TEXT,
                    monto_texto TEXT, moneda TEXT, payload_json TEXT NOT NULL,
                    last_seen TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reference_documents (
                    identity TEXT PRIMARY KEY, source TEXT NOT NULL,
                    parent_key TEXT NOT NULL, name TEXT NOT NULL,
                    stage TEXT, published_at TEXT, payload_json TEXT NOT NULL,
                    last_seen TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS document_downloads (
                    id INTEGER PRIMARY KEY, source TEXT NOT NULL,
                    parent_key TEXT NOT NULL, local_path TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                    downloaded_at TEXT NOT NULL, payload_json TEXT NOT NULL);
            ''')

    def save(self, payload: dict) -> int:
        now = datetime.now(timezone.utc).isoformat()
        payload.setdefault('extraido_en', now)
        encoded = json.dumps(payload, ensure_ascii=False)
        source, kind = payload['fuente'], payload['tipo']
        with DatabaseConnection(self.path) as db:
            cursor = db.execute(
                'INSERT INTO reference_events(source,kind,subject,created_at,payload_json) VALUES(?,?,?,?,?)',
                (source, kind, payload['asunto'], payload['extraido_en'], encoded))
            event_id = cursor.lastrowid
            if source == 'SEACE' and kind == 'busqueda':
                for row in payload['registros']:
                    # Conservative identity: a nomenclature alone is insufficient.
                    key = procedure_identity(row)
                    db.execute('''INSERT INTO seace_procedures VALUES(?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(identity) DO UPDATE SET monto_texto=excluded.monto_texto,
                        moneda=excluded.moneda,payload_json=excluded.payload_json,last_seen=excluded.last_seen''',
                        (key, row['nomenclatura'], row.get('entidad'), row.get('publicado_en'),
                         row.get('descripcion'), row.get('monto_texto'), row.get('moneda'),
                         json.dumps(row, ensure_ascii=False), now))
            for doc in payload.get('documentos', []):
                parent = payload['parent_key']
                key = identity({'source': source, 'parent': parent,
                                'name': doc.get('documento', doc.get('nombre')),
                                'stage': doc.get('etapa'), 'date': doc.get('publicado_en'),
                                'file': doc.get('archivo_texto', doc.get('url_descarga'))})
                db.execute('''INSERT INTO reference_documents VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(identity) DO UPDATE SET payload_json=excluded.payload_json,last_seen=excluded.last_seen''',
                    (key, source, parent, doc.get('documento', doc.get('nombre', 'Documento')),
                     doc.get('etapa'), doc.get('publicado_en'), json.dumps(doc, ensure_ascii=False), now))
            if kind == 'descarga':
                info = payload['descarga']
                db.execute('''INSERT INTO document_downloads
                    (source,parent_key,local_path,sha256,size_bytes,downloaded_at,payload_json)
                    VALUES(?,?,?,?,?,?,?)''',
                    (source, payload['parent_key'], info['ruta_local'], info['sha256'],
                     info['tamanio_bytes'], now, encoded))
        return event_id

    def recent(self, limit: int = 150) -> list[dict]:
        with DatabaseConnection(self.path) as db:
            rows = db.fetch_all('SELECT id,source,kind,subject,created_at FROM reference_events ORDER BY id DESC LIMIT ?', (limit,))
        return [dict(row) for row in rows]

    def get(self, event_id: int) -> dict:
        with DatabaseConnection(self.path) as db:
            row = db.fetch_one('SELECT payload_json FROM reference_events WHERE id=?', (event_id,))
        if row is None:
            raise ValueError('La consulta guardada ya no existe.')
        return json.loads(row['payload_json'])
