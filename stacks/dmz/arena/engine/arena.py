"""The arena (skynetv2.md → D18): models side by side on Ali's subscriptions. A test is a folder in
/arena/tests, the Skynet agent's working files (not git): test.toml (its contestants, each a lane, an
agent CLI on one of Ali's plans, × model × effort × variant; its stages, caps and judge), suite.py
(its rounds and checks) and world.py (the frozen world its agents act in). A run is one round in a
fresh world: the lane's CLI gets the round's prompt and files, the checks score what it did (the
world's log, its steps) and said, a judge model grades what a pattern can't, and its tokens, time and
share of the plan's windows are kept. One run at a time per lane; a lane waits while its 5-hour window
is above the test's cap, and for the next week once the arena has used its weekly cap. A test's files
are read again whenever they change.

Nothing runs until the Skynet agent starts it (Ali, 2026-11-04), from docker-dmz:
  docker exec arena python3 -I /arena/engine/arena.py start <test> [lane …] [--stage <stage>]
  docker exec arena python3 -I /arena/engine/arena.py stop <test> [lane …]
  docker exec arena python3 -I /arena/engine/arena.py status [test]
`start` runs a stage (the test's first unless named) on the lanes named (all unless named) until it's
done, across restarts; `stop` lets the run in flight finish, then nothing more (/results/control.json);
`reset <test>` sets its results aside (kept, renamed with the time) for a fresh start; `rescore <test>`
scores its runs again with the checks as they are now (a check fixed; the runs stand).

/results/<test>/runs.jsonl has a line per run (what's done: a restart resumes there); runs/<n>/ the
run itself (prompt, stream, reply, steps, world log, the judge's job); summary.json the standings and
Ali's blind pairs."""
import datetime
import glob
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import statistics
import sys
import threading
import time
import tomllib
import urllib.request

WORLDS = {"codex": "http://world-codex:8081", "claude": "http://world-claude:8081"}
LOCK = threading.Lock()
PACE = {}  # lane → its plan's windows as last read, and where the arena's week began
MODULES = {}  # a test's suite.py: path → (its folder's time, the module)
JUDGE = """You are grading an AI agent's work in a test. Don't run commands or use tools: read and judge.

The request it got:
<request>
{request}
</request>

What it did, in order (its tool calls and the world's answers):
<calls>
{calls}
</calls>

Its final reply:
<reply>
{reply}
</reply>

Judge each item strictly, from the material above alone:
{items}

Answer with JSON alone: [{{"item": 1, "pass": true, "why": "one line"}}, …]"""


def say(*words):
    print(datetime.datetime.now().strftime("%m-%d %H:%M:%S"), *words, flush=True)


def http(url, body=None):
    req = urllib.request.Request(url, None if body is None else json.dumps(body).encode(), {"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"null")


def jsonl(path):
    out = []
    for line in open(path, errors="replace") if os.path.exists(path) else []:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def mean(xs, digits=1):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), digits) if xs else None


def same_window(a, b):
    """Two readings of one window: its end, as each reports it, within a few minutes."""
    return bool(a and b) and abs(a["resets"] - b["resets"]) < 900


def plans():
    """The tests: each folder in /arena/tests with a test.toml (its suite is the folder itself)."""
    return {os.path.basename(os.path.dirname(p)): {**tomllib.load(open(p, "rb")), "suite": os.path.basename(os.path.dirname(p))}
            for p in sorted(glob.glob("/arena/tests/*/test.toml"))}


