import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameOccupiedError, UsernameInvalidError
from telethon.tl.functions.account import CheckUsernameRequest
from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest
from telethon.sessions import StringSession
import aiosqlite
from config import API_ID, API_HASH, DB_PATH
from worker.generator import generate_usernames

logger = logging.getLogger(__name__)

async def process_order(order_id: int, telegram_id: int, category: str, quantity: int, session_string: str):
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.error(f"User {telegram_id} session is invalid.")
        return
        
    targets = generate_usernames(category, limit=quantity * 10)
    found = 0
    
    for username in targets:
        if found >= quantity:
            break
            
        try:
            is_available = await client(CheckUsernameRequest(username=username))
            if is_available:
                new_channel = await client(CreateChannelRequest(
                    title=username.capitalize(),
                    about="Band qilindi",
                    megagroup=False
                ))
                channel_id = new_channel.chats[0].id
                
                await client(UpdateUsernameRequest(
                    channel=channel_id,
                    username=username
                ))
                
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("INSERT INTO registered_usernames (order_id, username) VALUES (?, ?)", (order_id, username))
                    await db.execute("UPDATE orders SET registered_count = registered_count + 1 WHERE id = ?", (order_id,))
                    await db.commit()
                
                found += 1
                logger.info(f"✅ Band qilindi: @{username}")
                
            await asyncio.sleep(1) # Delay against flood wait
            
        except FloodWaitError as e:
            logger.warning(f"FloodWait: Sleeping for {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except UsernameOccupiedError:
            pass
        except UsernameInvalidError:
            pass
        except Exception as e:
            logger.error(f"Error checking {username}: {e}")
            await asyncio.sleep(2)
            
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (order_id,))
        await db.commit()
        
    await client.disconnect()
