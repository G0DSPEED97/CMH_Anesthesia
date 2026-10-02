# Printer setup

Printer hardware has not yet been selected, so all device-specific values are configuration rather than source code.

## Recommended arrangement

- Install the thermal token printer and A4 laser printer on the Windows server PC.
- Give each printer a stable Windows queue name such as `CMH-Anesthesia-Token` and `CMH-Anesthesia-Form`.
- Install SumatraPDF on the server for silent PDF spooling.
- In **Settings**, enter both queue names, measure the thermal paper, set width/height, and enable automatic printing.

## Safe commissioning

1. Keep both automatic-print switches off.
2. Register a non-patient test record.
3. Open both PDFs and confirm dimensions, barcode readability, margins, and duplex settings.
4. Enable the A4 queue and verify front/back orientation.
5. Enable the thermal queue and verify cutting, darkness, barcode scanning, and text size.
6. Delete the test record directly in the commissioning database before go-live.

The software stores generated PDFs below `backend/data/generated/`; that directory is private and excluded from Git. Printer failure is reported to the user but does not roll back the patient entry.

## Windows environment override

If SumatraPDF is installed elsewhere, add this to `.env`:

```text
CMH_ANESTHESIA_SUMATRA_PATH=C:\Path\To\SumatraPDF.exe
```

Restart the server after changing `.env`.
