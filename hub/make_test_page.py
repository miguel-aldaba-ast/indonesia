"""Local test harness: the hub page against an in-memory copy of the database (not shipped)."""
import json, pathlib, sys
seed_dir, hub_html, out = map(pathlib.Path, sys.argv[1:4])
docs = {}
for f in seed_dir.glob("*.json"):
    d = json.loads(f.read_text())
    n = f.stem
    if n.startswith("site__"): docs["sites/" + n[len("site__"):]] = d
    elif n.startswith("meta__"): docs["meta/" + n[len("meta__"):]] = d
    elif n.startswith("country__"): docs["countries/" + n[len("country__"):]] = d
MOCK = """<script>
(function(){
  var store = %s, subs = [];
  function snapDoc(path){ var has = Object.prototype.hasOwnProperty.call(store, path); return {id: path.split('/').pop(), exists: has, data: function(){return has ? JSON.parse(JSON.stringify(store[path])) : undefined}}; }
  function collDocs(col){ return Object.keys(store).filter(function(p){ return p.indexOf(col + '/') === 0 && p.split('/').length === 2; }).map(snapDoc); }
  function notify(){ subs.slice().forEach(function(s){ s(); }); }
  function q(col, ord, lim){
    var o = { orderBy: function(f, d){ return q(col, {f: f, d: d || 'asc'}, lim); }, limit: function(n){ return q(col, ord, n); },
      get: async function(){ return build(); },
      onSnapshot: function(cb){ var fire = function(){ cb(build()); }; subs.push(fire); setTimeout(fire, 0); return function(){}; } };
    function build(){ var docs = collDocs(col); if (ord) docs.sort(function(a,b){ var x=(a.data()[ord.f]||''), y=(b.data()[ord.f]||''); return (x<y?-1:x>y?1:0) * (ord.d==='desc'?-1:1); }); if (lim) docs = docs.slice(0, lim); return {docs: docs, size: docs.length, empty: !docs.length}; }
    return o;
  }
  var DB = {
    collection: function(col){ var c = q(col); c.doc = function(id){ return DB.doc(col + '/' + (id || ('auto' + Math.random().toString(36).slice(2,8)))); };
      c.add = async function(data){ var r = c.doc(); await r.set(data); return r; }; return c; },
    doc: function(path){ return { path: path, get: async function(){ return snapDoc(path); },
      set: async function(d){ store[path] = JSON.parse(JSON.stringify(d)); notify(); },
      update: async function(d){ store[path] = Object.assign({}, store[path], d); notify(); },
      delete: async function(){ delete store[path]; notify(); },
      onSnapshot: function(cb){ var fire = function(){ cb(snapDoc(path)); }; subs.push(fire); setTimeout(fire, 0); return function(){}; } }; }
  };
  window.__store = store;
  window.claude = { use: async function(n){
    if (n === 'db') return DB;
    if (n === 'user') return { id: async function(){ return 'u_tester'; }, can: async function(){ return true; }, profiles: async function(ids){ var o = {}; ids.forEach(function(i){ o[i] = {name: 'Test User'}; }); return o; } };
    if (n === 'downloads') return { save: async function(o){ window.__saved = o; } };
    return null; } };
})();
</script>""" % json.dumps(docs)
html = hub_html.read_text(encoding="utf-8")
marker = "<script>\n(function () {\n  'use strict';"
i = html.index(marker)
out.write_text("<style>[hidden]{display:none!important}body{margin:0;font:14px system-ui}</style>\n" + html[:i] + MOCK + "\n" + html[i:], encoding="utf-8")
print("test page written", out.stat().st_size, "bytes;", len(docs), "docs")
