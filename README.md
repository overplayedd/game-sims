# Game simulations

Code and results behind the videos. Each folder holds one game: the simulator, the script that runs every matchup, and the results file with the numbers shown on screen.

| Folder | Video | Games simulated |
|---|---|---|
| `ludo/` | Ludo | 10,000,000 |

## Ludo

### Run it

```
cd ludo
gcc -O3 -o ludo ludo.c
python3 run_all.py        # all 190 matchups, 10,000,000 games (about 11 CPU-minutes)
python3 aggregate.py      # writes ludo_results.json and prints the tables
```

`jobs.jsonl` is the raw output of the run used in the video (one line per matchup, with its seed), and `ludo_results.json` is the summary built from it. `run_all.py` skips matchups already listed in `jobs.jsonl`, so delete that file first if you want to rerun everything from scratch. `check_independent.py` is a second simulator written separately in Python to cross-check the simple strategies.

### Rules used

Four players, four pieces each. A six releases a piece from base. A six gives another roll; a third six in a row loses the turn. Landing on an opponent sends it back to base, except on the eight safe squares (the four start squares and the four star squares). A piece needs the exact roll to get home. First player with all four pieces home wins.

House rules are switches on top of that: no safe squares, blocks (two pieces on one square cannot be landed on or passed), a bonus roll for a capture or for getting a piece home, leaving base on a 1 or a 6, no extra roll on a six, and no three-sixes penalty.

### Strategies

| Name in the code | What it does |
|---|---|
| `random` | Picks any legal move at random |
| `capturer` | Takes a capture if one is available, otherwise random |
| `rusher` | Always pushes the piece furthest ahead; leaves base only when forced |
| `spreader` | Brings every piece out, then always moves the piece furthest behind ("stick together") |
| `safe` | Never chases captures; only minimises its own exposure |
| `hunter_rusher` | Captures if possible, otherwise pushes the lead piece |
| `out_random` | Releases a piece on every six, otherwise random |
| `out_lead` | Releases a piece on every six, otherwise pushes the lead piece |
| `expert` | The "good player": weighs captures, releasing pieces, danger before and after the move, and progress |
| `expert_no_capture`, `expert_no_exit`, `expert_no_defence` | The good player with one habit switched off |

The good player is a hand-built strategy, not perfect play. Its results describe that player, not the best possible Ludo.

### What the numbers mean

Win rates against random players and against good players put the tested strategy in each of the four seats in turn (50,000 games per seat) against three copies of the opponent. Seat-order figures come from 600,000 games between four good players. Each headline win rate rests on 200,000 games, which puts it within about 0.2 percentage points.
