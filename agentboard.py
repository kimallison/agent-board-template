#!/usr/bin/env python3
"""Agent Board: a shared task board for one human and any number of AI agents.

tasks.js holds every task as JSON. DESK.md is the only file the human writes in.
This script is the only thing that rewrites either file, and it takes a lock first,
so the agents never clash.

  python3 agentboard.py intake     read the Desk: new requests, answers, sign-offs
  python3 agentboard.py desk       rewrite the agent-managed parts of the Desk
  python3 agentboard.py list [--owner NAME] [--status STATUS]
  python3 agentboard.py show T001
  python3 agentboard.py add --title "..." --owner agent-a [--area ..] [--detail ..] [--next ..]
  python3 agentboard.py set T001 [--owner ..] [--status ..] [--next ..] [--ask ..] [--result ..] --by agent-a --note "what you did"
  python3 agentboard.py close T001 --by agent-a --note "..."   (only when the human's own answer says it is done)

Statuses: working (an agent has it), waiting (needs the human: set --ask),
signoff (done, human to close: set --result), parked (later), closed (signed off).
Owners: your agents (edit AGENTS below; any number), triage (not yet routed), human.
"""
import json, os, re, sys, time, fcntl, argparse, datetime

AGENTS = ("agent-a", "agent-b")   # rename to suit; add as many names as you have agents
HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks.js")
DESK = os.path.join(HERE, "DESK.md")
LOCK = os.path.join(HERE, ".lock")
PREFIX = "window.TASKS = "
QUIET_SECS = 180  # if the human touched the Desk in the last 3 minutes, leave it alone

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def load():
    if not os.path.exists(TASKS):
        return []
    raw = open(TASKS, encoding="utf-8").read().strip()
    raw = raw[len(PREFIX):] if raw.startswith(PREFIX) else raw
    return json.loads(raw.rstrip(";"))

def save(tasks):
    tmp = TASKS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(PREFIX + json.dumps(tasks, indent=1, ensure_ascii=False) + ";\n")
    os.replace(tmp, TASKS)

class Locked:
    def __enter__(self):
        self.f = open(LOCK, "w"); fcntl.flock(self.f, fcntl.LOCK_EX); return self
    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN); self.f.close()

def next_id(tasks):
    return "T%03d" % (max([int(t["id"][1:]) for t in tasks] or [0]) + 1)

def find(tasks, tid):
    for t in tasks:
        if t["id"].upper() == tid.upper():
            return t
    sys.exit("No task " + tid)

def log(t, who, text):
    t.setdefault("log", []).append([now(), who, text])
    t["updated"] = now()

# ---------- The Desk ----------
HEAD = "# Desk\n\nWrite to your agents here. The right one picks it up at its next run.\n\n"
WRITE_H = "## Write to us"
WRITE_HELP = "<!-- One request per paragraph, with a blank line between them. Name an agent with @ to pick one. Start with a task number, like T001, to add a note to that task. -->"
WAIT_H = "## Waiting on you"
WAIT_HELP = "<!-- Type your answer after Answer:. Leave it blank if you are not ready. -->"
SIGN_H = "## Ready to sign off"
SIGN_HELP = "<!-- Tick the box to close a task. To send one back, leave it unticked and write what is wrong after Not yet:. -->"
ERR_H = "## Your errands"
ERR_HELP = "<!-- Real-world jobs only you can do. When one is done, write its number and done in Write to us, like T012 done. -->"
DEC_H = "## Decided for you"
DEC_HELP = "<!-- Small choices the agents made so they did not have to ask. To overturn one, write its number and what you want in Write to us. -->"
DONE_H = "## Completed"
DONE_HELP = "<!-- Finished work, newest first. -->"
DONE_SHOW = 20

def todays_decisions(tasks):
    today = datetime.date.today().isoformat()
    out = []
    for t in tasks:
        for e in t.get("log") or []:
            if len(e) >= 3 and e[0].startswith(today) and e[2].lstrip().lower().startswith("decided:"):
                out.append((t, e[1], e[2].lstrip()[8:].strip()))
    return out

