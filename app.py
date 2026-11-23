"""
Cricket Live Score Website — Python + Flask
================================================
REAL DATA ONLY — koi fake / demo score nahi hai.
Source: ESPN Cricinfo public JSON API (bina API key ke chalta hai)
  - Series discovery:  https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=cricket
  - Scoreboard:        https://site.api.espn.com/apis/site/v2/sports/cricket/{series_id}/scoreboard
  - Match summary:     https://site.web.api.espn.com/apis/site/v2/sports/cricket/{series_id}/summary?event={event_id}
Player images + team logos bhi ESPN CDN se aate hain:
  https://a.espncdn.com/i/headshots/cricket/players/full/{player_id}.png

Optional 2nd source (agar aap chahein): CricAPI / CricketData.org
  .env me CRICAPI_KEY daalein — tab /api/live usko fallback ke tor par use karega.
  Key free me yahan se milegi: https://cricapi.com  (100 hits/day free)

Run locally:
  pip install -r requirements.txt
  python app.py        ->  http://127.0.0.1:5000
Deploy: Render / PythonAnywhere / VPS — README.md dekhein.
"""
import os
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from flask import Flask, jsonify, render_template_string, request

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Live Cricket Score — Real-Time | ESPN Cricinfo Data</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f4f6f8;color:#111}
.hidden{display:none!important}
.topbar{background:#0b1e3a;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.brand{font-size:20px}.brand span{font-size:12px;opacity:.75;font-weight:400;margin-left:6px}
.top-right{font-size:12px;opacity:.9;display:flex;gap:14px;flex-wrap:wrap}
.filters{background:#fff;padding:12px 18px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #e2e6ea;position:sticky;top:0;z-index:5}
.chip{border:1px solid #cbd5e1;background:#fff;border-radius:999px;padding:7px 14px;cursor:pointer;font-size:14px}
.chip.active{background:#0b1e3a;color:#fff;border-color:#0b1e3a}
#searchBox{margin-left:auto;padding:8px 12px;border:1px solid #cbd5e1;border-radius:999px;min-width:200px}
.updated{font-size:12px;color:#64748b}
main{max-width:980px;margin:0 auto;padding:16px}
.featured{background:#0b1e3a;color:#fff;border-radius:16px;overflow:hidden;margin-bottom:20px}
.score-head{padding:22px 20px 10px;text-align:center}
.series{font-size:13px;opacity:.8}
.status-line{margin-top:6px;font-size:13px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.live-badge{background:#e11d48;color:#fff;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.55}}
.score-row{display:flex;justify-content:center;align-items:center;gap:18px;margin:18px 0 8px;flex-wrap:wrap}
.team{text-align:center;min-width:130px}
.team img{width:64px;height:64px;object-fit:contain;background:#fff;border-radius:50%;padding:6px}
.team .abbr{font-weight:800;font-size:18px;margin-top:6px}
.team .score{font-size:24px;font-weight:800}
.vs{font-size:28px;opacity:.6}
.result{color:#facc15;font-weight:700;font-size:17px;padding-bottom:14px}
.carousel-wrap{background:#fff;color:#111;padding:14px 14px 6px}
.carousel-title{font-weight:700;margin-bottom:10px}
.carousel{display:flex;gap:12px;overflow-x:auto;padding-bottom:12px}
.pcard{min-width:118px;text-align:center}
.pcard img{width:110px;height:110px;object-fit:cover;object-position:top;border-radius:12px;background:#e2e8f0;display:block}
.pcard .pname{font-size:13px;font-weight:700;margin-top:6px}
.pcard .pteam{font-size:12px;color:#64748b}
.tabs{display:flex;background:#fff;border-top:1px solid #e2e6ea}
.tab{flex:1;padding:13px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;font-size:15px;font-weight:600;color:#334155}
.tab.active{color:#0b1e3a;border-bottom-color:#e11d48}
.tab-panel{background:#fff;color:#111;padding:18px}
.performers{display:grid;gap:10px}
.perf{display:flex;align-items:center;gap:12px;border:1px solid #e2e8f0;border-radius:12px;padding:10px}
.perf img{width:52px;height:52px;border-radius:50%;object-fit:cover;object-position:top;background:#e2e8f0}
.perf .v{margin-left:auto;font-weight:800;font-size:18px;text-align:right}
.perf .v small{display:block;font-size:12px;color:#64748b;font-weight:400}
.notes p{background:#f8fafc;border-left:3px solid #0b1e3a;padding:10px 12px;border-radius:6px}
.hint{color:#64748b;font-size:13px}
table{width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px}
th,td{padding:8px;border-bottom:1px solid #e2e8f0;text-align:left}
th{background:#f8fafc}
.match-list{display:grid;gap:12px}
.mcard{background:#fff;border-radius:14px;padding:16px;cursor:pointer;border:2px solid transparent}
.mcard:hover{border-color:#0b1e3a}
.mcard.selected{border-color:#e11d48}
.mcard .mseries{font-size:12px;color:#64748b}
.mcard .mteams{font-size:17px;font-weight:800;margin:6px 0}
.mcard .mscore{font-size:15px}
.mcard .mstatus{color:#b45309;font-weight:700;margin-top:6px}
.mcard .mstatus.live{color:#e11d48}
.empty{background:#fff;border-radius:14px;padding:24px;text-align:center}
footer{max-width:980px;margin:0 auto;padding:20px;color:#64748b;font-size:12px;text-align:center}
@media(max-width:640px){.team .score{font-size:19px}.score-row{gap:10px}#searchBox{margin-left:0;width:100%}}

</style>
</head>
<body>
<header class="topbar">
  <div class="brand">🏏 <b>CRICKET LIVE</b> <span>Real-Time Score</span></div>
  <div class="top-right">
    <span id="liveClock"></span>
    <span class="src">Source: ESPN Cricinfo • Auto-refresh 20s</span>
  </div>
</header>

<div class="filters">
  <button class="chip active" data-filter="all">All Matches</button>
  <button class="chip" data-filter="live">🔴 Live</button>
  <button class="chip" data-filter="upcoming">Upcoming</button>
  <button class="chip" data-filter="results">Results</button>
  <input id="searchBox" type="search" placeholder="Search team… e.g. Pakistan, India">
  <span id="updatedAt" class="updated"></span>
</div>

<main>
  <section id="featured" class="featured hidden">
    <div class="score-head">
      <div class="series" id="fSeries"></div>
      <div class="status-line"><span id="fLiveBadge" class="live-badge">● LIVE</span><span id="fFormat"></span><span id="fVenue"></span></div>
      <div class="score-row" id="fScoreRow"></div>
      <div class="result" id="fResult"></div>
    </div>

    <!-- Player images carousel — bilkul screenshot jaisa, upar khiladiyon ki photos -->
    <div class="carousel-wrap">
      <div class="carousel-title">Players in this match</div>
      <div class="carousel" id="playerCarousel"></div>
    </div>

    <div class="tabs">
      <button class="tab active" data-tab="summary">Summary</button>
      <button class="tab" data-tab="scorecard">Scorecard</button>
      <button class="tab" data-tab="commentary">Commentary / Notes</button>
    </div>

    <div class="tab-panel" id="panel-summary">
      <h3>Top Performers</h3>
      <div id="topPerformers" class="performers"></div>
      <div id="summaryNotes" class="notes"></div>
    </div>

    <div class="tab-panel hidden" id="panel-scorecard">
      <div id="scorecard"></div>
    </div>

    <div class="tab-panel hidden" id="panel-commentary">
      <div id="commentaryBox" class="notes"></div>
      <p class="hint">Ball-by-ball commentary ESPN ke match page par available hoti hai — notes aur scorecard yahan live update hote hain.</p>
    </div>
  </section>

  <section>
    <h2 id="listHeading">Matches</h2>
    <div id="matchList" class="match-list"></div>
    <div id="emptyState" class="empty hidden">
      <h3>Abhi koi live match nahi chal raha</h3>
      <p>Neeche upcoming aur recent results dikhaye ja rahe hain. Jaise hi koi match live hoga, woh yahan khud aa jayega — koi fake score nahi dikhaya jata.</p>
    </div>
    <div id="errorState" class="empty hidden">
      <h3>Live data load nahi hui</h3>
      <p>ESPN Cricinfo se connection nahi mila. Page refresh karein ya thodi der baad dobara try karein.</p>
    </div>
  </section>
</main>

<footer>
  <p>Data: ESPN Cricinfo public API (real, live) • Player photos &amp; team logos: ESPN CDN • Ye site koi score invent nahi karti — jo ESPN par hai, wahi yahan hai.</p>
  <p>Unofficial fan site. Not affiliated with ESPN / ICC. For commercial use, please use a licensed API (CricAPI / Sportmonks).</p>
</footer>

<script>
// Cricket Live — frontend. Sirf /api/* se REAL data leta hai, koi hardcoded score nahi.
let allMatches = [];
let selected = null;   // {series_id, event_id}
let filter = "all";
let search = "";

const $ = (id) => document.getElementById(id);

function esc(s){ return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function fmtTime(ts){ return new Date(ts*1000).toLocaleTimeString("en-PK",{hour:"2-digit",minute:"2-digit",second:"2-digit"}); }
function initials(name){ return (name||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase(); }

async function loadMatches(){
  try{
    const r = await fetch("/api/live");
    const d = await r.json();
    if(!d.matches){ throw new Error(d.error||"no data"); }
    allMatches = d.matches;
    $("updatedAt").textContent = "Last updated: " + fmtTime(d.updated_at) + " • " + d.source + " • Live: " + d.live_count;
    $("errorState").classList.add("hidden");
    renderList();
    // auto-select: pehla live match, warna pehla result
    if(!selected){
      const pick = allMatches.find(m=>m.is_live) || allMatches[0];
      if(pick) selectMatch(pick);
    } else {
      // selected match ab bhi list me hai to refresh karein
      const cur = allMatches.find(m=>m.id===selected.event_id);
      if(cur) loadDetail(cur.series_id, cur.id, false);
    }
  }catch(e){
    $("errorState").classList.remove("hidden");
  }
}

function visibleMatches(){
  return allMatches.filter(m=>{
    if(filter==="live" && !m.is_live) return false;
    if(filter==="upcoming" && m.state!=="pre") return false;
    if(filter==="results" && m.state!=="post") return false;
    if(search && !m.name.toLowerCase().includes(search)) return false;
    return true;
  });
}

function renderList(){
  const list = visibleMatches();
  $("emptyState").classList.toggle("hidden", !(allMatches.length && !allMatches.some(m=>m.is_live) && filter==="all"));
  $("matchList").innerHTML = list.map(m=>{
    const t = m.teams.map(x=>`<div>${esc(x.short||x.name)} <span style="font-weight:400">${esc(x.score||"")}</span></div>`).join("");
    return `<div class="mcard ${selected&&selected.event_id===m.id?"selected":""}" data-sid="${esc(m.series_id)}" data-eid="${esc(m.id)}">
      <div class="mseries">${esc(m.series_name)} • ${esc(m.format)} • ${esc(m.venue||"")}</div>
      <div class="mteams">${esc(m.name)}</div>
      <div class="mscore">${t}</div>
      <div class="mstatus ${m.is_live?"live":""}">${m.is_live?"🔴 LIVE — ":""}${esc(m.status_detail||m.status_short||"")}</div>
    </div>`;
  }).join("") || `<div class="empty">Is filter me koi match nahi mila.</div>`;
  document.querySelectorAll(".mcard").forEach(el=>{
    el.onclick = ()=> selectMatch({series_id: el.dataset.sid, id: el.dataset.eid});
  });
}

function selectMatch(m){
  selected = {series_id: m.series_id, event_id: m.id};
  renderList();
  loadDetail(m.series_id, m.id, true);
  document.getElementById("featured").scrollIntoView({behavior:"smooth", block:"start"});
}

async function loadDetail(series_id, event_id, show){
  try{
    const r = await fetch(`/api/match?series_id=${encodeURIComponent(series_id)}&event_id=${encodeURIComponent(event_id)}`);
    const d = await r.json();
    if(d.error) return;
    $("featured").classList.remove("hidden");
    $("fSeries").textContent = d.description || d.name;
    $("fFormat").textContent = d.venue ? "📍 " + d.venue : "";
    $("fLiveBadge").style.display = d.is_live ? "" : "none";
    $("fResult").textContent = d.status_detail || "";
    $("fScoreRow").innerHTML = d.teams.map((t,i)=>`
      <div class="team">
        ${t.logo?`<img src="${esc(t.logo)}" alt="${esc(t.short)}" onerror="this.style.display='none'">`:""}
        <div class="abbr">${esc(t.short||t.name)}</div>
        <div>${esc(t.name)}</div>
        <div class="score">${esc(t.score||"—")}</div>
      </div>${i===0?'<div class="vs">⚡</div>':""}`).join("");

    // Player carousel — real headshots from ESPN
    $("playerCarousel").innerHTML = (d.carousel_players||[]).map(p=>`
      <div class="pcard">
        <img src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy"
             onerror="this.outerHTML='<div style=&quot;width:110px;height:110px;border-radius:12px;background:#0b1e3a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:800&quot;>${esc(initials(p.name))}</div>'">
        <div class="pname">${esc(p.name)}</div><div class="pteam">${esc(p.team)} • ${esc(p.position||"")}</div>
      </div>`).join("") || "<p>No player photos available for this match.</p>";

    // Top performers — screenshot wala section
    $("topPerformers").innerHTML = (d.top_performers||[]).map(p=>{
      const isBat = p.runs!=="" && p.runs!==undefined && p.wickets==="";
      const val = isBat ? `${p.runs} (${p.balls})` : `${p.wickets} wkts • ${p.conceded} runs`;
      const sub = isBat ? `SR: ${p.balls>0?((p.runs/p.balls)*100).toFixed(2):"—"}` : `ER: ${p.economy||"—"} • ${p.overs} ov`;
      return `<div class="perf">
        ${p.image?`<img src="${esc(p.image)}" alt="${esc(p.name)}" onerror="this.remove()">`:""}
        <div><b>${esc(p.name)}</b><br><small>${esc(p.innings_team||p.team||"")}</small></div>
        <div class="v">${esc(val)}<small>${esc(sub)}</small></div></div>`;
    }).join("") || "<p>Top performers abhi available nahi.</p>";

    // Scorecard
    $("scorecard").innerHTML = (d.innings||[]).map(inn=>{
      const isBat = inn.headline.toLowerCase()==="batting";
      const rows = inn.players.filter(p=> (isBat? p.runs!=="" : p.overs!=="")).map(p=> isBat
        ? `<tr><td>${esc(p.name)}</td><td>${esc(p.dismissal||"not out")}</td><td><b>${esc(p.runs)}</b></td><td>${esc(p.balls)}</td><td>${esc(p.fours)}</td><td>${esc(p.sixes)}</td></tr>`
        : `<tr><td>${esc(p.name)}</td><td>${esc(p.overs)}</td><td>${esc(p.maidens)}</td><td>${esc(p.conceded)}</td><td><b>${esc(p.wickets)}</b></td><td>${esc(p.economy)}</td></tr>`).join("");
      return `<h3>${esc(inn.team)} — ${esc(inn.headline)} ${esc(inn.runs? "("+inn.runs+")":"")} ${esc(inn.total||"")}</h3>
        <table><thead><tr>${isBat?"<th>Batter</th><th>Dismissal</th><th>R</th><th>B</th><th>4s</th><th>6s</th>":"<th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>ER</th>"}</tr></thead><tbody>${rows||"<tr><td colspan='6'>No data yet</td></tr>"}</tbody></table>
        ${inn.extras?`<p><small>Extras: ${esc(inn.extras)}</small></p>`:""}`;
    }).join("") || "<p>Scorecard abhi available nahi.</p>";

    const notesHtml = (d.notes||[]).map(n=>`<p>${esc(n)}</p>`).join("");
    $("summaryNotes").innerHTML = notesHtml;
    $("commentaryBox").innerHTML = notesHtml || "<p>Is match ke notes abhi nahi aaye.</p>";
  }catch(e){ /* agle refresh par dobara try hoga */ }
}

// Tabs
document.querySelectorAll(".tab").forEach(b=>{
  b.onclick = ()=>{
    document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
    b.classList.add("active");
    ["summary","scorecard","commentary"].forEach(t=> $("panel-"+t).classList.toggle("hidden", t!==b.dataset.tab));
  };
});
document.querySelectorAll(".chip").forEach(b=>{
  b.onclick = ()=>{
    document.querySelectorAll(".chip").forEach(x=>x.classList.remove("active"));
    b.classList.add("active"); filter = b.dataset.filter; renderList();
  };
});
$("searchBox").addEventListener("input", e=>{ search = e.target.value.trim().toLowerCase(); renderList(); });

setInterval(()=>{ $("liveClock").textContent = new Date().toLocaleString("en-PK"); }, 1000);
loadMatches();
setInterval(loadMatches, 20000);  // har 20 sec live refresh

</script>
</body>
</html>
"""

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (CricketLiveScore/1.0)"}
HEADER_URL = "https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=cricket"
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/cricket/{series_id}/scoreboard"
SUMMARY_URL = ("https://site.web.api.espn.com/apis/site/v2/sports/cricket/"
               "{series_id}/summary?event={event_id}&lang=en&region=in")
CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "").strip()
CRICAPI_URL = "https://api.cricapi.com/v1/currentMatches?apikey={key}&offset=0"

# ---- simple in-memory cache (ESPN ko har request par hit na karein) ----
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 20  # seconds — live score ke liye 20 sec kaafi hai


def cached_get(url, ttl=CACHE_TTL):
    now = time.time()
    with _cache_lock:
        hit = _cache.get(url)
        if hit and now - hit[0] < ttl:
            return hit[1]
    r = requests.get(url, headers=HEADERS, timeout=12)
    r.raise_for_status()
    data = r.json()
    with _cache_lock:
        _cache[url] = (now, data)
    return data


# ---------------------------------------------------------------- helpers
def team_info(comp):
    team = comp.get("team") or {}
    logos = team.get("logos") or []
    logo = team.get("logo") or (logos[0].get("href") if logos else "")
    return {
        "id": str(team.get("id", "")),
        "name": team.get("displayName") or team.get("name") or "",
        "short": team.get("abbreviation") or team.get("shortDisplayName") or "",
        "logo": logo,
        "color": team.get("color") or "#1a2a4a",
        "score": comp.get("score") or "",
        "winner": bool(comp.get("winner") in (True, "true")),
        "linescores": [
            {
                "period": ls.get("period"),
                "runs": ls.get("runs"),
                "wickets": ls.get("wickets"),
                "overs": ls.get("overs"),
                "description": ls.get("description") or "",
            }
            for ls in (comp.get("linescores") or [])
        ],
    }


def parse_event(ev, series_id, series_name):
    comp = (ev.get("competitions") or [{}])[0]
    status = comp.get("status") or ev.get("status") or {}
    stype = status.get("type") or {}
    state = stype.get("state") or ""          # in, pre, post
    detail = stype.get("detail") or status.get("detail") or ""
    short = stype.get("shortDetail") or ""
    venue = comp.get("venue") or {}
    cls = comp.get("class") or {}
    competitors = [team_info(c) for c in (comp.get("competitors") or [])]
    return {
        "id": str(ev.get("id", "")),
        "series_id": str(series_id),
        "series_name": series_name,
        "name": ev.get("name") or ev.get("shortName") or "",
        "shortName": ev.get("shortName") or "",
        "description": ev.get("description") or comp.get("description") or "",
        "format": cls.get("generalClassCard") or cls.get("name") or "",
        "date": ev.get("date") or comp.get("date") or "",
        "venue": venue.get("fullName") or "",
        "city": (venue.get("address") or {}).get("city") or "",
        "state": state,                       # in = live, pre = upcoming, post = result
        "status_detail": detail,             # e.g. "Pakistan A won by 48 runs"
        "status_short": short,
        "is_live": state == "in",
        "teams": competitors,
    }


def discover_series():
    """Header se active series ki list — har series ka numeric id milta hai."""
    data = cached_get(HEADER_URL, ttl=120)
    out = []
    for sport in data.get("sports", []):
        for lg in sport.get("leagues", []):
            out.append({
                "id": str(lg.get("id")),
                "name": lg.get("name") or "",
                "events": lg.get("events") or [],
            })
    return out


def fetch_series_matches(series, max_series=14):
    """Sirf pehli `max_series` series ka scoreboard fetch karein (speed + rate limit)."""
    matches = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(cached_get, SCOREBOARD_URL.format(series_id=s["id"])): s
            for s in series[:max_series]
        }
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                data = fut.result()
            except Exception:
                continue
            for ev in data.get("events", []):
                try:
                    matches.append(parse_event(ev, s["id"], s["name"]))
                except Exception:
                    continue
    # sort: live pehle, phir recent (post), phir upcoming
    order = {"in": 0, "post": 1, "pre": 2}
    matches.sort(key=lambda m: (order.get(m["state"], 3), m["date"] or ""))
    return matches


def cricapi_fallback():
    """Optional fallback — sirf tab jab CRICAPI_KEY set ho."""
    if not CRICAPI_KEY:
        return []
    try:
        data = cached_get(CRICAPI_URL.format(key=CRICAPI_KEY), ttl=60)
        out = []
        for m in data.get("data") or []:
            out.append({
                "id": str(m.get("id", "")),
                "series_id": "", "series_name": m.get("series") or "",
                "name": m.get("name") or "", "shortName": m.get("name") or "",
                "description": m.get("series") or "", "format": m.get("matchType") or "",
                "date": m.get("dateTimeGMT") or "", "venue": m.get("venue") or "",
                "city": "", "state": "in" if m.get("matchStarted") else "pre",
                "status_detail": m.get("status") or "",
                "status_short": m.get("status") or "",
                "is_live": bool(m.get("matchStarted")) and not m.get("matchEnded"),
                "teams": [
                    {"id": "", "name": t, "short": t, "logo": "", "color": "#1a2a4a",
                     "score": "", "winner": False, "linescores": []}
                    for t in (m.get("teams") or [])
                ],
                "score": m.get("score") or [],
            })
        return out
    except Exception:
        return []


# ---------------------------------------------------------------- routes
@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/api/live")
def api_live():
    """Sab matches: live + results + upcoming — hamesha ESPN se, real-time."""
    try:
        series = discover_series()
        matches = fetch_series_matches(series)
        source = "ESPN Cricinfo"
    except Exception as e:
        matches, source = [], "ESPN Cricinfo"
        err = str(e)
    else:
        err = ""
    if not matches:
        fb = cricapi_fallback()
        if fb:
            matches, source = fb, "CricAPI"
    return jsonify({
        "source": source,
        "updated_at": int(time.time()),
        "count": len(matches),
        "live_count": sum(1 for m in matches if m["is_live"]),
        "matches": matches,
        "error": err,
    })


@app.route("/api/match")
def api_match():
    """Ek match ki poori detail: scorecard, top performers, player images."""
    series_id = request.args.get("series_id", "")
    event_id = request.args.get("event_id", "")
    if not series_id or not event_id:
        return jsonify({"error": "series_id aur event_id dono chahiye"}), 400
    try:
        d = cached_get(SUMMARY_URL.format(series_id=series_id, event_id=event_id), ttl=20)
    except Exception as e:
        return jsonify({"error": f"ESPN se detail nahi mili: {e}"}), 502

    header = d.get("header") or {}
    comp = (header.get("competitions") or [{}])[0]
    status = comp.get("status") or {}
    stype = status.get("type") or {}

    # --- headshots map: player_id -> image url, naam, team ---
    headshots = {}
    players = {}
    for roster in d.get("rosters") or []:
        team_abbr = (roster.get("team") or {}).get("abbreviation") or ""
        for row in roster.get("roster") or []:
            a = row.get("athlete") or {}
            pid = str(a.get("id", ""))
            hs = (a.get("headshot") or {}).get("href") or ""
            # ESPN kuch khiladiyon ke liye generic silhouette deta hai — use photo na maanein
            if "default-player" in hs:
                hs = ""
            if pid:
                headshots[pid] = hs
                players[pid] = {
                    "id": pid, "name": a.get("displayName") or a.get("name") or "",
                    "short_name": a.get("shortName") or "",
                    "team": team_abbr,
                    "image": hs,
                    "position": (a.get("position") or {}).get("name") or "",
                }

    # --- matchcards: batting / bowling per innings ---
    innings = []
    for card in d.get("matchcards") or []:
        players_list = []
        for p in card.get("playerDetails") or []:
            pid = str(p.get("playerID", ""))
            players_list.append({
                "id": pid,
                "name": p.get("playerName") or "",
                "image": headshots.get(pid, ""),
                "team": players.get(pid, {}).get("team", ""),
                "runs": p.get("runs") or "",
                "balls": p.get("ballsFaced") or "",
                "fours": p.get("fours") or "",
                "sixes": p.get("sixes") or "",
                "dismissal": p.get("dismissal") or "",
                "overs": p.get("overs") or "",
                "maidens": p.get("maidens") or "",
                "conceded": p.get("conceded") or "",
                "wickets": p.get("wickets") or "",
                "economy": p.get("economyRate") or "",
            })
        innings.append({
            "headline": card.get("headline") or "",
            "team": card.get("teamName") or "",
            "innings": card.get("inningsNumber") or "",
            "runs": card.get("runs") or "",
            "total": card.get("total") or "",
            "extras": card.get("extras") or "",
            "players": players_list,
        })

    # --- top performers: batting me sab se zyada runs, bowling me sab se zyada wickets ---
    batters, bowlers = [], []
    for inn in innings:
        if inn["headline"].lower() == "batting":
            for p in inn["players"]:
                try:
                    if int(p["runs"] or 0) > 0:
                        batters.append({**p, "innings_team": inn["team"]})
                except ValueError:
                    pass
        if inn["headline"].lower() == "bowling":
            for p in inn["players"]:
                try:
                    if int(p["wickets"] or 0) > 0:
                        bowlers.append({**p, "innings_team": inn["team"]})
                except ValueError:
                    pass
    batters.sort(key=lambda x: int(x["runs"] or 0), reverse=True)
    bowlers.sort(key=lambda x: int(x["wickets"] or 0), reverse=True)
    top = batters[:3] + bowlers[:2]

    # --- player carousel: is match ke khiladi (headshot wale pehle) ---
    carousel = [p for p in players.values() if p["image"]]
    # top performers ko carousel me pehle rakhein
    top_ids = {p["id"] for p in top}
    carousel.sort(key=lambda p: (0 if p["id"] in top_ids else 1, p["name"]))

    # --- notes: toss / result / summary lines (commentary tab ke liye) ---
    notes = []
    for n in d.get("notes") or []:
        if isinstance(n, dict):
            notes.append(n.get("text") or n.get("headline") or "")
        elif isinstance(n, str):
            notes.append(n)
    notes = [x for x in notes if x]

    # --- leaders (ESPN ke official leaders, agar hon) ---
    leaders = []
    for group in d.get("leaders") or []:
        if isinstance(group, dict):
            for a in group.get("leaders") or []:
                ath = a.get("athlete") or {}
                leaders.append({
                    "label": group.get("name") or group.get("displayName") or "",
                    "name": ath.get("displayName") or "",
                    "value": a.get("displayValue") or "",
                    "image": (ath.get("headshot") or {}).get("href") or "",
                })

    return jsonify({
        "source": "ESPN Cricinfo",
        "updated_at": int(time.time()),
        "id": str(header.get("id") or event_id),
        "series_id": str(series_id),
        "name": header.get("name") or "",
        "description": header.get("description") or "",
        "status_detail": stype.get("detail") or "",
        "state": stype.get("state") or "",
        "is_live": stype.get("state") == "in",
        "venue": (d.get("gameInfo") or {}).get("venue", {}).get("fullName") or "",
        "teams": [team_info(c) for c in (comp.get("competitors") or [])],
        "innings": innings,
        "top_performers": top,
        "carousel_players": carousel[:22],
        "notes": notes,
        "leaders": leaders[:10],
    })


@app.route("/api/series")
def api_series():
    try:
        return jsonify({"series": discover_series(), "source": "ESPN Cricinfo"})
    except Exception as e:
        return jsonify({"error": str(e), "series": []}), 502


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
