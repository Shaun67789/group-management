from fastapi import FastAPI, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import secrets
from typing import Optional
from fastapi.templating import Jinja2Templates
import uvicorn
import os

from database import db
from bot_manager import bot_manager

app = FastAPI()

os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    if db.get_config().get("is_running", False):
        bot_manager.start_bot()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = db.get_config()
    stats = db.get_all_stats()
    
    # Get all users and groups for the tables
    with db.lock:
        raw_data = db._read()
        users = raw_data.get("users", {})
        groups = raw_data.get("groups", {})
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": config,
        "stats": stats,
        "users": users,
        "groups": groups
    })

@app.post("/api/broadcast")
async def broadcast_message(
    request: Request,
    message: str = Form(""),
    target: str = Form("groups") # "groups" or "users"
):
    if not bot_manager.bot:
        return RedirectResponse(url="/?error=BotNotRunning", status_code=303)
        
    with db.lock:
        raw_data = db._read()
        items = raw_data.get(target, {}).keys()
        
    count = 0
    for item_id in items:
        try:
            bot_manager.bot.send_message(int(item_id), f"📢 <b>ADMIN BROADCAST</b>\n\n{message}", parse_mode="HTML")
            count += 1
        except:
            pass
            
    return RedirectResponse(url=f"/?success=BroadcastSentTo{count}", status_code=303)

@app.post("/api/toggle")
async def toggle_bot(request: Request):
    config = db.get_config()
    current_status = config.get("is_running", False)
    new_status = not current_status
    db.update_config("is_running", new_status)
    
    if new_status:
        bot_manager.start_bot()
    else:
        bot_manager.stop_bot()
        
    return RedirectResponse(url="/", status_code=303)

@app.post("/api/settings")
async def update_settings(
    request: Request,
    bot_token: str = Form(""),
    owner_username: str = Form("")
):
    owner_username = owner_username.replace("@", "")
    db.update_config("bot_token", bot_token.strip())
    db.update_config("owner_username", owner_username.strip())
    
    config = db.get_config()
    if config.get("is_running", False):
        bot_manager.restart_bot()
        
    return RedirectResponse(url="/", status_code=303)

@app.post("/api/remote_action")
async def remote_action(
    request: Request,
    group_id: str = Form(""),
    user_id: str = Form(""),
    action: str = Form("")
):
    if not bot_manager.bot:
        return RedirectResponse(url="/?error=BotNotRunning", status_code=303)
        
    try:
        chat_id = int(group_id.strip())
        target_id = int(user_id.strip())
        
        if action == "ban":
            bot_manager.bot.ban_chat_member(chat_id, target_id)
            message = "User Banned"
        elif action == "kick":
            bot_manager.bot.ban_chat_member(chat_id, target_id)
            bot_manager.bot.unban_chat_member(chat_id, target_id)
            message = "User Kicked"
        elif action == "promote":
            bot_manager.bot.promote_chat_member(chat_id, target_id, 
                can_change_info=True, can_post_messages=True, can_edit_messages=True,
                can_delete_messages=True, can_invite_users=True, can_restrict_members=True,
                can_pin_messages=True, can_promote_members=False)
            message = "User Promoted"
        else:
            return RedirectResponse(url="/?error=InvalidAction", status_code=303)
            
        return RedirectResponse(url=f"/?success={message}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=303)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