def module(path):
    """A test's Python file, loaded again whenever anything in its folder changed (tests are working
    files: its data too)."""
    t = max(os.path.getmtime(os.path.join(r, f)) for r, _, fs in os.walk(os.path.dirname(path)) for f in fs)
    if MODULES.get(path, (None,))[0] != t:
        spec = importlib.util.spec_from_file_location("test_" + hashlib.sha1(path.encode()).hexdigest()[:8], path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        MODULES[path] = (t, m)
    return MODULES[path][1]


def suite(name):
    return module(f"/arena/tests/{name}/suite.py")


def opt(fn, *args, **keywords):
    """A test's function called with the keywords it takes (a test written before them takes fewer)."""
    takes = inspect.signature(fn).parameters
    return fn(*args, **{k: v for k, v in keywords.items() if k in takes})


def score(checks):
    """Percent of the weight decided that passed; a judge's item still to come isn't counted yet."""
    decided = [c for c in checks if c.get("ok") is not None]
    return round(100 * sum(c["weight"] for c in decided if c["ok"]) / (sum(c["weight"] for c in decided) or 1), 1)


# --- what's left to run --------------------------------------------------------------------------------

def jobs(name, p, recs):
    """The runs a plan still needs, in order: each stage's contestants one after another (a contestant's
    runs sit together in its plan's windows), each over every round of the suite."""
    rounds, done, out = list(suite(p["suite"]).ROUNDS), {r["key"] for r in recs}, []
    for stage in p["stages"]:
        if "top" in stage:
            people, more = finalists(name, p, recs, stage)
            if people is None:
                return out + [j for j in more if j["key"] not in done]
        else:
            people = [(lane, m, stage["effort"], v) for lane, cfg in p["lanes"].items() for m in cfg["models"]
                      for v in stage.get("variants", [""])]
        for lane, model, effort, variant in people:
            for rep in range(stage.get("repeats", 1)):
                out += [j for rnd in rounds for j in [job(name, stage["name"], lane, model, effort, rnd, rep, variant)]
                        if j["key"] not in done]
    return out


def job(plan, stage, lane, model, effort, rnd, rep, variant=""):
    who = f"{lane}/{model}/{effort}" + (f"/{variant}" if variant else "")
    return {"plan": plan, "stage": stage, "lane": lane, "model": model, "effort": effort, "variant": variant, "round": rnd,
            "repeat": rep, "key": f"{stage}/{who}/{rnd}/{rep}"}


def finalists(name, p, recs, stage):
    """The first stage's best `top` (lane, model, variant), by mean score, each at the stage's efforts;
    (None, runs) while that isn't settled: the first stage unfinished, or a close call (within `close`
    points of the cut), whose contestants run it once more first."""
    first, rounds = p["stages"][0], list(suite(p["suite"]).ROUNDS)
    people = [(lane, m, v) for lane, cfg in p["lanes"].items() for m in cfg["models"] for v in first.get("variants", [""])]
    runs = [r for r in recs if r["stage"] == first["name"]]
    if not {(lane, m, v, rnd) for lane, m, v in people for rnd in rounds} <= {
            (r["lane"], r["model"], r.get("variant", ""), r["round"]) for r in runs}:
        return None, []
    marks = {k: mean(r["score"] for r in runs if (r["lane"], r["model"], r.get("variant", "")) == k) for k in people}
    ranked = sorted(people, key=lambda k: -marks[k])
    top, close = stage["top"], stage.get("close", 0)
    if len(ranked) > top and marks[ranked[top - 1]] - marks[ranked[top]] < close:
        cut = marks[ranked[top - 1]]
        more = [job(name, first["name"], lane, m, first["effort"], rnd, 1, v) for lane, m, v in ranked if abs(marks[(lane, m, v)] - cut) < close
                for rnd in rounds]
        if any(j["key"] not in {r["key"] for r in recs} for j in more):
            return None, more
    return [(lane, m, e, v) for lane, m, v in ranked[:top] for e in stage["efforts"]], []


# --- pacing ------------------------------------------------------------------------------------------

def blocked(lane, p):
    """(until when, why) the lane mustn't run under the plan's caps, or None."""
    caps, st, now, why = p.get("caps", {}), PACE.get(lane, {}), time.time(), []
    fh, wk, base = st.get("five_hour"), st.get("week"), st.get("week_base")
    if fh and fh["used"] >= caps.get("five_hour", 60) and fh["resets"] > now:
        why.append((fh["resets"] + 60, f"its 5-hour window is at {fh['used']:.0f}%"))
    if same_window(wk, base) and wk["used"] - base["used"] >= caps.get("week", 20) and wk["resets"] > now:
        why.append((wk["resets"] + 60, f"the arena has used {wk['used'] - base['used']:.0f}% of its week"))
    return max(why) if why else None


def wait(lane, p):
    """Sleeps (30 minutes at most, then looks again) while the lane mustn't run. True if it slept."""
    if not (b := blocked(lane, p)):
        return False
    say(lane, "waits until", datetime.datetime.fromtimestamp(b[0]).strftime("%a %d %H:%M"), "(" + b[1] + ")")
    time.sleep(min(b[0] - time.time(), 1800))
    return True


def paced(lane, first, last):
    """The lane's windows after a run; a new week starts the arena's weekly count from its first reading."""
    if not last:
        return
    with LOCK:
        st = PACE.setdefault(lane, {})
        if not same_window(st.get("week_base"), last["week"]):
            st["week_base"] = {"resets": last["week"]["resets"], "used": (first or last)["week"]["used"]}
        st.update(last)
        with open("/results/pace.json", "w") as f:
            json.dump(PACE, f)


# --- what a CLI leaves: its reply, tokens, the plan's windows, and its steps ---------------------------

def usage_codex(d):
    """Codex: its stream, its last message (-o), and its session (tokens, the plan's windows)."""
    counts = [r["payload"] for r in jsonl(f"{d}/session.jsonl")
              if r.get("type") == "event_msg" and (r.get("payload") or {}).get("type") == "token_count"]
    limits = [c["rate_limits"] for c in counts if (c.get("rate_limits") or {}).get("primary")]
    win = lambda rl: {"five_hour": {"used": rl["primary"]["used_percent"], "resets": rl["primary"]["resets_at"]},  # noqa: E731
                      "week": {"used": rl["secondary"]["used_percent"], "resets": rl["secondary"]["resets_at"]}}
    total = next((c["info"]["total_token_usage"] for c in reversed(counts) if c.get("info")), {})
    steps = []
    for e in jsonl(f"{d}/events.jsonl"):
        i = e.get("item") or {}
        if e.get("type") == "item.completed" and i.get("type") in ("command_execution", "web_search", "mcp_tool_call", "file_change"):
            kind = {"command_execution": "command", "web_search": "search", "mcp_tool_call": "tool", "file_change": "edit"}[i["type"]]
            steps.append({"kind": kind, "text": str(i.get("command") or i.get("query") or i.get("tool") or i.get("changes") or "")[:400]})
    return {"reply": open(f"{d}/reply.txt", errors="replace").read() if os.path.exists(f"{d}/reply.txt") else "",
            "tokens": {"input": total.get("input_tokens"), "cached": total.get("cached_input_tokens"),
                       "output": total.get("output_tokens"), "reasoning": total.get("reasoning_output_tokens")},
            "tools": len(steps), "steps": steps, "first": win(limits[0]) if limits else None, "last": win(limits[-1]) if limits else None}


def usage_claude(d):
    """Claude Code: its stream (the result with tokens and the list-price cost; the plan's windows)."""
    events = jsonl(f"{d}/events.jsonl")
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    limits = [w for e in events if e.get("type") == "rate_limit_event"
              for w in [(e.get("rate_limit_info") or {}).get("unifiedWindows") or {}] if w.get("five_hour") and w.get("seven_day")]
    win = lambda w: {"five_hour": {"used": round(w["five_hour"]["utilization"] * 100, 1), "resets": w["five_hour"]["resetsAt"]},  # noqa: E731
                     "week": {"used": round(w["seven_day"]["utilization"] * 100, 1), "resets": w["seven_day"]["resetsAt"]}}
    u = result.get("usage") or {}
    steps = []
    for e in events:
        for b in (e.get("message") or {}).get("content") or [] if e.get("type") == "assistant" else []:
            if b.get("type") == "tool_use":
                a = b.get("input") or {}
                kind = "command" if b.get("name") == "Bash" else "search" if b.get("name") in ("WebSearch", "WebFetch") else "tool"
                steps.append({"kind": kind, "text": str(a.get("command") or a.get("query") or a.get("url") or f"{b.get('name')} {a}")[:400]})
    return {"reply": result.get("result") or "",
            "tokens": {"input": sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
                       "cached": u.get("cache_read_input_tokens"), "output": u.get("output_tokens"),
                       "reasoning": (u.get("output_tokens_details") or {}).get("thinking_tokens")},
            "cost_usd": result.get("total_cost_usd"), "tools": len(steps), "steps": steps,
            "first": win(limits[0]) if limits else None, "last": win(limits[-1]) if limits else None}


USAGE = {"codex": usage_codex, "claude": usage_claude}


# --- a run ------------------------------------------------------------------------------------------

def hand(lane, d, model, effort, timeout, prompt, files=None, collect=(), env=None, key=""):
    """A job left for a lane (its files, job.env, prompt, then `ready`), and its answer waited for."""
    if not os.path.exists(f"{d}/ready"):  # else a job a restart left going: wait for it
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(f"{d}/files")
        with open(f"{d}/key", "w") as f:  # for status
            f.write(key)
        for rel, data in (files or {}).items():
            os.makedirs(os.path.dirname(f"{d}/files/{rel}"), exist_ok=True)
            with open(f"{d}/files/{rel}", "wb") as f:
                f.write(data)
        with open(f"{d}/job.env", "w") as f:
            f.write("".join(f"{k}='{v}'\n" for k, v in {"MODEL": model, "EFFORT": effort, "TIMEOUT": timeout,
                                                          "COLLECT": " ".join(collect), **(env or {})}.items()))
        with open(f"{d}/prompt.txt", "w") as f:
            f.write(prompt)
        for root, dirs, names in os.walk(d):
            for n in [root] + [os.path.join(root, x) for x in dirs + names]:
                os.chown(n, 1000, 1000)
        open(f"{d}/ready", "w").close()
    start = time.time()
    while not os.path.exists(f"{d}/done") and time.time() - start < timeout + 600:
        time.sleep(3)


def run(name, p, j):
    s, lane = suite(p["suite"]), j["lane"]
    timeout = s.ROUNDS[j["round"]].get("timeout") or p.get("timeout", 1200)
    d = f"/jobs/{lane}/{hashlib.sha1(f'{name}/{j['key']}'.encode()).hexdigest()[:12]}"
    if not os.path.exists(f"{d}/ready"):
        http(f"{WORLDS[lane]}/load", {"suite": p["suite"], "round": j["round"]})
        say(lane, "runs", j["key"])
    variant = j.get("variant", "")
    hand(lane, d, j["model"], j["effort"], timeout, opt(s.prompt, j["round"], variant=variant),
         opt(s.files, j["round"], lane, variant=variant), s.collect(j["round"]), getattr(s, "ENV", {}), j["key"])
    try:
        world = http(f"{WORLDS[lane]}/log")
    except OSError:
        world = None
    usage = USAGE[lane](d)
    reply, steps = usage.pop("reply"), usage.pop("steps")
    collected = {}
    for root, _, names in os.walk(f"{d}/collected"):
        for n in names:
            collected[os.path.relpath(os.path.join(root, n), f"{d}/collected")] = open(os.path.join(root, n), errors="replace").read()
    checks = [{**c, "ok": c.get("ok")} for c in opt(s.check, j["round"], reply, world, collected, steps=steps, variant=variant)]
    took = os.path.getmtime(f"{d}/done") - os.path.getmtime(f"{d}/taken") if os.path.exists(f"{d}/done") else None
    rec = {**j, "at": datetime.datetime.now().isoformat(timespec="seconds"), "seconds": round(took) if took else None,
           "exit": open(f"{d}/exit").read().strip() if os.path.exists(f"{d}/exit") else "no answer", "score": score(checks),
           "red": [c["check"] for c in checks if c.get("red") and c["ok"] is False], "checks": checks, "usage": usage,
           "steps": len(steps), "reply": reply}
    for f, data in (("world.json", world), ("steps.json", steps)):
        with open(f"{d}/{f}", "w") as out:
            json.dump(data, out, ensure_ascii=False)
    with LOCK:
        recs = records(name)
        rec["n"] = len(recs) + 1
        os.makedirs(f"/results/{name}/runs", exist_ok=True)
        shutil.move(d, f"/results/{name}/runs/{rec['n']:04d}")
        with open(f"/results/{name}/runs.jsonl", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        summary(name, p, recs + [rec])
    paced(lane, usage.get("first"), usage.get("last"))
    say(lane, j["key"], "score", rec["score"], "red" if rec["red"] else "", f"{rec['seconds']}s", "exit", rec["exit"])


def judging(name, p, lane):
    """The first run of a started test whose judge items wait, if this lane is its judge's."""
    if (p.get("judge") or {}).get("lane") != lane or name not in control():
        return None
    return next((r for r in records(name) if any(c.get("judge") and c.get("ok") is None for c in r["checks"])), None)


def judge(name, p, rec):
    """A judge model grades a run's judge items (a rubric each) from the request, the run's calls and
    its reply, in one job on the judge's lane; its usage counts in that lane's windows like a run's."""
    cfg, s = p["judge"], suite(p["suite"])
    items = [c for c in rec["checks"] if c.get("judge") and c.get("ok") is None]
    run_dir = f"/results/{name}/runs/{rec['n']:04d}"
    world = json.load(open(f"{run_dir}/world.json")) if os.path.exists(f"{run_dir}/world.json") else None
    calls = "\n".join(f"{c['verb']} {json.dumps(c.get('args'), ensure_ascii=False)[:200]} → {c.get('status')}"
                      for c in (world or {}).get("calls", [])[:120]) or "(none)"
    prompt = JUDGE.format(request=s.ROUNDS[rec["round"]].get("text", rec["round"]), calls=calls, reply=rec["reply"][:12000],
                          items="\n".join(f"{i}. {c['judge']}" for i, c in enumerate(items, 1)))
    d = f"/jobs/{cfg['lane']}/judge-" + hashlib.sha1(f"{name}/{rec['n']}".encode()).hexdigest()[:10]
    say(cfg["lane"], "judges", name, rec["n"])
    hand(cfg["lane"], d, cfg["model"], cfg.get("effort", "low"), 900, prompt, key=f"judge {name} #{rec['n']}")
    usage = USAGE[cfg["lane"]](d)
    found = re.search(r"\[.*\]", usage["reply"], re.S)
    try:
        verdicts = {v["item"]: v for v in json.loads(found.group(0))} if found else {}
    except (ValueError, TypeError, KeyError):
        verdicts = {}
    with LOCK:
        recs = records(name)
        r = next(x for x in recs if x["n"] == rec["n"])
        pending = [c for c in r["checks"] if c.get("judge") and c.get("ok") is None]
        for i, c in enumerate(pending, 1):
            v = verdicts.get(i) or {"pass": False, "why": "the judge gave no verdict"}
            c.update(ok=bool(v.get("pass")), why=str(v.get("why", ""))[:300])
        r.update(score=score(r["checks"]), red=[c["check"] for c in r["checks"] if c.get("red") and c["ok"] is False],
                 judge={"model": cfg["model"], "effort": cfg.get("effort", "low"), "tokens": usage["tokens"]})
        shutil.rmtree(f"{run_dir}/judge", ignore_errors=True)
        shutil.move(d, f"{run_dir}/judge")
        rewrite(name, p, recs)
    paced(cfg["lane"], usage.get("first"), usage.get("last"))


def records(name):
    return jsonl(f"/results/{name}/runs.jsonl")


def rewrite(name, p, recs):
    """The records written whole, and the standings with them (under the lock)."""
    with open(f"/results/{name}/runs.jsonl.new", "w") as f:
        f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
    os.replace(f"/results/{name}/runs.jsonl.new", f"/results/{name}/runs.jsonl")
    summary(name, p, recs)


def summary(name, p, recs):
    """The standings: per contestant (stage, lane, model, effort, variant), its mean score, its spread
    across repeats and red flags, its score per round, tokens, steps and time per run, and its runs'
    share of the plan's windows (each run's rise in the window since its lane's run before, in the
    same window), and the blind pairs."""
    s, prev, rows = suite(p["suite"]), {}, {}
    for r in sorted(recs, key=lambda r: r["n"]):
        last, first, before, r["use"] = r["usage"].get("last"), r["usage"].get("first"), prev.get(r["lane"]), {}
        for w in ("five_hour", "week") if last else ():
            b = before[w] if before and same_window(before[w], last[w]) else (first or {}).get(w)
            r["use"][w] = round(last[w]["used"] - b["used"], 1) if same_window(b, last[w]) else None
        prev[r["lane"]] = last or before
        rows.setdefault((r["stage"], r["lane"], r["model"], r["effort"], r.get("variant", "")), []).append(r)

    def spread(rs):
        per_repeat = [mean(r["score"] for r in rs if r["repeat"] == k) for k in sorted({r["repeat"] for r in rs})]
        return round(statistics.pstdev(per_repeat), 1) if len(per_repeat) > 1 else None

    standings = [{"stage": k[0], "lane": k[1], "model": k[2], "effort": k[3], "variant": k[4], "runs": len(rs),
                  "score": mean(r["score"] for r in rs), "spread": spread(rs), "red": sorted({f for r in rs for f in r["red"]}),
                  "unjudged": sum(1 for r in rs for c in r["checks"] if c.get("judge") and c.get("ok") is None),
                  "rounds": {rnd: mean(r["score"] for r in rs if r["round"] == rnd) for rnd in s.ROUNDS},
                  "seconds": mean(r["seconds"] for r in rs), "steps": mean(r.get("steps") for r in rs),
                  "tokens": {t: mean((r["usage"].get("tokens") or {}).get(t) for r in rs) for t in ("input", "cached", "output", "reasoning")},
                  "five_hour": mean((r["use"].get("five_hour") for r in rs), 2), "week": mean((r["use"].get("week") for r in rs), 2),
                  "cost_usd": mean((r["usage"].get("cost_usd") for r in rs), 3)} for k, rs in rows.items()]
    order = [st["name"] for st in p["stages"]]
    who = lambda r: "/".join(x for x in (r["lane"], r["model"], r["effort"], r.get("variant", "")) if x)  # noqa: E731
    blind = {rnd: [{"n": r["n"], "who": who(r), "text": s.blind(r["reply"])}
                   for r in recs if r["round"] == rnd and r["reply"]] for rnd, cfg in s.ROUNDS.items() if cfg.get("vote")}
    with open(f"/results/{name}/summary.json", "w") as f:
        json.dump({"plan": name, "updated": datetime.datetime.now().isoformat(timespec="seconds"),
                   "standings": sorted(standings, key=lambda x: (order.index(x["stage"]) if x["stage"] in order else 99, -(x["score"] or 0))),
                   "blind": blind}, f, ensure_ascii=False, indent=1)


# --- what the agent starts ---------------------------------------------------------------------------

def control():
    try:
        return json.load(open("/results/control.json"))
    except (OSError, ValueError):
        return {}


def started(plan, lane, stage):
    c = control().get(plan) or {}
    return lane in c.get("lanes", []) and stage in c.get("stages", [])


def status(only=None):
    """What's started, each lane's state and what it has left to run, and the standings so far."""
    if os.path.exists("/results/pace.json"):
        PACE.update(json.load(open("/results/pace.json")))
    out = []
    for name, p in plans().items():
        if only and name != only:
            continue
        recs, ctl = records(name), control().get(name)
        out.append(f"{name}: " + (f"started {', '.join(ctl['stages'])} on {', '.join(ctl['lanes'])}" if ctl else "not started"))
        left = jobs(name, p, recs)
        for lane in p["lanes"]:
            st = open(f"/jobs/{lane}/.status").read().strip() if os.path.exists(f"/jobs/{lane}/.status") else "no lane"
            mine = [j for j in left if j["lane"] == lane and started(name, lane, j["stage"])]
            now = [open(k).read() for k in glob.glob(f"/jobs/{lane}/*/key") if not os.path.exists(os.path.join(os.path.dirname(k), "done"))]
            win, b = PACE.get(lane, {}), blocked(lane, p)
            out.append(f"  {lane}: {st}; {sum(r['lane'] == lane for r in recs)} runs done, {len(mine)} started to go"
                       + (f"; running {now[0]}" if now else "")
                       + (f"; waits until {datetime.datetime.fromtimestamp(b[0]):%a %d %H:%M} ({b[1]})" if b and mine else "")
                       + (f"; its plan's 5-hour window {win['five_hour']['used']:.0f}%, week {win['week']['used']:.0f}%" if win.get("five_hour") else ""))
        if os.path.exists(f"/results/{name}/summary.json"):
            for x in json.load(open(f"/results/{name}/summary.json"))["standings"]:
                who = "/".join(v for v in (x["lane"], x["model"], x["effort"], x.get("variant", "")) if v)
                out.append(f"  {x['stage']} {who}: {x['score']}" + (f" ±{x['spread']}" if x.get("spread") is not None else "")
                           + f" ({x['runs']} runs" + (f", 5-hour {x['five_hour']}% and week {x['week']}% a run" if x["five_hour"] is not None else "")
                           + (f", {x['unjudged']} to judge" if x.get("unjudged") else "") + ")"
                           + (f", red: {'; '.join(x['red'])}" if x["red"] else ""))
    return "\n".join(out)


def command(args):
    """start | stop | status | reset | rescore, as the module's docstring says."""
    cmd, rest = args[0], args[1:]
    if cmd == "status":
        return print(status(rest[0] if rest else None))
    stage = rest.pop(rest.index("--stage") + 1) if "--stage" in rest else None
    plan, *lanes = [a for a in rest if a != "--stage"]
    p, c = plans()[plan], control()
    order = [s["name"] for s in p["stages"]]
    if set(lanes) - set(p["lanes"]) or (stage and stage not in order) or cmd not in ("start", "stop", "reset", "rescore"):
        raise SystemExit(f"start|stop|reset|rescore {plan} [{' '.join(p['lanes'])}] [--stage {'|'.join(order)}]")
    lanes = lanes or list(p["lanes"])
    if cmd == "reset":  # a fresh start: the plan's results set aside, kept, and nothing of it started
        if [k for k in glob.glob("/jobs/*/*/key") if not os.path.exists(os.path.join(os.path.dirname(k), "done"))]:
            raise SystemExit("a run is in flight: stop the plan, and reset once it's done")
        if os.path.exists(f"/results/{plan}"):
            os.rename(f"/results/{plan}", f"/results/{plan}.{datetime.datetime.now():%Y%m%d-%H%M}")
        c.pop(plan, None)
    elif cmd == "rescore":  # the runner does it between two records (rescored())
        open(f"/results/{plan}/rescore", "w").close()
        return print(f"{plan}: rescoring within a minute")
    elif cmd == "start":
        e = c.setdefault(plan, {"lanes": [], "stages": []})
        e["lanes"] = sorted(set(e["lanes"]) | set(lanes))
        e["stages"] = [s for s in order if s in e["stages"] or s == (stage or order[0])]
    elif plan in c:
        c[plan]["lanes"] = [x for x in c[plan]["lanes"] if x not in lanes]
        if not c[plan]["lanes"]:
            del c[plan]
    with open("/results/control.json.new", "w") as f:
        json.dump(c, f)
    os.replace("/results/control.json.new", "/results/control.json")
    print(status(plan))


def rescored(plan, p):
    """Every run of a plan scored again by the suite's checks as they are now (a check fixed: the runs
    stand); a judge's verdicts are kept for an item whose rubric didn't change. The runner's own, under
    the lock its records are written with."""
    s = suite(p["suite"])
    with LOCK:
        recs = records(plan)
        for r in recs:
            d = f"/results/{plan}/runs/{r['n']:04d}"
            world = json.load(open(f"{d}/world.json")) if os.path.exists(f"{d}/world.json") else None
            steps = json.load(open(f"{d}/steps.json")) if os.path.exists(f"{d}/steps.json") else []
            collected = {os.path.relpath(os.path.join(root, n), f"{d}/collected"): open(os.path.join(root, n), errors="replace").read()
                         for root, _, names in os.walk(f"{d}/collected") for n in names}
            judged = {(c["check"], c["judge"]): c for c in r["checks"] if c.get("judge") and c.get("ok") is not None}
            checks = []
            for c in opt(s.check, r["round"], r["reply"], world, collected, steps=steps, variant=r.get("variant", "")):
                old = judged.get((c["check"], c.get("judge"))) if c.get("judge") else None
                checks.append({**c, "ok": old["ok"], "why": old.get("why")} if old else {**c, "ok": c.get("ok")})
            r.update(checks=checks, score=score(checks), red=[x["check"] for x in checks if x.get("red") and x["ok"] is False])
        rewrite(plan, p, recs)
        os.remove(f"/results/{plan}/rescore")
    say(plan, "rescored", len(recs), "runs")


# --- the lanes ----------------------------------------------------------------------------------------

def lane(name):
    while True:
        try:
            ready = os.path.exists(f"/jobs/{name}/.status") and open(f"/jobs/{name}/.status").read().strip() == "ready"
            tests = plans()
            grade = next(((plan, p, r) for plan, p in tests.items() if (r := judging(plan, p, name))), None)
            todo = [(plan, p, j) for plan, p in tests.items() if name in p["lanes"] for j in jobs(plan, p, records(plan))
                    if j["lane"] == name and started(plan, name, j["stage"])]
            if not ready or not (grade or todo):
                time.sleep(60)
            elif grade and not wait(name, grade[1]):
                judge(*grade)
            elif todo and not grade and not wait(name, todo[0][1]):
                run(*todo[0])
        except Exception as e:  # noqa: BLE001 - a lane keeps going; the log says why
            say(name, "error:", repr(e))
            time.sleep(60)


if __name__ == "__main__":
    if sys.argv[1:]:
        command(sys.argv[1:])
        sys.exit()
    if os.path.exists("/results/pace.json"):
        PACE.update(json.load(open("/results/pace.json")))
    for name in WORLDS:
        threading.Thread(target=lane, args=(name,), daemon=True).start()
    while True:
        open("/tmp/alive", "w").close()
        for plan, p in plans().items():
            try:
                if os.path.exists(f"/results/{plan}/rescore"):
                    rescored(plan, p)
            except Exception as e:  # noqa: BLE001 - the runner keeps going; the log says why
                say(plan, "rescore failed:", repr(e))
        time.sleep(30)
