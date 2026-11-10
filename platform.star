# platform.star: every app this server runs
src = config("demo_src", "github.com/openrundev/demo")
box = {"cpus": "1", "memory": "512m"}

# Engineering: three frameworks, no Dockerfile in any of them
app("/eng/dashboard", src + "/dashboard",
    spec="python-streamlit", container_opts=box)
app("/eng/inventory", src + "/inventory",
    spec="go", params={"port": 8080}, container_opts=box)
app("/eng/oncall", src + "/oncall",
    spec="js-hono", container_opts=box)

# Tasks: one Postgres schema, three apps, three database roles
admin = binding("/tasks-data/admin", "postgres")
edit = binding("/tasks-data/edit", admin.path,
               grants=["read:*", "full:todo"])
view = binding("/tasks-data/view", admin.path, grants=["read:*"])
app("/tasks/admin", src + "/tasks", spec="python-fasthtml", verify=True,
    params={"APP_MODULE": "admin:app"}, bindings=[admin.path])
app("/tasks/edit", src + "/tasks", spec="python-fasthtml",
    params={"APP_MODULE": "todo:app"}, bindings=[edit.path])
app("/tasks/view", src + "/tasks", spec="python-fasthtml",
    params={"APP_MODULE": "todo:app"}, bindings=[view.path])

# Ops: two functions, served as a web form and as MCP tools
app("/ops/svc", src + "/svc")

# Everyone: static files, and a proxied site with no login
app("/shared/handbook", src + "/handbook", spec="static")
app("docs.:", "-", spec="proxy", auth="none",
    params={"url": "https://openrun.dev"})
