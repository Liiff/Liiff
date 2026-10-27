"""Membuat header.svg, stack.svg, projects.svg dari data GitHub asli."""
import os, io, json, math, random, urllib.request
from datetime import datetime, timezone
from html import escape

LOGIN = os.environ.get("USERNAME", "liff_co")
TOKEN = os.environ.get("GH_TOKEN", "")
SANS = "'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
FALLBACK_COLORS = ["#a855f7", "#fb923c", "#facc15", "#38bdf8", "#3b82f6"]

QUERY = """
query($login:String!){ user(login:$login){
  name login bio avatarUrl
  followers{totalCount}
  contributionsCollection{ contributionCalendar{ totalContributions } }
  repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC, first:100, orderBy:{field:PUSHED_AT,direction:DESC}){
    totalCount
    nodes{ name description stargazerCount pushedAt
      primaryLanguage{name color}
      repositoryTopics(first:3){nodes{topic{name}}} }
  }
  pinnedItems(first:2, types:REPOSITORY){ nodes{ ... on Repository{
    name description stargazerCount pushedAt
    primaryLanguage{name color}
    repositoryTopics(first:3){nodes{topic{name}}} } } }
} }"""

def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]

def fetch_avatar(url):
    try:
        with urllib.request.urlopen(url + ("&" if "?" in url else "?") + "s=96") as r:
            return r.read()
    except Exception:
        return None

def ago(iso):
    d = datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))
    s = d.total_seconds()
    if s < 3600: return "updated just now" if s < 300 else f"updated {int(s//60)}m ago"
    if s < 86400: return f"updated {int(s//3600)}h ago"
    if s < 86400*60: return f"updated {int(s//86400)}d ago"
    return f"updated {int(s//(86400*30))}mo ago"

def wrap(text, width=22, lines=2):
    words, out, cur = (text or "No description").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    out.append(cur)
    out = out[:lines]
    if len(" ".join(words)) > sum(len(x) for x in out) + lines:
        out[-1] = out[-1][:width-1].rstrip() + "…"
    return out

def pill(x, y, label, color):
    w = 46 + len(label) * 7.8
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="30" rx="15" fill="#0f1a2e" stroke="#243553"/>'
            f'<circle cx="{x+16}" cy="{y+15}" r="5" fill="{color}"/>'
            f'<text x="{x+30}" y="{y+20}" font-family="{SANS}" font-size="14" fill="#cbd5e1">{escape(label)}</text>'), w + 8

def portrait(cx, cy, avatar_bytes):
    random.seed(4)
    out, step = [], 4.2
    img = None
    if avatar_bytes:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((33, 35))
        except Exception:
            img = None
    for i in range(-16, 17):
        for j in range(-17, 18):
            nx, ny = i / 16.5, j / 17.5
            d = nx * nx + ny * ny
            if d > 1: continue
            if img:
                r_, g_, b_ = img.getpixel((i + 16, j + 17))
                col = f"rgb({r_},{g_},{b_})"
            else:
                col = f"hsl({int(20 + (nx+1)/2*110)},65%,{60 + int(15*random.random())}%)"
            r = 1.7 * (1 - 0.3 * d) * (0.85 + 0.25 * random.random())
            out.append(f'<circle cx="{cx+i*step:.1f}" cy="{cy+j*step:.1f}" r="{r:.2f}" fill="{col}" opacity="{0.6+0.4*(1-d):.2f}"/>')
    return "".join(out)

