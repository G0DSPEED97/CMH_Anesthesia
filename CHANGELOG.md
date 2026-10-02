# Changelog

All notable project changes are recorded here. The project follows semantic versioning and keeps deployment-ready changes on the `main` branch after review.

## 1.0.0 2026-10-03

### Added

- Reception registration for army or service number, searchable rank, name, unit, age, sex, proposed surgery, and proposed anaesthetic.
- Daily token numbering, Code 128 token PDF generation, and a two-page pre-anaesthetic form.
- Doctor review and future operation-date scheduling from the original reception record.
- Daily OT roster, six operational statuses, optimistic record-version checks, and audit logging.
- Silent television display that rotates between active cases and the next three patients.
- Role-based authentication, real-time WebSocket notifications, printer-queue integration, and Mac and Windows launchers.
- PostgreSQL provisioning, Alembic initial schema migration, database operations guide, and PostgreSQL-only application configuration.
- Manager presentation, printable presentation PDF, and project experience report.

### Revised

- Replaced the first presentation screenshots with 1422 by 800 pixel captures after the initial images were found to be unsuitable for projection and printing.
- Reworked the presentation cover to show the full OT display instead of a cropped patient name.
- Removed automatic table creation from application startup and seed execution so Alembic remains the schema authority.

### Deployment decisions still required

- Select the thermal token printer and confirm its paper dimensions.
- Confirm the A4 printer queues, CMH private network addressing, HTTPS policy, backup destination, retention period, and production user list.
