"""Command registry and dispatch for NEXUS Console."""
from __future__ import annotations

import json
from typing import Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.box import SIMPLE_HEAVY

from src.cli.client import NexusClient
from src.cli.streaming import stream_chat_sync


def _print_json(console: Console, data: dict):
    console.print_json(json.dumps(data, ensure_ascii=False))


def _print_table(console: Console, headers: list[str], rows: list[list[str]], title: str = ""):
    t = Table(title=title, box=SIMPLE_HEAVY, title_style="bold cyan")
    for h in headers:
        t.add_column(h, style="cyan")
    for row in rows:
        t.add_row(*[str(c) for c in row])
    console.print(t)


def _check_auth(console: Console, r: dict) -> bool:
    if r.get("_auth_required"):
        console.print("[red]✗ Authentication required. Use /login[/]")
        return True
    return False


# ── Command implementations ──────────────────────────────────────────

def cmd_chat(client: NexusClient, console: Console, args: str, **kw):
    if not args.strip():
        console.print("[dim]Usage: /chat <message> or just type your message[/]")
        return
    # Try streaming first, fallback to HTTP
    try:
        result = stream_chat_sync(client.base_url, client.token, args, console)
    except Exception:
        result = None
    if result is None:
        # Fallback to HTTP
        console.print("[dim]⟳ Fallback to HTTP...[/]")
        try:
            r = client.chat(args)
            if "response" in r:
                console.print(Markdown(r["response"]))
            elif "error" in r:
                console.print(f"[red]✗ {r['error']}[/]")
            else:
                _print_json(console, r)
        except Exception as e:
            console.print(f"[red]✗ HTTP fallback failed: {e}[/]")


def cmd_status(client: NexusClient, console: Console, args: str, **kw):
    r = client.status()
    if _check_auth(console, r):
        return

    online = r.get("online", False)
    v = r.get("version", "?")
    status_color = "green" if online else "red"
    status_text = "ONLINE" if online else "OFFLINE"
    console.print(f"[bold cyan]◆ NEXUS v{v}[/] — [{status_color}]{status_text}[/]")

    # Engines
    engines = r.get("engines", {})
    if engines:
        parts = []
        for eng, st in engines.items():
            icon = "[green]●[/]" if st == "online" else "[dim]○[/]"
            parts.append(f"{icon} {eng}")
        console.print(f"  Engines: {'  '.join(parts)}")

    # Memory
    memory = r.get("memory", {})
    if memory:
        parts = []
        for kind, stats in memory.items():
            if isinstance(stats, dict):
                total = stats.get("total_entries", stats.get("total_patterns", "?"))
                parts.append(f"{kind}:{total}")
        console.print(f"  Memory: {'  │  '.join(parts)}")

    # Cerebro
    cerebro = r.get("cerebro", {})
    if cerebro:
        console.print(
            f"  Cerebro: {cerebro.get('conversaciones', '?')} conversations, "
            f"{cerebro.get('conocimientos', '?')} knowledge"
        )


def cmd_agent(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 2)
    action = parts[0] if parts else "list"

    if action == "list":
        r = client.gemas()
        if _check_auth(console, r):
            return
        gems = r.get("gems", [])
        rows = []
        for g in gems:
            name = g.get("name", str(g)) if isinstance(g, dict) else str(g)
            status = g.get("status", "") if isinstance(g, dict) else ""
            rows.append([name, status])
        _print_table(console, ["Agent", "Status"], rows, title=f"Agents ({len(rows)})")
    elif action == "tell" and len(parts) >= 3:
        name, task = parts[1], parts[2]
        r = client.chat(task, gem=name)
        if "response" in r:
            console.print(Markdown(r["response"]))
        elif "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
    elif action == "loop" and len(parts) >= 2:
        task = " ".join(parts[1:])
        r = client.agent_loop_run(task)
        if "result" in r:
            console.print(Panel(r["result"], title="Agent Loop"))
        elif "response" in r:
            console.print(Markdown(r["response"]))
        elif "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
    else:
        console.print("[dim]Usage: /agent list | tell <name> <task> | loop <task>[/]")


