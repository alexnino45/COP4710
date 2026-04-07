# COP4710 Reading List Project - Reorganized Structure

This version reorganizes the project so each teammate can work in a clean area without overlapping responsibilities.

## Folder ownership

- `app.py` - main Flask entry point shared by backend team
- `routes/` - Tomas and Alex backend routes
- `templates/` and `static/` - Avery frontend pages and styling
- `database/` - Christian database setup, schema, and SQLite file
- `data/` - Kaggle and support CSV files
- `docs/` - project writeups and change log

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Rebuild the database if needed:
   `python database/setup_database.py`
4. Run Flask:
   `python app.py`

## Week 2 backend deliverables

- Homepage route connected
- Login page route connected
- User page route connected
- Create user route implemented
- Database helper separated for reuse

## Suggested team workflow

- Tomas and Alex add backend logic inside `routes/`
- Avery replaces placeholder templates with final UI
- Christian updates schema and setup script when database changes are approved
- Keep docs updated in `docs/` so the written report matches the codebase
