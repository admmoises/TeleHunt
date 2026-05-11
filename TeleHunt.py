import asyncio
import datetime
import json
import os
import re
import sqlite3
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import User, MessageMediaPhoto, MessageMediaPoll, MessageMediaStory, MessageMediaDocument
from tabulate import tabulate
from urllib.parse import urlparse
from argparse import ArgumentParser

# Customize Lib

from modules.colors import colors,messages,wol,workwol,termux,worktermux
from modules.colors import messages as mes

FILES = {
    "accounts": "accounts.json",
    "groups": "groups.json",
    "channels": "channels.json",
    "bots": "bots.json",
    "directs": "directs.json",
    "messages": "messages.json",
    "capture": "capture.json",
    "links": "links.json",
}
GLOBAL_UNIQUE_MESSAGES = set()

def readname(name):
    return __import__("unicodedata").normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    
def load_accounts(name):
    if not os.path.exists(name):
        return []
    with open(name, "r", encoding="utf-8") as f:
        return json.load(f)

def save_accounts(data):
    with open(FILES['accounts'], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


async def stream_save_list(file, stream_data, lock):
    async with lock:
        save_data(file, stream_data)

def clear():
    os.system("cls || clear")

def OS():
    return os.path.exists("/data/data/com.termux")

def get_message_type(message):
    if message.media:
        match message.media:
            case MessageMediaPhoto():
                return "Photo"
            case MessageMediaPoll():
                return "Poll"
            case MessageMediaStory():
                return "Story"
            case MessageMediaDocument():
                mime = message.media.document.mime_type or ""
                file_name = ""
                if message.media.document.attributes:
                    for attr in message.media.document.attributes:
                        if hasattr(attr, "file_name"):
                            file_name = attr.file_name.lower()
                match mime:
                    case mime if mime.startswith("video"):
                        return "Video"
                    case mime if mime.startswith("audio"):
                        return "Audio"
                    case mime if "ogg" in mime:
                        return "Voice"
                    case "image/gif":
                        return "GIF"
                    case "application/x-tgsticker":
                        return "Sticker"
                    case _ if file_name.endswith(".pdf"):
                        return "PDF"
                    case _ if file_name.endswith(".sql"):
                        return "SQL"
                    case _ if file_name.endswith(".py"):
                        return "Python File"
                    case _ if file_name.endswith(".go"):
                        return "Go File"
                    case _ if file_name.endswith(".php"):
                        return "Php File"
                    case _ if file_name.endswith(".docx"):
                        return "DOCX"
                    case _ if file_name.endswith(".zip"):
                        return "ZIP"
                    case _ if file_name.endswith(".rar"):
                        return "RAR"
                    case _ if file_name.endswith(".apk"):
                        return "APK File"
                    case _ if file_name.endswith(".exe"):
                        return "Executable File"
                    case _ if file_name.endswith(".txt"):
                        return "Text File"
                    case _ if file_name.endswith(".json"):
                        return "JSON File"
                    case _:
                        return "File"
    return "Text"

async def resolve_prompt_value(provider, prompt_text):
    if provider is None:
        return None
    try:
        result = provider(prompt_text)
    except TypeError:
        result = provider()

    if asyncio.iscoroutine(result):
        result = await result
    return result


async def connect_with_retry(client, session_label="unknown", retries=5, base_delay=1.0):
    for attempt in range(1, retries + 1):
        try:
            await client.connect()
            # Avoid session entity writes when the sqlite session is contested.
            if hasattr(client, "session") and client.session:
                client.session.save_entities = False
            return True
        except (sqlite3.OperationalError, Exception) as e:
            if "database is locked" not in str(e).lower():
                raise

            if attempt < retries:
                wait_seconds = base_delay * attempt
                print(
                    f"{messages['war']}Session locked for {session_label}. "
                    f"Retrying in {wait_seconds:.1f}s ({attempt}/{retries})..."
                )
                await asyncio.sleep(wait_seconds)
                continue

            print(
                f"{messages['error']}Session database is locked for {session_label}. "
                "Close other processes using this account and try again."
            )
            return False

async def get_chat_id_by_username(client, username):
    try: 
        entity = await client.get_entity(username)
        
        if isinstance(entity, User):  
            return entity.id 
        else:
            print(f"{messages['error']}{username} is not a user.")
            return 3
    except Exception as e:
        print(f"{messages['error']}Error while resolving {username}: {e}")  
        return 3


async def get_user_by_username(client, username):
    try:
        user = await client.get_entity(username)
        return user
    except Exception as e:
        print(f"{messages['error']}Error fetching user by username {username}: {e}")
        return 3
    
def show_accounts():
    accounts = load_accounts(FILES['accounts'])
    if accounts:
        print(f"\n{messages['normal']}")
        for acc in accounts:
            print(f"{messages['suc']}Account Number: {acc['account_number']}")
            print(f"{messages['suc']}Name: {acc['first_name']} {acc['last_name']}")
            print(f"{messages['suc']}Username: @{acc['username']}")
            print(f"{messages['suc']}Phone: {acc['phone']}")
            print(f"{messages['suc']}User ID: {acc['user_id']}")
            print(f"{messages['suc']}Session File: {acc['session_file']}")
            print(f"{messages['suc']}Session Created At: {acc['session_created_at']}")
            print(f"{colors['yellow']}-" * 50)
    else:
        print(f"{messages['error']}No accounts found.") 

async def get_user_by_id(client, user_id):
    try:
        user = await client.get_entity(user_id)
        return user
    except Exception as e:
        print(f"{messages['war']}Error fetching user by ID {user_id}: {e}")
        return 3
    
async def add_account(api_hash, api_id, phone, code_provider=None, password_provider=None):
    session_name = f"session_{phone.replace('+','')}"
    print(f"{messages['suc']}Creating session: {session_name}.session")

    client = TelegramClient(session_name, api_id=int(api_id), api_hash=api_hash)
    if not await connect_with_retry(client, phone):
        return

    if not await client.is_user_authorized():  
        print(f"{messages['suc']}Code sent to {phone}")
        sent_code = await client.send_code_request(phone) 
        if code_provider is None:
            code = input(f"{messages['suc']}Enter the code: ")
        else:
            code = await resolve_prompt_value(code_provider, f"{messages['suc']}Enter the code: ")

        if not code:
            print(f"{messages['error']}No login code was provided.")
            await client.disconnect()
            return

        try:
            await client.sign_in(phone, phone_code_hash=sent_code.phone_code_hash, code=code) 
        except SessionPasswordNeededError:
            if password_provider is None:
                password = input(f"{messages['war']}Two-step password required: ")
            else:
                password = await resolve_prompt_value(password_provider, f"{messages['war']}Two-step password required: ")
            if not password:
                print(f"{messages['error']}No two-step password was provided.")
                await client.disconnect()
                return
            await client.sign_in(password=password) 

    me = await client.get_me()  

    account_data = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone,
        "user_id": me.id,
        "username": me.username,
        "first_name": me.first_name,
        "last_name": me.last_name,
        "session_file": f"{session_name}.session",
        "session_created_at": datetime.datetime.now().isoformat(),
        "is_active": True
    }

    accounts = load_accounts(FILES['accounts'])
    account_data["account_number"] = len(accounts) + 1
    accounts.append(account_data)
    save_accounts(accounts)

    print(f"\n{messages['normal']}Account added successfully:")
    print(f"{messages['suc']}Name: {me.first_name} {me.last_name}")
    print(f"{messages['suc']}Username: @{me.username}")
    print(f"{messages['suc']}User ID: {me.id}")
    print(f"{messages['suc']}Session File: {session_name}.session")

    await client.disconnect()  

