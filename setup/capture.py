#!/usr/bin/env python3
"""Record a real run of the demo against the server made by setup.sh.

Usage: capture.py <phase>...   (phases: part1, stage, promote, idle, destroy, audit)
Every command, its output and its timing go to cap/data.json. Run it through
record.sh, which sources env.sh first.
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time

S = os.path.dirname(os.path.abspath(__file__))
PLAT = os.path.dirname(S)
HOME = os.environ["OPENRUN_HOME"]
CAP = os.path.join(S, "cap")
os.makedirs(CAP, exist_ok=True)
DATA = os.path.join(CAP, "data.json")
ENV = dict(os.environ)
PORT = os.environ["DEMO_HTTPS_PORT"]
PG = os.environ["DEMO_PG_NAME"]
BASE = "https://localhost:" + PORT
PW = {u: u + os.environ["DEMO_PW_SUFFIX"] for u in ("alice", "bob", "carol")}
APPS = ["/eng/dashboard", "/eng/inventory", "/eng/oncall", "/tasks/admin", "/tasks/edit",
        "/tasks/view", "/ops/svc", "/shared/handbook", "docs.localhost:/"]
OWNER = {"/eng": "alice", "/tasks": "alice", "/ops": "bob", "/shared": "carol"}

data = json.load(open(DATA)) if os.path.exists(DATA) else {}


def save():
    json.dump(data, open(DATA, "w"), indent=1)


def run(key, cmd, cwd=PLAT, shell=False):
    """Run a command, record output + duration under key."""
    t = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=ENV, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    dur = time.time() - t
    out = p.stdout.rstrip("\n")
    data[key] = {"cmd": cmd if shell else " ".join(cmd), "out": out, "secs": round(dur, 2), "rc": p.returncode}
    save()
    print(f"[{key}] rc={p.returncode} {dur:.2f}s\n{out[-1500:]}\n")
    return out


def url(app):
    if app.startswith("docs."):
        return f"https://docs.localhost:{PORT}/"
    return BASE + app + "/"


def hit_cmd(app, user=None):
    auth = f"-u {user}:{PW[user]} " if user else ""
    return f"curl -sk {auth}-o /dev/null -w '%{{http_code}} %{{time_total}}s' {url(app)}"


def hit(app, user=None):
    out = subprocess.run(hit_cmd(app, user), shell=True, capture_output=True, text=True).stdout
    code, t = out.split()
    return int(code), round(float(t.rstrip("s")), 3)


def owner(app):
    for pre, u in OWNER.items():
        if app.startswith(pre):
            return u
    return None


def first_hits(key):
    """Request every app at once as a permitted user: time until each one answers."""
    t = time.time()
    with cf.ThreadPoolExecutor(len(APPS)) as ex:
        res = dict(zip(APPS, ex.map(lambda a: hit(a, owner(a)), APPS)))
    data[key] = {"apps": {a: {"status": s, "secs": d} for a, (s, d) in res.items()},
                 "wall_secs": round(time.time() - t, 2)}
    save()
    print(key, json.dumps(data[key], indent=1))


def containers(key):
    out = subprocess.run("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep '^clc-app_prd' || true",
                         shell=True, capture_output=True, text=True).stdout.strip()
    data[key] = out.splitlines()
    save()
    print(key, len(data[key]), "containers")
    return data[key]


def psql(key, sql):
    return run(key, ["docker", "exec", PG, "psql", "-U", "postgres", "-d", "apps", "-c", sql])


def mcp(user, method, params, meta=""):
    keyfile = open(os.path.join(HOME, "keys", f"{user}.txt")).read()
    tok = re.search(r"orun_pat_[A-Za-z0-9_-]+", keyfile).group(0)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    p = subprocess.run(["curl", "-sk", "-X", "POST", BASE + "/_openrun/app_mcp?auth=builtin",
                        "-H", "Authorization: Bearer " + tok, "-H", "Content-Type: application/json",
                        "-H", "Accept: application/json, text/event-stream", "-d", body],
                       capture_output=True, text=True)
    txt = p.stdout
    m = re.search(r"^data: (.*)$", txt, re.M)
    return json.loads(m.group(1)) if m else {"raw": txt}


def part1():
    data.clear()
    data["captured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run("version", ["openrun", "server", "version"])
    # clean slate (not part of the story)
    subprocess.run(["openrun", "delete", "platform.star"], cwd=PLAT, env=ENV, capture_output=True)
    containers("containers_before")
    psql("roles_before", r"\du")

    # 1. one command
    run("apply", ["openrun", "apply", "--approve", "--promote", "platform.star"])
    run("app_list", ["openrun", "app", "list"])
    first_hits("first_hits")
    containers("containers_after")
    run("docker_stats", "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' | grep '^clc-app_prd'", shell=True)

    # 2. who can reach what
    matrix = {}
    for u in [None, "alice", "bob", "carol"]:
        matrix[u or "anonymous"] = {a: hit(a, u)[0] for a in APPS}
    data["matrix"] = matrix
    save()
    print(json.dumps(matrix, indent=1))
    for u in ["alice", "bob", "carol"]:
        run(f"app_list_{u}", ["openrun", "--as", f"builtin:{u}", "app", "list"])
    run("anon_curl", f"curl -sk -o /dev/null -w '%{{http_code}}' {BASE}/eng/inventory/api/items", shell=True)
    run("whoami_alice", f"curl -sk -u alice:$PW {BASE}/eng/inventory/api/items".replace("$PW", PW["alice"]), shell=True)
    run("whoami_user", f"curl -sk -u alice:$PW {BASE}/eng/inventory/api/items | jq .user".replace("$PW", PW["alice"]), shell=True)
    run("whoami_oncall", f"curl -sk -u alice:$PW {BASE}/eng/oncall/api/rota".replace("$PW", PW["alice"]), shell=True)

    # 3. one database, three roles
    run("binding_list", ["openrun", "binding", "list"])
    psql("roles", r"\du")
    psql("schemas", r"\dn")
    run("app_edit_create", f"curl -sk -u alice:{PW['alice']} -X POST {BASE}/tasks/edit/create -d 'title=Write the launch post' | grep -o 'Could not save[^<]*\\|Write the launch post' | sort -u", shell=True)
    run("app_view_create", f"curl -sk -u alice:{PW['alice']} -X POST {BASE}/tasks/view/create -d 'title=Sneak one in' | grep -o 'Could not save[^<]*\\|Sneak one in' | sort -u", shell=True)
    run("db_edit_update", ["openrun", "binding", "run-command", "/tasks-data/edit",
                           "update todo set details = 'due on launch day' where title = 'Write the launch post'"])
    run("db_admin_user", ["openrun", "binding", "run-command", "/tasks-data/admin", "select current_user"])
    run("db_edit_user", ["openrun", "binding", "run-command", "/tasks-data/edit", "select current_user"])
    run("db_view_select", ["openrun", "binding", "run-command", "/tasks-data/view",
                           "select current_user, count(*) as todos from todo"])
    run("db_view_insert", ["openrun", "binding", "run-command", "/tasks-data/view",
                           "insert into todo (title, done) values ('sneak one in', false)"])
    run("db_view_delete", ["openrun", "binding", "run-command", "/tasks-data/view", "delete from todo"])

    # 4. the ops actions as MCP tools, one key per agent
    m = {}
    for u in ["bob", "carol"]:
        r = mcp(u, "tools/list", {})
        m[f"tools_{u}"] = [{"name": t["name"], "title": t.get("title"), "annotations": t.get("annotations"),
                            "description": t.get("description")} for t in r.get("result", {}).get("tools", [])]
    calls = [("status_carol", "carol", "ops_svc__status", {"service": "api", "env": "prod"}),
             ("restart_carol", "carol", "ops_svc__restart", {"service": "api", "env": "prod"}),
             ("status_bob", "bob", "ops_svc__status", {"service": "api", "env": "prod"}),
             ("restart_bob_dry", "bob", "ops_svc__restart", {"service": "api", "env": "prod", "replicas": 2, "dry_run": True}),
             ("restart_bob", "bob", "ops_svc__restart", {"service": "api", "env": "prod", "replicas": 2})]
    for key, u, tool, args in calls:
        m["call_" + key] = {"user": u, "tool": tool, "arguments": args,
                            "response": mcp(u, "tools/call", {"name": tool, "arguments": args})}
    data["mcp"] = m
    save()
    print(json.dumps(m, indent=1)[:6000])


def stage():
    # 5. ship a change: staged first, promoted after a look
    hb = os.path.join(PLAT, "handbook", "index.html")
    src = open(hb).read()
    if "Changes are staged" not in src:
        src = src.replace("<li>Nobody edits the server by hand</li>",
                          "<li>Nobody edits the server by hand</li><li>Changes are staged: this line shipped on launch day</li>")
        open(hb, "w").write(src)
    run("stage_apply", ["openrun", "apply", "--approve", "platform.star", "/shared/handbook"])
    grep = "grep -c 'this line shipped' || true"
    run("stage_check_prod", f"curl -sk -u carol:{PW['carol']} {BASE}/shared/handbook/ | {grep}", shell=True)
    run("stage_check_stage", f"curl -sk -u carol:{PW['carol']} https://stage.localhost:{PORT}/shared/handbook/ | {grep}", shell=True)
    run("stage_app_list", ["openrun", "app", "list", "--internal", "/shared/handbook"])
    run("stage_versions_before", ["openrun", "version", "list", "/shared/handbook"])


STAGED = "<li>Changes are staged: this line shipped on launch day</li>"


def unstage():
    # put handbook/index.html back the way the repo has it
    hb = os.path.join(PLAT, "handbook", "index.html")
    open(hb, "w").write(open(hb).read().replace(STAGED, ""))


def promote():
    run("promote", ["openrun", "app", "promote", "/shared/handbook"])
    run("stage_check_prod_after", f"curl -sk -u carol:{PW['carol']} {BASE}/shared/handbook/ | grep -c 'this line shipped' || true", shell=True)
    run("stage_versions_after", ["openrun", "version", "list", "/shared/handbook"])


COUNT = "docker ps -q --filter name=clc-app_prd | wc -l"


def idle():
    # 6. idle apps stop; the next request starts them again
    t = time.time()
    run("idle_count_before", COUNT, shell=True)
    run("idle_mem_before", "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | grep '^clc-app_prd'", shell=True)
    while True:
        n = len(containers("idle_containers_now"))
        if n == 0 or time.time() - t > 600:
            break
        time.sleep(10)
    data["idle_wait_secs"] = round(time.time() - t)
    run("idle_count_after", COUNT, shell=True)
    wake = {}
    for a in ["/eng/inventory", "/eng/oncall", "/tasks/edit", "/eng/dashboard"]:
        cmd = hit_cmd(a, owner(a))
        cold = run("wake_cold_" + a, cmd, shell=True)
        warm = run("wake_warm_" + a, cmd, shell=True)
        wake[a] = {"cmd": cmd, "cold": cold, "warm": warm}
    data["wake"] = wake
    save()


def destroy():
    # 7. delete everything the file declares, then bring it back
    run("delete", ["openrun", "delete", "platform.star"])
    containers("containers_deleted")
    psql("roles_deleted", r"\du")
    run("app_list_deleted", ["openrun", "app", "list"])
    data["deleted_status"] = hit("/eng/inventory", "alice")[0]
    run("restore_apply", ["openrun", "apply", "--approve", "--promote", "platform.star"])
    first_hits("restore_hits")
    containers("containers_restored")
    psql("roles_restored", r"\du")


def audit():
    db = "metadata/clace_audit.db"
    run("audit_counts", ["sqlite3", "-header", db, "select event_type, count(*) as n from audit group by 1 order by 2 desc"], cwd=HOME)
    run("audit_total", ["sqlite3", db, "select count(*) from audit"], cwd=HOME)
    run("audit_mcp", ["sqlite3", "-header", db,
                      "select user_id, operation, target, status from audit where event_type = 'mcp' order by create_time"], cwd=HOME)
    run("audit_system", ["sqlite3", "-header", db,
                         "select user_id, operation, target, status, count(*) as n from audit where event_type = 'system' group by 1,2,3,4 order by min(create_time)"], cwd=HOME)


if __name__ == "__main__":
    for ph in sys.argv[1:]:
        globals()[ph]()
