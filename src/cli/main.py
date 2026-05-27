import argparse
import json
import sys
import os
from src.cli.client import NexusClient


def print_json(data: dict):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_auth(r: dict, args):
    if r.get("_auth_required") or "authentication required" in str(r.get("error", "")).lower():
        print("Authentication required. Run: nexus login")
        sys.exit(1)


def cmd_login(args):
    r = args.client.login(args.password)
    if "token" in r:
        args.client.set_token(r["token"])
        print("Logged in successfully")
    elif r.get("error"):
        print(f"Login failed: {r['error']}")
    else:
        print_json(r)


def cmd_status(args):
    r = args.client.status()
    check_auth(r, args)
    d = r.get("director")
    v = r.get("version", "?")
    online = r.get("online", False)
    print(f"NEXUS v{v} - {'ONLINE' if online else 'OFFLINE'}")
    if d:
        print(f"  Role: {d.get('role', '?')}")
        print(f"  Project: {d.get('project', '?')}")
        print(f"  Architecture: {d.get('architecture', '?')}")
    engines = r.get("engines", {})
    print(f"  Director: {d if d else 'lightweight mode'}")
    for eng, status in engines.items():
        print(f"  {eng}: {status}")


def cmd_chat(args):
    r = args.client.chat(args.message, gem=args.agent or "")
    if "response" in r:
        print(r["response"])
    elif "error" in r:
        print(f"Error: {r['error']}")
    else:
        print_json(r)


def cmd_agent(args):
    if args.action == "list":
        r = args.client.gemas()
        if isinstance(r, dict) and "gems" in r:
            for g in r["gems"]:
                name = g.get("name", g) if isinstance(g, dict) else g
                print(f"  {name}")
        elif "error" in r:
            print(f"Error: {r['error']}")
        else:
            print_json(r)
    elif args.action == "tell":
        r = args.client.chat(args.task, gem=args.name)
        if "response" in r:
            print(r["response"])
        elif "error" in r:
            print(f"Error: {r['error']}")
        else:
            print_json(r)
    elif args.action == "loop":
        r = args.client.agent_loop_run(args.task)
        if "result" in r:
            print(r["result"])
        elif "response" in r:
            print(r["response"])
        elif "error" in r:
            print(f"Error: {r['error']}")
        else:
            print_json(r)


def cmd_memory(args):
    if args.action == "search":
        r = args.client.memory_search(args.query, limit=args.limit)
        results = r.get("results", r.get("observations", []))
        if results:
            for i, obs in enumerate(results, 1):
                content = obs.get("content", obs.get("text", str(obs)))[:200]
                print(f"  {i}. {content}")
        else:
            print("No results found")
    elif args.action == "stats":
        r = args.client.memory_stats()
        print_json(r)
    elif args.action == "consolidate":
        r = args.client.memory_consolidate()
        print_json(r)
    elif args.action == "health":
        r = args.client.memory_health()
        print_json(r)


def cmd_devloop(args):
    if args.action == "run":
        r = args.client.devloop_run(args.task)
        print_json(r)
    elif args.action == "status":
        r = args.client.devloop_status()
        print_json(r)


def cmd_conductor(args):
    if args.action == "spawn":
        r = args.client.conductor_spawn(args.name, args.goal)
        print_json(r)
    elif args.action == "list":
        r = args.client.conductor_list()
        print_json(r)
    elif args.action == "merge":
        r = args.client.conductor_merge(args.name)
        print_json(r)
    elif args.action == "cleanup":
        r = args.client.conductor_cleanup(args.name)
        print_json(r)


def cmd_skill(args):
    if args.action == "list":
        r = args.client.skill_list()
        skills = r.get("skills", r.get("results", []))
        if skills:
            for s in skills:
                name = s.get("name", s.get("title", str(s)))
                desc = s.get("description", "")[:80]
                print(f"  {name} — {desc}")
        else:
            print("No skills found")
    elif args.action == "install":
        r = args.client.skill_install(args.name)
        print_json(r)
    elif args.action == "publish":
        r = args.client.skill_publish(args.name)
        print_json(r)


def cmd_doctor(args):
    r = args.client.doctor()
    print_json(r)


def cmd_health(args):
    r = args.client.health()
    print_json(r)


def cmd_tokens(args):
    r = args.client.token_usage()
    print_json(r)


def cmd_absorb(args):
    if args.action == "repo":
        r = args.client.absorb_repo(args.path)
        print_json(r)
    elif args.action == "status":
        r = args.client.absorb_status()
        print_json(r)


def build_parser():
    p = argparse.ArgumentParser(prog="nexus", description="SuperNEXUS v2 CLI")
    p.add_argument("--host", default=os.environ.get("NEXUS_HOST", "http://localhost:9000"),
                    help="API server URL (default: http://localhost:9000)")
    p.add_argument("--json", action="store_true", help="Raw JSON output")

    sub = p.add_subparsers(dest="command", required=True)

    # login
    sp = sub.add_parser("login", help="Authenticate with the API server")
    sp.add_argument("password", help="API password")
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

    if args.json and hasattr(args, "func"):
        r = {"command": args.command}
        if args.command == "status":
            d = args.client.status()
            r = d if isinstance(d, dict) else {"data": str(d)}
        elif args.command == "login":
            r = args.client.login(args.password)
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