def build_header(u, langs, avatar):
    random.seed(1)
    stars = "".join(
        f'<circle cx="{random.randint(16,544)}" cy="{random.randint(12,270)}" r="{random.choice([0.8,1.2,1.6])}" fill="#fff" class="tw" style="animation-delay:{random.random()*3:.2f}s"/>'
        for _ in range(22))
    nodes = u["repositories"]["nodes"]
    vals = [
        ("Repositories", str(u["repositories"]["totalCount"]), '<rect x="2" y="3" width="18" height="12" rx="2"/><path d="M7 19h8"/>'),
        ("Stars", str(sum(n["stargazerCount"] for n in nodes)), '<path d="M11 2l2.7 5.6 6.1.9-4.4 4.3 1 6.1L11 16l-5.4 2.9 1-6.1L2.2 8.5l6.1-.9z"/>'),
        ("Contributions", str(u["contributionsCollection"]["contributionCalendar"]["totalContributions"]), '<path d="M3 18V9M9 18V4M15 18v-7M21 18V7"/>'),
        ("Followers", str(u["followers"]["totalCount"]), '<circle cx="11" cy="7" r="4"/><path d="M3 20c1-4 4-6 8-6s7 2 8 6"/>'),
    ]
    stats = ""
    for k, (label, val, icon) in enumerate(vals):
        x, y = 28 + (k % 2) * 262, 218 + (k // 2) * 40
        stats += (f'<g transform="translate({x},{y})"><g fill="none" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" transform="translate(0,-12) scale(1.1)">{icon}</g>'
                  f'<text x="32" y="6" font-family="{SANS}" font-size="19" fill="#5eead4" font-weight="700">{val}</text>'
                  f'<text x="{44+11*len(val)}" y="6" font-family="{SANS}" font-size="15" fill="#cbd5e1">{label}</text></g>')
    pills, x = "", 28
    for n, _, c in langs[:4]:
        p, w = pill(x, 150, n, c)
        if x + w > 540: break
        pills += p; x += w
    name = u["name"] or u["login"]
    size = 46 if len(name) <= 9 else 34 if len(name) <= 14 else 26
    bio = (u["bio"] or "").strip()
    bio = bio if len(bio) <= 32 else bio[:31] + "…"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="290" viewBox="0 0 560 290">
<defs><linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#6366f1"/></linearGradient>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a1226"/><stop offset="1" stop-color="#0b1b33"/></linearGradient>
<filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<style>.tw{{animation:tw 3s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.15}}50%{{opacity:1}}}}.nm{{animation:fi 1.2s ease-out both}}@keyframes fi{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}</style>
<rect x="2" y="2" width="556" height="286" rx="20" fill="url(#bg)" stroke="url(#bd)" stroke-width="2.5"/>
{stars}
<g class="nm">
<text x="28" y="48" font-family="{MONO}" font-size="16" fill="#5eead4">@{escape(u["login"])}</text>
<text x="28" y="100" font-family="{SANS}" font-size="{size}" font-weight="800" fill="#fff" filter="url(#glow)">{escape(name)}</text>
<text x="28" y="130" font-family="{MONO}" font-size="14" fill="#94a3b8">{escape(bio)}</text></g>
{portrait(470,78,avatar)}{pills}{stats}</svg>'''

def build_stack(langs):
    rows = ""
    top = max([p for _, p, _ in langs] + [1])
    for i, (n, p, c) in enumerate(langs):
        y = 118 + i * 46
        w = max(p / top * 270, 16)
        rows += (f'<circle cx="34" cy="{y}" r="7" fill="{c}"/>'
                 f'<text x="52" y="{y+6}" font-family="{SANS}" font-size="17" fill="#e2e8f0">{escape(n)}</text>'
                 f'<text x="188" y="{y+6}" font-family="{MONO}" font-size="16" fill="{c}" font-weight="700">{p}%</text>'
                 f'<rect x="250" y="{y-6}" width="280" height="12" rx="6" fill="#1b2538"/>'
                 f'<rect x="250" y="{y-6}" width="{w:.0f}" height="12" rx="6" fill="{c}" class="bar" style="animation-delay:{i*0.15}s"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="330" viewBox="0 0 560 330">
<defs><linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee" stop-opacity=".6"/><stop offset="1" stop-color="#6366f1" stop-opacity=".6"/></linearGradient></defs>
<style>.bar{{transform-box:fill-box;transform-origin:left;animation:g 1.2s ease-out both}}@keyframes g{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}</style>
<rect x="1.5" y="1.5" width="557" height="327" rx="20" fill="#0a1226" stroke="url(#bd)" stroke-width="2"/>
<text x="28" y="48" font-family="{SANS}" font-size="26" font-weight="700" fill="#fff">Language Stack</text>
<text x="28" y="72" font-family="{SANS}" font-size="14" fill="#5eead4">Repository-weighted technologies</text>
<text x="532" y="46" text-anchor="end" font-family="{MONO}" font-size="13" fill="#5eead4">&gt; stack.scan_</text>
{rows}</svg>'''

