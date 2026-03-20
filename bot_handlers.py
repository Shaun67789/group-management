import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import logging

logger = logging.getLogger(__name__)

def is_admin(bot, chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

def is_owner(username):
    config = db.get_config()
    owner = config.get("owner_username", "OwnerUser123")
    if not username: return False
    return username.lower().replace("@", "") == owner.lower()

def can_act_on(bot, chat_id, executor_id, executor_username, target_id, target_username):
    if is_owner(executor_username):
        return True # Owner can do anything
    if is_owner(target_username):
        return False # Nobody can act on the owner
    if is_admin(bot, chat_id, target_id):
        return False # Admins cannot be acted upon by other admins
    return True

def get_target_user(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    
    parts = message.text.split()
    if len(parts) > 1:
        target = parts[1].replace("@", "")
        # telebot doesn't easily translate username to user_id without a local cache or reply
        # So typically ID is expected if not reply
        try:
            return int(target)
        except ValueError:
            return None # Username resolution requires a database or MTProto
    return None

def register_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        db.ensure_user(message.from_user.id, name=message.from_user.first_name)
        if message.chat.type in ['group', 'supergroup']:
            db.ensure_group(message.chat.id)
            
        markup = InlineKeyboardMarkup()
        config = db.get_config()
        owner = config.get("owner_username", "OwnerUser123")
        bot_username = bot.get_me().username
        
        markup.add(
            InlineKeyboardButton("👤 Contact Owner", url=f"https://t.me/{owner}"),
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{bot_username}?startgroup=true")
        )
        markup.add(InlineKeyboardButton("📜 Commands & Help", callback_data="show_help"))
        
        text = (f"<b>✨ Hello {message.from_user.first_name}! I am the Ultimate Group Manager</b>\n\n"
                "I bring high-end command-and-control features to your Telegram communities. From advanced moderation to smart automation, I'm here to ensure your group stays safe and active.\n\n"
                "🛡️ <b>Key Pillars:</b>\n"
                "• <b>Security:</b> Robust ban/mute/warn engines.\n"
                "• <b>Utility:</b> Admin tools like pin/del/promote.\n"
                "• <b>Engagement:</b> Custom filters and greetings.\n\n"
                "<i>Tap the button below for a full list of commands!</i>")
        bot.reply_to(message, text, reply_markup=markup, parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: call.data == "show_help")
    def help_callback(call):
        cmd_help(call.message)
        bot.answer_callback_query(call.id)

    @bot.message_handler(commands=['help'])
    def cmd_help(message):
        text = ("<b>🛠️ Bot Commands List</b>\n\n"
                "<b>🛡️ Moderation:</b>\n"
                "• /ban - Permanent ban\n"
                "• /unban - Revoke ban\n"
                "• /kick - Remove user (can rejoin)\n"
                "• /mute - Silence user\n"
                "• /unmute - Restore chat\n"
                "• /warn - Formal warning (3 = ban)\n\n"
                "<b>👮 Admin Tools:</b>\n"
                "• /lock - Lock group (Admins only)\n"
                "• /unlock - Unlock group\n"
                "• /promote - Give admin rights\n"
                "• /demote - Remove admin rights\n"
                "• /settitle - Change group name\n"
                "• /setdesc - Change group description\n"
                "• /pin - Pin message\n"
                "• /unpin - Unpin all\n"
                "• /del - Delete message\n"
                "• /report - Alert group admins\n"
                "• /link - Get group invite link\n\n"
                "<b>🤖 Automation & Auto-Mod:</b>\n"
                "• /setwelcome - Set greeting\n"
                "• /setrules - Set group rules\n"
                "• /rules - Show group rules\n"
                "• /addfilter - Create auto-reply\n"
                "• /filters - List active filters\n"
                "• /addbadword - Add word to auto-mod\n"
                "• /delbadword - Remove auto-mod word\n"
                "• /antispam - Toggle Link Protection (on/off)\n\n"
                "<b>📊 Information:</b>\n"
                "• /info - User profile & status\n"
                "• /admins - List all group admins\n"
                "• /start - Premium bot intro")
        
        if message.chat.type == 'private':
            bot.send_message(message.chat.id, text, parse_mode="HTML")
        else:
            bot.reply_to(message, "I've sent the command list to your Private Messages! 📥")
            try:
                bot.send_message(message.from_user.id, text, parse_mode="HTML")
            except:
                bot.reply_to(message, "Please start me in Private Chat first so I can send you the help menu.")

    @bot.message_handler(commands=['info'])
    def cmd_info(message):
        db.ensure_user(message.from_user.id, name=message.from_user.first_name)
        target = get_target_user(message)
        
        if not target:
            target_user = message.from_user
        elif isinstance(target, int):
            user_data = db.get_user(target)
            name = user_data.get("name", "Unknown") if user_data else "Unknown"
            class TempUser:
                id = target
                first_name = name
                username = None
            target_user = TempUser()
        else:
            target_user = target
            
        user_data = db.get_user(target_user.id)
        warnings = user_data.get("warnings", 0) if user_data else 0
        
        role = "Member"
        status_text = "Standard"
        bio = "N/A"
        
        if message.chat.type in ['group', 'supergroup']:
            try:
                member_info = bot.get_chat_member(message.chat.id, target_user.id)
                if member_info.status == 'creator':
                    role = "👑 Owner / Creator"
                elif member_info.status == 'administrator':
                    role = "🛡️ Administrator"
                elif member_info.status == 'restricted':
                    role = "⚠️ Restricted User"
                
                # Try to get more info if it's a real user object
                if hasattr(target_user, 'username') and target_user.username:
                    status_text = f"@{target_user.username}"
            except:
                pass

        if is_owner(getattr(target_user, 'username', None)):
            role = "⭐ Global Owner"
            
        text = (f"<b>👤 Deep User Intelligence</b>\n\n"
                f"<b>📛 Name:</b> {target_user.first_name}\n"
                f"<b>🆔 ID:</b> <code>{target_user.id}</code>\n"
                f"<b>🎭 Role:</b> {role}\n"
                f"<b>🌐 Username:</b> {status_text}\n"
                f"<b>⚠️ Warnings:</b> {warnings}/3\n"
                f"<b>📅 First Seen:</b> {'Recorded' if user_data else 'New Arrival'}\n"
                f"<b>📡 Status:</b> {'Premium Active' if message.from_user.is_premium else 'Free Tier'}")
        bot.reply_to(message, text, parse_mode="HTML")

    @bot.message_handler(commands=['admins'])
    def cmd_admins(message):
        if message.chat.type not in ['group', 'supergroup']: return
        try:
            admins = bot.get_chat_administrators(message.chat.id)
            text = f"<b>🛡️ Administrators in {message.chat.title}</b>\n\n"
            for admin in admins:
                symbol = "👑" if admin.status == 'creator' else "🛡️"
                name = admin.user.first_name
                if admin.user.is_bot: continue
                text += f"{symbol} {name} (<code>{admin.user.id}</code>)\n"
            bot.reply_to(message, text, parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to fetch admin list: {e}")

    @bot.message_handler(commands=['ban'])
    def cmd_ban(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        
        target = get_target_user(message)
        if not target:
            return bot.reply_to(message, "Reply to a user or provide their ID to ban.")
            
        t_id = target if isinstance(target, int) else target.id
        t_uname = None if isinstance(target, int) else target.username
        
        if not can_act_on(bot, message.chat.id, message.from_user.id, message.from_user.username, t_id, t_uname):
            return bot.reply_to(message, "⚠️ Cannot perform this action on this user (Admin/Owner protection).")
            
        try:
            bot.ban_chat_member(message.chat.id, t_id)
            bot.reply_to(message, f"🔨 User <code>{t_id}</code> has been banned.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to ban: {str(e)}")

    @bot.message_handler(commands=['kick'])
    def cmd_kick(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user or provide their ID to kick.")
        t_id = target if isinstance(target, int) else target.id
        t_uname = None if isinstance(target, int) else target.username
        if not can_act_on(bot, message.chat.id, message.from_user.id, message.from_user.username, t_id, t_uname): return
        
        try:
            bot.ban_chat_member(message.chat.id, t_id)
            bot.unban_chat_member(message.chat.id, t_id) # Kicks and unbans so they can join back
            bot.reply_to(message, f"👢 User <code>{t_id}</code> has been kicked from the group.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to kick: {str(e)}")

    @bot.message_handler(commands=['mute'])
    def cmd_mute(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user or provide their ID.")
        t_id = target if isinstance(target, int) else target.id
        if not can_act_on(bot, message.chat.id, message.from_user.id, message.from_user.username, t_id, getattr(target, 'username', None)): return
        
        try:
            bot.restrict_chat_member(message.chat.id, t_id, can_send_messages=False)
            bot.reply_to(message, f"🔇 User <code>{t_id}</code> has been muted.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, str(e))

    @bot.message_handler(commands=['unmute'])
    def cmd_unmute(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user or provide their ID.")
        t_id = target if isinstance(target, int) else target.id
        
        try:
            bot.restrict_chat_member(message.chat.id, t_id,
                can_send_messages=True, can_send_media_messages=True, 
                can_send_other_messages=True, can_add_web_page_previews=True)
            bot.reply_to(message, f"🔊 User <code>{t_id}</code> has been unmuted.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, str(e))

    @bot.message_handler(commands=['unban'])
    def cmd_unban(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user or provide their ID.")
        t_id = target if isinstance(target, int) else target.id
        
        try:
            bot.unban_chat_member(message.chat.id, t_id, only_if_banned=True)
            bot.reply_to(message, f"🕊️ User <code>{t_id}</code> has been unbanned.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, str(e))

    @bot.message_handler(commands=['warn'])
    def cmd_warn(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user or provide their ID.")
        t_id = target if isinstance(target, int) else target.id
        if not can_act_on(bot, message.chat.id, message.from_user.id, message.from_user.username, t_id, getattr(target, 'username', None)): return
        
        warnings = db.add_warning(t_id, getattr(target, 'first_name', 'Unknown'))
        
        if warnings >= 3:
            try:
                bot.ban_chat_member(message.chat.id, t_id)
                db.reset_warnings(t_id)
                bot.reply_to(message, f"⚠️ User <code>{t_id}</code> reached 3 warnings and was banned.", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, f"⚠️ User reached 3 warnings, but I couldn't ban them: {e}")
        else:
            bot.reply_to(message, f"⚠️ User <code>{t_id}</code> warned. ({warnings}/3)", parse_mode="HTML")

    @bot.message_handler(commands=['del'])
    def cmd_del(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        if not message.reply_to_message: return bot.reply_to(message, "Reply to a message to delete it.")
        try:
            bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

    @bot.message_handler(commands=['promote'])
    def cmd_promote(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user to promote them.")
        t_id = target if isinstance(target, int) else target.id
        
        try:
            bot.promote_chat_member(message.chat.id, t_id, 
                can_change_info=True, can_post_messages=True, can_edit_messages=True,
                can_delete_messages=True, can_invite_users=True, can_restrict_members=True,
                can_pin_messages=True, can_promote_members=False)
            bot.reply_to(message, f"⏫ User <code>{t_id}</code> has been promoted to Admin!", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to promote: {e}")

    @bot.message_handler(commands=['demote'])
    def cmd_demote(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        
        target = get_target_user(message)
        if not target: return bot.reply_to(message, "Reply to a user to demote them.")
        t_id = target if isinstance(target, int) else target.id
        
        if not can_act_on(bot, message.chat.id, message.from_user.id, message.from_user.username, t_id, getattr(target, 'username', None)):
            return bot.reply_to(message, "⚠️ Protection: Cannot demote this user.")
            
        try:
            bot.promote_chat_member(message.chat.id, t_id, 
                can_change_info=False, can_post_messages=False, can_edit_messages=False,
                can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                can_pin_messages=False, can_promote_members=False)
            bot.reply_to(message, f"⏬ User <code>{t_id}</code> has been demoted.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to demote: {e}")

    @bot.message_handler(commands=['pin'])
    def cmd_pin(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        if not message.reply_to_message: return bot.reply_to(message, "Reply to a message to pin it.")
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Message pinned!")
        except Exception as e:
            bot.reply_to(message, str(e))

    @bot.message_handler(commands=['unpin'])
    def cmd_unpin(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        try:
            bot.unpin_all_chat_messages(message.chat.id)
            bot.reply_to(message, "📌 All messages unpinned!")
        except Exception as e:
            bot.reply_to(message, str(e))

    @bot.message_handler(commands=['report'])
    def cmd_report(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not message.reply_to_message: return bot.reply_to(message, "Reply to a message to report it to admins.")
        try:
            admins = bot.get_chat_administrators(message.chat.id)
            for admin in admins:
                if not admin.user.is_bot:
                    bot.send_message(admin.user.id, f"🚨 <b>Report from {message.chat.title}</b>\n\n"
                                                      f"Reported by: {message.from_user.first_name}\n"
                                                      f"Message: <a href='https://t.me/c/{str(message.chat.id)[4:]}/{message.reply_to_message.message_id}'>View Message</a>", parse_mode="HTML")
            bot.reply_to(message, "🚨 Admins have been notified.")
        except Exception as e:
            pass

    @bot.message_handler(commands=['setwelcome'])
    def cmd_setwelcome(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            db.update_group_setting(message.chat.id, "welcome_message", parts[1])
            bot.reply_to(message, "✅ Welcome message updated!\nUse {name} or {id} to format.")
        else:
            bot.reply_to(message, "Provide the welcome text.")

    @bot.message_handler(content_types=['new_chat_members'])
    def welcome_new_member(message):
        group = db.get_group(message.chat.id)
        if not group: return
        welcome_text = group.get("welcome_message", "Welcome {name}!")
        for member in message.new_chat_members:
            if member.id == bot.get_me().id: continue
            text = welcome_text.replace("{name}", member.first_name).replace("{id}", str(member.id))
            bot.send_message(message.chat.id, text, parse_mode="HTML")

    @bot.message_handler(commands=['setrules'])
    def cmd_setrules(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            db.update_group_setting(message.chat.id, "rules", parts[1])
            bot.reply_to(message, "✅ Rules updated!")

    @bot.message_handler(commands=['rules'])
    def cmd_rules(message):
        if message.chat.type not in ['group', 'supergroup']: return
        group = db.get_group(message.chat.id)
        if group:
            bot.reply_to(message, group.get("rules", "No rules set."))

    @bot.message_handler(commands=['addfilter'])
    def cmd_addfilter(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        
        parts = message.text.split(None, 1)
        if len(parts) < 2: return bot.reply_to(message, "Format: /addfilter <keyword> by replying to media/text.")
        keyword = parts[1].strip()
        
        if not message.reply_to_message:
            return bot.reply_to(message, "You must reply to the media or text you want to set as the filter.")
            
        m = message.reply_to_message
        filter_data = {}
        if m.text:
            filter_data = {"type": "text", "text": m.text}
        elif m.photo:
            filter_data = {"type": "photo", "file_id": m.photo[-1].file_id, "caption": m.caption or ""}
        elif m.sticker:
            filter_data = {"type": "sticker", "file_id": m.sticker.file_id}
        elif m.animation:
            filter_data = {"type": "gif", "file_id": m.animation.file_id}
        else:
            return bot.reply_to(message, "Unsupported media type.")
            
        db.add_filter(message.chat.id, keyword, filter_data)
        bot.reply_to(message, f"✅ Filter '{keyword}' added successfully!")

    @bot.message_handler(commands=['filters'])
    def cmd_list_filters(message):
        if message.chat.type not in ['group', 'supergroup']: return
        group = db.get_group(message.chat.id)
        if not group or not group.get("filters"):
            return bot.reply_to(message, "No filters defined for this group.")
        
        fts = group["filters"].keys()
        text = "<b>🔍 Active Group Filters:</b>\n\n" + "\n".join([f"• {f}" for f in fts])
        bot.reply_to(message, text, parse_mode="HTML")

    @bot.message_handler(commands=['lock'])
    def cmd_lock(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        try:
            bot.set_chat_permissions(message.chat.id, telebot.types.ChatPermissions(can_send_messages=False))
            bot.reply_to(message, "🔒 <b>Group Locked!</b> Regular members can no longer send messages.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to lock: {e}")

    @bot.message_handler(commands=['unlock'])
    def cmd_unlock(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        try:
            bot.set_chat_permissions(message.chat.id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            bot.reply_to(message, "🔓 <b>Group Unlocked!</b> Regular members can now speak.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"Failed to unlock: {e}")

    @bot.message_handler(commands=['link'])
    def cmd_link(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        try:
            invite_link = bot.export_chat_invite_link(message.chat.id)
            bot.reply_to(message, f"🔗 <b>Secure Invite Link:</b>\n{invite_link}", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, "⚠️ Failed to fetch link. Ensure I have the 'Invite Users' admin permission.")

    @bot.message_handler(commands=['addbadword'])
    def cmd_addbadword(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            word = parts[1].strip().lower()
            group = db.get_group(message.chat.id)
            bad_words = group.get("bad_words", [])
            if word not in bad_words:
                bad_words.append(word)
                db.update_group_setting(message.chat.id, "bad_words", bad_words)
            bot.reply_to(message, f"🔇 <b>Auto-Mod Update:</b> Added '{word}' to the active filter list.", parse_mode="HTML")
        else:
            bot.reply_to(message, "Format: /addbadword <word>")

    @bot.message_handler(commands=['delbadword'])
    def cmd_delbadword(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            word = parts[1].strip().lower()
            group = db.get_group(message.chat.id)
            bad_words = group.get("bad_words", [])
            if word in bad_words:
                bad_words.remove(word)
                db.update_group_setting(message.chat.id, "bad_words", bad_words)
                bot.reply_to(message, f"✅ Removed '{word}' from the auto-mod filter.")
            else:
                bot.reply_to(message, "That word is not in the filter.")
        else:
            bot.reply_to(message, "Format: /delbadword <word>")

    @bot.message_handler(commands=['antispam'])
    def cmd_antispam(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split()
        if len(parts) > 1 and parts[1].lower() in ['on', 'off']:
            status = (parts[1].lower() == 'on')
            db.update_group_setting(message.chat.id, "antispam", status)
            bot.reply_to(message, f"🛡️ <b>Anti-Spam Link Protection:</b> {'Enabled ✅' if status else 'Disabled ❌'}", parse_mode="HTML")
        else:
            bot.reply_to(message, "Format: /antispam <on/off>")

    @bot.message_handler(commands=['settitle'])
    def cmd_settitle(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            try:
                bot.set_chat_title(message.chat.id, parts[1])
                bot.reply_to(message, "✅ <b>Group Title Updated!</b>", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, f"⚠️ Failed to update title. Make sure I have 'Change Group Info' admin rights.")
        else:
            bot.reply_to(message, "Format: /settitle <New Title>")

    @bot.message_handler(commands=['setdesc'])
    def cmd_setdesc(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username): return
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            try:
                bot.set_chat_description(message.chat.id, parts[1])
                bot.reply_to(message, "✅ <b>Group Description Updated!</b>", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, f"⚠️ Failed to update description. Make sure I have 'Change Group Info' admin rights.")
        else:
            bot.reply_to(message, "Format: /setdesc <New Description>")

    # Command Registration
    try:
        commands = [
            telebot.types.BotCommand("start", "Premium Bot Introduction"),
            telebot.types.BotCommand("help", "List all available commands"),
            telebot.types.BotCommand("info", "Check user profile & deep stats"),
            telebot.types.BotCommand("ban", "Permanently ban a user"),
            telebot.types.BotCommand("kick", "Remove user from group"),
            telebot.types.BotCommand("mute", "Restrict user from talking"),
            telebot.types.BotCommand("unmute", "Restore talking privileges"),
            telebot.types.BotCommand("lock", "Lock the group (Admin only)"),
            telebot.types.BotCommand("unlock", "Unlock the group"),
            telebot.types.BotCommand("warn", "Issue a formal warning"),
            telebot.types.BotCommand("promote", "Promote to Administrator"),
            telebot.types.BotCommand("demote", "Remove Administrator rights"),
            telebot.types.BotCommand("link", "Fetch group invite link"),
            telebot.types.BotCommand("settitle", "Change Group Title"),
            telebot.types.BotCommand("setdesc", "Change Group Description"),
            telebot.types.BotCommand("addbadword", "Add word to Auto-Mod filter"),
            telebot.types.BotCommand("delbadword", "Remove word from filter"),
            telebot.types.BotCommand("antispam", "Toggle Anti-Invite Link Protection"),
            telebot.types.BotCommand("pin", "Pin a message"),
            telebot.types.BotCommand("del", "Delete a message"),
            telebot.types.BotCommand("rules", "Show group guidelines"),
            telebot.types.BotCommand("filters", "List active multimedia filters"),
            telebot.types.BotCommand("admins", "List all group admins"),
            telebot.types.BotCommand("report", "Secretly alert admins")
        ]
        bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"Failed to register commands: {e}")

    @bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'sticker', 'animation', 'document'])
    def all_messages(message):
        if message.chat.type not in ['group', 'supergroup']: return
        if not message.text: return
        
        group = db.get_group(message.chat.id)
        if not group: return
        
        text_lower = message.text.lower()
        
        # Anti-Spam (Link Protection) Module
        antispam_active = group.get("antispam", False)
        if antispam_active and not is_admin(bot, message.chat.id, message.from_user.id) and not is_owner(message.from_user.username):
            if "t.me/" in text_lower or "telegram.me/" in text_lower or "telegram.dog/" in text_lower:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"🚫 <b>Anti-Spam Violation</b>: {message.from_user.first_name}, Telegram invite links are forbidden here.", parse_mode="HTML")
                    return
                except:
                    pass
        
        bad_words = group.get("bad_words", [])
        text_lower = message.text.lower()
        
        for bw in bad_words:
            if bw in text_lower:
                if not is_admin(bot, message.chat.id, message.from_user.id):
                    try:
                        bot.delete_message(message.chat.id, message.message_id)
                        warnings = db.add_warning(message.from_user.id, message.from_user.first_name)
                        if warnings >= 3:
                            bot.ban_chat_member(message.chat.id, message.from_user.id)
                            db.reset_warnings(message.from_user.id)
                            bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name} was banned for reaching 3 warnings due to bad language.", parse_mode="HTML")
                        else:
                            bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name}, watch your language! Warning {warnings}/3", parse_mode="HTML")
                        return
                    except:
                        pass
                        
        filters = group.get("filters", {})
        for trigger, f_data in filters.items():
            if trigger in text_lower:
                ftype = f_data.get("type")
                if ftype == "text":
                    bot.reply_to(message, f_data.get("text"))
                elif ftype == "photo":
                    bot.send_photo(message.chat.id, f_data.get("file_id"), caption=f_data.get("caption"), reply_to_message_id=message.message_id)
                elif ftype == "sticker":
                    bot.send_sticker(message.chat.id, f_data.get("file_id"), reply_to_message_id=message.message_id)
                elif ftype == "gif":
                    bot.send_animation(message.chat.id, f_data.get("file_id"), reply_to_message_id=message.message_id)
                break
