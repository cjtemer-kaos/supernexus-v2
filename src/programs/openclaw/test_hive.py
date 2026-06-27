from nexus_hive_bridge import NexusHiveBridge

bridge = NexusHiveBridge("openclaw")

print("=== OpenClaw se une a la NexusHive ===\n")

bridge.send_message("supernexus", "OpenClaw joined the Hive!", "general")

msgs = bridge.get_all_messages(5)
for m in msgs:
    print(f"[{m['sender']} -> {m['target']}] {m['content'][:60]}...")