def card(x, r):
    lang = r["primaryLanguage"] or {"name": "—", "color": "#64748b"}
    l = wrap(r["description"], width=27)
    topics = [t["topic"]["name"] for t in r["repositoryTopics"]["nodes"]][:2]
    tags, tx = "", x + 18
    for t in topics:
        w = 24 + len(t) * 7
        if tx + w > x + 236: break
        tags += (f'<rect x="{tx}" y="226" width="{w:.0f}" height="26" rx="7" fill="#0f2038" stroke="#1e3a5f"/>'
                 f'<text x="{tx+w/2:.0f}" y="243" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#38bdf8">{escape(t)}</text>')
        tx += w + 8
    name = r["name"] if len(r["name"]) <= 18 else r["name"][:17] + "…"
    return (f'<rect x="{x}" y="100" width="250" height="200" rx="14" fill="#0d1a30" stroke="#1e3a5f"/>'
            f'<circle cx="{x+22}" cy="128" r="5.5" fill="{lang["color"] or "#64748b"}"/>'
            f'<text x="{x+38}" y="134" font-family="{SANS}" font-size="16" font-weight="700" fill="#fff">{escape(name)}</text>'
            f'<text x="{x+18}" y="162" font-family="{SANS}" font-size="14" fill="#94a3b8">{escape(l[0])}</text>'
            f'<text x="{x+18}" y="182" font-family="{SANS}" font-size="14" fill="#94a3b8">{escape(l[1]) if len(l)>1 else ""}</text>'
            f'<text x="{x+18}" y="214" font-family="{SANS}" font-size="14" fill="#facc15">★ {r["stargazerCount"]}</text>'
            f'<text x="{x+70}" y="214" font-family="{SANS}" font-size="14" fill="#cbd5e1">{escape(lang["name"])}</text>'
            f'{tags}<text x="{x+18}" y="283" font-family="{MONO}" font-size="12" fill="#64748b">{ago(r["pushedAt"])}</text>')

def build_projects(repos):
    cards = "".join(card(20 + i * 270, r) for i, r in enumerate(repos[:2]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
<defs><linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee" stop-opacity=".6"/><stop offset="1" stop-color="#6366f1" stop-opacity=".6"/></linearGradient></defs>
<rect x="1.5" y="1.5" width="557" height="317" rx="20" fill="#0a1226" stroke="url(#bd)" stroke-width="2"/>
<text x="28" y="44" font-family="{MONO}" font-size="17" fill="#cbd5e1">Projects.list</text>
<text x="176" y="44" font-family="{MONO}" font-size="13" fill="#64748b">./projects.sh --all</text>
<line x1="28" y1="60" x2="532" y2="60" stroke="#1e3a5f"/>
<text x="28" y="84" font-family="{SANS}" font-size="14" fill="#5eead4">Featured projects</text>
{cards}</svg>'''

def language_stats(nodes):
    count, color = {}, {}
    for n in nodes:
        pl = n["primaryLanguage"]
        if pl:
            count[pl["name"]] = count.get(pl["name"], 0) + 1
            color[pl["name"]] = pl["color"]
    total = sum(count.values()) or 1
    ranked = sorted(count.items(), key=lambda kv: -kv[1])[:5]
    return [(n, round(c / total * 100), color.get(n) or FALLBACK_COLORS[i % 5]) for i, (n, c) in enumerate(ranked)]

def main(user=None):
    u = user or fetch()
    nodes = u["repositories"]["nodes"]
    langs = language_stats(nodes)
    pinned = u["pinnedItems"]["nodes"]
    repos = pinned if pinned else sorted(nodes, key=lambda n: -n["stargazerCount"])
    avatar = fetch_avatar(u["avatarUrl"]) if not user else None
    for fn, svg in (("header.svg", build_header(u, langs, avatar)),
                    ("stack.svg", build_stack(langs)),
                    ("projects.svg", build_projects(repos))):
        with open(fn, "w", encoding="utf-8") as f:
            f.write(svg)
    print("OK:", LOGIN, langs)

if __name__ == "__main__":
    main()
