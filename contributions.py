#!/usr/bin/env python3
# Draws contributions.svg like the GitHub graph: commits from the public repos are counted too.
import collections, datetime, json, os, subprocess, tempfile, urllib.request

USER, ORGS = "Juco7L7", ["Juco7L7", "snapos-distro"]
TOKEN = os.environ["GITHUB_TOKEN"]
NONE_COLOR, GREENS = "#e8820f", ["#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans,Helvetica,Arial,sans-serif"

def api(url, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None,
                                 {"Authorization": f"bearer {TOKEN}", "User-Agent": USER})
    return json.load(urllib.request.urlopen(req))

q = '{user(login:"%s"){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount weekday}}}}}}' % USER
weeks = api("https://api.github.com/graphql", {"query": q})["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
count = collections.Counter({d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]})
first = weeks[0]["contributionDays"][0]["date"]

with tempfile.TemporaryDirectory() as tmp:
    for owner in ORGS:
        kind = "orgs" if owner != USER else "users"
        for repo in api(f"https://api.github.com/{kind}/{owner}/repos?type=public&per_page=100"):
            if repo["private"] or repo["size"] == 0:
                continue
            path = os.path.join(tmp, f"{owner}-{repo['name']}")
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", repo["clone_url"], path], check=True)
            log = subprocess.run(["git", "-C", path, "log", "--all", f"--author={USER}", "--invert-grep",
                                  "--grep=^Contributions graph", f"--since={first}", "--format=%H %ad", "--date=short"],
                                 capture_output=True, text=True, check=True).stdout.split("\n")
            for line in set(filter(None, log)):
                count[line.split()[1]] += 1

days = [d for w in weeks for d in w["contributionDays"]]
total = sum(count[d["date"]] for d in days)
nonzero = sorted(count[d["date"]] for d in days if count[d["date"]])

def level(n):
    if not n:
        return NONE_COLOR
    for i, q in enumerate((0.25, 0.5, 0.75)):
        if n <= nonzero[int(q * (len(nonzero) - 1))]:
            return GREENS[i]
    return GREENS[3]

C, S, LEFT, TOP = 10, 13, 40, 70
W = LEFT + len(weeks) * S + 16
H = TOP + 7 * S + 44
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
       f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="6" fill="#0d1117" stroke="#30363d"/>',
       f'<text x="16" y="28" fill="#e6edf3" font-size="16">{total} contributions in the last year</text>']
last = -3
for i, w in enumerate(weeks):
    d0 = datetime.date.fromisoformat(w["contributionDays"][0]["date"])
    if (i == 0 and d0.day <= 7 or d0.day <= 7 and i) and i - last > 2:
        out.append(f'<text x="{LEFT + i * S}" y="{TOP - 8}" fill="#e6edf3" font-size="12">{d0.strftime("%b")}</text>')
        last = i
    for d in w["contributionDays"]:
        n = count[d["date"]]
        tip = f'{n or "No"} contribution{"" if n == 1 else "s"} on {d["date"]}'
        out.append(f'<rect x="{LEFT + i * S}" y="{TOP + d["weekday"] * S}" width="{C}" height="{C}" rx="2" '
                   f'fill="{level(n)}" stroke="#1b1f230f"><title>{tip}</title></rect>')
for wd, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
    out.append(f'<text x="12" y="{TOP + wd * S + 9}" fill="#e6edf3" font-size="12">{name}</text>')
fy = TOP + 7 * S + 22
out.append(f'<text x="{LEFT}" y="{fy}" fill="#8b949e" font-size="12">Learn how we count contributions</text>')
lx = W - 16 - 5 * S - 34
out.append(f'<text x="{lx - 30}" y="{fy}" fill="#8b949e" font-size="12">Less</text>')
for k, col in enumerate([NONE_COLOR] + GREENS):
    out.append(f'<rect x="{lx + k * S}" y="{fy - 10}" width="{C}" height="{C}" rx="2" fill="{col}"/>')
out.append(f'<text x="{lx + 5 * S + 4}" y="{fy}" fill="#8b949e" font-size="12">More</text></svg>')
open("contributions.svg", "w").write("\n".join(out) + "\n")
print(total)
