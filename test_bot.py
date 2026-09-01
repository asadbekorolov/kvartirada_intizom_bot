import asyncio
import os
import sys
from datetime import datetime, date

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from config import settings
from database.connection import init_db, get_db
from database.repositories import (
    UserRepository,
    DutyRepository,
    TaskRepository,
    WaterRepository,
    SwapRepository,
    DeepCleanRepository
)
from services.queue_service import QueueService, WATER_QUEUE_IDS, DEFAULT_DAILY_DUTY, SUNDAY_CLEANING_PAIRS


async def run_tests():
    print("=" * 60)
    print("🧪 KVARTIRA BOT — INTEGRATION & UNIT TEST SUITE")
    print("=" * 60)

    # Use a temporary test DB
    import time
    db_file = f"test_kvartira_{int(time.time())}.db"
    settings.DB_PATH = db_file


    print("\n1. Initializing Database and Seeding Data...")
    await init_db()
    users = await UserRepository.get_all_users()
    assert len(users) == 8, f"Expected 8 users, got {len(users)}"
    print(f"✅ Seeding OK: Found {len(users)} flatmates.")
    for u in users:
        print(f"   • ID {u['id']}: {u['name']} (Room {u['room_number']})")

    print("\n2. Testing Default Duty Rotations...")
    # Mon: Jaloliddin (6), Tue: Firdavs (2), Wed: Asadbek (7), Thu: Asadbek bro (3), Fri: Mavlonbek (8), Sat: Avazbek (1), Sun: Omadbek (4) & Ilyosbek (5)
    test_mon = date(2026, 8, 31) # Monday
    duty_mon = await QueueService.get_daily_duty(test_mon)
    assert len(duty_mon) == 1 and duty_mon[0]["id"] == 6, f"Expected Jaloliddin (6) on Mon, got {duty_mon}"
    print(f"✅ Monday Duty OK: {duty_mon[0]['name']}")

    test_sun = date(2026, 9, 6) # Sunday
    duty_sun = await QueueService.get_daily_duty(test_sun)
    assert len(duty_sun) == 2, f"Expected 2 users on Sun, got {len(duty_sun)}"
    sun_ids = {u["id"] for u in duty_sun}
    assert sun_ids == {4, 5}, f"Expected {4, 5} on Sun, got {sun_ids}"
    print(f"✅ Sunday Duty Pair OK: {[u['name'] for u in duty_sun]}")

    print("\n3. Testing Water Queue & Out-of-Turn Delivery...")
    curr_user, next_user, idx = await QueueService.get_water_duty_info()
    assert curr_user["id"] == 1, f"Expected Avazbek (1) as 1st water bringer, got {curr_user}"
    assert next_user["id"] == 2, f"Expected Firdavs (2) as 2nd water bringer, got {next_user}"
    print(f"✅ Water Queue Init OK: Current={curr_user['name']}, Next={next_user['name']}")

    # Out-of-turn delivery: Firdavs (2) brings water ahead of Avazbek
    record_result = await QueueService.record_water_delivery(brought_by_user_id=2, photo_file_id="photo_file_123")
    assert record_result["brought_by"]["id"] == 2
    assert record_result["next_user"]["id"] == 3 # Asadbek bro (3) is next
    print(f"✅ Out-of-Turn Delivery OK: Firdavs brought water -> Next is {record_result['next_user']['name']}")

    logs = await WaterRepository.get_water_logs(limit=5)
    assert len(logs) == 1 and logs[0]["photo_file_id"] == "photo_file_123"
    print(f"✅ Water Log Insertion OK: ID={logs[0]['id']}, BroughtBy={logs[0]['brought_by_name']}")

    print("\n4. Testing Daily Task Checklist Engine...")
    today_str = "2026-09-01"
    # Toggle tasks step by step
    r1 = await TaskRepository.toggle_task(today_str, "cooking", user_id=1)
    assert r1["new_state"] is True and r1["all_completed"] is False
    
    r2 = await TaskRepository.toggle_task(today_str, "bread", user_id=2)
    r3 = await TaskRepository.toggle_task(today_str, "table_dishes", user_id=3)
    r4 = await TaskRepository.toggle_task(today_str, "trash", user_id=4)
    assert r4["all_completed"] is True, "Expected all_completed=True when 4 tasks done"
    print("✅ Daily Task Checklist Toggle & All Completed Trigger OK!")

    print("\n5. Testing Peer-to-Peer Duty Swap Engine...")
    # Avazbek (1) requests swap for Monday with Mavlonbek (8)
    req_id = "test_swap_001"
    await SwapRepository.create_swap_request(req_id, requester_id=1, target_id=8, day_of_week=0, target_date="2026-08-31")
    req = await SwapRepository.get_swap_request(req_id)
    assert req["status"] == "PENDING"
    
    # Approve swap
    await SwapRepository.update_swap_status(req_id, "APPROVED")
    await DutyRepository.set_daily_override(week_number=36, day_of_week=0, assigned_user_ids="8")

    override_duty = await QueueService.get_daily_duty(test_mon)
    assert len(override_duty) == 1 and override_duty[0]["id"] == 8, f"Expected Mavlonbek (8) after swap, got {override_duty}"
    print(f"✅ Duty Swap Override OK: Monday Duty is now {override_duty[0]['name']}")

    # Test Sunday Weekly Reset
    await DutyRepository.clear_weekly_overrides(week_number=36)
    reset_duty = await QueueService.get_daily_duty(test_mon)
    assert len(reset_duty) == 1 and reset_duty[0]["id"] == 6, f"Expected default Jaloliddin (6) after reset, got {reset_duty}"
    print(f"✅ Sunday Weekly Override Reset OK: Restored to {reset_duty[0]['name']}")

    print("\n6. Testing Admin Operations & User Binds...")
    await UserRepository.bind_telegram_id(user_id=1, telegram_id=999888777)
    u1 = await UserRepository.get_user_by_telegram_id(999888777)
    assert u1["id"] == 1, "Telegram ID mapping failed"
    print(f"✅ User Telegram Binding OK: {u1['name']} -> TG ID 999888777")

    print("\n7. Testing Lightweight HTTP Health-Check Server...")
    from services.web_server import create_web_app
    from aiohttp.test_utils import TestClient, TestServer
    app = create_web_app()
    client = TestClient(TestServer(app))
    await client.start_server()

    resp_root = await client.get("/")
    assert resp_root.status == 200
    data_root = await resp_root.json()
    assert data_root["status"] == "ok" and data_root["service"] == "kvartira_bot"
    print(f"✅ HTTP GET / OK: {data_root}")

    resp_health = await client.get("/health")
    assert resp_health.status == 200
    data_health = await resp_health.json()
    assert data_health["status"] == "ok" and "timestamp" in data_health
    print(f"✅ HTTP GET /health OK: {data_health}")

    await client.close()

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY! PROD-READY SYSTEM VERIFIED!")
    print("=" * 60)


    # Clean up test db file
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except Exception:
        pass



if __name__ == "__main__":
    asyncio.run(run_tests())
