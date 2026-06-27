import argparse
import json
import sys
import os
from src.cli.client import NexusClient
from src.cli.ui import NexusUI


def print_json(data: dict):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_auth(r: dict, args):
    if r.get("_auth_required") or "authentication required" in str(r.get("error", "")).lower():
        args.ui.error("Authentication required. Run: nexus login")
        sys.exit(1)


def cmd_login(args):
    r = args.client.login(args.username, args.password)
    if "token" in r:
        args.client.set_token(r["token"])
        args.ui.success(f"Logged in as {args.username}")
    elif r.get("error"):
        args.ui.error(f"Login failed: {r['error']}")
    else:
        print_json(r)


def cmd_status(args):
    r = args.client.status()
    check_auth(r, args)
    d = r.get("director")
    v = r.get("version", "?")
    online = r.get("online", False)

    status = "ONLINE" if online else "OFFLINE"
    sc = args.ui._c("success")
    ec = args.ui._c("error")
    args.ui.console.print(f"[bold cyan]NEXUS v{v}[/] - [{sc if online else ec}]{status}[/]")

    if d:
        args.ui.table(
            ["Property", "Value"],
            [["Role", d.get("role", "?")],
             ["Project", d.get("project", "?")],
             ["Architecture", d.get("architecture", "?")]],
        )

    engines = r.get("engines", {})
    args.ui.subheader("Engines")
    for eng, status in engines.items():
        sc = args.ui._c("success")
        mc = args.ui._c("muted")
        s = "+" if status == "online" else "-"
        args.ui.console.print(f"  [{sc if status == 'online' else mc}]{s}[/] {eng}: {status}")

    memory = r.get("memory", {})
    if memory:
        args.ui.subheader("Memory")
        for kind, stats in memory.items():
            if isinstance(stats, dict):
                rate = stats.get("success_rate", "?")
                args.ui.info(f"{kind}: {stats.get('total_entries', stats.get('total_patterns', '?'))} entries, {rate} success rate")

    cerebro = r.get("cerebro", {})
    if cerebro:
        args.ui.subheader("Cerebro")
        args.ui.info(f"{cerebro.get('conversaciones', '?')} conversations, {cerebro.get('conocimientos', '?')} knowledge items")


def cmd_chat(args):
    args.ui.thinking("Thinking...")
    r = args.client.chat(args.message, gem=args.agent or "")
    args.ui.stop_thinking()
    if "response" in r:
        args.ui.md(r["response"])
    elif "error" in r:
        args.ui.error(f"{r['error']}")
    else:
        print_json(r)


def cmd_agent(args):
    if args.action == "list":
        r = args.client.gemas()
        check_auth(r, args)
        if isinstance(r, dict) and "gems" in r:
            rows = []
            for g in r["gems"]:
                name = g.get("name", g) if isinstance(g, dict) else g
                rows.append([name, ""])
            args.ui.table(["Gema", "Capabilities"], rows)
        elif "error" in r:
            args.ui.error(f"{r['error']}")
        else:
            print_json(r)
    elif args.action == "tell":
        args.ui.thinking()
        r = args.client.chat(args.task, gem=args.name)
        args.ui.stop_thinking()
        if "response" in r:
            args.ui.md(r["response"])
        elif "error" in r:
            args.ui.error(f"{r['error']}")
        else:
            print_json(r)
    elif args.action == "loop":
        args.ui.thinking()
        r = args.client.agent_loop_run(args.task)
        args.ui.stop_thinking()
        if "result" in r:
            args.ui.panel(r["result"], title="Agent Loop Result")
        elif "response" in r:
            args.ui.md(r["response"])
        elif "error" in r:
            args.ui.error(f"{r['error']}")
        else:
            print_json(r)


def cmd_memory(args):
    if args.action == "search":
        r = args.client.memory_search(args.query, limit=args.limit)
        check_auth(r, args)
        results = r.get("results", r.get("observations", []))
        if results:
            for i, obs in enumerate(results, 1):
                content = obs.get("content", obs.get("text", str(obs)))[:200]
                args.ui.info(f"{i}. {content}")
        else:
            args.ui.warning("No results found")
    elif args.action == "stats":
        r = args.client.memory_stats()
        check_auth(r, args)
        rows = []
        for k, v in r.items():
            if isinstance(v, (int, float, str, bool)):
                rows.append([str(k), str(v)])
        args.ui.table(["Key", "Value"], rows, title="Memory Stats")
    elif args.action == "consolidate":
        r = args.client.memory_consolidate()
        check_auth(r, args)
        if "message" in r or "status" in r:
            args.ui.success(r.get("message", r.get("status", "Done")))
        else:
            print_json(r)
    elif args.action == "health":
        r = args.client.memory_health()
        check_auth(r, args)
        print_json(r)