async def search_messages_for_account(account, search_text=3, sender=3, limit=3, forward_to=3, file_type=3, stream_data=None, stream_lock=None):
    try:
        session_name = account['session_file'].split('.')[0]
        client = TelegramClient(session_name, account['api_id'], account['api_hash'])
        if not await connect_with_retry(client, account['phone']):
            return []

        print(f"{messages['wait']}Searching messages for account: {account['phone']}")

        messages_found = []
        find_counter = 0

        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_channel or dialog.is_group or dialog.is_user or (isinstance(dialog.entity, User) and dialog.entity.bot):
                    async for message in client.iter_messages(dialog.id):
                        msg_text = message.text or ""
                        if not msg_text:
                            continue

                        if search_text and search_text.lower() not in msg_text.lower():
                            continue

                        if sender and str(message.sender_id) != sender:
                            continue

                        if file_type:
                            message_type = get_message_type(message)
                            if message_type.lower() != file_type.lower():
                                continue

                        cleaned_msg_text = readname(msg_text)
                        message_type = get_message_type(message)

                        sender_obj = await message.get_sender()
                        if isinstance(sender_obj, User):
                            sender_name = sender_obj.first_name or "Unknown"
                        elif dialog.is_channel:
                            sender_name = dialog.entity.title or "Unknown Channel"
                        elif dialog.is_group:
                            sender_name = dialog.entity.title or "Unknown Group"
                        else:
                            sender_name = "Unknown"

                        found_message = {
                            "dialog_id": dialog.id,
                            "message_id": message.id,
                            "sender_id": message.sender_id,
                            "sender_name": sender_name,
                            "message_type": message_type,
                            "message": cleaned_msg_text[:150],
                            "date": message.date.isoformat()
                        }
                        messages_found.append(found_message)

                        if stream_data is not None and stream_lock is not None:
                            stream_data.append(found_message)
                            await stream_save_list(FILES["messages"], stream_data, stream_lock)

                        find_counter += 1
                        if limit and find_counter >= limit:
                            break

                if limit and find_counter >= limit:
                    break

        except Exception as e:
            print(f"{messages['error']}Error: {e}")

        await client.disconnect()
        return messages_found

    except Exception as e:
        print(f"{messages['war']}{account['phone']}: {e}")
        return []

