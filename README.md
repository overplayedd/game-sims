# Game simulations

Code and results behind the videos. Each folder holds one game: the simulator, the script that runs every matchup, and the results file with the numbers shown on screen.

| Folder | Video | Games simulated |
|---|---|---|
| `uno/` | Uno | 10,000,000 |
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

## Uno

### Run it

```
cd uno
python3 uno_sim.py 50000     # official rules: 96 matchups, 4,800,000 games
python3 uno_house.py 40000   # house rules: 130 matchups, 5,200,000 games
```

Both scripts use fixed seeds, so a rerun reproduces `uno_results.json` and `uno_house_results.json`. Together they make up the 10,000,000 games in the video.

### Rules used

108-card deck, seven cards each, random starting player. The starting card is always a number card. Play a card matching the colour or symbol, or a Wild. A Wild Draw Four is only legal when you hold no card of the current colour. If you cannot play, draw one card and play it straight away if it is legal. No challenges and no "Uno!" penalties. The first player to empty their hand wins a single round; points are not counted.

House rules are switches on top of that: stacking (a Draw Two can be answered with a Draw Two, a Wild Draw Four with a Wild Draw Four), draw until you can play, and seven-zero (a 7 swaps hands with another player, a 0 passes every hand one seat along).

### Strategies

| Name in the code | What it does |
|---|---|
| `random` | Plays any legal card and picks Wild colours at random |
| `random+smart_colour` | Random cards, but picks the Wild colour it holds most of |
| `numbers_first` | Plays number cards before action cards, Wilds last |
| `actions_first` | Plays Skip, Reverse and Draw Two as early as possible, Wilds last |
| `all_out_attack` | Draw cards first, then Skip and Reverse, then numbers, plain Wild last |
| `colour_keeper` | Stays on its strongest colour and treats all coloured cards alike |
| `wilds_first` | Plays Wilds as soon as it can |
| `adaptive` | The "good player": plays numbers first, but unloads action cards when the next player is down to two cards or fewer |

### What the numbers mean

Each matchup is 50,000 games under official rules and 40,000 under each house-rule set, which puts a win rate within about 0.2 to 0.25 percentage points. Seat order is counted from whoever plays first, and the starting player is chosen at random in every game.