def cmd_devloop(args):
    if args.action == "run":
        r = args.client.devloop_run(args.task)
        check_auth(r, args)
        args.ui.panel(json.dumps(r, indent=2, ensure_ascii=False), title="DevLoop Run")
    elif args.action == "status":
        r = args.client.devloop_status()
        check_auth(r, args)
        args.ui.panel(json.dumps(r, indent=2, ensure_ascii=False), title="DevLoop Status")


def cmd_conductor(args):
    r = args.client.conductor_list() if args.action == "list" else {}
    check_auth(r, args)
    if args.action == "spawn":
        r = args.client.conductor_spawn(args.name, args.goal)
        args.ui.success(f"Worktree '{args.name}' spawned")
    elif args.action == "merge":
        r = args.client.conductor_merge(args.name)
        args.ui.success(f"Worktree '{args.name}' merged")
    elif args.action == "cleanup":
        r = args.client.conductor_cleanup(args.name)
        args.ui.success(f"Worktree '{args.name}' cleaned up")
    if r.get("error"):
        args.ui.error(str(r["error"]))
    elif "status" in r or "message" in r:
        args.ui.info(r.get("status", r.get("message", "")))
    elif r:
        args.ui.panel(json.dumps(r, indent=2, ensure_ascii=False))


def cmd_skill(args):
    if args.action == "list":
        r = args.client.skill_list()
        check_auth(r, args)
        skills = r.get("skills", r.get("results", []))
        if skills:
            rows = []
            for s in skills[:20]:
                name = s.get("name", s.get("title", str(s)))[:30]
                desc = s.get("description", "")[:60]
                rows.append([name, desc])
            args.ui.table(["Name", "Description"], rows, title=f"Skills ({len(skills)} total)")
            if len(skills) > 20:
                args.ui.info(f"... and {len(skills) - 20} more (use --json for full list)")
        else:
            args.ui.warning("No skills found")
    elif args.action == "install":
        r = args.client.skill_install(args.name)
        check_auth(r, args)
        if "error" in r:
            args.ui.error(str(r["error"]))
        else:
            args.ui.success(f"Skill '{args.name}' installed")
    elif args.action == "publish":
        r = args.client.skill_publish(args.name)
        check_auth(r, args)
        if "error" in r:
            args.ui.error(str(r["error"]))
        else:
            args.ui.success(f"Skill '{args.name}' published")


def cmd_doctor(args):
    r = args.client.doctor()
    check_auth(r, args)
    rows = []
    for k, v in r.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                rows.append([f"{k}.{sk}", str(sv)[:60]])
        else:
            rows.append([k, str(v)[:60]])
    args.ui.table(["Check", "Result"], rows, title="Doctor Diagnostics")


def cmd_health(args):
    r = args.client.health()
    check_auth(r, args)
    if isinstance(r, dict):
        rows = []
        for k, v in r.items():
            if isinstance(v, dict):
                status = v.get("state", str(v.get("status", "?")))
                rows.append([k, status])
            else:
                rows.append([k, str(v)])
        args.ui.table(["Component", "Status"], rows, title="Circuit Breaker Health")


def cmd_tokens(args):
    r = args.client.token_usage()
    check_auth(r, args)
    rows = []
    for k, v in r.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                rows.append([f"{k}.{sk}", str(sv)])
        else:
            rows.append([k, str(v)])
    args.ui.table(["Metric", "Value"], rows, title="Token Usage")


def cmd_brain(args):
    if args.action == "stats":
        r = args.client.brain_stats()
        check_auth(r, args)
        rows = []
        for k, v in r.items():
            if isinstance(v, (int, float, str, bool)):
                rows.append([str(k), str(v)])
        args.ui.table(["Key", "Value"], rows, title="Brain Stats")
    elif args.action == "recall":
        if not args.query:
            args.ui.error("Query required: nexus brain recall <query>")
            return
        r = args.client.brain_recall(args.query)
        check_auth(r, args)
        if "prompt" in r:
            args.ui.md(r["prompt"])
        elif "context" in r:
            args.ui.md(str(r["context"]))
        else:
            print_json(r)
    elif args.action == "learn":
        if not args.query:
            args.ui.error("Content required: nexus brain learn <content>")
            return
        r = args.client.brain_learn(args.query, category=args.category or "")
        check_auth(r, args)
        if "error" in r:
            args.ui.error(str(r["error"]))
        else:
            args.ui.success("Knowledge stored in cerebro")
    elif args.action == "knowledge":
        r = args.client.brain_knowledge()
        check_auth(r, args)
        items = r.get("knowledge", r.get("items", []))
        if isinstance(items, list):
            for i, item in enumerate(items[:20], 1):
                if isinstance(item, dict):
                    cat = item.get("category", "?")
                    content = str(item.get("content", item.get("text", "")))[:120]
                    args.ui.info(f"[{cat}] {content}")
                else:
                    args.ui.info(f"{i}. {str(item)[:120]}")
        else:
            print_json(r)
    elif args.action == "export":
        r = args.client.brain_export()
        check_auth(r, args)
        print_json(r)