sent_message_ids = set() 
sent_messages_info = []   

async def forward_messages_for_all_clients(account_messages, forward_user, forward_clients, limit=3):
    f = 0  

    print(f"{mes['suc']}Forwarding messages from {len(forward_clients)} clients.")

    async def forward_from_client(forward_client, messages):
        nonlocal f
        for msg in messages:
            if limit and f >= limit:
                return 
            if msg["message_id"] in sent_message_ids:
                print(f"{mes['war']}Skipping already forwarded message {msg['message_id']}")
                continue  

            try:
               
                original = await forward_client.get_messages(msg["dialog_id"], ids=msg["message_id"])
                await original.forward_to(forward_user.id)
               
                sent_message_ids.add(msg["message_id"]) 
                sent_messages_info.append({
                    "sender_id": msg["sender_id"],
                    "sender_name": msg["sender_name"],
                    "message_type": msg["message_type"],
                    "message": msg["message"], 
                    "date": msg["date"]
                })

                f += 1
                print(f"{mes['suc']}Forwarded message {f} to {forward_user.username if forward_user else forward_user.id}")
                if f >= limit:
                    return  

            except Exception as e:
                print(f"{mes['war']}Error forwarding message from client {forward_client.session.filename}: {e}")

    tasks = []
    for forward_client, account in zip(forward_clients, account_messages.keys()):
        messages = account_messages[account]
        tasks.append(forward_from_client(forward_client, messages))

    await asyncio.gather(*tasks)

    print(f"{mes['suc']}Messages forwarded successfully!")

