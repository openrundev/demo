#!/usr/bin/env python3
"""Turn cap/data.json (the recorded run) into the replay page's data.js and shots.

Usage: build_data.py <path to openrun>/docs/static/demo/replay [--shots]

Output shown in the replay is trimmed from the recording, never rewritten.
The only substitution is the password in curl commands (shown as $PW).
"""
import json
import os
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(S)
OUT = os.path.abspath(sys.argv[1])
SOURCE = "github.com/openrundev/demo"
d = json.load(open(os.path.join(S, "cap", "data.json")))
src = open(os.path.join(DEMO, "platform.star")).read()
assert SOURCE in src
lines = src.rstrip("\n").split("\n")

CROPS = {"handbook": "1200x336+0+0", "handbook-stage": "1200x336+0+0", "tasks-view-denied": "1100x250+50+70", "svc-restart": "920x420+260+10"}

APPS = [
    ("dashboard", "/eng/dashboard", "Streamlit", "Python", "A Streamlit dashboard, built from requirements.txt", "eng"),
    ("inventory", "/eng/inventory", "Go", "Go", "A net/http server, compiled from main.go", "eng"),
    ("oncall", "/eng/oncall", "Hono on Node", "JavaScript", "A Hono app, built from package.json", "eng"),
    ("tasks-admin", "/tasks/admin", "FastHTML + Postgres", "Python", "Admin app, owns the tasks schema", "eng"),
    ("tasks-edit", "/tasks/edit", "FastHTML + Postgres", "Python", "Work queue, may read everything and write tasks", "eng"),
    ("tasks-view", "/tasks/view", "FastHTML + Postgres", "Python", "The same code with a read-only database role", "eng, support"),
    ("svc", "/ops/svc", "Starlark actions", "Starlark", "Two functions that become a web form and MCP tools", "ops, support (status only)"),
    ("handbook", "/shared/handbook", "Static files", "", "A folder of HTML behind the login", "everyone signed in"),
    ("docs", "docs.localhost:/", "Proxy", "", "A proxied site with auth set to none", "anyone"),
]


def stmt_lines(path):
    """1-based [start, end] of the app(...) statement declaring path."""
    for i, l in enumerate(lines):
        if l.startswith("app(") and f'"{path}"' in l:
            j, depth = i, 0
            while True:
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0:
                    return [i + 1, j + 1]
                j += 1
    raise SystemExit("no app line for " + path)


def secs_of(key):
    return d[key]["secs"]


def tail(key, n):
    return "\n".join(d[key]["out"].split("\n")[-n:])


def redact(cmd):
    return re.sub(r"-u (\w+):[\w-]+", r"-u \1:$PW", cmd)


first = d["first_hits"]["apps"]
restore = d["restore_hits"]["apps"]
apps = []
for id_, path, kind, fw, about, access in APPS:
    url = "https://docs.localhost/" if path.startswith("docs.") else "https://localhost" + path
    key = path
    apps.append({"id": id_, "path": path if not path.startswith("docs.") else "docs.localhost", "url": url, "kind": kind,
                 "fw": fw, "about": about, "access": access, "shot": "svc-restart" if id_ == "svc" else id_, "lines": stmt_lines("docs.:" if path.startswith("docs.") else path),
                 "first": first[key]["secs"], "container": id_ in ("dashboard", "inventory", "oncall", "tasks-admin", "tasks-edit", "tasks-view")})
path_id = {p: i for i, p, *_ in APPS}

mem = 0.0
for l in d["idle_mem_before"]["out"].split("\n"):
    m = re.search(r"\t([\d.]+)MiB", l)
    if m:
        mem += float(m.group(1))

roles = [l.split("|")[0].strip() for l in d["roles"]["out"].split("\n") if l.strip().startswith("cl_rol")]


def role_of(key):
    return re.search(r'"current_user": "([^"]+)"', d[key]["out"]).group(1)


def short(role):
    return role[:14] + "…" + role[-6:]


