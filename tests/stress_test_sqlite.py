"""
SQLite Concurrency Stress Test - SuperNEXUS v2 Message Board
Simulates 22 concurrent Gemas writing 50 messages each (1100 total).
"""

import sqlite3
import threading
import time
import random
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List

DB_PATH = r"C:\Users\cjtr\.nexus\brain\message_board.db"
NUM_WRITERS = 22
MESSAGES_PER_WRITER = 50
TOTAL_MESSAGES = NUM_WRITERS * MESSAGES_PER_WRITER
BUSY_TIMEOUT = 5000
CHANNELS = ["general", "alerts", "logs", "coordination", "status"]
MSG_TYPES = ["chat", "alert", "command", "status", "heartbeat"]
GEMA_NAMES = [
    "gema-01", "gema-02", "gema-03", "gema-04", "gema-05",
    "gema-06", "gema-07", "gema-08", "gema-09", "gema-10",
    "gema-11", "gema-12", "gema-13", "gema-14", "gema-15",
    "gema-16", "gema-17", "gema-18", "gema-19", "gema-20",
    "gema-21", "gema-22",
]


@dataclass
class WriterStats:
    writer_id: str
    success_count: int = 0
    fail_count: int = 0
    busy_errors: int = 0
    other_errors: int = 0
    total_time: float = 0.0
    insert_times: list = field(default_factory=list)


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and busy timeout."""
    conn = sqlite3.connect(DB_PATH, timeout=BUSY_TIMEOUT / 1000.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT}")
    return conn


def generate_message(writer_id: str, seq: int) -> tuple:
    """Generate a message tuple for insertion."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.", time.gmtime()) + f"{time.time() % 1:.3f}"[2:]
    channel = random.choice(CHANNELS)
    msg_type = random.choice(MSG_TYPES)
    content = f"[StressTest] {writer_id} msg #{seq}: payload-{random.randint(1000, 9999)}"
    metadata = json.dumps({
        "stress_test": True,
        "writer": writer_id,
        "seq": seq,
        "priority": random.randint(1, 5),
    })
    return (timestamp, writer_id, "*", channel, content, msg_type, metadata)


def writer_task(writer_id: str) -> WriterStats:
    """Execute writes for a single Gema."""
    stats = WriterStats(writer_id=writer_id)
    conn = get_connection()
    try:
        for seq in range(1, MESSAGES_PER_WRITER + 1):
            msg = generate_message(writer_id, seq)
            start = time.perf_counter()
            try:
                conn.execute(
                    "INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    msg,
                )
                conn.commit()
                elapsed = time.perf_counter() - start
                stats.success_count += 1
                stats.insert_times.append(elapsed)
            except sqlite3.OperationalError as e:
                elapsed = time.perf_counter() - start
                stats.insert_times.append(elapsed)
                if "database is locked" in str(e).lower() or "busy" in str(e).lower():
                    stats.busy_errors += 1
                else:
                    stats.other_errors += 1
                stats.fail_count += 1
                conn.rollback()
    finally:
        stats.total_time = sum(stats.insert_times)
        conn.close()
    return stats


def run_stress_test() -> dict:
    """Run the full stress test and return results."""
    print(f"{'='*60}")
    print(f"  SQLite Concurrency Stress Test - SuperNEXUS v2")
    print(f"{'='*60}")
    print(f"  Database: {DB_PATH}")
    print(f"  Writers:  {NUM_WRITERS}")
    print(f"  Messages per writer: {MESSAGES_PER_WRITER}")
    print(f"  Total messages: {TOTAL_MESSAGES}")
    print(f"  WAL mode: enabled")
    print(f"  Busy timeout: {BUSY_TIMEOUT}ms")
    print(f"{'='*60}")

    # Get pre-test count
    conn = get_connection()
    pre_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    print(f"\n  Messages before test: {pre_count}")

    # Run concurrent writers
    print(f"\n  Starting {NUM_WRITERS} concurrent writers...")
    overall_start = time.perf_counter()

    all_stats: List[WriterStats] = []
    with ThreadPoolExecutor(max_workers=NUM_WRITERS) as executor:
        futures = {
            executor.submit(writer_task, gema_name): gema_name
            for gema_name in GEMA_NAMES
        }
        for future in as_completed(futures):
            stats = future.result()
            all_stats.append(stats)

    overall_elapsed = time.perf_counter() - overall_start

    # Aggregate results
    total_success = sum(s.success_count for s in all_stats)
    total_fail = sum(s.fail_count for s in all_stats)
    total_busy = sum(s.busy_errors for s in all_stats)
    total_other = sum(s.other_errors for s in all_stats)
    all_insert_times = [t for s in all_stats for t in s.insert_times]
    avg_insert = sum(all_insert_times) / len(all_insert_times) if all_insert_times else 0
    min_insert = min(all_insert_times) if all_insert_times else 0
    max_insert = max(all_insert_times) if all_insert_times else 0
    success_rate = (total_success / TOTAL_MESSAGES) * 100 if TOTAL_MESSAGES > 0 else 0

    # Get post-test count
    conn = get_connection()
    post_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total time:              {overall_elapsed:.3f}s")
    print(f"  Messages inserted:       {total_success}/{TOTAL_MESSAGES}")
    print(f"  Success rate:            {success_rate:.2f}%")
    print(f"  SQLITE_BUSY errors:      {total_busy}")
    print(f"  Other errors:            {total_other}")
    print(f"  Avg insert time:         {avg_insert*1000:.3f}ms")
    print(f"  Min insert time:         {min_insert*1000:.3f}ms")
    print(f"  Max insert time:         {max_insert*1000:.3f}ms")
    print(f"  Throughput:              {total_success/overall_elapsed:.1f} msg/s")
    print(f"  DB count before:         {pre_count}")
    print(f"  DB count after:          {post_count}")
    print(f"  DB delta:                {post_count - pre_count}")
    print(f"{'='*60}")

    # Per-writer breakdown
    print(f"\n  Per-Writer Breakdown:")
    print(f"  {'Writer':<12} {'OK':>4} {'FAIL':>5} {'BUSY':>5} {'Time(s)':>8}")
    print(f"  {'-'*12} {'-'*4} {'-'*5} {'-'*5} {'-'*8}")
    for s in sorted(all_stats, key=lambda x: x.writer_id):
        print(f"  {s.writer_id:<12} {s.success_count:>4} {s.fail_count:>5} {s.busy_errors:>5} {s.total_time:>8.3f}")

    print(f"\n{'='*60}")
    if total_fail == 0:
        print(f"  STATUS: ALL {TOTAL_MESSAGES} MESSAGES INSERTED SUCCESSFULLY")
    else:
        print(f"  STATUS: {total_fail} FAILURES DETECTED")
    print(f"{'='*60}")

    return {
        "total_time": overall_elapsed,
        "total_success": total_success,
        "total_fail": total_fail,
        "total_busy": total_busy,
        "success_rate": success_rate,
        "avg_insert_ms": avg_insert * 1000,
        "throughput": total_success / overall_elapsed,
        "db_delta": post_count - pre_count,
    }


if __name__ == "__main__":
    results = run_stress_test()