async def search_messages(account_numbers, search_text=3, sender=3, limit=3, forward_to=3, file_type=3):
    accounts = load_accounts(FILES['accounts'])

    if account_numbers == "all":
        selected_accounts = accounts
    else:
        account_numbers = list(map(int, account_numbers.split(",")))
        selected_accounts = [acc for acc in accounts if acc['account_number'] in account_numbers]

    if not selected_accounts:
        print(f"{messages['war']}No accounts found.")
        return

    account_messages = {}
    stream_messages = []
    stream_lock = asyncio.Lock()
    save_data(FILES["messages"], stream_messages)

    tasks = []
    for account in selected_accounts:
        tasks.append(
            search_messages_for_account(
                account,
                search_text,
                sender,
                limit,
                forward_to,
                file_type,
                stream_data=stream_messages,
                stream_lock=stream_lock
            )
        )

    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        account_messages[selected_accounts[i]['phone']] = result

    if limit:
        all_messages = []
        for messages in account_messages.values():
            all_messages.extend(messages)

        all_messages = all_messages[:limit]
    else:
        all_messages = []
        for messages in account_messages.values():
            all_messages.extend(messages)

    if forward_to and all_messages:
        print(f"\n{mes['wait']}Forwarding messages...")

        forward_clients = []

        for account in selected_accounts:
            forward_client = TelegramClient(account['session_file'], account['api_id'], account['api_hash'])
            if not await connect_with_retry(forward_client, account['phone']):
                continue
            forward_clients.append(forward_client)

        if not forward_clients:
            print(f"{mes['war']}No available sessions to forward messages.")
            return

        forward_user = 3
        if forward_to.startswith('@'):
            forward_user = await get_user_by_username(forward_clients[0], forward_to[1:])
        else:
            try:
                forward_user = await get_user_by_id(forward_clients[0], int(forward_to))
            except ValueError:
                print(f"{mes['error']}Invalid forward_to value: {forward_to}")
                forward_user = 3

        if not forward_user:
            print(f"{mes['war']}Forward target not found.")
        else:

            await forward_messages_for_all_clients(account_messages, forward_user, forward_clients, limit)

        for forward_client in forward_clients:
            await forward_client.disconnect()

    if sent_messages_info:
        headers = ["Sender ID", "Sender Name", "Message Type", "Message Text", "Date"]
        table = [
            [msg["sender_id"], msg["sender_name"], msg["message_type"], msg["message"], msg["date"]]
            for msg in sent_messages_info
        ]
        print(f"{mes['suc']}Results Table: {colors['white']}\n\n")
        print(tabulate(table, headers, tablefmt="fancy_grid", maxcolwidths=[15, 15, 15, 40, 20]))
    else:
        print(f"{mes['war']}No messages found or forwarded.")


async def fetchDGC(account_numbers, entity_type):
    accounts = load_accounts(FILES['accounts'])

    if account_numbers == "all":
        selected_accounts = accounts
    else:
        account_numbers = list(map(int, account_numbers.split(",")))
        selected_accounts = [acc for acc in accounts if acc['account_number'] in account_numbers]

    if not selected_accounts:
        print(f"{messages['war']} No accounts found.")
        return

    stream_entities = []
    stream_lock = asyncio.Lock()
    entity_file = FILES.get(entity_type, FILES['groups'])
    save_data(entity_file, stream_entities)

    async def process_account(account):
        session_name = account['session_file'].split('.')[0]
        client = TelegramClient(session_name, account['api_id'], account['api_hash'])
        if not await connect_with_retry(client, account['phone']):
            return

        print(f"{messages['wait']} Fetching {entity_type} for account: {account['phone']}")

        entities = []
        
        try:
            async for dialog in client.iter_dialogs():
                if (dialog.is_group and entity_type == "groups") or \
                (dialog.is_channel and entity_type == "channels") or \
                (dialog.is_user and entity_type == "dms") or \
                (isinstance(dialog.entity, User) and dialog.entity.bot and entity_type == "bots"):
                    try:
                        entity = await client.get_entity(dialog.id)
                        name = readname(dialog.name)
                        username = getattr(entity, 'username', 'Private')

                        entity_data = None
                        if entity_type == "bots" and isinstance(dialog.entity, User) and getattr(dialog.entity, 'bot', False):
                            entity_data = {
                                "name": name,
                                "id": entity.id,
                                "username": username,
                                "type": "Bot",
                                "created_at": datetime.datetime.now().isoformat(),
                                "account_phone": account['phone']
                            }
                        elif entity_type == "dms" and dialog.is_user:
                            phone = getattr(entity, 'phone', "N/A")
                            entity_data = {
                                "name": name,
                                "id": entity.id,
                                "username": username,
                                "phone": phone,
                                "type": "Direct Message",
                                "created_at": datetime.datetime.now().isoformat(),
                                "account_phone": account['phone']
                            }
                        elif entity_type != "bots" and entity_type != "dms":
                            entity_data = {
                                "name": name,
                                "id": entity.id,
                                "username": username,
                                "type": entity_type.capitalize(),
                                "created_at": datetime.datetime.now().isoformat(),
                                "account_phone": account['phone']
                            }

                        if entity_data is not None:
                            entities.append(entity_data)
                            stream_entities.append(entity_data)
                            await stream_save_list(entity_file, stream_entities, stream_lock)
                    except Exception as e:
                        print(f"{messages['error']}Error: {e}")

        except Exception as e:
            print(f"{messages['error']}: {e}")

        await client.disconnect()

        if entities:
            headers = [f"{entity_type.capitalize()} Name", f"{entity_type.capitalize()} ID", "Username"]
            table = [[entity["name"], entity["id"], entity["username"]] for entity in entities]
            print(tabulate(table, headers, tablefmt="fancy_grid"))
        else:
            print(f"{messages['war']}No {entity_type} found.")

    tasks = [process_account(account) for account in selected_accounts]
    await asyncio.gather(*tasks)




