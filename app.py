import os

import gradio as gr
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "telegram_unsubscribe")

app = FastAPI(title="Telegram Unsubscribe")

AUTH_STATE = {
    "client": None,
    "phone": None,
    "code_sent": False,
}


def validate_phone(phone_number: str) -> bool:
    return bool(phone_number) and phone_number.startswith("+") and len(phone_number) >= 10


async def _get_client():
    if AUTH_STATE["client"] is None:
        AUTH_STATE["client"] = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    return AUTH_STATE["client"]


async def send_code(phone_number: str):
    if not validate_phone(phone_number):
        return "❌ Numéro invalide. Entrez un numéro international valide (ex: +225XXXXXXXXXX)."

    if not API_ID or not API_HASH:
        return "❌ Configurez TELEGRAM_API_ID et TELEGRAM_API_HASH dans votre environnement."

    try:
        client = await _get_client()
        await client.connect()
        await client.send_code_request(phone_number)
        AUTH_STATE["phone"] = phone_number
        AUTH_STATE["code_sent"] = True
        return "✅ Code envoyé. Entrez le code reçu de Telegram, puis cliquez sur 'Se connecter'."
    except PhoneNumberInvalidError:
        return "❌ Numéro de téléphone invalide."
    except Exception as exc:
        return f"❌ Erreur lors de l'envoi du code: {exc}"


async def login(phone_number: str, code: str, password: str):
    if not validate_phone(phone_number):
        return "❌ Numéro invalide."

    if not code:
        return "❌ Entrez le code reçu sur Telegram avant de vous connecter."

    client = await _get_client()

    try:
        await client.connect()
        if password:
            await client.sign_in(phone_number, code, password=password)
        else:
            await client.sign_in(phone_number, code)

        if await client.is_user_authorized():
            AUTH_STATE["phone"] = phone_number
            AUTH_STATE["code_sent"] = False
            return "✅ Connexion réussie. Vous pouvez maintenant désabonner des chaînes."
        return "❌ La connexion n'a pas été confirmée."
    except SessionPasswordNeededError:
        return "⚠️ Votre compte Telegram utilise une authentification à deux facteurs. Entrez votre mot de passe puis réessayez."
    except PhoneCodeInvalidError:
        return "❌ Code de vérification invalide. Demandez un nouveau code et réessayez."
    except Exception as exc:
        return f"❌ Erreur lors de la connexion: {exc}"


async def unsubscribe_all():
    client = await _get_client()

    try:
        await client.connect()
        if not await client.is_user_authorized():
            return "❌ Vous n'êtes pas connecté à Telegram. Connectez-vous d'abord."

        dialogs = await client.get_dialogs()
        channels = [
            d for d in dialogs
            if getattr(d, "is_channel", False) and not getattr(d, "is_group", False)
        ]

        deleted_count = 0
        for channel in channels:
            try:
                await client.delete_dialog(channel)
                deleted_count += 1
            except Exception as exc:
                return f"❌ Erreur avec {getattr(channel, 'title', 'canal')}: {exc}"

        await client.log_out()
        return f"✅ {deleted_count} chaînes supprimées. Déconnecté de Telegram."
    except Exception as exc:
        return f"❌ Erreur: {exc}"
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


with gr.Blocks(title="Désabonnement Telegram") as demo:
    gr.Markdown("# Désabonnement Telegram\nConnectez-vous à Telegram pour supprimer toutes les chaînes auxquelles vous êtes abonné.")

    with gr.Row():
        phone = gr.Textbox(label="📱 Numéro de téléphone", placeholder="+225XXXXXXXXXX")

    with gr.Row():
        code = gr.Textbox(label="🔐 Code reçu (si demandé)", placeholder="12345")
        password = gr.Textbox(label="🔒 Mot de passe (2FA, optionnel)", type="password", placeholder="Laissez vide si vous n'avez pas de 2FA")

    status = gr.Textbox(label="Statut", lines=5)

    with gr.Row():
        send_code_btn = gr.Button("Envoyer le code")
        login_btn = gr.Button("Se connecter")
        unsubscribe_btn = gr.Button("Désabonner")

    send_code_btn.click(send_code, inputs=phone, outputs=status)
    login_btn.click(login, inputs=[phone, code, password], outputs=status)
    unsubscribe_btn.click(unsubscribe_all, inputs=None, outputs=status)


@app.get("/")
def home():
    return {"message": "App Telegram Unsubscribe Active"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7860)
