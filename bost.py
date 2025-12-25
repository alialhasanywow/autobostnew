import telethon
from telethon import TelegramClient, events, functions, types
from telethon.errors import FloodWaitError, SessionPasswordNeededError, AuthKeyError
from telethon.sessions import SQLiteSession
import asyncio
import re
import random
import time
from datetime import datetime, timedelta
import os
import json
import logging
from typing import List, Dict, Optional
import traceback

# تعطيل تحذيرات Telethon المزعجة
logging.getLogger('telethon').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# بيانات جميع الحسابات
ACCOUNTS = [
    {
        "phone": "+19109995417",
        "app_id": "36456889",
        "api_hash": "69379c223b45bdc831b64b1c3be64b80"
    },
    {
        "phone": "+18705728913",
        "app_id": "37266437",
        "api_hash": "71bbd50fb993facf2c1121a2ca464c5c"
    },
    {
        "phone": "+19255678460",
        "app_id": "39447569",
        "api_hash": "7e78000f2dc7483e0a9a41d6585481a4"
    },
    {
        "phone": "+19149873844",
        "app_id": "31668997",
        "api_hash": "275788ac5ab620d59299097331dbb3e7"
    },
    {
        "phone": "+18707688963",
        "app_id": "34122639",
        "api_hash": "16e5b450b2328da919bdc2dc73b18ce5"
    }
]

OWNER_ID = 819127707

# Global variables
user_ids = {}
reply_tracking = {}
auto_posting_tasks = {}
account_errors = {}
account_credentials = {}
clients = []
active_posting = {}
posting_queues = {}
reconnect_tasks = {}

def load_settings():
    global reply_tracking
    try:
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                data = json.load(f)
                reply_tracking = data.get('reply_tracking', {})
                reply_tracking = {str(k): v for k, v in reply_tracking.items()}
    except Exception as e:
        print(f"⚠️ Error loading settings: {e}")
        reply_tracking = {}

def save_settings():
    try:
        with open('settings.json', 'w') as f:
            json.dump({
                'reply_tracking': reply_tracking,
            }, f, indent=4)
    except Exception as e:
        print(f"⚠️ Error saving settings: {e}")

# إنشاء مجلد الجلسات
os.makedirs('sessions', exist_ok=True)

# إنشاء العملاء مع جلسات SQLite أكثر استقراراً
for i, acc in enumerate(ACCOUNTS, 1):
    try:
        session_file = f'sessions/account_{i}.session'
        
        client = TelegramClient(
            session=SQLiteSession(session_file),
            api_id=acc["app_id"],
            api_hash=acc["api_hash"],
            connection_retries=10,
            retry_delay=1,
            auto_reconnect=True,
            flood_sleep_threshold=0
        )
        
        # تعطيل تحديث الجلسة التلقائي لمنع المشاكل
        client.session = SQLiteSession(session_file)
        
        clients.append(client)
        account_credentials[i] = acc
        print(f"✅ Client {i} created: {acc['phone']}")
    except Exception as e:
        print(f"❌ Error creating client {i}: {e}")

async def force_reconnect(account_num):
    """إعادة الاتصال القسري للحساب"""
    try:
        if account_num in reconnect_tasks:
            return
        
        print(f"🔄 إعادة الاتصال بالحساب {account_num}...")
        
        client = clients[account_num-1]
        
        # قطع الاتصال الحالي
        try:
            await client.disconnect()
        except:
            pass
        
        # تنظيف الجلسة القديمة
        session_file = f'sessions/account_{account_num}.session'
        if os.path.exists(session_file):
            try:
                backup_file = f'sessions/account_{account_num}.session.backup_{int(time.time())}'
                os.rename(session_file, backup_file)
            except:
                pass
        
        # إنشاء جلسة جديدة
        client.session = SQLiteSession(session_file)
        
        # إعادة الاتصال
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"🔐 الحساب {account_num} يحتاج إعادة تسجيل دخول")
            # هنا يمكن إضافة منطق إعادة التسجيل إذا لزم
            
        print(f"✅ تم إعادة الاتصال بالحساب {account_num}")
        account_errors[account_num] = None
        
    except Exception as e:
        print(f"❌ فشل إعادة الاتصال بالحساب {account_num}: {e}")
        account_errors[account_num] = f"Connection error: {str(e)}"
    finally:
        if account_num in reconnect_tasks:
            reconnect_tasks.pop(account_num, None)

