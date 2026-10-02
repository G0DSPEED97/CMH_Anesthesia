# PostgreSQL and Alembic Operations

CMH Anaesthesia uses PostgreSQL for every normal development, demonstration, pilot, and production deployment. SQLite is limited to isolated automated tests and is rejected by the application unless the test flag is enabled.

## Database responsibility

The deployment owner must provide a PostgreSQL database, an application role with access only to that database, and a protected `CMH_ANESTHESIA_DATABASE_URL`. The repository contains no live credentials or patient data.

The supplied Mac and Windows launchers create or connect to the `cmh_anesthesia` database, install the Python driver, run Alembic migrations, seed the controlled reference data, and then start the application.

## Schema migration workflow

Run all Alembic commands from the `backend` directory after loading the project environment.

```bash
alembic current
alembic upgrade head
alembic history
```

For a schema change, update the SQLAlchemy model, generate a candidate revision, inspect the generated upgrade and downgrade operations, and test both directions against a disposable PostgreSQL database.

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Commit the model change and migration revision together. Do not use `Base.metadata.create_all()` in application startup or deployment scripts because it bypasses migration history and cannot provide an auditable upgrade path.

## Deployment sequence

1. Back up the current PostgreSQL database.
2. Stop application access or place the department in the approved maintenance window.
3. Deploy the tagged application revision.
4. Run `alembic upgrade head` once from the server.
5. Run `python -m app.seed` to add any missing reference values without replacing existing records.
6. Start the application and verify `/api/v1/health`.
7. Test login, patient search, roster retrieval, and display updates with synthetic records.

## Backup and restore

Use CMH-approved encrypted storage. A practical daily backup command is:

```bash
pg_dump --format=custom --file=cmh_anesthesia_YYYYMMDD.dump cmh_anesthesia
```

Restore drills should use a separate database and must be recorded. A backup is not considered operationally reliable until a restore has completed successfully.

```bash
createdb cmh_anesthesia_restore_test
pg_restore --clean --if-exists --no-owner --dbname=cmh_anesthesia_restore_test cmh_anesthesia_YYYYMMDD.dump
```

The IT head should approve the backup location, retention period, restore-test frequency, PostgreSQL administrator custody, and the maintenance window before live patient use.