def section(text, head):
    m = re.search(r"^" + re.escape(head) + r"\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""

def strip_comments(s):
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)

STAMP = os.path.join(HERE, ".desk_written")

def desk_recent():
    """True only if the human (not this script) changed the Desk in the last few minutes."""
    if not os.path.exists(DESK): return False
    m = os.path.getmtime(DESK)
    ours = os.path.exists(STAMP) and open(STAMP).read().strip() == repr(m)
    return not ours and time.time() - m < QUIET_SECS

def route(para):
    low = para.lower()
    for ag in AGENTS:
        if "@" + ag in low: return ag
    return "triage"

def cmd_intake(a):
    if not os.path.exists(DESK):
        print("No desk yet."); return
    if desk_recent():
        print("The Desk was edited in the last 3 minutes. Skipping intake this run."); return
    with Locked():
        text = open(DESK, encoding="utf-8").read()
        tasks = load(); out = []
        body = strip_comments(section(text, WRITE_H)).strip()
        for para in [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]:
            ref = re.match(r"^(T\d{3})\b[\s:.,-]*(.*)", para, re.S | re.I)
            if ref and any(x["id"] == ref.group(1).upper() for x in tasks):
                t = find(tasks, ref.group(1)); note = ref.group(2).strip()
                t["answer"] = note
                if t["status"] in ("waiting", "signoff", "parked", "closed"): t["status"] = "working"
                if t["owner"] in ("human", ""): t["owner"] = "triage"
                log(t, "human", "Note: " + note); out.append(f"NOTE {t['id']}: {note[:80]}")
                continue
            owner = route(para)
            t = {"id": next_id(tasks), "title": re.sub(r"\s+", " ", para)[:90], "area": "", "owner": owner,
                 "status": "working", "detail": para, "next": "", "ask": "", "answer": "", "result": "",
                 "source": "Desk", "created": now(), "updated": now(), "log": []}
            log(t, "human", "Request: " + para)
            tasks.append(t); out.append(f"NEW {t['id']} ({owner}): {para[:80]}")
        for m in re.finditer(r"^### (T\d+)[^\n]*\n(.*?)(?=^### |\Z)", section(text, WAIT_H), re.S | re.M):
            am = re.search(r"^Answer:[ \t]*(.*?)\s*\Z", strip_comments(m.group(2)), re.S | re.M)
            ans = am.group(1).strip() if am else ""
            if ans:
                t = find(tasks, m.group(1))
                if t["status"] == "waiting":
                    t["answer"] = ans; t["status"] = "working"
                    if t["owner"] in ("human", ""): t["owner"] = "triage"
                    log(t, "human", "Answer: " + ans); out.append(f"ANSWER {t['id']}: {ans[:80]}")
        for m in re.finditer(r"^- \[( |x|X)\] (T\d+)[^\n]*\n?((?:[ \t]+[^\n]*\n?)*)", section(text, SIGN_H), re.M):
            t = find(tasks, m.group(2))
            if t["status"] != "signoff": continue
            if m.group(1).lower() == "x":
                t["status"] = "closed"; t["closed"] = now(); log(t, "human", "Signed off"); out.append(f"CLOSED {t['id']}")
            else:
                nm = re.search(r"Not yet:[ \t]*(.+)", m.group(3))
                if nm and nm.group(1).strip():
                    t["status"] = "working"; t["answer"] = nm.group(1).strip()
                    log(t, "human", "Sent back: " + t["answer"]); out.append(f"SENT BACK {t['id']}: {t['answer'][:80]}")
        save(tasks)
        write_desk(tasks, keep_write=False)
    print("\n".join(out) or "Nothing new on the Desk.")

