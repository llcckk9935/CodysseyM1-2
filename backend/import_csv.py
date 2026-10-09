"""Explicit initial import; existing dates are never overwritten."""
import csv
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from app.models import DataInput, serialize_input
from app.repository import get_repository


def read_rows(path):
    with open(path, encoding='cp949', newline='') as f:
        rows = list(csv.DictReader(f))
    result = []
    seen = set()
    for row in rows:
        payload = DataInput(date=datetime.strptime(row['구분'], '%Y년%m월%d일').date(),
                            value=row['보통휘발유'])
        record = serialize_input(payload)
        if record['date'] in seen:
            raise ValueError('Duplicate date')
        seen.add(record['date'])
        result.append(record)
    return result


if __name__ == '__main__':
    load_dotenv()
    records = read_rows(Path(sys.argv[1]))
    repo = get_repository()
    from google.api_core.exceptions import AlreadyExists
    imported = skipped = 0
    for record in records:
        try:
            repo.collection.document(record['date']).create({**record, 'source': '한국석유공사 오피넷 (사용자 제공 CSV)',
                 'is_modified': False, 'original_value': record['value']})
            imported += 1
        except AlreadyExists:
            skipped += 1
    print({'imported': imported, 'existing_skipped': skipped})
