import os
import asyncio

import gradio as gr
import nest_asyncio
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.errors import PhoneNumberInvalidError

# Only needed if this code runs inside an already active event loop
nest_asyncio.apply()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "telegram_unsubscribe")

# FastAPI app
app = FastAPI(title="Telegram Unsubscribe")


def validate_phone(phone_number: str) -> bool:
    return bool(phone_number) and phone_number.startswith("+") and len(phone_number) >= 10


async def unsubscribe_telegram(phone_number: str) -> str:
    """
    Connects to Telegram, unsubscribes from all channels, and logs out.
    """
    if not validate_phone(phone_number):
        return "❌ Numéro invalide. Entrez un numéro avec l'indicatif international (ex: +225XXXXXXXXXX)."

    if not API_ID or not API_HASH:
        return "❌ Configurez TELEGRAM_API_ID et TELEGRAM_API_HASH dans votre environnement."

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            return "❌ Session Telegram non autorisée. Authentifiez-vous depuis Telegram avant de relancer l'opération."

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
    except PhoneNumberInvalidError:
        return "❌ Numéro de téléphone invalide."
    except Exception as exc:
        return f"❌ Erreur: {exc}"
    finally:
        await client.disconnect()


# Gradio UI

def web_interface(phone_number: str):
    return asyncio.run(unsubscribe_telegram(phone_number))


iface = gr.Interface(
    fn=web_interface,
    inputs=gr.Textbox(label="📱 Numéro de téléphone (+225XXXXXXXXXX)"),
    outputs="text",
    title="🔴 Désabonnement Telegram",
    description="Entrez votre numéro pour vous désabonner de toutes les chaînes Telegram.",
    flagging_mode="never",
    allow_flagging=False,
)


@app.get("/")
def home():
    return {"message": "App Telegram Unsubscribe Active"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7860)
