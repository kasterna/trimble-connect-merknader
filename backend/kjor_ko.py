"""Kjør en kø av vimpel/fjern-vimpel-handlinger (eksportert fra Merknader-extensionen)
mot en lokal IFC-fil, uten server eller Trimble Connect REST API.

Bruk:
    python kjor_ko.py <ifc_fil> <ko_fil.json>

Filen redigeres i-place (atomisk temp-fil + rename, se ifc_ops.behandle_items).
Bruk en KOPI av IFC-filen — ikke originalen fra Trimble Connect.
"""
import argparse
import json
import sys

import ifc_ops


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ifc_fil", help="Sti til IFC-filen som skal endres (redigeres i-place, atomisk).")
    parser.add_argument("ko_fil", help="Sti til kø-JSON-filen eksportert fra Merknader-extensionen.")
    args = parser.parse_args()

    with open(args.ko_fil, "r", encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        items = [items]

    if not items:
        print("Tom kø, ingenting å gjøre.")
        return

    resultater = ifc_ops.behandle_items(args.ifc_fil, items)

    feil = 0
    for item, (ok, melding) in zip(items, resultater):
        prefix = "OK  " if ok else "FEIL"
        print(f"{prefix} [{item.get('type')}] {melding}")
        if not ok:
            feil += 1

    print()
    print(f"Ferdig: {len(resultater) - feil}/{len(resultater)} OK.")
    sys.exit(1 if feil else 0)


if __name__ == "__main__":
    main()