def pick(key, *needles):
    """The lines of a recorded output that contain one of the needles."""
    return "\n".join(l for l in d[key]["out"].split("\n") if any(n in l for n in needles))


binding_lines = [i + 1 for i, l in enumerate(lines) if "binding(" in l or (i > 0 and "binding(" in lines[i - 1] and l.startswith(" "))]

mcp = d["mcp"]


def tool(t):
    ann = t.get("annotations") or {}
    return {"name": t["name"], "about": [l for l in t["description"].split("\n") if not l.startswith("App ")][0], "destructive": bool(ann.get("destructiveHint"))}


def call(key):
    c = mcp["call_" + key]
    r = c["response"]
    if "error" in r:
        text, failed = "error: " + r["error"]["message"], True
    else:
        text, failed = r["result"]["content"][0]["text"].strip(), bool(r["result"].get("isError"))
    if len(text) > 400:  # the refusal explains the protocol at length: keep its first clause and its verdict
        text = text.split(": it declared")[0] + ". " + re.search(r"The server will not run it \(destructive_confirm=require\)\.", text).group(0)
    return {"tool": c["tool"], "args": json.dumps(c["arguments"], separators=(",", ":")), "text": text, "failed": failed}


sel = d["db_view_select"]["out"]
sel_lines = [l.strip() for l in sel.split("\n") if "current_user\":" in l or "\"todos\":" in l]
wake = []
for p, w in d["wake"].items():
    wake.append({"id": path_id[p], "cmd": redact(w["cmd"]), "out": w["cold"], "secs": float(w["cold"].split()[1].rstrip("s"))})
    assert w["cold"].startswith("200 ") and w["warm"].startswith("200 ")
audit_rows = [dict(zip(("user", "op", "target", "status"), l.split("|"))) for l in d["audit_mcp"]["out"].split("\n")[1:]]

data = {
    "capturedAt": d["captured_at"],
    "footnote": f"Recorded {d['captured_at'][:10]} on a MacBook with Docker (warm build cache), OpenRun built from main. Output is trimmed, not edited.",
    "source": SOURCE,
    "file": src,
    "apps": apps,
    "apply": {"cmd": "openrun apply --approve --promote platform.star",
              "out": pick("apply", "app(s) created", "binding(s) created"), "secs": secs_of("apply")},
    "firstWall": d["first_hits"]["wall_secs"],
    "matrix": {u: {path_id[p]: c for p, c in m.items()} for u, m in d["matrix"].items()},
    "users": [
        {"id": "anonymous", "label": "Not signed in", "sub": "no account", "why": "Only the docs proxy is declared with auth=\"none\"."},
        {"id": "alice", "label": "alice", "sub": "group eng", "why": "Grant: group eng on /eng/** and /tasks/**."},
        {"id": "bob", "label": "bob", "sub": "group ops", "why": "Grant: group ops on /ops/**."},
        {"id": "carol", "label": "carol", "sub": "group support", "why": "Grant: group support on /tasks/view and /ops/**."},
    ],
    "auth": {
        "anonCmd": d["anon_curl"]["cmd"], "anonOut": d["anon_curl"]["out"],
        "whoCmd": redact(d["whoami_user"]["cmd"]), "whoOut": d["whoami_user"]["out"],
    },
    "db": {
        "lines": binding_lines,
        "rows": [
            {"app": "/tasks/admin", "grants": "owner", "means": "creates and owns the schema", "role": short(role_of("db_admin_user"))},
            {"app": "/tasks/edit", "grants": "read:*, full:todo", "means": "reads everything, writes the todo table", "role": short(role_of("db_edit_user"))},
            {"app": "/tasks/view", "grants": "read:*", "means": "read only", "role": short(role_of("db_view_select"))},
        ],
        "selectCmd": d["db_view_select"]["cmd"].replace("/tasks-data/view select", '/tasks-data/view "select') + '"',
        "selectOut": "\n".join(sel_lines),
        "insertCmd": d["db_view_insert"]["cmd"].replace("/tasks-data/view insert", '/tasks-data/view "insert') + '"',
        "insertOut": d["db_view_insert"]["out"],
    },
    "mcp": {
        "endpoint": "/_openrun/app_mcp",
        "agents": [{"id": "carol", "label": "carol", "sub": "group support"}, {"id": "bob", "label": "bob", "sub": "group ops"}],
        "main": ["ops_svc__status", "ops_svc__restart"],
        "tools": {u: [tool(t) for t in mcp["tools_" + u]] for u in ("bob", "carol")},
        "calls": {"carol": [call("status_carol"), call("restart_carol")], "bob": [call("restart_bob_dry"), call("restart_bob")]},
    },
    "ship": {
        "applyCmd": d["stage_apply"]["cmd"], "applyOut": d["stage_apply"]["out"].split("\n")[0],
        "promoteCmd": d["promote"]["cmd"], "promoteOut": d["promote"]["out"],
    },
    "idle": {"countCmd": d["idle_count_before"]["cmd"], "before": d["idle_count_before"]["out"].strip(),
             "after": d["idle_count_after"]["out"].strip(), "mem": round(mem), "waitSecs": d["idle_wait_secs"], "wake": wake},
    "destroy": {
        "delCmd": d["delete"]["cmd"], "delOut": pick("delete", "app(s) deleted"), "delSecs": secs_of("delete"),
        "applyOut": pick("restore_apply", "app(s) created", "binding(s) created"), "applySecs": secs_of("restore_apply"),
        "hits": [{"id": path_id[p], "secs": v["secs"]} for p, v in restore.items()], "wall": d["restore_hits"]["wall_secs"],
    },
    "audit": {"total": int(d["audit_total"]["out"]), "cmd": d["audit_counts"]["cmd"].replace("clace_audit.db select", 'clace_audit.db "select') + '"',
              "out": d["audit_counts"]["out"], "rows": audit_rows},
}