def cmd_hive(args):
    if args.action == "status":
        r = args.client.hive_status()
        check_auth(r, args)
        rows = []
        for k, v in r.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    rows.append([f"{k}.{sk}", str(sv)[:60]])
            else:
                rows.append([k, str(v)[:60]])
        args.ui.table(["Key", "Value"], rows, title="Hive Status")
    elif args.action == "send":
        if not args.target or not args.message_text:
            args.ui.error("Usage: nexus hive send <target> <message>")
            return
        r = args.client.hive_send(args.target, args.message_text, channel=args.channel or "general")
        check_auth(r, args)
        if "error" in r:
            args.ui.error(str(r["error"]))
        else:
            args.ui.success(f"Message sent to {args.target}")


def cmd_system(args):
    if args.action == "stats":
        r = args.client.system_stats()
        check_auth(r, args)
        rows = []
        for k, v in r.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    rows.append([f"{k}.{sk}", str(sv)[:60]])
            else:
                rows.append([k, str(v)[:60]])
        args.ui.table(["Key", "Value"], rows, title="System Stats")
    elif args.action == "safe":
        r = args.client.system_safe()
        check_auth(r, args)
        rows = [[k, str(v)[:60]] for k, v in r.items()]
        args.ui.table(["Check", "Result"], rows, title="Safety Status")


def cmd_absorb(args):
    if args.action == "repo":
        r = args.client.absorb_repo(args.path)
        check_auth(r, args)
        if "error" in r:
            args.ui.error(str(r["error"]))
        else:
            args.ui.success(f"Absorbing {args.path}")
            if "status" in r:
                args.ui.info(r["status"])
    elif args.action == "status":
        r = args.client.absorb_status()
        check_auth(r, args)
        if isinstance(r, dict):
            rows = [[k, str(v)[:60]] for k, v in r.items()]
            args.ui.table(["Key", "Value"], rows, title="Absorption Status")


