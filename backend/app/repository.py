import json
import os
from functools import lru_cache


class Conflict(Exception):
    pass


class Missing(Exception):
    pass


class FirestoreRepository:
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore
        key = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if not key and not path:
            raise RuntimeError('Firestore credentials are not configured')
        credential = credentials.Certificate(json.loads(key) if key else path)
        try:
            app = firebase_admin.get_app('fuel-assistant')
        except ValueError:
            app = firebase_admin.initialize_app(credential, name='fuel-assistant')
        self.db = firestore.client(app)
        self.collection = self.db.collection('data')

    def list(self):
        return sorted([{'id': d.id, **d.to_dict()} for d in self.collection.stream()],
                      key=lambda r: r['date'])

    def create(self, payload):
        from google.api_core.exceptions import AlreadyExists
        record = {**payload, 'source': 'user', 'is_modified': False, 'original_value': None}
        try:
            self.collection.document(payload['date']).create(record)
        except AlreadyExists as exc:
            raise Conflict() from exc
        return {'id': payload['date'], **record}

    def update(self, identifier, payload):
        from firebase_admin import firestore
        ref = self.collection.document(identifier)

        @firestore.transactional
        def change(transaction):
            snap = ref.get(transaction=transaction)
            if not snap.exists:
                raise Missing()
            old = snap.to_dict()
            if payload['date'] != old['date']:
                raise Conflict()
            original = old.get('original_value')
            record = {**old, **payload, 'is_modified':
                      payload['value'] != original if original is not None else False}
            transaction.set(ref, record)
            return {'id': identifier, **record}
        return change(self.db.transaction())

    def delete(self, identifier):
        from firebase_admin import firestore
        ref = self.collection.document(identifier)

        @firestore.transactional
        def remove(transaction):
            if not ref.get(transaction=transaction).exists:
                raise Missing()
            transaction.delete(ref)
        remove(self.db.transaction())


@lru_cache
def get_repository():
    return FirestoreRepository()