def cmd_brain(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 1)
    action = parts[0] if parts else "stats"
    query = parts[1] if len(parts) > 1 else ""

    if action == "stats":
        r = client.brain_stats()
        if _check_auth(console, r):
            return
        rows = [[str(k), str(v)] for k, v in r.items() if isinstance(v, (int, float, str, bool))]
        _print_table(console, ["Key", "Value"], rows, title="Brain Stats")
    elif action == "recall":
        if not query:
            console.print("[dim]Usage: /brain recall <query>[/]")
            return
        r = client.brain_recall(query)
        if _check_auth(console, r):
            return
        console.print(Markdown(str(r.get("prompt", r.get("context", json.dumps(r))))))
    elif action == "learn":
        if not query:
            console.print("[dim]Usage: /brain learn <content>[/]")
            return
        r = client.brain_learn(query)
        if _check_auth(console, r):
            return
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print("[green]✓ Knowledge stored[/]")
    elif action == "knowledge":
        r = client.brain_knowledge()
        if _check_auth(console, r):
            return
        items = r.get("knowledge", r.get("items", []))
        if isinstance(items, list):
            for i, item in enumerate(items[:20], 1):
                if isinstance(item, dict):
                    cat = item.get("category", "?")
                    txt = str(item.get("content", item.get("text", "")))[:100]
                    console.print(f"  [cyan]{i}.[/] [{cat}] {txt}")
                else:
                    console.print(f"  [cyan]{i}.[/] {str(item)[:100]}")
        else:
            _print_json(console, r)
    elif action == "export":
        r = client.brain_export()
        if _check_auth(console, r):
            return
        _print_json(console, r)
    else:
        console.print("[dim]Usage: /brain stats|recall|learn|knowledge|export [query][/]")


def cmd_memory(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 1)
    action = parts[0] if parts else "stats"
    query = parts[1] if len(parts) > 1 else ""

    if action == "search":
        if not query:
            console.print("[dim]Usage: /memory search <query>[/]")
            return
        r = client.memory_search(query)
        if _check_auth(console, r):
            return
        results = r.get("results", r.get("observations", []))
        if results:
            for i, obs in enumerate(results, 1):
                txt = obs.get("content", obs.get("text", str(obs)))[:150]
                console.print(f"  [cyan]{i}.[/] {txt}")
        else:
            console.print("[dim]No results[/]")
    elif action == "stats":
        r = client.memory_stats()
        if _check_auth(console, r):
            return
        rows = [[str(k), str(v)] for k, v in r.items() if isinstance(v, (int, float, str, bool))]
        _print_table(console, ["Key", "Value"], rows, title="Memory Stats")
    elif action == "consolidate":
        r = client.memory_consolidate()
        if _check_auth(console, r):
            return
        console.print(f"[green]✓ {r.get('message', r.get('status', 'Done'))}[/]")
    elif action == "health":
        r = client.memory_health()
        if _check_auth(console, r):
            return
        _print_json(console, r)
    else:
        console.print("[dim]Usage: /memory search|stats|consolidate|health [query][/]")


def cmd_hive(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 2)
    action = parts[0] if parts else "status"

    if action == "status":
        r = client.hive_status()
        if _check_auth(console, r):
            return
        rows = []
        for k, v in r.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    rows.append([f"{k}.{sk}", str(sv)[:60]])
            else:
                rows.append([k, str(v)[:60]])
        _print_table(console, ["Key", "Value"], rows, title="Hive Status")
    elif action == "send" and len(parts) >= 3:
        target, msg = parts[1], parts[2]
        r = client.hive_send(target, msg)
        if _check_auth(console, r):
            return
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Sent to {target}[/]")
    else:
        console.print("[dim]Usage: /hive status | send <target> <message>[/]")