def write_desk(tasks, keep_write=True):
    old = open(DESK, encoding="utf-8").read() if os.path.exists(DESK) else ""
    kept = strip_comments(section(old, WRITE_H)).strip() if keep_write else ""
    waiting = [t for t in tasks if t["status"] == "waiting" and not t.get("errand")]
    errands = [t for t in tasks if t.get("errand") and t["status"] != "closed"]
    sign = [t for t in tasks if t["status"] == "signoff"]
    L = [HEAD, WRITE_H, WRITE_HELP, "", kept, "", "", WAIT_H, WAIT_HELP, ""]
    if not waiting: L += ["Nothing needs you right now.", ""]
    for t in waiting:
        due = f" (due {t['due']})" if t.get("due") else ""
        yn = " Yes or no." if t.get("ask_type") == "yesno" and "yes or no" not in (t.get("ask") or "").lower() else ""
        L += [f"### {t['id']} · {t['title']}{due}", (t.get("ask") or t["detail"]) + yn, "", "Answer: ", ""]
    L += [SIGN_H, SIGN_HELP, ""]
    if not sign: L += ["Nothing to sign off right now.", ""]
    for t in sign:
        L += [f"- [ ] {t['id']} · {t['title']}", f"    Done: {t.get('result') or 'see the board'}", "    Not yet: ", ""]
    L += [ERR_H, ERR_HELP, ""]
    if not errands: L += ["No errands for you right now.", ""]
    for t in errands:
        due = f" (due {t['due']})" if t.get("due") else ""
        L += [f"- {t['id']} · {t['title']}{due}", f"    {t.get('ask') or t.get('next') or t['detail']}".rstrip(), ""]
    L += [DEC_H, DEC_HELP, ""]
    decs = todays_decisions(tasks)
    if not decs: L += ["Nothing decided for you today.", ""]
    for t, who, txt in decs:
        L += [f"- {t['id']} · {t['title']} ({who}): {txt}"]
    if decs: L += [""]
    L += [DONE_H, DONE_HELP, ""]
    closed = sorted([t for t in tasks if t["status"] == "closed"], key=lambda t: t.get("closed") or "")[::-1]
    if not closed: L += ["Nothing completed yet.", ""]
    for t in closed[:DONE_SHOW]:
        done = (t.get("result") or "").strip() or "No summary recorded."
        if len(done) > 220: done = done[:218].rsplit(" ", 1)[0] + " ..."
        L += [f"- {t['id']} · {t['title']} (closed {t.get('closed') or 'earlier'})", f"    Done: {done}", ""]
    with open(DESK + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(L).rstrip() + "\n")
    os.replace(DESK + ".tmp", DESK)
    with open(STAMP, "w") as f: f.write(repr(os.path.getmtime(DESK)))

def cmd_desk(a):
    if desk_recent():
        print("The Desk was edited in the last 3 minutes. Skipping."); return
    with Locked():
        tasks = load()
        if os.path.exists(DESK):
            text = open(DESK, encoding="utf-8").read()
            typed = [m.group(1) for m in re.finditer(r"^### (T\d+)[^\n]*\n(?:.*?\n)*?Answer:[ \t]*\S", section(text, WAIT_H), re.M)]
            ticked = re.findall(r"^- \[[xX]\] (T\d+)", section(text, SIGN_H), re.M)
            if typed or ticked:
                print("There are typed answers or ticks not yet taken in. Run intake first."); return
        write_desk(tasks)
    print("Desk rewritten.")

# ---------- task commands ----------
def cmd_close(a):
    with Locked():
        tasks = load(); t = find(tasks, a.id)
        if not t.get("answer"): sys.exit("Only close a task when the human's own answer says it is done or not needed.")
        t["status"] = "closed"; t["closed"] = now(); log(t, a.by or "agent", a.note or "Closed on the human's answer")
        save(tasks)
    print(t["id"], "closed")

def cmd_list(a):
    for t in sorted(load(), key=lambda t: (t.get("due") or "9999", t["id"])):
        if a.owner and t["owner"] != a.owner: continue
        if a.status and t["status"] != a.status: continue
        if not a.status and t["status"] == "closed": continue
        print(f"{t['id']} [{t['status']}/{t['owner']}] {t.get('area','')} {t['title']}")
        if t.get("answer"): print(f"     Answer: {t['answer']}")
        if t.get("next"): print(f"     next: {t['next']}")

