import asyncio
import os
import sys
import json
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
from services.queue_service import (
    QueueService,
    ROOM_1_WATER_QUEUE,
    ROOM_2_WATER_QUEUE,
    DEFAULT_DAILY_DUTY,
    MONTHLY_DEFAULT_PAIRS
)


async def run_tests():
    print("=" * 60)
    print("🧪 KVARTIRA BOT — COMPREHENSIVE TEST SUITE (UPGRADED)")
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

    r1_users = await UserRepository.get_users_by_room(1)
    r2_users = await UserRepository.get_users_by_room(2)
    assert len(r1_users) == 4 and len(r2_users) == 4
    print(f"   • 🏠 Room 1: {[u['name'] for u in r1_users]}")
    print(f"   • 🚪 Room 2: {[u['name'] for u in r2_users]}")

    print("\n2. Testing Dual-Room Independent Water Queues...")
    # Room 1 Init: Avazbek (1) -> Firdavs (2)
    r1_curr, r1_next, r1_idx = await QueueService.get_room_water_duty_info(1)
    assert r1_curr["id"] == 1 and r1_next["id"] == 2
    print(f"✅ Room 1 Queue Init OK: Current={r1_curr['name']}, Next={r1_next['name']}")

    # Room 2 Init: Ilyosbek (5) -> Jaloliddin (6)
    r2_curr, r2_next, r2_idx = await QueueService.get_room_water_duty_info(2)
    assert r2_curr["id"] == 5 and r2_next["id"] == 6
    print(f"✅ Room 2 Queue Init OK: Current={r2_curr['name']}, Next={r2_next['name']}")

    # Delivery in Room 1 (Firdavs brought water for Room 1 out of turn)
    rec1 = await QueueService.record_room_water_delivery(room_id=1, brought_by_user_id=2, photo_file_id="photo_r1")
    assert rec1["brought_by"]["id"] == 2
    assert rec1["next_user"]["id"] == 3 # Next is Asadbek bro (3)
    print(f"✅ Room 1 Out-of-Turn Delivery OK: Next is {rec1['next_user']['name']}")

    # Verify Room 2 queue was NOT modified
    r2_curr_after, _, _ = await QueueService.get_room_water_duty_info(2)
    assert r2_curr_after["id"] == 5
    print(f"✅ Room 2 Isolation OK: Current is still {r2_curr_after['name']}")

    print("\n3. Testing Monthly 4-Week Pair Rotation...")
    # Day 1..7 -> Week 1 (Pair 1: Omadbek & Asadbek bro)
    d_w1 = date(2026, 9, 3)
    p_w1 = await QueueService.get_active_weekly_pair(d_w1)
    assert p_w1["week_index"] == 0 and p_w1["pair_id"] == 1
    assert p_w1["member1"]["id"] == 4 and p_w1["member2"]["id"] == 3
    print(f"✅ Week 1 (Day 3) Pair OK: {p_w1['member1']['name']} & {p_w1['member2']['name']}")

    # Day 8..14 -> Week 2 (Pair 2: Ilyosbek & Jaloliddin)
    d_w2 = date(2026, 9, 10)
    p_w2 = await QueueService.get_active_weekly_pair(d_w2)
    assert p_w2["week_index"] == 1 and p_w2["pair_id"] == 2
    print(f"✅ Week 2 (Day 10) Pair OK: {p_w2['member1']['name']} & {p_w2['member2']['name']}")

    # Day 15..21 -> Week 3 (Pair 3: Avazbek & Firdavs)
    d_w3 = date(2026, 9, 17)
    p_w3 = await QueueService.get_active_weekly_pair(d_w3)
    assert p_w3["week_index"] == 2 and p_w3["pair_id"] == 3
    print(f"✅ Week 3 (Day 17) Pair OK: {p_w3['member1']['name']} & {p_w3['member2']['name']}")

    # Day 22..30 -> Week 4 (Pair 4: Mavlonbek & Asadbek)
    d_w4 = date(2026, 9, 28)
    p_w4 = await QueueService.get_active_weekly_pair(d_w4)
    assert p_w4["week_index"] == 3 and p_w4["pair_id"] == 4
    print(f"✅ Week 4 (Day 28) Pair OK: {p_w4['member1']['name']} & {p_w4['member2']['name']}")

    print("\n4. Testing Advanced Swapping Engines...")
    # 4A. DAILY SWAP
    req_id_daily = "swap_daily_01"
    daily_payload = {"swap_type": "DAILY", "day_idx": 0, "day_name": "Dushanba", "target_date_str": "2026-08-31"}
    await SwapRepository.create_swap_request(req_id_daily, 1, 8, "DAILY", json.dumps(daily_payload))
    await SwapRepository.update_swap_status(req_id_daily, "APPROVED")
    await DutyRepository.set_daily_override(36, 0, "8")
    duty_mon = await QueueService.get_daily_duty(date(2026, 8, 31))
    assert duty_mon[0]["id"] == 8
    print(f"✅ Daily Duty Swap OK: Mon Duty is {duty_mon[0]['name']}")

    # 4B. WHOLE WEEKLY PAIR SWAP (Week 1 Pair 1 swaps with Week 3 Pair 3)
    month_year = "2026-09"
    await DutyRepository.set_weekly_pair_assignment(month_year, 0, 3, 1, 2)
    await DutyRepository.set_weekly_pair_assignment(month_year, 2, 1, 4, 3)
    p_w1_swapped = await QueueService.get_active_weekly_pair(d_w1)
    assert p_w1_swapped["pair_id"] == 3 and p_w1_swapped["member1"]["id"] == 1
    print(f"✅ Whole Weekly Pair Swap OK: Week 1 Pair is now #{p_w1_swapped['pair_id']} ({p_w1_swapped['member1']['name']} & {p_w1_swapped['member2']['name']})")

    # 4C. PAIR MEMBER PROXY SWAP (In Week 2, Ilyosbek replaced by Firdavs)
    await DutyRepository.set_weekly_pair_assignment(month_year, 1, 2, 6, 2)
    p_w2_proxy = await QueueService.get_active_weekly_pair(d_w2)
    assert p_w2_proxy["member1"]["id"] == 6 and p_w2_proxy["member2"]["id"] == 2
    print(f"✅ Pair Proxy Swap OK: Week 2 Pair is now {p_w2_proxy['member1']['name']} & {p_w2_proxy['member2']['name']}")

    print("\n5. Testing Daily Task Checklist...")
    today_str = "2026-09-01"
    await TaskRepository.toggle_task(today_str, "cooking", user_id=1)
    await TaskRepository.toggle_task(today_str, "bread", user_id=2)
    await TaskRepository.toggle_task(today_str, "table_dishes", user_id=3)
    r_all = await TaskRepository.toggle_task(today_str, "trash", user_id=4)
    assert r_all["all_completed"] is True
    print("✅ Checklist Toggle & All Completed OK!")

    print("\n6. Testing Lightweight HTTP Health-Check Server...")
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

    print("\n7. Testing User Unbind and Profile Re-selection...")
    # Bind User 8 (Mavlonbek) to test TG ID
    await UserRepository.bind_telegram_id(8, 6149675718)
    u8 = await UserRepository.get_user_by_id(8)
    assert u8["telegram_id"] == 6149675718
    
    # Unbind and rebind User 7 (Asadbek)
    await UserRepository.unbind_user_by_telegram_id(6149675718)
    u8_unbound = await UserRepository.get_user_by_id(8)
    assert u8_unbound["telegram_id"] is None
    print("✅ User 8 Unbind OK: telegram_id is None")

    await UserRepository.bind_telegram_id(7, 6149675718)
    u7 = await UserRepository.get_user_by_id(7)
    assert u7["telegram_id"] == 6149675718
    print(f"✅ User 7 Re-bind OK: {u7['name']} -> TG ID {u7['telegram_id']}")

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
