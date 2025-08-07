import os
import json
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from feedback_bot import router

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Пример: https://iposuda.onrender.com

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

app = FastAPI()


@app.on_event("startup")
async def startup():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")


@app.on_event("shutdown")
async def shutdown():
    await bot.delete_webhook()
    await bot.session.close()


@app.post("/webhook")
async def handle_webhook(req: Request):
    raw_body = await req.body()
    print("🔔 Входящий апдейт:", raw_body.decode())
    update = Update.model_validate(json.loads(raw_body))
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": "Bot is running (Render Webhook Mode)"}
