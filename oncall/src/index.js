// On-call rota: a Hono app. No login code here, OpenRun passes the user in.
import { Hono } from 'hono'

const app = new Hono()

const rota = [
  { week: 'This week', primary: 'Priya', secondary: 'Marcus', team: 'Platform' },
  { week: 'Next week', primary: 'Marcus', secondary: 'Elena', team: 'Platform' },
  { week: 'In two weeks', primary: 'Elena', secondary: 'Tomas', team: 'Platform' },
  { week: 'In three weeks', primary: 'Tomas', secondary: 'Priya', team: 'Platform' },
]

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))

const render = (user) => `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>On-call</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font: 16px/1.5 system-ui, sans-serif; margin: 2.5rem auto; max-width: 44rem; padding: 0 1rem; color: #1c2024; }
h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
p.who { color: #5b6470; margin: 0 0 1.5rem; }
.now { border: 1px solid #e3e6ea; border-left: 4px solid #e8590c; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; }
.now b { font-size: 1.4rem; display: block; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #e3e6ea; }
th { font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; color: #5b6470; }
code { background: #f1f3f5; padding: .1rem .35rem; border-radius: 4px; }
</style></head><body>
<h1>On-call</h1>
<p class="who">Request from <code>${esc(user)}</code>, served by Hono on Node</p>
<div class="now">On call now<b>${esc(rota[0].primary)}</b>backup ${esc(rota[0].secondary)}</div>
<table><tr><th>Week</th><th>Primary</th><th>Secondary</th><th>Team</th></tr>
${rota.map((r) => `<tr><td>${esc(r.week)}</td><td>${esc(r.primary)}</td><td>${esc(r.secondary)}</td><td>${esc(r.team)}</td></tr>`).join('\n')}
</table>
</body></html>`

app.get('/', (c) => c.html(render(c.req.header('x-openrun-user') || 'anonymous')))
app.get('/api/rota', (c) => c.json({ user: c.req.header('x-openrun-user') || 'anonymous', rota }))

export default app
