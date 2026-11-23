"""Runs every Ludo matchup (10,000,000 games total). Resumable: finished jobs are kept in jobs.jsonl."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BOTS = ["random", "capturer", "rusher", "spreader", "safe", "hunter_rusher", "expert",
        "out_random", "out_lead", "expert_no_capture", "expert_no_exit", "expert_no_defence"]
RANDOM, EXPERT = 0, 6
SAFE, THREE6, BLOCKS, BONUS, EXIT1, NOEXTRA6 = 1, 2, 4, 8, 16, 32
STD = SAFE | THREE6
VARIANTS = {
    "no_safe_squares": STD & ~SAFE,
    "no_three_sixes_rule": STD & ~THREE6,
    "blocks": STD | BLOCKS,
    "bonus_roll_for_capture_or_home": STD | BONUS,
    "exit_on_1_or_6": STD | EXIT1,
    "no_extra_roll_on_six": STD | NOEXTRA6,
}

jobs = []  # (section, label, rules, np, bots, games)
def hero_jobs(section, label, rules, hero, opp, per_seat, np=4):
    for seat in range(np):
        b = [opp] * 4; b[seat] = hero
        if np == 2: b[2] = b[3] = 0
        jobs.append((section, f"{label}|seat{seat}", rules, np, b, per_seat))

for h in range(len(BOTS)):
    hero_jobs("vs_random", BOTS[h], STD, h, RANDOM, 50000)
    hero_jobs("vs_expert", BOTS[h], STD, h, EXPERT, 50000)
jobs.append(("seat_order", "all_random", STD, 4, [0, 0, 0, 0], 400000))
jobs.append(("seat_order", "all_expert", STD, 4, [6, 6, 6, 6], 600000))
for name, mask in VARIANTS.items():
    jobs.append(("house_rules", f"{name}|all_expert", mask, 4, [6, 6, 6, 6], 200000))
    jobs.append(("house_rules", f"{name}|all_random", mask, 4, [0, 0, 0, 0], 100000))
    hero_jobs("house_rules", f"{name}|expert_vs_random", mask, EXPERT, RANDOM, 25000)
    hero_jobs("house_rules", f"{name}|expert_no_capture_vs_expert", mask, 9, EXPERT, 25000)
    hero_jobs("house_rules", f"{name}|expert_no_defence_vs_expert", mask, 11, EXPERT, 25000)
jobs.append(("two_player", "all_expert", STD, 2, [6, 6, 0, 0], 200000))
jobs.append(("two_player", "all_random", STD, 2, [0, 0, 0, 0], 100000))
hero_jobs("two_player", "expert_vs_random", STD, EXPERT, RANDOM, 50000, np=2)
hero_jobs("two_player", "expert_no_capture_vs_expert", STD, 9, EXPERT, 50000, np=2)
hero_jobs("two_player", "expert_no_defence_vs_expert", STD, 11, EXPERT, 50000, np=2)

total = sum(j[5] for j in jobs)
print("jobs", len(jobs), "games", total, flush=True)
if len(sys.argv) > 1 and sys.argv[1] == "plan": sys.exit()

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "jobs.jsonl")
done = set()
if os.path.exists(out):
    for line in open(out): done.add(json.loads(line)["key"])

def run(ix):
    section, label, rules, np, bots, games = jobs[ix]
    key = f"{section}/{label}"
    if key in done: return None
    r = subprocess.run([os.path.join(here, "ludo"), str(rules), str(np), *map(str, bots), str(games), str(1000 + ix)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout); d["key"] = key; d["section"] = section; d["label"] = label
    return d

with ThreadPoolExecutor(2) as ex, open(out, "a") as f:
    for d in ex.map(run, range(len(jobs))):
        if d: f.write(json.dumps(d) + "\n"); f.flush()
print("finished", flush=True)