async def capture_messages(account, target_username, forward_to, limit=3, file_type=3, stream_data=None, stream_lock=None):
    session_name = account['session_file'].split('.')[0]
    client = TelegramClient(session_name, account['api_id'], account['api_hash'])
    if not await connect_with_retry(client, account['phone']):
        return

    print(f"{messages['wait']}Searching for messages of user {target_username} in account {account['phone']}")
    target = await get_chat_id_by_username(client, target_username)
    collected = []

    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_group:  
                try:
                    async for message in client.iter_messages(dialog.id):
                        if message.sender_id == target:  
                            if file_type:
                                message_type = get_message_type(message)
                                if message_type.lower() != file_type.lower():
                                    continue 

                            
                            if message.id in GLOBAL_UNIQUE_MESSAGES:
                                continue 
                            GLOBAL_UNIQUE_MESSAGES.add(message.id) 

                            cleaned_msg_text = readname(message.text or "")
                            sender_name = dialog.entity.title

                            captured_message = {
                                "dialog_id": dialog.id,
                                "message_id": message.id,
                                "sender_id": message.sender_id,
                                "sender_name": sender_name,
                                "message_type": get_message_type(message),
                                "message": cleaned_msg_text[:150],  
                                "date": message.date.isoformat()
                            }
                            collected.append(captured_message)
                            if stream_data is not None and stream_lock is not None:
                                stream_data.append(captured_message)
                                await stream_save_list(FILES["capture"], stream_data, stream_lock)

                        if limit and len(collected) >= limit:
                            break
                except Exception as e:
                    print(f"{messages['war']}Error processing messages in group {dialog.id}: {e}")
    except Exception as e:
        print(f"{messages['error']}Error in account {account['phone']}: {e}")

    await client.disconnect()

    if collected:
        headers = ["Sender ID", "Sender Name", "Message Type", "Message Text", "Date"]
        table = [
            [msg["sender_id"], msg["sender_name"], msg["message_type"], msg["message"], msg["date"]]
            for msg in collected
        ]
        print(f"\n{messages['suc']}Results Table:{colors['white']}\n\n")
        print(tabulate(table, headers, tablefmt="fancy_grid", maxcolwidths=[15, 15, 15, 40, 20]))

        if forward_to:
            print(f"\n{messages['wait']}Forwarding messages...")
            forward_client = TelegramClient("forwarder", account['api_id'], account['api_hash'])
            if not await connect_with_retry(forward_client, account['phone']):
                return

            forward_user = 3
            if forward_to.startswith('@'):
                forward_user = await client.get_entity(forward_to)
            else:
                try:
                    forward_user = await client.get_entity(int(forward_to))
                except ValueError:
                    print(f"{messages['error']}Invalid forward_to value: {forward_to}")

            if forward_user:
                for msg in collected:
                    original = await forward_client.get_messages(msg["dialog_id"], ids=msg["message_id"])
                    await original.forward_to(forward_user.id)

                print(f"{messages['suc']} Messages forwarded successfully!")
            await forward_client.disconnect()

    else:
        print(f"{messages['war']}No messages found.")

async def capture_messages_for_account(account, target_username, forward_to, limit=3, file_type=3, stream_data=None, stream_lock=None):
    await capture_messages(account, target_username, forward_to, limit, file_type, stream_data=stream_data, stream_lock=stream_lock)