# sanity: what the page claims must match the recording
assert len(d["containers_deleted"]) == 0, "containers survived the delete"
assert d["deleted_status"] != 200, d["deleted_status"]
assert d["stage_check_prod"]["out"] == "0" and d["stage_check_stage"]["out"] == "1" and d["stage_check_prod_after"]["out"] == "1"
assert not [l for l in d["roles_deleted"]["out"].split("\n") if "cl_rol" in l], "roles survived the delete"
assert len(d["idle_containers_now"]) == 0, "containers still running after idle wait"
assert all(v["status"] == 200 for v in first.values()) and all(v["status"] == 200 for v in restore.values())
assert data["idle"]["before"] == str(len(d["containers_after"])) and data["idle"]["after"] == "0"
assert "ops_svc__restart" not in [t["name"] for t in data["mcp"]["tools"]["carol"]]
assert DEMO not in json.dumps(data) and os.environ.get("DEMO_PW_SUFFIX", "-demo-pw") not in json.dumps(data), "local path or password leaked into the page data"

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "data.js"), "w").write("// Generated from a recorded run by setup/build_data.py in the demo repo. Do not edit by hand.\nwindow.LAUNCH = " + json.dumps(data, indent=1) + ";\n")
print("data.js", os.path.getsize(os.path.join(OUT, "data.js")), "bytes; mem", round(mem), "MiB; roles", len(roles), "; lines", len(lines))

if "--shots" in sys.argv:
    os.makedirs(os.path.join(OUT, "shots"), exist_ok=True)
    shot = lambda n: os.path.join(S, "cap", "shots", n + ".png")
    for n in [a["id"] for a in apps] + ["tasks-view-denied", "svc-restart", "svc-carol", "handbook-stage"]:
        subprocess.run(["magick", shot(n), "-resize", "1200x750", "-quality", "82", os.path.join(OUT, "shots", n + ".webp")], check=True)
    # wide crops shown inline in the result panel: name -> geometry
    for n, geo in CROPS.items():
        subprocess.run(["magick", shot(n), "-crop", geo, "+repage", "-quality", "84", os.path.join(OUT, "shots", n + "-crop.webp")], check=True)
