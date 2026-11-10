// Inventory service: a plain net/http server with no auth code of its own.
// OpenRun does the login and passes the user on every request.
package main

import (
	"encoding/json"
	"html/template"
	"log"
	"net/http"
)

type item struct {
	SKU   string `json:"sku"`
	Name  string `json:"name"`
	Stock int    `json:"stock"`
}

var items = []item{
	{"KB-104", "Mechanical keyboard", 42},
	{"MN-270", "27 inch monitor", 17},
	{"DK-300", "USB-C dock", 8},
	{"HS-020", "Headset", 63},
	{"LT-140", "14 inch laptop", 5},
}

var page = template.Must(template.New("page").Parse(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Inventory</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font: 16px/1.5 system-ui, sans-serif; margin: 2.5rem auto; max-width: 44rem; padding: 0 1rem; color: #1c2024; }
h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
p.who { color: #5b6470; margin: 0 0 1.5rem; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #e3e6ea; }
th { font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; color: #5b6470; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
td.low { color: #b42318; font-weight: 600; }
code { background: #f1f3f5; padding: .1rem .35rem; border-radius: 4px; }
</style></head><body>
<h1>Inventory</h1>
<p class="who">Request from <code>{{.User}}</code>, served by a Go binary</p>
<table><tr><th>SKU</th><th>Item</th><th style="text-align:right">In stock</th></tr>
{{range .Items}}<tr><td><code>{{.SKU}}</code></td><td>{{.Name}}</td><td class="n{{if lt .Stock 10}} low{{end}}">{{.Stock}}</td></tr>
{{end}}</table>
</body></html>`))

func user(r *http.Request) string {
	if u := r.Header.Get("X-Openrun-User"); u != "" {
		return u
	}
	return "anonymous"
}

func main() {
	http.HandleFunc("/api/items", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"user": user(r), "items": items})
	})
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		page.Execute(w, map[string]any{"User": user(r), "Items": items})
	})
	log.Fatal(http.ListenAndServe("0.0.0.0:8080", nil))
}
