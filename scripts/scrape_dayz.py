# -*- coding: utf-8 -*-
"""DayZ scraper — dayz.fandom.com.

Boards: food / weapons / ammo / magazines / clothing / equipment.
Templates are {{Food Template}}, {{InfoboxWeapon}}, {{AmmoInfobox}},
{{Item Template}}-style — generic: capture ANY first infobox with |k = v lines.
Routing is by source category. Redirects resolved via redirects=1.
Ranged weapons come from the "List of ranged weapons" table (names), then
each weapon page is fetched for its InfoboxWeapon.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "src", "data")
CACHE_DIR = os.path.join(BASE_DIR, "scripts", "cache")
API = "https://dayz.fandom.com/api.php"
UA = "DayZDB/1.0 (site: dayz-db.pages.dev; contact franceiwhdbks865@gmail.com)"

# board -> source categories
FETCH_CATS = {
    "food": ["Food"],
    "ammo": ["Ammunition"],
    "magazines": ["Magazines"],
    "weapons": ["Melee Weapons", "Explosives", "Grenades", "Non-lethal Weapons",
               "Assault Rifles", "Battle Rifles", "Bolt-action Rifles", "Breech-action Rifles",
               "Handguns", "Launchers", "Marksman Rifles", "Semi-automatic Rifles",
               "Shotguns", "Submachine Guns"],
    "clothing": ["Backpacks", "Belts", "Eyewear", "Gloves", "Hats", "Helmets",
                 "Masks", "Pants", "Shirts and Jackets", "Shoes", "Vests"],
    "equipment": ["Equipment", "Containers", "Tools"],
}
LIST_PAGES = {}

num_re = re.compile(r"-?\d+(?:\.\d+)?")


def num(v):
    if v is None:
        return None
    m = num_re.search(v)
    return float(m.group(0)) if m else None


def strip_comments(wt):
    wt = re.sub(r"<!--.*?-->", "", wt, flags=re.S)
    wt = re.sub(r"<!-{2,}-{1}.*?-{2,}->{1}", "", wt, flags=re.S)
    return wt


def opener():
    return urllib.request.build_opener()


def opener_proxy():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": "http://127.0.0.1:7897",
                                     "http": "http://127.0.0.1:7897"}))


OP = opener()


def api(p, retry_proxy=True):
    global OP
    url = API + "?" + urllib.parse.urlencode({**p, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        return json.load(OP.open(req, timeout=40))
    except Exception as e:
        if retry_proxy:
            print("  [net] direct failed, switching to proxy:", str(e)[:50])
            OP = opener_proxy()
            return api(p, retry_proxy=False)
        raise


def match_any_infobox(wt):
    """Find first top-level template whose name contains Infobox/Template/infobox."""
    wt = strip_comments(wt)
    for m in re.finditer(r"\{\{\s*([A-Za-z][A-Za-z0-9 _]{1,50}?)\s*(\||\n)", wt):
        name = m.group(1).strip()
        if not re.search(r"infobox|template", name, flags=re.I):
            continue
        start = m.start() + 2
        depth, i = 1, start
        while i < len(wt) - 1 and depth > 0:
            if wt[i] == "{":
                depth += 1
            elif wt[i] == "}":
                depth -= 1
            i += 1
        body = wt[start:i - 1]
        if body.count("=") >= 2:  # must have params
            return name, body
    return None, None


def split_params(body):
    parts, buf = [], []
    depth_t = depth_l = 0
    i = 0
    while i < len(body):
        c = body[i]
        if c == "|" and depth_t == 0 and depth_l == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(c)
            if body.startswith("{{", i): depth_t += 1; i += 1
            elif body.startswith("}}", i): depth_t -= 1; i += 1
            elif body.startswith("[[", i): depth_l += 1; i += 1
            elif body.startswith("]]", i): depth_l -= 1; i += 1
        i += 1
    parts.append("".join(buf))
    return parts


def parse_params(body):
    out = {}
    for part in split_params(body):
        part = part.strip()
        if part.startswith("|"):
            part = part[1:]
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if not k or k in out:
            continue
        out[k] = v.strip()
    return out


def clean(v):
    if not v:
        return ""
    v = strip_comments(v)
    v = re.sub(r"<br\s*/?>", "; ", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", v)
    v = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2", v)
    v = re.sub(r"\[(https?://\S+)\]", "", v)
    v = v.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", v).strip()


def first_para(wt):
    body = strip_comments(wt)
    # drop infobox region
    m = re.search(r"\}\}", body)
    if m:
        body = body[m.end():]
    for ln in body.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith(("=", "{", "|", "[[", "<", "#")):
            return clean(ln)[:400]
    return ""


def cat_members(cat):
    titles, cont = [], {}
    while True:
        r = api({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat,
                 "cmtype": "page", "cmnamespace": "0", "cmlimit": "500", **cont})
        titles += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
        cont = r.get("continue") or {}
        if not cont:
            return titles
        time.sleep(0.4)


def fetch_wikitexts(titles, cache_path):
    """Fetch revisions with redirects=1; returns {resolved_title: wikitext}.
    Incremental: only fetch titles missing from cache, then merge."""
    wts = {}
    if os.path.exists(cache_path):
        wts = json.load(open(cache_path, encoding="utf-8"))
    titles = [t for t in titles if t not in wts]
    if not titles:
        return wts
    batch = 15
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        r = None
        for attempt in range(3):
            try:
                r = api({"action": "query", "prop": "revisions", "rvprop": "content",
                         "rvslots": "main", "redirects": 1, "titles": "|".join(chunk)})
                break
            except Exception as e:
                print(f"  [batch {i}] ERR {str(e)[:50]}, retry {attempt + 1}")
                time.sleep(3)
        if not r:
            continue
        # redirect mapping: original -> resolved
        q = r.get("query", {})
        redir = {}
        for rr in q.get("redirects", []):
            redir[rr["from"]] = rr["to"]
        for pg in q.get("pages", {}).values():
            rev = pg.get("revisions") or []
            wts[pg["title"]] = rev[0]["slots"]["main"]["*"] if rev else ""
        if (i // batch) % 10 == 0:
            print(f"  fetched {min(i + batch, len(titles))}/{len(titles)}")
        time.sleep(0.35)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(wts, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return wts


def slug(t):
    s = re.sub(r"\s+", "-", t.strip().lower())
    return re.sub(r"[^a-z0-9\-]", "", s) or "item"


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    # 1) gather titles per board
    board_titles = {}
    for board, cats in FETCH_CATS.items():
        ts = set()
        for c in cats:
            got = cat_members(c)
            print(f"[cat] {board} <- {c}: {len(got)}")
            ts.update(got)
            time.sleep(0.3)
        board_titles[board] = sorted(ts)
    # 2) ranged weapons from list pages (wikitable first-column links)
    for board, pages in LIST_PAGES.items():
        for lp in pages:
            r = api({"action": "query", "prop": "revisions", "rvprop": "content",
                     "rvslots": "main", "redirects": 1, "titles": lp})
            for pg in r["query"]["pages"].values():
                rev = pg.get("revisions") or []
                txt = rev[0]["slots"]["main"]["*"] if rev else ""
            txt = strip_comments(txt)
            names = set()
            for tbl in re.findall(r"\{\|.*?\|\}", txt, flags=re.S):
                for row in re.findall(r"^\|-(?:.*?)\n(.*?)(?=^\|-|\|\})", tbl, flags=re.S | re.M):
                    mm = re.search(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]", row)
                    if mm:
                        names.append(mm.group(1)) if False else names.add(mm.group(1).split("/")[0].strip())
            names = {n for n in names if n and not n.lower().startswith(("list ", "weapon"))}
            print(f"[list] {lp}: {len(names)} weapon names")
            board_titles[board] = sorted(set(board_titles[board]) | names)
    all_titles = sorted({t for ts in board_titles.values() for t in ts})
    print(f"[total] {len(all_titles)} unique pages")
    cache = os.path.join(CACHE_DIR, "wikitexts.json")
    wts = fetch_wikitexts(all_titles, cache)
    # 3) route + parse (first infobox wins; board by source)
    for board, titles in board_titles.items():
        out = []
        seen = set()
        for t in titles:
            wt = wts.get(t, "")
            if not wt or wt.startswith("#REDIRECT"):
                continue
            tname, body = match_any_infobox(wt)
            if not body:
                continue
            key = slug(t)
            if key in seen:
                continue
            seen.add(key)
            p = parse_params(body)
            rec = {
                "title": t, "slug": key, "template": tname,
                "image": clean(p.get("image", "")),
                "fields": {k: clean(v) for k, v in p.items() if k != "image"},
            }
            rec["intro"] = first_para(wt)
            out.append(rec)
        path = os.path.join(DATA_DIR, f"dayz_{board}.json")
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[out] {board}: {len(out)}")


if __name__ == "__main__":
    main()
