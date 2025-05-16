from flask import Flask, request, jsonify, send_from_directory
import google.generativeai as genai
from flask_cors import CORS
import os
import random

# Gemini API Setup
genai.configure(api_key="AIzaSyAnb5zp7pSuirXWY0YXVGaKt5OkMZ2jG3U")
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

# Dummy RAG Database (without OTPs)
database = [
    {"account_number": f"10000{i}", "emi": f"₹{4000 + i*200}/month", "balance": f"₹{50000 + i*1000}", "user_id": f"USR10{i}"}
    for i in range(10)
]

# In-memory OTP Store
otp_store = {}

app = Flask(__name__, static_folder="frontend")
CORS(app)

# Session Data (in-memory)
session_data = {
    "stage": "greeting",
    "selected_action": None,
    "account_number": None
}

def get_main_menu_text():
    return (
        "Hi! What would you like to do?\n"
        "1. Check EMI\n"
        "2. Check Balance\n"
        "3. Check User ID\n"
        "Please type 1, 2, or 3 to choose."
    )

@app.route("/start")
def start_chat():
    session_data.update({"stage": "greeting", "selected_action": None, "account_number": None})
    reply = get_main_menu_text()
    return jsonify({"reply": reply})

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message").strip().lower()
    stage = session_data["stage"]

    # Step 1: Choose Action
    if stage == "greeting":
        if user_message in ["1", "check emi", "emi"]:
            session_data["selected_action"] = "emi"
        elif user_message in ["2", "check balance", "balance"]:
            session_data["selected_action"] = "balance"
        elif user_message in ["3", "check user id", "user id"]:
            session_data["selected_action"] = "user_id"
        else:
            return jsonify({"reply": "Please type 1, 2, or 3 to choose: Check EMI, Check Balance, or Check User ID."})
        
        session_data["stage"] = "awaiting_account"
        return jsonify({"reply": "Please enter your account number:"})

    # Step 2: Enter Account Number
    elif stage == "awaiting_account":
        account_number = user_message
        session_data["account_number"] = account_number
        account_exists = any(acc["account_number"] == account_number for acc in database)
        if account_exists:
            otp = str(random.randint(1000, 9999))
            otp_store[account_number] = otp
            session_data["stage"] = "awaiting_otp"
            return jsonify({"reply": f"OTP generated: {otp}\nPlease enter the OTP sent to your registered number."})
        else:
            return jsonify({"reply": "Invalid account number. Please try again."})

    # Step 3: Enter OTP
    elif stage == "awaiting_otp":
        account_number = session_data["account_number"]
        otp = user_message
        if otp_store.get(account_number) == otp:
            account = next(acc for acc in database if acc["account_number"] == account_number)
            data_key = session_data["selected_action"]
            # Create formatted response for each type
            if data_key == "emi":
                reply = (
                    f"### EMI Details\n\n"
                    f"Okay, I understand. The user's monthly EMI (Equated Monthly Installment) is {account[data_key]}.\n"
                    f"Is there anything else I can help you with regarding this EMI? For example, are you interested in calculating:\n"
                    f"* **The loan amount?** This requires knowing the interest rate and loan tenure.\n"
                    f"* **The total interest paid?** This also requires the interest rate and loan tenure.\n"
                    f"* **The remaining loan amount?** This would need the number of EMIs already paid.\n"
                    f"* **Something else?** Please provide more details if you have a specific question.\n\n"
                    + get_main_menu_text()
                )
            elif data_key == "balance":
                reply = (
                    f"### Balance Details\n\n"
                    f"The balance for account number {account_number} is {account[data_key]}.\n\n"
                    + get_main_menu_text()
                )
            else:  # user_id
                reply = (
                    f"### User ID Details\n\n"
                    f"The User ID associated with account number {account_number} is {account[data_key]}.\n\n"
                    + get_main_menu_text()
                )

            # Reset session to allow new queries
            session_data.update({"stage": "greeting", "selected_action": None, "account_number": None})
            otp_store.pop(account_number, None)
            return jsonify({"reply": reply, "close_otp": True})
        else:
            # Reset on invalid OTP
            session_data.update({"stage": "greeting", "selected_action": None, "account_number": None})
            otp_store.pop(account_number, None)
            reply = "Invalid OTP. Process restarted.\n\n" + get_main_menu_text()
            return jsonify({"reply": reply, "close_otp": True})

    else:
        # Reset fallback
        session_data.update({"stage": "greeting", "selected_action": None, "account_number": None})
        return jsonify({"reply": "Please type 'hi' to start again.\n\n" + get_main_menu_text()})

# Serve static frontend
@app.route("/")
def serve_index():
    return send_from_directory("frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("frontend", path)

if __name__ == "__main__":
    app.run(debug=True)