def cmd_system(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split()
    action = parts[0] if parts else "stats"

    if action == "stats":
        r = client.system_stats()
        if _check_auth(console, r):
            return
        rows = []
        for k, v in r.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    rows.append([f"{k}.{sk}", str(sv)[:60]])
            else:
                rows.append([k, str(v)[:60]])
        _print_table(console, ["Key", "Value"], rows, title="System Stats")
    elif action == "safe":
        r = client.system_safe()
        if _check_auth(console, r):
            return
        rows = [[k, str(v)[:60]] for k, v in r.items()]
        _print_table(console, ["Check", "Result"], rows, title="Safety Status")
    else:
        console.print("[dim]Usage: /system stats|safe[/]")


def cmd_doctor(client: NexusClient, console: Console, args: str, **kw):
    r = client.doctor()
    if _check_auth(console, r):
        return
    rows = []
    for k, v in r.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                rows.append([f"{k}.{sk}", str(sv)[:60]])
        else:
            rows.append([k, str(v)[:60]])
    _print_table(console, ["Check", "Result"], rows, title="Diagnostics")


def cmd_health(client: NexusClient, console: Console, args: str, **kw):
    r = client.health()
    if _check_auth(console, r):
        return
    rows = []
    for k, v in r.items():
        if isinstance(v, dict):
            rows.append([k, v.get("state", str(v.get("status", "?")))])
        else:
            rows.append([k, str(v)])
    _print_table(console, ["Component", "Status"], rows, title="Health")


def cmd_tokens(client: NexusClient, console: Console, args: str, **kw):
    r = client.token_usage()
    if _check_auth(console, r):
        return
    rows = []
    for k, v in r.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                rows.append([f"{k}.{sk}", str(sv)])
        else:
            rows.append([k, str(v)])
    _print_table(console, ["Metric", "Value"], rows, title="Token Usage")


def cmd_model(client: NexusClient, console: Console, args: str, **kw):
    name = args.strip()
    if name:
        # Switch model
        r = client._post("/api/actors/model-select", {"model": name})
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Model set to {name}[/]")
    else:
        # Show current
        r = client.status()
        director = r.get("director", {})
        model = director.get("model", "unknown")
        console.print(f"[cyan]◆[/] Active model: [bold]{model}[/]")


def cmd_skill(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 1)
    action = parts[0] if parts else "list"

    if action == "list":
        r = client.skill_list()
        if _check_auth(console, r):
            return
        skills = r.get("skills", r.get("results", []))
        rows = []
        for s in skills[:20]:
            name = s.get("name", s.get("title", str(s)))[:30]
            desc = s.get("description", "")[:50]
            rows.append([name, desc])
        _print_table(console, ["Skill", "Description"], rows, title=f"Skills ({len(skills)})")
    elif action == "install" and len(parts) > 1:
        r = client.skill_install(parts[1])
        if _check_auth(console, r):
            return
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Installed {parts[1]}[/]")
    else:
        console.print("[dim]Usage: /skill list | install <name>[/]")


def cmd_conductor(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 2)
    action = parts[0] if parts else "list"

    if action == "list":
        r = client.conductor_list()
        if _check_auth(console, r):
            return
        _print_json(console, r)
    elif action == "spawn" and len(parts) >= 2:
        name = parts[1]
        goal = parts[2] if len(parts) > 2 else ""
        r = client.conductor_spawn(name, goal)
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Spawned {name}[/]")
    elif action == "merge" and len(parts) >= 2:
        r = client.conductor_merge(parts[1])
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Merged {parts[1]}[/]")
    elif action == "cleanup" and len(parts) >= 2:
        r = client.conductor_cleanup(parts[1])
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Cleaned {parts[1]}[/]")
    else:
        console.print("[dim]Usage: /conductor list|spawn|merge|cleanup <name> [goal][/]")


def cmd_devloop(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 1)
    action = parts[0] if parts else "status"

    if action == "status":
        r = client.devloop_status()
        if _check_auth(console, r):
            return
        _print_json(console, r)
    elif action == "run" and len(parts) > 1:
        r = client.devloop_run(parts[1])
        if _check_auth(console, r):
            return
        _print_json(console, r)
    else:
        console.print("[dim]Usage: /devloop status | run <task>[/]")


def cmd_absorb(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split(None, 1)
    action = parts[0] if parts else "status"

    if action == "status":
        r = client.absorb_status()
        if _check_auth(console, r):
            return
        _print_json(console, r)
    elif action == "repo" and len(parts) > 1:
        r = client.absorb_repo(parts[1])
        if _check_auth(console, r):
            return
        if "error" in r:
            console.print(f"[red]✗ {r['error']}[/]")
        else:
            console.print(f"[green]✓ Absorbing {parts[1]}[/]")
    else:
        console.print("[dim]Usage: /absorb status | repo <path>[/]")


def cmd_help(client: NexusClient, console: Console, args: str, **kw):
    from src.cli.completer import COMMAND_TREE, COMMAND_HELP

    target = args.strip()
    if target and target in COMMAND_HELP:
        cmd_name = target if target.startswith("/") else f"/{target}"
        console.print(f"\n[bold cyan]{cmd_name}[/] — {COMMAND_HELP.get(cmd_name, '')}")
        subs = COMMAND_TREE.get(cmd_name, [])
        if subs:
            console.print(f"  Subcommands: {', '.join(subs)}")
        console.print()
        return

    rows = []
    for cmd, desc in sorted(COMMAND_HELP.items()):
        subs = COMMAND_TREE.get(cmd, [])
        sub_str = " ".join(subs) if subs else ""
        rows.append([cmd, desc, sub_str])
    _print_table(console, ["Command", "Description", "Subcommands"], rows, title="NEXUS Console Commands")
    console.print("[dim]  Tip: Type without / to chat directly. Tab for autocomplete.[/]")


def cmd_login(client: NexusClient, console: Console, args: str, **kw):
    parts = args.strip().split()
    if len(parts) >= 2:
        username, password = parts[0], parts[1]
    else:
        console.print("[dim]Usage: /login <username> <password>[/]")
        return

    r = client.login(username, password)
    if "token" in r:
        client.set_token(r["token"])
        console.print(f"[green]✓ Logged in as {username}[/]")
    elif "error" in r:
        console.print(f"[red]✗ {r['error']}[/]")


# ── Command Registry ─────────────────────────────────────────────────

# ── New endpoints wired (commits 7..48) ──────────────────────────────

def cmd_sessions(client: NexusClient, console: Console, args: str, **kw):
    """List sessions catalog with budget+logs info."""
    r = client.sessions_catalog()
    if _check_auth(console, r): return
    rows = [
        [s.get("session_id","?"), str(s.get("request_count",0)),
         str(s.get("total_tokens",0)), f"${s.get('cost_usd',0)}",
         s.get("summary_status","-"), s.get("last_update","-")[:19]]
        for s in r.get("sessions", [])
    ]
    _print_table(console, ["Session","Req","Tokens","Cost","Status","Last"],
                 rows, title=f"Sessions ({r.get('count',0)})")


def cmd_budget(client: NexusClient, console: Console, args: str, **kw):
    """Budget per session or all (no args = all, <sid> = one)."""
    sid = args.strip()
    if sid:
        r = client.session_budget(sid)
        if _check_auth(console, r): return
        _print_json(console, r)
    else:
        r = client.budget_all()
        if _check_auth(console, r): return
        console.print(f"[cyan]Total sessions:[/] {r.get('sessions',0)}, "
                      f"[cyan]total cost:[/] ${r.get('total_cost_usd',0)}")
        if r.get("cap_env"):
            console.print(f"[yellow]NEXUS_MAX_USD_PER_SESSION={r['cap_env']}[/]")


def cmd_scratchpad(client: NexusClient, console: Console, args: str, **kw):
    """/scratchpad <sid> [read|append <text>|clear]"""
    parts = args.split(None, 2)
    if not parts:
        console.print("[dim]Usage: /scratchpad <session_id> [read|append <text>|clear][/]")
        return
    sid = parts[0]
    op = parts[1] if len(parts) > 1 else "read"
    if op == "read":
        r = client.session_scratchpad_read(sid)
        if _check_auth(console, r): return
        console.print(Panel(r.get("content","(empty)"), title=f"Scratchpad: {sid}"))
    elif op == "append" and len(parts) > 2:
        r = client.session_scratchpad_write(sid, append=parts[2])
        console.print(f"[green]✓[/] {r}")
    elif op == "clear":
        r = client.session_scratchpad_write(sid, clear=True)
        console.print("[green]✓[/] cleared")
    else:
        console.print("[dim]Usage: /scratchpad <sid> [read|append <text>|clear][/]")


def cmd_cookbook(client: NexusClient, console: Console, args: str, **kw):
    """Hardware scan + recommended Ollama models."""
    r = client.cookbook_scan()
    if _check_auth(console, r): return
    hw = r.get("hardware", {})
    console.print(f"[cyan]HW:[/] {hw.get('os')} / CPU={hw.get('cpu_count')} / "
                  f"RAM={hw.get('ram_gb')}GB / VRAM={hw.get('vram_gb')}GB "
                  f"({hw.get('gpu_name','no GPU')}) / disk={hw.get('free_disk_gb')}GB")
    rows = [[m["name"], m["tier"], f"{m['size_gb']}GB",
             f"{m['vram_gb']}GB", m["use"]] for m in r.get("recommended", [])]
    _print_table(console, ["Model","Tier","Size","VRAM","Use"], rows,
                 title=f"Recommended ({len(r.get('recommended',[]))}/{len(r.get('can_run',[]))})")


def cmd_sbom(client: NexusClient, console: Console, args: str, **kw):
    """Software Bill of Materials — full inventory."""
    r = client.sbom()
    if _check_auth(console, r): return
    s = r.get("summary", {})
    rows = [[k, str(v)] for k, v in s.items()]
    _print_table(console, ["Component","Value"], rows, title="SBOM Summary")


def cmd_caps(client: NexusClient, console: Console, args: str, **kw):
    """Capability audit — gemas + missing caps."""
    r = client.caps_audit()
    if _check_auth(console, r): return
    console.print(f"[cyan]Enforcement:[/] {r.get('enforcement_active')}, "
                  f"gemas with missing caps: {r.get('gemas_with_missing')}/{r.get('total_gemas')}")
    if args.strip() == "v":  # verbose
        for gema, missing in (r.get("missing") or {}).items():
            console.print(f"  [yellow]{gema}[/]: {len(missing)} missing")


def cmd_mcp(client: NexusClient, console: Console, args: str, **kw):
    """MCP health probe. Pass 'restart' to attempt restart."""
    r = client.mcp_health(restart=(args.strip() == "restart"))
    if _check_auth(console, r): return
    console.print(f"[cyan]MCP:[/] total={r.get('total')} alive={r.get('alive')} "
                  f"connected={r.get('connected')} restarted={r.get('restarted')}")
    rows = [[n, "UP" if s["connected"] else "down",
             "yes" if s["process_alive"] else "no", str(s["tool_count"])]
            for n, s in (r.get("servers") or {}).items()]
    _print_table(console, ["Server","State","Process","Tools"], rows, title="MCP Servers")


def cmd_workers(client: NexusClient, console: Console, args: str, **kw):
    """Stalled background workers (default threshold 30min)."""
    th = int(args.strip()) if args.strip().isdigit() else 30
    r = client.workers_stalled(threshold_minutes=th)
    if _check_auth(console, r): return
    console.print(f"[cyan]Stalled workers:[/] {r.get('stalled_count',0)} "
                  f"(threshold {r.get('threshold_minutes')}min)")
    for w in r.get("stalled", []):
        console.print(f"  [yellow]{w['name']}[/]: {w['minutes_since']}min "
                      f"(interval={w['interval_seconds']}s, errors={w['error_count']})")


def cmd_dmn(client: NexusClient, console: Console, args: str, **kw):
    """DMN background reflection. Pass 'tick' to force scan."""
    if args.strip() == "tick":
        r = client.dmn_tick()
        if _check_auth(console, r): return
        console.print(f"[cyan]Tick:[/] {r.get('count',0)} candidates")
        for c in r.get("candidates", [])[:10]:
            console.print(f"  [{c['level']}] {c['category']}: {c['title']}")
    else:
        r = client.dmn_stats()
        if _check_auth(console, r): return
        s = r.get("stats", {})
        console.print(f"[cyan]DMN:[/] running={r.get('running')} interval={r.get('interval_s')}s | "
                      f"ticks={s.get('ticks')} candidates={s.get('candidates')} "
                      f"spoken={s.get('spoken')} logged={s.get('logged')} dropped={s.get('dropped')}")


def cmd_events(client: NexusClient, console: Console, args: str, **kw):
    """Event bus stats."""
    r = client.events_stats()
    if _check_auth(console, r): return
    console.print(f"[cyan]Events:[/] emitted={r.get('events_emitted')} "
                  f"subs={r.get('subscribers')} persist={r.get('persist_enabled')}")
    if r.get("subscriber_labels"):
        console.print(f"  subscribers: {r['subscriber_labels']}")


def cmd_slash(client: NexusClient, console: Console, args: str, **kw):
    """List server-side slash commands (the palette)."""
    r = client.slash_list()
    if _check_auth(console, r): return
    rows = [[c["name"], ",".join(c["aliases"]) or "-", c["args"], c["description"]]
            for c in r.get("commands", [])]
    _print_table(console, ["Cmd","Aliases","Args","Description"], rows,
                 title=f"Slash palette ({r.get('count',0)})")


def cmd_setup(client: NexusClient, console: Console, args: str, **kw):
    """Setup wizard: preflight or state."""
    if args.strip() == "state":
        r = client.setup_state()
    else:
        r = client.setup_preflight()
    if _check_auth(console, r): return
    _print_json(console, r)


def cmd_a2a(client: NexusClient, console: Console, args: str, **kw):
    """A2A agent card (/.well-known/agent.json)."""
    r = client.a2a_card()
    if _check_auth(console, r): return
    console.print(f"[cyan]A2A:[/] {r.get('name')} v{r.get('version')} | "
                  f"skills={len(r.get('skills',[]))} endpoints={len(r.get('endpoints',[]))}")
    caps = [k for k,v in r.get("capabilities", {}).items() if v]
    console.print(f"  capabilities: {caps}")


COMMANDS: dict[str, Callable] = {
    "/chat": cmd_chat,
    "/status": cmd_status,
    "/agent": cmd_agent,
    "/brain": cmd_brain,
    "/memory": cmd_memory,
    "/hive": cmd_hive,
    "/system": cmd_system,
    "/doctor": cmd_doctor,
    "/health": cmd_health,
    "/tokens": cmd_tokens,
    "/model": cmd_model,
    "/skill": cmd_skill,
    "/conductor": cmd_conductor,
    "/devloop": cmd_devloop,
    "/absorb": cmd_absorb,
    "/help": cmd_help,
    "/login": cmd_login,
    # New (commits 7..48)
    "/sessions": cmd_sessions,
    "/budget": cmd_budget,
    "/scratchpad": cmd_scratchpad,
    "/cookbook": cmd_cookbook,
    "/sbom": cmd_sbom,
    "/caps": cmd_caps,
    "/mcp": cmd_mcp,
    "/workers": cmd_workers,
    "/dmn": cmd_dmn,
    "/events": cmd_events,
    "/slash": cmd_slash,
    "/setup": cmd_setup,
    "/a2a": cmd_a2a,
}


def dispatch(
    text: str,
    client: NexusClient,
    console: Console,
) -> str | None:
    """Dispatch a command or bare text. Returns 'exit' to quit, 'clear' to clear."""
    text = text.strip()
    if not text:
        return None

    # Special commands
    if text in ("/exit", "/quit", "/q"):
        return "exit"
    if text in ("/clear", "/cls"):
        return "clear"

    # /theme handling
    if text.startswith("/theme"):
        parts = text.split(None, 1)
        if len(parts) > 1:
            return f"theme:{parts[1]}"
        else:
            console.print("[dim]Usage: /theme nexus|dark|cyberpunk|minimal[/]")
            return None

    # /command dispatch
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if cmd in COMMANDS:
            try:
                COMMANDS[cmd](client=client, console=console, args=args)
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/]")
        else:
            console.print(f"[red]✗ Unknown command: {cmd}. Type /help[/]")
        return None

    # Bare text → chat (skip if looks like a path search artifact)
    if text.startswith("Buscando") or text.startswith("No encontrado"):
        return None
    cmd_chat(client=client, console=console, args=text)
    return None
