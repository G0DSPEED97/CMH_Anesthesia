# CMH Anaesthesia Management System

Standalone reception, pre-anaesthetic review, operation scheduling, OT control, and silent television-display software for the CMH Dhaka Department of Anaesthesiology.

The system is deliberately simple for non-technical staff: large controls, role-specific screens, no hidden gestures, no audio cues, and no AI/OCR dependency. It runs on one Windows server PC and is opened by the approved reception, doctor, OT-control, and display computers over the private LAN.

## Workflow

1. **Reception** records army/service number, searchable rank, name, unit, age, sex, proposed surgery, and proposed anaesthetic.
2. The server creates a daily token (for example `A-001`), a Code 128 barcode token PDF, and a two-page A4 anaesthesia form. Configured print queues receive the documents without browser printing.
3. **Anaesthesia doctor** calls the patient, completes the review summary, and selects the future OT date. The patient remains linked to the original reception record even when the operation is days later.
4. The selected date automatically creates that day's **OT roster**. No duplicate typing, image import, OCR, or embedded AI is used.
5. **OT control** assigns a table and moves the patient through `Waiting`, `Called`, `In OT`, `In progress`, `Completed`, or `Cancelled`.
6. The wall television silently alternates between current cases and the next three patients every 10/15 seconds. Both intervals are configurable.

## Technology

- Angular 21 and TypeScript
- Python 3.11+ and FastAPI
- SQLAlchemy, Alembic, and PostgreSQL
- Authenticated WebSocket change notifications
- ReportLab A4/thermal PDFs and OS print queues
- HttpOnly, SameSite=Strict session cookies and PBKDF2-SHA256 password hashes

## Roles

- `admin`: settings and all operational modules
- `reception`: registration, token/form generation, reception list, and reprints
- `doctor`: patient calling, review, and future OT scheduling
- `ot_controller`: daily roster and live OT status
- `auditor`: read-only data access (API foundation included)
- `display`: reception and OT television views only

Every seeded account must replace its generated temporary password on first login. Staff should use separate accounts in production; administrators can create them through the protected user API.

## One-command setup

### Windows deployment PC

Run `RUN_WINDOWS.bat` as Administrator. It checks Python and Node.js, offers to install missing prerequisites through WinGet, installs/starts PostgreSQL 17, creates a restricted `cmh_anesthesia` database role, runs migrations, builds the frontend, seeds initial accounts, and starts the LAN server on port `8200`.

Open `http://127.0.0.1:8200` on the server. Other approved PCs use `http://SERVER-PC-IP:8200`. Configure Windows Firewall so TCP `8200` is accepted only from the CMH private LAN/VLAN.

### macOS development or server

```bash
chmod +x run.sh START_DEV_MAC.sh
./run.sh
```

`run.sh` can install PostgreSQL 17 through Homebrew, creates the database and restricted role, builds both applications, migrates the database, and starts FastAPI on port `8200`.

For daily development after PostgreSQL is ready:

```bash
./START_DEV_MAC.sh
```

Initial passwords are printed only when `.env` is first created. Keep `.env` private and backed up securely.

PostgreSQL is mandatory for application use. SQLite is enabled only inside automated tests. Database schema changes are applied through Alembic rather than automatic table creation; see [PostgreSQL and Alembic operations](docs/DATABASE_OPERATIONS.md).

## Printer setup

The application never invokes the browser print dialog. On submit, the backend generates immutable PDFs and sends them to configured operating-system print queues.

- Token defaults: 80 × 110 mm, Code 128 barcode, configurable width/height and queue name.
- Form: A4, two pages, configurable A4 queue.
- macOS/Linux printing uses `lp`.
- Windows uses SumatraPDF silent printing; set `CMH_ANESTHESIA_SUMATRA_PATH` if installed outside `C:\Program Files\SumatraPDF\SumatraPDF.exe`.
- If a printer is unavailable, patient creation still succeeds and staff can retry from **Reprint token**. A printer failure never loses the patient record.

See [Printer setup](docs/PRINTER_SETUP.md).

## Project records

- [Change history](CHANGELOG.md)
- [PostgreSQL and Alembic operations](docs/DATABASE_OPERATIONS.md)
- Final manager report in `docs/reports/`
- Final presentation and print PDF in `output/`

## Development checks

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/ruff check app tests

cd ../frontend
npm ci
npm run check
```

The frontend production builder runs the Angular AOT compiler followed by esbuild. It is platform-neutral and avoids browser/CDN dependencies, which keeps LAN deployments offline-capable.

## Data protection

This public repository contains no patient data. `References/`, generated PDFs, databases, credentials, build output, and local logs are ignored by Git. The reference photographs supplied for layout work stay only on the development machine because they contain identifiable service/patient details.

Use HTTPS and secure cookies before any deployment that crosses a trusted isolated LAN. Back up PostgreSQL daily to CMH-approved encrypted storage and perform restore drills.

## Army rank data

The initial searchable ranks use the official [Bangladesh Army rank categories](https://www.army.mil.bd/Rank-Categories): commissioned officers, junior commissioned officers, and NCO/soldier grades. Administrators can later extend or deactivate values without changing historical records.