def cmd_show(a):
    print(json.dumps(find(load(), a.id), indent=1, ensure_ascii=False))

FIELDS = ["title", "area", "owner", "status", "detail", "next", "ask", "result", "source", "ask_type", "due", "errand"]

def norm_errand(v):
    """errand is stored as "yes" or "" so older tasks without the field still work."""
    if v is None: return None
    v = v.strip().lower()
    if v in ("yes", "y", "true", "1"): return "yes"
    if v in ("no", "n", "false", "0", ""): return ""
    sys.exit("--errand takes yes or no.")

def cmd_add(a):
    with Locked():
        tasks = load()
        t = {"id": next_id(tasks), "answer": "", "created": now(), "updated": now(), "log": []}
        a.errand = norm_errand(a.errand)
        for f in FIELDS: t[f] = getattr(a, f) or ""
        t["status"] = t["status"] or "working"
        log(t, a.by or t["owner"], a.note or "Added")
        tasks.append(t); save(tasks)
    print(t["id"])

def cmd_set(a):
    if not (a.note or "").strip() or a.note.strip().lower() in ("updated", "update", "done"):
        sys.exit("Add --note saying what you actually did, so it shows on the card.")
    if not a.by: sys.exit("Add --by with your agent name.")
    a.errand = norm_errand(a.errand)
    with Locked():
        tasks = load(); t = find(tasks, a.id)
        for f in FIELDS:
            v = getattr(a, f)
            if v is not None: t[f] = v
        if a.status == "waiting" and not t.get("ask"): sys.exit("A waiting task needs --ask")
        if a.status == "signoff" and not t.get("result"): sys.exit("A signoff task needs --result")
        if a.status == "working" and a.clear_answer: t["answer"] = ""
        if a.status == "closed": sys.exit("Only the human closes tasks, by ticking them on the Desk.")
        log(t, a.by, a.note)
        save(tasks)
    print(t["id"], t["status"], t["owner"])

RUNS = os.path.join(HERE, "runs.jsonl")

def cmd_runlog(a):
    """One plain line per run on what moved, so the human can see the board is alive."""
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps([now(), a.by, a.text[:240]]) + "\n")
    print("logged")

def cmd_pending(a):
    """Tasks with fresh input from the human, or new and unrouted, that this agent should act on."""
    for t in load():
        if t["status"] != "working": continue
        last = (t.get("log") or [["", "", ""]])[-1]
        if (t["owner"] == a.owner and last[1] == "human") or t["owner"] == "triage":
            print(t["id"], t["title"][:60])

p = argparse.ArgumentParser()
s = p.add_subparsers(dest="cmd", required=True)
s.add_parser("intake"); s.add_parser("desk")
rl = s.add_parser("runlog"); rl.add_argument("--by", required=True); rl.add_argument("--text", required=True)
pe = s.add_parser("pending"); pe.add_argument("--owner", required=True)
c = s.add_parser("close"); c.add_argument("id"); c.add_argument("--by"); c.add_argument("--note")
l = s.add_parser("list"); l.add_argument("--owner"); l.add_argument("--status")
sh = s.add_parser("show"); sh.add_argument("id")
for name in ("add", "set"):
    x = s.add_parser(name)
    if name == "set": x.add_argument("id"); x.add_argument("--clear-answer", action="store_true")
    for f in FIELDS: x.add_argument("--" + f.replace("_", "-"), dest=f)
    x.add_argument("--by"); x.add_argument("--note")
a = p.parse_args()
{"intake": cmd_intake, "desk": cmd_desk, "list": cmd_list, "show": cmd_show, "add": cmd_add, "set": cmd_set, "close": cmd_close, "runlog": cmd_runlog, "pending": cmd_pending}[a.cmd](a)
