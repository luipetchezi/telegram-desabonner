import os
import asyncio
import nest_asyncio
import gradio as gr
from fastapi import FastAPI
from telethon.sync import TelegramClient

# Apply nest_asyncio to allow async execution
nest_asyncio.apply()

# API credentials
API_ID = 29652347
API_HASH = '252c2a9543ea390f41388db164332464'

# FastAPI app
app = FastAPI()

# Create an async function to handle Telegram unsubscribing
async def unsubscribe_telegram(phone_number):
    """
    Connects to Telegram, unsubscribes from all channels, and logs out.
    """
    client = TelegramClient("session", API_ID, API_HASH)

    try:
        await client.start(phone_number)
        dialogs = await client.get_dialogs()
        channels = [d for d in dialogs if d.is_channel and not d.is_group]

        total_channels = len(channels)
        for channel in channels:
            try:
                await client.delete_dialog(channel)
            except Exception as e:
                return f"❌ Erreur avec {channel.title}: {e}"

        await client.log_out()
        return f"✅ {total_channels} chaînes supprimées. Déconnecté de Telegram."
    except Exception as e:
        return f"❌ Erreur: {e}"
    finally:
        await client.disconnect()

# Gradio UI
def web_interface(phone_number):
    if not phone_number.startswith("+") or len(phone_number) < 10:
        return "❌ Numéro invalide. Entrez un numéro avec l'indicatif international (ex: +225XXXXXXXXXX)."
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(unsubscribe_telegram(phone_number))
    return result

# Create Gradio Interface
iface = gr.Interface(
    fn=web_interface,
    inputs=gr.Textbox(label="📱 Numéro de téléphone (+225XXXXXXXXXX)"),
    outputs="text",
    title="🔴 Désabonnement Telegram",
    description="Entrez votre numéro pour vous désabonner de toutes les chaînes Telegram.",
    allow_flagging="never"
)

# Run FastAPI with Gradio
@app.get("/")
def home():
    return {"message": "App Telegram Unsubscribe Active"}

@app.get("/run")
def run_app():
    iface.launch(share=True)

# Run with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
