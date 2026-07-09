import os

from flask import Flask, jsonify, request
from flask_cors import CORS

import ifc_ops

app = Flask(__name__)
CORS(app)

# Fase 2 (nedlasting/opplasting via Trimble Connect REST API) er ikke bygget ennå.
# Inntil videre peker backend-en på én lokal IFC-fil, satt via miljøvariabelen IFC_FIL
# (kan overstyres per request med "ifc_fil" i JSON-bodyen). Når TC REST-integrasjonen
# kommer, er det kun denne stien som byttes ut med "last ned til temp-fil, kjør, last opp
# igjen" — selve ifcopenshell-logikken i ifc_ops.py trenger ingen endring.
STANDARD_IFC_FIL = os.environ.get("IFC_FIL", "")


def _ifc_sti(payload):
    sti = payload.get("ifc_fil") or STANDARD_IFC_FIL
    if not sti:
        return None
    return sti


@app.route("/api/status")
def api_status():
    return jsonify({
        "ifc_fil": STANDARD_IFC_FIL,
        "finnes": bool(STANDARD_IFC_FIL and os.path.isfile(STANDARD_IFC_FIL)),
    })


@app.route("/api/vimpel", methods=["POST"])
def api_vimpel():
    d = request.json or {}
    sti = _ifc_sti(d)
    if not sti or not os.path.isfile(sti):
        return jsonify({"error": "IFC-fil ikke funnet (satt via IFC_FIL eller 'ifc_fil' i requesten): " + str(sti)}), 400
    if not d.get("guid"):
        return jsonify({"error": "Mangler 'guid'"}), 400

    item = {
        "type": "vimpel",
        "guid": d["guid"],
        "merknad": d.get("merknad", ""),
        "utfort_av": d.get("utfort_av", ""),
        "disiplin": d.get("disiplin", ""),
        "prosjekt": d.get("prosjekt", ""),
        "revisjonsnummer": d.get("revisjonsnummer", ""),
        "revisjonen_gjelder": d.get("revisjonen_gjelder", ""),
        "flagg_farge": d.get("flagg_farge", "#CC0000"),
    }
    try:
        resultater = ifc_ops.behandle_items(sti, [item])
        ok, melding = resultater[0]
        return jsonify({"ok": ok, "melding": melding}), (200 if ok else 400)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farge", methods=["POST"])
def api_farge():
    d = request.json or {}
    sti = _ifc_sti(d)
    if not sti or not os.path.isfile(sti):
        return jsonify({"error": "IFC-fil ikke funnet (satt via IFC_FIL eller 'ifc_fil' i requesten): " + str(sti)}), 400
    if not d.get("guid"):
        return jsonify({"error": "Mangler 'guid'"}), 400

    item = {
        "type": "farge",
        "guid": d["guid"],
        "farge": d.get("farge", "#CC0000"),
        "merknad": d.get("merknad", ""),
        "utfort_av": d.get("utfort_av", ""),
        "disiplin": d.get("disiplin", ""),
        "prosjekt": d.get("prosjekt", ""),
        "revisjonsnummer": d.get("revisjonsnummer", ""),
        "revisjonen_gjelder": d.get("revisjonen_gjelder", ""),
    }
    try:
        resultater = ifc_ops.behandle_items(sti, [item])
        ok, melding = resultater[0]
        return jsonify({"ok": ok, "melding": melding}), (200 if ok else 400)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fjern-vimpel", methods=["POST"])
def api_fjern_vimpel():
    d = request.json or {}
    sti = _ifc_sti(d)
    if not sti or not os.path.isfile(sti):
        return jsonify({"error": "IFC-fil ikke funnet (satt via IFC_FIL eller 'ifc_fil' i requesten): " + str(sti)}), 400
    if not d.get("guid"):
        return jsonify({"error": "Mangler 'guid'"}), 400

    item = {"type": "fjern-vimpel", "guid": d["guid"]}
    try:
        resultater = ifc_ops.behandle_items(sti, [item])
        ok, melding = resultater[0]
        return jsonify({"ok": ok, "melding": melding}), (200 if ok else 400)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n  Merknader-backend startet (Fase 2 — lokal fil, ingen Trimble Connect REST API ennå).")
    print("  IFC_FIL =", STANDARD_IFC_FIL or "(ikke satt — send 'ifc_fil' i hver request)")
    print("  http://localhost:5003\n")
    app.run(debug=False, port=5003, threaded=True)