async def start_all_clients():
    print("=" * 60)
    print("🚀 بدء تشغيل جميع الحسابات...")
    print("=" * 60)
    
    for i, client in enumerate(clients, 1):
        try:
            print(f"\n🔄 جاري تشغيل الحساب {i} ({account_credentials[i]['phone']})...")
            
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"📱 الحساب {i} يحتاج تسجيل دخول...")
                
                try:
                    await client.send_code_request(account_credentials[i]['phone'])
                    print(f"✅ تم إرسال رمز التحقق للحساب {i}")
                    
                    code = input(f"📝 أدخل رمز التحقق للحساب {i}: ").strip()
                    
                    try:
                        await client.sign_in(account_credentials[i]['phone'], code)
                        print(f"✅ تم تسجيل دخول الحساب {i}")
                    except SessionPasswordNeededError:
                        print(f"🔒 الحساب {i} يتطلب كلمة مرور")
                        password = input(f"🔐 أدخل كلمة المرور: ").strip()
                        await client.sign_in(password=password)
                        print(f"✅ تم التحقق من الحساب {i}")
                    except Exception as e:
                        print(f"❌ خطأ في تسجيل الدخول للحساب {i}: {e}")
                        continue
                        
                except Exception as e:
                    print(f"❌ خطأ في إرسال رمز التحقق للحساب {i}: {e}")
                    continue
            
            # اختبار الاتصال
            try:
                me = await client.get_me()
                print(f"✅ الحساب {i} يعمل: {me.first_name or ''} {me.last_name or ''}".strip())
                account_errors[i] = None
            except Exception as e:
                print(f"⚠️ مشكلة في اتصال الحساب {i}: {e}")
                account_errors[i] = "Connection issue"
            
        except Exception as e:
            print(f"❌ خطأ تشغيل الحساب {i}: {e}")
            account_errors[i] = str(e)

async def get_user_ids():
    global user_ids
    print("\n" + "=" * 60)
    print("📊 جاري جلب معلومات الحسابات...")
    print("=" * 60)
    
    for i, client in enumerate(clients, 1):
        try:
            me = await client.get_me()
            user_ids[i] = me.id
            
            print(f"\n✅ الحساب {i}:")
            print(f"   📞 {account_credentials[i]['phone']}")
            print(f"   🆔 {me.id}")
            print(f"   👤 {me.first_name or ''} {me.last_name or ''}".strip())
            print(f"   📛 @{me.username}" if me.username else "   📛 بدون يوزر")
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ خطأ في معلومات الحساب {i}: {e}")
            account_errors[i] = f"ID error"

async def extreme_send(client, entity, message, account_num, max_retries=1000):
    """إرسال متطرف لا يتوقف أبداً"""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await client.send_message(entity=entity, message=message)
            return True
            
        except FloodWaitError as e:
            # تجاهل FloodWait والمتابعة فوراً
            print(f"⚡ FloodWait للحساب {account_num}: {e.seconds}s - متابعة")
            continue
            
        except (ConnectionError, OSError, TimeoutError) as e:
            # مشاكل شبكة - إعادة محاولة فورية
            retry_count += 1
            continue
            
        except Exception as e:
            if "session" in str(e).lower() or "security" in str(e).lower():
                # مشكلة في الجلسة - إعادة الاتصال
                print(f"🔧 مشكلة جلسة للحساب {account_num} - إعادة محاولة")
                await asyncio.sleep(0.5)
                continue
            else:
                # أي خطأ آخر - تجاهل والمتابعة
                retry_count += 1
                continue
    
    return False

