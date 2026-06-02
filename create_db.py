"""
Internal schema-only initialization — not for manual use.

Full startup (schema, actual user, startup files) runs via bootstrap when you start the app.
See src/bootstrap.py and doc/RUNBOOK.md.
"""

import os
import sys

if os.environ.get('SOIDIED_INTERNAL') != '1':
    print('create_db.py is for internal use only.')
    print('Start the app to initialize the database and startup files:')
    print('  python api.py')
    sys.exit(1)

from src.db.schema import run_standalone_schema_init

run_standalone_schema_init()
