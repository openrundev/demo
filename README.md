# OpenRun demo

One declaration file, `platform.star`, that sets up a small internal platform
on [OpenRun](https://openrun.dev): nine apps in five frameworks behind one
login, with per-team access, a Postgres role per app, an ops tool served to AI
agents as MCP tools, staging, and idle apps that stop. It is the run replayed
at https://openrun.dev/demo/.

| App | What it is | Source |
| :--- | :--- | :--- |
| `/eng/dashboard` | Streamlit dashboard | `dashboard/` |
| `/eng/inventory` | Go `net/http` service | `inventory/` |
| `/eng/oncall` | Hono app on Node | `oncall/` |
| `/tasks/admin`, `/tasks/edit`, `/tasks/view` | FastHTML apps sharing one Postgres schema, each with its own role | `tasks/` |
| `/ops/svc` | Starlark actions: service status and a rolling restart | `svc/` |
| `/shared/handbook` | Static files | `handbook/` |
| `docs.localhost` | Proxy to openrun.dev, no login | |

None of the app directories has a Dockerfile or any login code.

## Run it

You need OpenRun, and Docker or Podman.

```sh
git clone https://github.com/openrundev/demo && cd demo
setup/setup.sh
. setup/env.sh
openrun apply --approve --promote platform.star
```

`setup/setup.sh` makes a throwaway server in `.server/`, separate from any
OpenRun install you already have. It:

- writes `.server/openrun.toml` (login required by default, MCP enabled, the
  restart script allowed) and starts the server on https://localhost:25942
- starts a Postgres container and registers it as the `postgres/main` service
- adds three users, one per team: `alice` (eng), `bob` (ops), `carol` (support).
  Passwords are `<name>-demo-pw`
- loads the grants from `rbac.json`
- creates an MCP key for bob's and carol's agents in `.server/keys/`

`. setup/env.sh` points the `openrun` CLI in your shell at that server.
`setup/teardown.sh --purge` removes all of it.

| Group | Can open | Extra |
| :--- | :--- | :--- |
| `eng` | `/eng/**`, `/tasks/**` | |
| `ops` | `/ops/**` | the `svc_restart` permission, which the restart action requires |
| `support` | `/tasks/view`, `/ops/**` | sees the status action only |
| everyone | `/shared/**`, `docs.localhost` | |

With an OIDC or SAML provider in place of builtin users, the groups come from
the identity provider and nothing else changes.

## Things to try

Open https://localhost:25942/eng/dashboard and sign in as each user, then:

```sh
openrun --as builtin:carol app list              # carol sees four of the nine apps
openrun binding run-command /tasks-data/view \
  "insert into todo (title, done) values ('x', false)"   # permission denied for table todo
openrun apply --approve platform.star /shared/handbook   # after editing handbook/index.html: staged only
openrun app promote /shared/handbook
openrun delete platform.star                     # removes apps, containers, images and database roles
```

To connect an agent, add `https://localhost:25942/_openrun/app_mcp?auth=builtin`
as an MCP server with the key from `.server/keys/bob.txt` or `carol.txt` as the
bearer token. Carol's agent is offered `ops_svc__status`. Bob's is also offered
`ops_svc__restart`, which is destructive and needs a client that can ask him
to confirm.

## On your own server

`platform.star` reads the app sources from this repository by default, so on a
server that already has a Postgres service and users:

```sh
openrun apply --approve --promote github.com/openrundev/demo/platform.star
```

The server settings the demo relies on are the ones `setup/setup.sh` writes.

## How the replay is recorded

Everything on the replay page comes from one run of these scripts.

| Script | Does |
| :--- | :--- |
| `setup/setup.sh` | Creates the server, as above |
| `setup/record.sh` | The whole run in story order: `capture.py`, then `shots.cjs` |
| `setup/capture.py` | Runs each command and stores its output and timing in `setup/cap/data.json` |
| `setup/shots.cjs` | Playwright screenshots of every app |
| `setup/build_data.py` | Trims the recording into the page's `data.js` and `shots/`, and asserts that what the page claims matches the recording |
| `setup/record.cjs` | Records the autoplaying page to video |

```sh
setup/setup.sh && setup/record.sh
python3 setup/build_data.py ../openrun/docs/static/demo/replay --shots
```

Rules the page follows: output is trimmed, never rewritten; the only
substitution is the password in curl commands (`$PW`).