def setup_handlers(client, account_num):
    @client.on(events.NewMessage(outgoing=True, pattern=r'^s (\d+) (\d+)$'))
    async def swing(event):
        try:
            if account_errors.get(account_num):
                await event.edit(f"❌ الحساب {account_num} معطل")
                return
                
            if event.is_reply:
                parts = event.text.split()
                range_num = int(parts[2])
                chatId = event.chat_id
                message = await event.get_reply_message()
                
                auto_posting_tasks[account_num] = True
                
                await event.edit(f"🚀 بدء النشر بالحساب {account_num}...")
                
                success_count = 0
                
                for i in range(range_num):
                    if not auto_posting_tasks.get(account_num, False):
                        break
                    
                    try:
                        await extreme_send(client, chatId, message, account_num)
                        success_count += 1
                        
                        # تحديث العرض كل 20 رسالة
                        if (i+1) % 20 == 0:
                            try:
                                await event.edit(f"⚡ الحساب {account_num}: {success_count}/{range_num}")
                            except:
                                pass
                        
                    except Exception as e:
                        # تجاهل جميع الأخطاء
                        continue
                
                result_msg = f"✅ الحساب {account_num}: {success_count}/{range_num}"
                try:
                    await event.edit(result_msg)
                except:
                    pass
                
                auto_posting_tasks[account_num] = False
                
        except Exception as e:
            auto_posting_tasks[account_num] = False
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.ن0$'))
    async def stop_auto_posting(event):
        auto_posting_tasks[account_num] = False
        try:
            await event.edit(f"⏹ توقف الحساب {account_num}")
        except:
            pass
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.ح([01])$'))
    async def toggle_reply_tracking(event):
        try:
            state = int(event.pattern_match.group(1))
            reply_tracking[str(account_num)] = bool(state)
            save_settings()
            await event.edit(f"{'✅ مفعل' if state else '❌ معطل'} تتبع الحساب {account_num}")
        except:
            pass
    
    @client.on(events.NewMessage(incoming=True))
    async def track_replies(event):
        try:
            if not reply_tracking.get(str(account_num), False):
                return
            
            if event.is_reply and event.sender_id != user_ids.get(account_num):
                replied_msg = await event.get_reply_message()
                
                if replied_msg and replied_msg.sender_id == user_ids.get(account_num):
                    try:
                        await client.send_message("me", f"📨 رد على الحساب {account_num}")
                    except:
                        pass
        except:
            pass
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^sg (\d+) (\d+) (.+)$'))
    async def auto_post_to_channel(event):
        try:
            if event.is_reply:
                parts = event.text.split()
                repeat_count = int(parts[2])
                channel_link = parts[3]
                
                replied_msg = await event.get_reply_message()
                
                try:
                    channel_entity = await client.get_entity(channel_link)
                except:
                    try:
                        await event.edit("❌ خطأ في القناة")
                    except:
                        pass
                    return
                
                try:
                    await event.edit(f"🚀 الحساب {account_num} يبدأ النشر...")
                except:
                    pass
                
                auto_posting_tasks[account_num] = True
                success_count = 0
                
                for i in range(repeat_count):
                    if not auto_posting_tasks.get(account_num, False):
                        break
                    
                    try:
                        await extreme_send(client, channel_entity, replied_msg, account_num)
                        success_count += 1
                    except:
                        continue
                
                auto_posting_tasks[account_num] = False
                
        except Exception as e:
            auto_posting_tasks[account_num] = False
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.نشر_سريع (\d+) (.+)$'))
    async def fast_post_all(event):
        """نشر سريع بكل الحسابات معاً"""
        try:
            if event.is_reply:
                parts = event.text.split()
                repeat_count = int(parts[1])
                channel_link = parts[2]
                
                replied_msg = await event.get_reply_message()
                
                try:
                    channel_entity = await client.get_entity(channel_link)
                except:
                    try:
                        await event.edit("❌ خطأ في القناة")
                    except:
                        pass
                    return
                
                try:
                    await event.edit(f"⚡ بدء النشر السريع بكل الحسابات...")
                except:
                    pass
                
                # جمع الحسابات النشطة
                active_accounts = []
                for acc_num in range(1, len(clients) + 1):
                    if not account_errors.get(acc_num):
                        active_accounts.append(acc_num)
                
                # إنشاء مهام النشر لجميع الحسابات
                tasks = []
                for acc_num in active_accounts:
                    if acc_num == account_num:  # تخطي الحساب الحالي
                        continue
                    
                    acc_client = clients[acc_num-1]
                    task = asyncio.create_task(
                        mass_post(acc_client, channel_entity, replied_msg, acc_num, repeat_count)
                    )
                    tasks.append(task)
                
                # تشغيل الحساب الحالي أيضاً
                auto_posting_tasks[account_num] = True
                current_task = asyncio.create_task(
                    mass_post(client, channel_entity, replied_msg, account_num, repeat_count)
                )
                tasks.append(current_task)
                
                # انتظار انتهاء المهام
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                auto_posting_tasks[account_num] = False
                
                try:
                    await event.edit("✅ تم النشر السريع بكل الحسابات")
                except:
                    pass
                
        except Exception as e:
            auto_posting_tasks[account_num] = False
    
    async def mass_post(client, entity, message, acc_num, count):
        """نشر جماعي لحساب واحد"""
        for i in range(count):
            if not auto_posting_tasks.get(acc_num, True):
                break
            try:
                await extreme_send(client, entity, message, acc_num)
            except:
                continue
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.اعادة تشغيل (\d+)$'))
    async def restart_account(event):
        try:
            acc_num = int(event.pattern_match.group(1))
            if acc_num > len(clients):
                await event.edit("❌ رقم حساب غير صحيح")
                return
            
            await event.edit(f"🔄 إعادة تشغيل الحساب {acc_num}...")
            
            # إيقاف النشر إذا كان يعمل
            auto_posting_tasks[acc_num] = False
            
            # إعادة الاتصال
            await force_reconnect(acc_num)
            
            await event.edit(f"✅ تم إعادة تشغيل الحساب {acc_num}")
            
        except Exception as e:
            await event.edit(f"❌ خطأ: {str(e)[:100]}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.الحالة$'))
    async def show_accounts_status(event):
        status_lines = ["⚡ حالة الحسابات:"]
        
        for acc_num in range(1, len(clients) + 1):
            phone = account_credentials.get(acc_num, {}).get('phone', 'Unknown')
            
            if account_errors.get(acc_num):
                status = "🔴 معطل"
            elif auto_posting_tasks.get(acc_num, False):
                status = "🟢 ناشر"
            else:
                status = "🟢 جاهز"
            
            status_lines.append(f"{acc_num}. {phone[:10]}... - {status}")
        
        status_lines.append("")
        status_lines.append(f"📊 إجمالي: {len(clients)} حساب")
        
        await event.edit("\n".join(status_lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.حسابي$'))
    async def show_my_account(event):
        try:
            me = await client.get_me()
            info = [
                f"👤 الحساب {account_num}",
                f"📞 {account_credentials[account_num]['phone']}",
                f"🆔 {me.id}",
                f"👤 {me.first_name or ''}",
                f"📛 @{me.username}" if me.username else "📛 بدون يوزر"
            ]
            await event.edit("\n".join(info))
        except:
            await event.edit("❌ خطأ في جلب المعلومات")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.الاوامر$'))
    async def show_commands(event):
        commands = [
            "⚡ الأوامر السريعة:",
            "",
            "s [تأخير] [عدد] - نشر رسالة",
            "sg [تأخير] [عدد] [رابط] - نشر في قناة",
            ".نشر_سريع [عدد] [رابط] - نشر بكل الحسابات",
            ".ن0 - إيقاف النشر",
            ".ح1/.ح0 - تتبع الردود",
            ".الحالة - حالة الحسابات",
            ".اعادة تشغيل [رقم] - إعادة تشغيل حساب",
            ".حسابي - معلومات الحساب"
        ]
        await event.edit("\n".join(commands))

async def monitor_and_reconnect():
    """مراقبة وإعادة الاتصال التلقائي"""
    while True:
        try:
            for i, client in enumerate(clients, 1):
                try:
                    # اختبار بسيط للاتصال
                    await client.get_me()
                    if account_errors.get(i):
                        print(f"✅ الحساب {i} عاد للعمل")
                        account_errors[i] = None
                except Exception as e:
                    if not account_errors.get(i):
                        print(f"⚠️ فقدان اتصال الحساب {i}: {str(e)[:50]}")
                        account_errors[i] = "Connection lost"
                        auto_posting_tasks[i] = False
                    
                    # محاولة إعادة الاتصال
                    if i not in reconnect_tasks:
                        reconnect_tasks[i] = asyncio.create_task(force_reconnect(i))
            
            await asyncio.sleep(10)  # فحص كل 10 ثواني
            
        except Exception as e:
            await asyncio.sleep(10)

async def main():
    print("=" * 60)
    print("🚀 BOT TELEGRAM MULTI-ACCOUNT")
    print("⚡ VERSION: ULTRA FAST - NO DELAY")
    print("=" * 60)
    
    load_settings()
    
    await start_all_clients()
    await get_user_ids()
    
    # إعداد handlers
    for i, client in enumerate(clients, 1):
        setup_handlers(client, i)
        auto_posting_tasks[i] = False
        if i not in account_errors:
            account_errors[i] = None
    
    # بدء المراقبة
    asyncio.create_task(monitor_and_reconnect())
    
    print("\n" + "=" * 60)
    print("✅ النظام جاهز للعمل!")
    print("=" * 60)
    
    print("\n⚡ الأوامر الرئيسية:")
    print("s [عدد] - نشر رسالة (الرد عليها)")
    print("sg [عدد] [رابط] - نشر في قناة")
    print(".نشر_سريع [عدد] [رابط] - نشر بكل الحسابات معاً")
    print(".ن0 - إيقاف النشر للحساب الحالي")
    print(".اعادة تشغيل [رقم] - إعادة تشغيل حساب معطل")
    print("=" * 60)
    
    # عرض الحسابات
    print("\n🔹 الحسابات المتاحة:")
    for i in range(1, len(ACCOUNTS) + 1):
        status = "✅ نشط" if not account_errors.get(i) else "❌ معطل"
        print(f"  {i}. {ACCOUNTS[i-1]['phone']} - {status}")
    print("=" * 60)
    
    # تشغيل جميع العملاء
    tasks = []
    for i, client in enumerate(clients, 1):
        if not account_errors.get(i):
            task = asyncio.create_task(client.run_until_disconnected())
            tasks.append(task)
            print(f"▶️ تشغيل الحساب {i}...")
    
    try:
        if tasks:
            print(f"\n🚀 {len(tasks)} حساب يعمل الآن...")
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            print("❌ لا توجد حسابات نشطة")
            print("🔄 حاول إعادة تشغيل البوت")
            
    except KeyboardInterrupt:
        print("\n⏹ إيقاف البوت...")
    except Exception as e:
        print(f"\n💥 خطأ غير متوقع: {e}")
        print("🔄 حاول إعادة التشغيل")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ تم إيقاف البوت")
    except Exception as e:
        print(f"\n💥 خطأ فادح: {e}")