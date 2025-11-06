from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import qrcode
from io import BytesIO
import base64
import traceback

app = Flask(__name__, template_folder="templates")
CORS(app)  # permite chamadas de qualquer origem durante dev

# Dados fixos
NAME = "Marcos Gabriel Geraldo Aragão"
CPF = "66378260494"
EMAIL = "cgcousingroup@gmail.com"

BASE_URL = "https://api.syncpayments.com.br/api/v1/payment-link"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://app.syncpayments.com.br",
    "Referer": "https://app.syncpayments.com.br/"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    try:
        # tenta JSON primeiro (retorna None se não é JSON)
        body = request.get_json(silent=True)
        if body is None:
            # tenta form data
            body = request.form.to_dict()
        if not body:
            # tenta query params (por segurança)
            body = request.args.to_dict()

        print("---- REQUISICAO RECEBIDA (/gerar_pix) ----")
        print("Headers:", dict(request.headers))
        print("Raw data length:", len(request.get_data() or b""))
        print("Parsed body:", body)

        # aceita vários nomes
        link_id = body.get("link_id") or body.get("api_url") or body.get("linkId")
        valor = body.get("valor") or body.get("amount") or body.get("value")

        # tenta converter para float
        try:
            valor = float(valor) if valor is not None and str(valor) != "" else 0.0
        except Exception:
            valor = 0.0

        if not link_id or valor <= 0:
            return jsonify({"success": False, "error": "Dados inválidos: link_id e valor obrigatórios", "received": body}), 400

        api_url = f"{BASE_URL}/{link_id}/qrcode"

        payloads = [
            {"name": NAME, "document": CPF, "email": EMAIL, "amount": valor},
            {"name": NAME, "document": {"number": CPF, "type": "cpf"}, "email": EMAIL, "amount": valor},
            {"payer": {"name": NAME, "email": EMAIL, "document": {"number": CPF, "type": "cpf"}}, "amount": valor},
        ]

        # tenta cada formato
        for payload in payloads:
            try:
                r = requests.post(api_url, json=payload, headers=HEADERS, timeout=15)
                print("POST", api_url, "status:", r.status_code)
                try:
                    resp_json = r.json()
                except Exception:
                    resp_json = {"raw_text": r.text[:500]}
                print("Resposta SyncPayments:", resp_json)
            except Exception as e:
                print("Erro ao conectar SyncPayments:", e)
                continue

            pix_code = resp_json.get("pix_code") or (resp_json.get("data") or {}).get("pix_code")
            if pix_code:
                qr = qrcode.make(pix_code)
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                return jsonify({"success": True, "pix_code": pix_code, "qrcode_base64": qr_b64})

        return jsonify({"success": False, "error": "Não foi possível obter pix_code da SyncPayments."}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


