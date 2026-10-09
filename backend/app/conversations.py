from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4
from app.repository import get_repository, Missing, Conflict


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class RateLimited(Exception):
    pass


class ConversationRepository:
    def __init__(self, db):
        self.db = db
        self.collection = db.collection('conversations')

    def create(self, owner, title, messages, **extra):
        identifier = str(uuid4())
        now = timestamp()
        record = {'owner': owner, 'title': title, 'messages': messages,
                  'created_at': now, 'updated_at': now, 'revision': 1, **extra}
        self.collection.document(identifier).create(record)
        return {'id': identifier, **record}

    def get(self, owner, identifier):
        snap = self.collection.document(identifier).get()
        if not snap.exists or snap.to_dict().get('owner') != owner:
            raise Missing()
        return {'id': snap.id, **snap.to_dict()}

    def list(self, owner):
        from google.cloud.firestore_v1.base_query import FieldFilter
        rows = []
        for d in self.collection.where(filter=FieldFilter('owner', '==', owner)).stream():
            r = d.to_dict()
            rows.append({'id': d.id, 'title': r['title'], 'created_at': r['created_at'],
                         'updated_at': r['updated_at'], 'message_count': len(r['messages'])})
        return sorted(rows, key=lambda r: r['updated_at'], reverse=True)

    def append(self, owner, identifier, revision, messages, **extra):
        from firebase_admin import firestore
        ref = self.collection.document(identifier)

        @firestore.transactional
        def change(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists or snap.to_dict().get('owner') != owner:
                raise Missing()
            r = snap.to_dict()
            if r['revision'] != revision:
                raise Conflict()
            if len(r['messages']) + len(messages) > 100:
                raise Conflict()
            r.update(messages=r['messages'] + messages, revision=revision+1,
                     updated_at=timestamp(), **extra)
            tx.set(ref, r)
            return {'id': identifier, **r}
        return change(self.db.transaction())

    def delete(self, owner, identifier):
        from firebase_admin import firestore
        ref = self.collection.document(identifier)

        @firestore.transactional
        def remove(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists or snap.to_dict().get('owner') != owner:
                raise Missing()
            tx.delete(ref)
        remove(self.db.transaction())

    def reserve_chat(self, owner, per_minute, daily_max):
        """Count attempted requests persistently before calling OpenAI."""
        from firebase_admin import firestore
        now = datetime.now(timezone.utc)
        minute = now.strftime('%Y%m%d%H%M')
        day = now.strftime('%Y%m%d')
        user_ref = self.db.collection('chat_limits').document(owner)
        global_ref = self.db.collection('chat_limits').document('global')

        @firestore.transactional
        def reserve(tx):
            user = user_ref.get(transaction=tx).to_dict() or {}
            total = global_ref.get(transaction=tx).to_dict() or {}
            user_count = user.get('count', 0) if user.get('minute') == minute else 0
            total_count = total.get('count', 0) if total.get('day') == day else 0
            if user_count >= per_minute or total_count >= daily_max:
                raise RateLimited()
            tx.set(user_ref, {'minute': minute, 'count': user_count+1})
            tx.set(global_ref, {'day': day, 'count': total_count+1})
        reserve(self.db.transaction())


@lru_cache
def get_conversations():
    return ConversationRepository(get_repository().db)