async def capture_main(account_numbers, target_username, forward_to, limit=3, file_type=3):
    accounts = load_accounts(FILES['accounts'])

    if account_numbers == "all":
        selected_accounts = accounts
    else:
        account_numbers = list(map(int, account_numbers.split(",")))
        selected_accounts = [acc for acc in accounts if acc['account_number'] in account_numbers]

    stream_capture = []
    stream_lock = asyncio.Lock()
    save_data(FILES["capture"], stream_capture)

    tasks = []
    for account in selected_accounts:
        tasks.append(
            capture_messages_for_account(
                account,
                target_username,
                forward_to,
                limit,
                file_type,
                stream_data=stream_capture,
                stream_lock=stream_lock
            )
        )

    await asyncio.gather(*tasks)

async def fetch_messages_from_channel(client, channel_link, limit="all", on_message=None):
    try:
        channel = await client.get_entity(channel_link)
        print(f"{mes['wait']}Fetching messages from channel: {channel.title} ({channel.id})")

        messages = []
        async for message in client.iter_messages(channel.id, limit=None if limit == "all" else int(limit)):
            msg_text = message.text or ""
            if not msg_text:
                continue

            message_data = {
                "dialog_id": channel.id,
                "message_id": message.id,
                "sender_id": message.sender_id,
                "message": msg_text[:150], 
                "date": message.date.isoformat()
            }
            messages.append(message_data)

            if on_message is not None:
                await on_message(message_data)

          
            if limit != "all" and len(messages) >= int(limit):
                break

        return messages
    except Exception as e:
        print(f"{mes['war']}Error fetching messages from channel {channel_link}: {e}")
        return []


async def forward_messages_to_channel(client, messages, forward_to, limit="all", download_decision_provider=None):
    try:
        if not limit:
            limit = "all"
        forward_user = None
        if forward_to.startswith('@'):
            forward_user = await get_user_by_username(client, forward_to[1:])
        else:
            try:
                forward_user = await get_user_by_id(client, int(forward_to))
            except ValueError:
                print(f"{mes['error']}Invalid forward_to value: {forward_to}")
                forward_user = None

        download_messages = False

        if forward_user:
            f = 0  
            for msg in messages:
                if limit != "all" and f >= int(limit):  
                    break

                original = await client.get_messages(msg["dialog_id"], ids=msg["message_id"])

                try:
                    
                    if original.text and not original.media:
                       
                        await client.send_message(forward_user.id, original.text)
                        f += 1
                        print(f"{mes['suc']}Forwarded message (text) to {forward_user.username if forward_user else forward_user.id}")

              
                    elif original.media and not original.text:
                       
                        file_path = await original.download_media(file="downloads/")
                        print(f"{mes['suc']}Downloaded media file to {file_path}")
                        await client.send_file(forward_user.id, file_path)
                        f += 1
                        print(f"{mes['suc']}Forwarded media message to {forward_user.username if forward_user else forward_user.id}")

                   
                    elif original.media and original.text:
                        
                        await original.forward_to(forward_user.id)
                        f += 1
                        print(f"{mes['suc']}Forwarded media with caption to {forward_user.username if forward_user else forward_user.id}")

                except Exception as e:
                    print(f"{mes['war']}Error forwarding message: {e}")
                  
                    if not download_messages: 
                        if download_decision_provider is None:
                            user_input = input(f"{mes['ques']}Do you want to download and send the post manually? (y/n): ").lower()
                            wants_download = user_input == 'y'
                        else:
                            decision = await resolve_prompt_value(
                                download_decision_provider,
                                f"{mes['ques']}Do you want to download and send the post manually? (y/n): "
                            )
                            if isinstance(decision, bool):
                                wants_download = decision
                            else:
                                wants_download = str(decision).strip().lower() in ("y", "yes", "s", "sim")
                        if wants_download:
                            download_messages = True
                            print(f"{mes['suc']}sending post {msg['message_id']} manually...")
                    
                    if download_messages:
                     
                        if original.media:
                            file_path = await original.download_media(file="downloads/")
                            if file_path:
                                print(f"{mes['suc']}File downloaded to {file_path}")
                                
                              
                                await client.send_file(forward_user.id, file_path, caption=original.text)
                                print(f"{mes['wait']}Manually forwarded message to {forward_user.username if forward_user else forward_user.id} with caption.")
                                f += 1
                        else:
                            print(f"{mes['war']}No media found in message {msg['message_id']}, skipping download.")
        else:
            print(f"{mes['war']}Forward target not found.")
    except Exception as e:
        print(f"{mes['war']}Error forwarding messages: {e}")

