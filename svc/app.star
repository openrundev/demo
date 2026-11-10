load("exec.in", "exec")

def status(dry_run, args):
    rows = []
    for i in range(1, args.replicas + 1):
        rows.append({"instance": "%s-%d" % (args.service, i), "env": args.env, "state": "healthy", "uptime": "%dh" % (12 * i)})
    return ace.result("%s instances in %s" % (args.service, args.env), rows, ace.TABLE)

def restart(dry_run, args):
    if args.env == "prod" and args.replicas < 2:
        return ace.result("Validation failed", param_errors={"replicas": "prod keeps at least 2 instances during a restart"})
    if dry_run:
        return ace.result("Ready to restart %d %s instances in %s" % (args.replicas, args.service, args.env))
    return exec.run("./restart.sh", [args.service, args.env, str(args.replicas)],
                    cwd=ace.config("ops_dir", "/opt/ops"), stream=True)

app = ace.app("Service Ops",
    actions=[
        ace.action("Status", "/", status, read_only=True,
                   description="Show the instances of a service"),
        ace.action("Restart", "/restart", restart, is_async=True, timeout="10m",
                   show_validate=True, destructive=True, permit=["svc_restart"],
                   description="Rolling restart of a service, one instance at a time"),
    ],
    permissions=[ace.permission("exec.in", "run", ["./restart.sh"])],
)
