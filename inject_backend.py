import re

def inject_middleware():
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add Middleware class
    middleware_code = """
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class SubscriptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Faqat user apilarga (admin emas) va check_subscription ga tushmasligi kerak
        if path.startswith("/api/") and not path.startswith("/api/admin/") and path != "/api/check_subscription" and path != "/api/auth/webhook":
            init_data = request.headers.get("X-Telegram-Init-Data", "")
            if init_data:
                user = verify_init_data(init_data)
                if user:
                    user_id = user["id"]
                    # Obunani tekshiramiz
                    unsubbed = await get_unsubscribed_channels(bot, user_id)
                    if unsubbed:
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": "subscription_required", 
                                "channels": [dict(c) for c in unsubbed]
                            }
                        )
        return await call_next(request)
"""
    if "class SubscriptionMiddleware" not in content:
        # just insert it before app = FastAPI()
        app_idx = content.find("app = FastAPI()")
        if app_idx != -1:
            content = content[:app_idx] + middleware_code + "\n" + content[app_idx:]

    # 2. Add app.add_middleware(SubscriptionMiddleware)
    if "app.add_middleware(SubscriptionMiddleware)" not in content:
        app_idx = content.find("app = FastAPI()")
        if app_idx != -1:
            insert_idx = content.find("\n", app_idx)
            content = content[:insert_idx] + "\napp.add_middleware(SubscriptionMiddleware)" + content[insert_idx:]

    # 3. Add /api/check_subscription route
    check_sub_route = """
@app.get("/api/check_subscription")
async def api_check_subscription(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data: raise HTTPException(403)
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    user_id = user['id']
    unsubbed = await get_unsubscribed_channels(bot, user_id, bypass_cache=True)
    if not unsubbed:
        # Referral logic: Obunadan muvaffaqiyatli o'tsa, reward beramiz
        await process_referral_reward(user_id)
        return {"ok": True}
    else:
        return {"ok": False, "channels": [dict(c) for c in unsubbed]}

async def process_referral_reward(user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Check users table
            async with db.execute("SELECT referrer_id, reward_given FROM users WHERE telegram_id=?", (user_id,)) as c:
                u_row = await c.fetchone()
            
            if u_row and u_row['referrer_id'] and not u_row['reward_given']:
                ref_id = u_row['referrer_id']
                # Check referrals table
                async with db.execute("SELECT id FROM referrals WHERE user_id=?", (user_id,)) as c:
                    ref_exists = await c.fetchone()
                
                if not ref_exists:
                    # Give reward
                    await db.execute("UPDATE users SET balance = balance + 1000 WHERE telegram_id=?", (ref_id,))
                    await db.execute("UPDATE users SET reward_given = 1 WHERE telegram_id=?", (user_id,))
                    await db.execute("INSERT INTO referrals (referrer_id, user_id, reward_given, reward_amount) VALUES (?, ?, 1, 1000)", (ref_id, user_id))
                    await db.commit()
                    
                    try:
                        await bot.send_message(ref_id, f"🎁 <b>Referral Bonus!</b>\\nSizning do'stingiz majburiy obunadan o'tdi.\\nBalansingizga <b>+1000 so'm</b> qo'shildi!", parse_mode="HTML")
                    except: pass
    except Exception as e:
        logger.error(f"process_referral_reward error: {e}")
"""
    if "api_check_subscription" not in content:
        route_idx = content.find("@app.get(\"/api/user\")")
        if route_idx != -1:
            content = content[:route_idx] + check_sub_route + "\n" + content[route_idx:]

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Injected middleware and check_subscription route successfully.")

if __name__ == "__main__":
    inject_middleware()