async def forward_from_channel(account_numbers, link, forward_to, limit="all", show_table=False, download_decision_provider=None):
    accounts = load_accounts(FILES['accounts'])
    normalized_limit = limit if limit else "all"

    if account_numbers == "all":
        selected_accounts = accounts
    else:
        account_numbers = list(map(int, account_numbers.split(",")))
        selected_accounts = [acc for acc in accounts if acc['account_number'] in account_numbers]

    all_forwarded_messages = []
    stream_messages = []
    stream_lock = asyncio.Lock()
    save_data(FILES["messages"], stream_messages)

    tasks = []
    for account in selected_accounts:
        session_name = account['session_file'].split('.')[0]
        client = TelegramClient(session_name, account['api_id'], account['api_hash'])
        if not await connect_with_retry(client, account['phone']):
            continue

        async def on_found_message(message_data):
            stream_messages.append(message_data)
            await stream_save_list(FILES["messages"], stream_messages, stream_lock)

        messages = await fetch_messages_from_channel(client, link, normalized_limit, on_message=on_found_message)

        if messages:

            await forward_messages_to_channel(
                client,
                messages,
                forward_to,
                normalized_limit,
                download_decision_provider=download_decision_provider
            )

            for msg in messages:
                all_forwarded_messages.append([msg["sender_id"], msg["message"], msg["date"]]) 

        await client.disconnect()

    if show_table and all_forwarded_messages:
        headers = ["Sender ID", "Message", "Date"]
        print(f"\n{mes['suc']}Forwarded Messages:")
        print(tabulate(all_forwarded_messages, headers, tablefmt="fancy_grid", maxcolwidths=[15, 40, 20]))
    else:
        print(f"{mes['suc']}Messages forwarded successfully!")


def save_links(links):
    if not links:
        return

    if os.path.exists(FILES["links"]):
        with open(FILES["links"], "r", encoding="utf-8") as f:
            existing_links = json.load(f)
    else:
        existing_links = {}

    for domain, domain_links in links.items():
        if domain not in existing_links:
            existing_links[domain] = []

        for link in domain_links:
            if link not in existing_links[domain]:
                existing_links[domain].append(link)

    with open(FILES["links"], "w", encoding="utf-8") as f:
        json.dump(existing_links, f, indent=4, ensure_ascii=False)

async def link_finder(account_number):
    accounts = load_accounts(FILES['accounts'])
    if account_number == "all":
        selected_accounts = accounts
    else:
        account_numbers = list(map(int, account_number.split(","))) if isinstance(account_number, str) else [account_number]
        selected_accounts = [acc for acc in accounts if acc['account_number'] in account_numbers]

    if not selected_accounts:
        print(f"{messages['war']}Account not found.")
        return
    links_found = {}
    existing_links_in_memory = set()

    for account in selected_accounts:
        session_name = account['session_file'].split('.')[0]
        client = TelegramClient(session_name, account['api_id'], account['api_hash'])
        if not await connect_with_retry(client, account['phone']):
            continue

        print(f"{messages['wait']}Searching links for account: {account['phone']}")

        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_channel or dialog.is_group or dialog.is_user or isinstance(dialog.entity, User):
                    async for message in client.iter_messages(dialog.id):
                        msg_text = message.text or ""
                        if msg_text:
                            links = extract_links(msg_text)
                            for link in links:
                                if link in existing_links_in_memory:
                                    continue

                                domain = get_domain(link)
                                if domain not in links_found:
                                    links_found[domain] = []

                                links_found[domain].append(link)
                                existing_links_in_memory.add(link)
                                save_links(links_found)
                                print(f"{messages['suc']}Found: {colors['yellow']}{link} ({colors['white']}Domain: {colors['red']}{domain}{colors['reset']})")

        except Exception as e:
            print(f"{messages['error']}Error: {e}")
        finally:
            await client.disconnect()

    if links_found:
        print(f"\n{messages['suc']}Links Found and Saved:")
        for domain, domain_links in links_found.items():
            if domain_links:
                print(f"{colors['cyan']}Domain: {colors['yellow']}{domain}")
                for link in domain_links:
                    print(f"{colors['green']}Link:{colors['yellow']}{link}")
                    print("-" * 50)
    else:
        print(f"{messages['error']}No links found.")


