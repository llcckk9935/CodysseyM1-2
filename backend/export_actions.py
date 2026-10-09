"""Export the deployed Actions schema without embedding any secrets."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from app.routers.actions import actions_schema

if __name__ == '__main__':
    load_dotenv()
    schema = actions_schema(os.getenv('ACTIONS_PUBLIC_BASE_URL', ''))
    output = Path(__file__).resolve().parents[1] / 'docs/actions-openapi.json'
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)