def build_parser():
    p = argparse.ArgumentParser(prog="nexus", description="SuperNEXUS v2 CLI")
    p.add_argument("--host", default=os.environ.get("NEXUS_HOST", "http://localhost:9000"),
                    help="API server URL (default: http://localhost:9000)")
    p.add_argument("--theme", "-t", default=os.environ.get("NEXUS_THEME", "nexus"),
                    choices=["nexus", "dark", "cyberpunk", "minimal"],
                    help="UI theme (default: nexus)")
    p.add_argument("--json", action="store_true", help="Raw JSON output")

    sub = p.add_subparsers(dest="command", required=True)

    # login
    sp = sub.add_parser("login", help="Authenticate with the API server")
    sp.add_argument("username", help="Username")
    sp.add_argument("password", help="Password")
    sp.set_defaults(func=cmd_login)

    # status
    sp = sub.add_parser("status", help="System status")
    sp.set_defaults(func=cmd_status)

    # doctor
    sp = sub.add_parser("doctor", help="Run diagnostics")
    sp.set_defaults(func=cmd_doctor)

    # health
    sp = sub.add_parser("health", help="Circuit breaker health")
    sp.set_defaults(func=cmd_health)

    # tokens
    sp = sub.add_parser("tokens", help="Token usage report")
    sp.set_defaults(func=cmd_tokens)

    # chat
    sp = sub.add_parser("chat", help="Chat with NEXUS")
    sp.add_argument("message", help="Your message")
    sp.add_argument("--agent", "-g", default="", help="Target specific gema")
    sp.set_defaults(func=cmd_chat)

    # agent
    sp = sub.add_parser("agent", help="Manage agents/gemas")
    sp.add_argument("action", choices=["list", "tell", "loop"])
    sp.add_argument("name", nargs="?", default="", help="Agent name (for tell)")
    sp.add_argument("task", nargs="?", default="", help="Task (for tell/loop)")
    sp.set_defaults(func=cmd_agent)

    # memory
    sp = sub.add_parser("memory", help="Memory operations")
    sp.add_argument("action", choices=["search", "stats", "consolidate", "health"])
    sp.add_argument("query", nargs="?", default="", help="Search query")
    sp.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    sp.set_defaults(func=cmd_memory)

    # devloop
    sp = sub.add_parser("devloop", help="Development loop")
    sp.add_argument("action", choices=["run", "status"])
    sp.add_argument("task", nargs="?", default="", help="Task to run")
    sp.set_defaults(func=cmd_devloop)

    # conductor
    sp = sub.add_parser("conductor", help="Conductor worktree manager")
    sp.add_argument("action", choices=["spawn", "list", "merge", "cleanup"])
    sp.add_argument("name", nargs="?", default="", help="Worktree name")
    sp.add_argument("--goal", default="", help="Goal for spawn")
    sp.set_defaults(func=cmd_conductor)

    # skill
    sp = sub.add_parser("skill", help="Skill marketplace")
    sp.add_argument("action", choices=["list", "install", "publish"])
    sp.add_argument("name", nargs="?", default="", help="Skill name")
    sp.set_defaults(func=cmd_skill)

    # brain
    sp = sub.add_parser("brain", help="Cerebro knowledge base")
    sp.add_argument("action", choices=["stats", "recall", "learn", "knowledge", "export"])
    sp.add_argument("query", nargs="?", default="", help="Query or content")
    sp.add_argument("--category", "-c", default="", help="Category for learn")
    sp.set_defaults(func=cmd_brain)

    # hive
    sp = sub.add_parser("hive", help="Inter-agent messaging")
    sp.add_argument("action", choices=["status", "send"])
    sp.add_argument("target", nargs="?", default="", help="Target agent")
    sp.add_argument("message_text", nargs="?", default="", help="Message content")
    sp.add_argument("--channel", default="general", help="Channel (default: general)")
    sp.set_defaults(func=cmd_hive)

    # system
    sp = sub.add_parser("system", help="System stats and safety")
    sp.add_argument("action", choices=["stats", "safe"])
    sp.set_defaults(func=cmd_system)

    # absorb
    sp = sub.add_parser("absorb", help="Code absorption")
    sp.add_argument("action", choices=["repo", "status"])
    sp.add_argument("path", nargs="?", default="", help="Repo path/URL")
    sp.set_defaults(func=cmd_absorb)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.client = NexusClient(args.host)
    args.ui = NexusUI(style=args.theme)

    if args.json and hasattr(args, "func"):
        r = {"command": args.command}
        if args.command == "status":
            d = args.client.status()
            r = d if isinstance(d, dict) else {"data": str(d)}
        elif args.command == "login":
            r = args.client.login(args.username, args.password)
            if "token" in r:
                args.client.set_token(r["token"])
        elif args.command == "chat":
            r = args.client.chat(args.message, gem=args.agent or "")
        elif args.command == "agent":
            if args.action == "list":
                r = args.client.gemas()
            elif args.action == "tell":
                r = args.client.chat(args.task, gem=args.name)
            elif args.action == "loop":
                r = args.client.agent_loop_run(args.task)
        elif args.command == "memory":
            if args.action == "search":
                r = args.client.memory_search(args.query, limit=args.limit)
            elif args.action == "stats":
                r = args.client.memory_stats()
            elif args.action == "consolidate":
                r = args.client.memory_consolidate()
            elif args.action == "health":
                r = args.client.memory_health()
        elif args.command == "devloop":
            if args.action == "run":
                r = args.client.devloop_run(args.task)
            elif args.action == "status":
                r = args.client.devloop_status()
        elif args.command == "conductor":
            if args.action == "spawn":
                r = args.client.conductor_spawn(args.name, args.goal)
            elif args.action == "list":
                r = args.client.conductor_list()
            elif args.action == "merge":
                r = args.client.conductor_merge(args.name)
            elif args.action == "cleanup":
                r = args.client.conductor_cleanup(args.name)
        elif args.command == "skill":
            if args.action == "list":
                r = args.client.skill_list()
            elif args.action == "install":
                r = args.client.skill_install(args.name)
            elif args.action == "publish":
                r = args.client.skill_publish(args.name)
        elif args.command == "doctor":
            r = args.client.doctor()
        elif args.command == "health":
            r = args.client.health()
        elif args.command == "tokens":
            r = args.client.token_usage()
        elif args.command == "brain":
            if args.action == "stats":
                r = args.client.brain_stats()
            elif args.action == "recall":
                r = args.client.brain_recall(args.query)
            elif args.action == "learn":
                r = args.client.brain_learn(args.query, category=args.category or "")
            elif args.action == "knowledge":
                r = args.client.brain_knowledge()
            elif args.action == "export":
                r = args.client.brain_export()
        elif args.command == "hive":
            if args.action == "status":
                r = args.client.hive_status()
            elif args.action == "send":
                r = args.client.hive_send(args.target, args.message_text, channel=args.channel or "general")
        elif args.command == "system":
            if args.action == "stats":
                r = args.client.system_stats()
            elif args.action == "safe":
                r = args.client.system_safe()
        elif args.command == "absorb":
            if args.action == "repo":
                r = args.client.absorb_repo(args.path)
            elif args.action == "status":
                r = args.client.absorb_status()
        print_json(r)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