def extract_links(text):
    
    link_regex = r'https?://[^\s]+' 
    return re.findall(link_regex, text)


def get_domain(link):
    parsed_url = urlparse(link)
    domain = parsed_url.netloc  
    
    if domain.startswith("www."): 
        domain = domain[4:]

    return domain


if __name__ == "__main__":
    b = termux if OS() else wol
    w = worktermux if OS() else workwol
    clear()
    print (b)
    parser = ArgumentParser(description=f"{messages['wait']}TeleHunt")

    parser.add_argument("--add", type=str, help="Add account: apihash:apiid:phone")
    parser.add_argument("--show", action="store_true", help="Show all accounts")
    parser.add_argument("--acc", type=str, help="Account numbers for specific actions (e.g. 1,2 or all)")
    parser.add_argument("--groups", action="store_true", help="Show all groups for the specified account")
    parser.add_argument("--channels", action="store_true", help="Show all channels for the specified account")
    parser.add_argument("--bots", action="store_true", help="Show all bots for the specified account")
    parser.add_argument("--dms", action="store_true", help="Show direct messages")

    parser.add_argument("--search-text", type=str, help="Text to search in messages")
    parser.add_argument("--sender", type=str, help="Chat ID of the sender to filter messages")
    parser.add_argument("--limit", type=int, help="Limit the number of messages to search")
    parser.add_argument("--forward", type=str, help="Username or User ID to forward the messages")
    parser.add_argument("--file-type", type=str, help="Filter by file type (e.g. pdf, zip, etc.)")
    parser.add_argument("--capture", action="store_true", help="Capture all messages of a target user")
    parser.add_argument("--target", type=str, help="Username or user_id to capture messages from")
    parser.add_argument("--link", type=str, help="Link or username of the channel to fetch messages from")
    parser.add_argument("--table", action="store_true", help="Show results in a table format")
    parser.add_argument("--linkfinder", action="store_true", help="Find all links in messages and save them")

    args = parser.parse_args()

    if args.add:
        parts = args.add.split(":")
        if len(parts) != 3:
            print(f"{messages['warn']}Format must be: apihash:apiid:phone")
        else:
            api_hash, api_id, phone = parts
            asyncio.run(add_account(api_hash, api_id, phone))
        exit()

    if args.show:
        show_accounts()
        exit()

    if not args.acc:
        print(rf"""
{colors['yellow']}
 _____    _      _   _             _   
|_   _|__| | ___| | | |_   _ _ __ | |_ 
  | |/ _ \ |/ _ \ |_| | | | | '_ \| __|
  | |  __/ |  __/  _  | |_| | | | | |_ 
  |_|\___|_|\___|_| |_|\__,_|_| |_|\__|
               
{messages['error']}Invalid arguments. Use --help for usage information.""")
        exit()

    search_with_empty_text_and_filetype = args.search_text == "" and bool(args.file_type)
    search_with_non_empty_text = bool(args.search_text)

    dispatch = [
        (search_with_non_empty_text or search_with_empty_text_and_filetype, lambda: search_messages(args.acc, args.search_text, args.sender, args.limit, args.forward, args.file_type)),
        (args.link and args.forward, lambda: forward_from_channel(args.acc, args.link, args.forward, args.limit, args.table)),
        (args.groups, lambda: fetchDGC(args.acc, "groups")),
        (args.linkfinder, lambda: link_finder(args.acc)),
        (args.capture and args.target, lambda: capture_main(args.acc, args.target, args.forward, args.limit, args.file_type)),
        (args.channels, lambda: fetchDGC(args.acc, "channels")),
        (args.bots, lambda: fetchDGC(args.acc, "bots")),
        (args.dms, lambda: fetchDGC(args.acc, "dms")),
    ]

    for condition, func in dispatch:
        if condition:
            clear()
            print(w)
            try:
                asyncio.run(func())
            except KeyboardInterrupt:
                print(f"{messages['war']}Interrupted by user. Partial results remain saved.")
            break
    else:
        print (f"{messages['error']}Invalid arguments. Use --help for usage information.")

