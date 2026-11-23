"""
Uno simulator: how much does strategy matter?

Rules modelled (official Mattel rules, simplified where noted):
- 108-card deck, 7 cards each, random starting player.
- Starting card is always a number card (simplification).
- Play a card matching colour or symbol, or a Wild.
- Wild Draw Four is only legal when you hold no card of the current colour.
- If you cannot play, draw one card; you may play it straight away if legal.
- No stacking of Draw Two / Draw Four, no challenges, no "Uno!" penalties.
- Winner = first player to empty their hand (single round, no points).

Usage: python3 uno_sim.py [games_per_config]
"""
import json
import random
import sys
import time
from multiprocessing import Pool, cpu_count

SKIP, REV, D2, WILD, WD4 = 10, 11, 12, 13, 14
W = 4  # colour index for wild cards


def make_deck():
    d = []
    for c in range(4):
        d.append((c, 0))
        for v in range(1, 13):
            d.append((c, v))
            d.append((c, v))
    d += [(W, WILD)] * 4 + [(W, WD4)] * 4
    return d


DECK = make_deck()
assert len(DECK) == 108


def legal_moves(hand, color, value):
    out = []
    has_color = False
    has_wd4 = False
    for card in hand:
        c, v = card
        if c == W:
            if v == WILD:
                out.append(card)
            else:
                has_wd4 = True
        elif c == color:
            has_color = True
            out.append(card)
        elif v == value:
            out.append(card)
    if has_wd4 and not has_color:
        out.append((W, WD4))
    return out


def color_counts(hand):
    cnt = [0, 0, 0, 0]
    for c, _ in hand:
        if c != W:
            cnt[c] += 1
    return cnt


# ---- strategies -------------------------------------------------------------
# Each tier function returns a priority (lower = play sooner).

def t_numbers_first(card, nxt):
    c, v = card
    if c == W:
        return 2 if v == WILD else 3
    return 1 if v >= 10 else 0


def t_actions_first(card, nxt):
    c, v = card
    if c == W:
        return 2 if v == WILD else 3
    return 0 if v >= 10 else 1


def t_all_out(card, nxt):
    c, v = card
    if v in (WD4, D2):
        return 0
    if v in (SKIP, REV):
        return 1
    if v == WILD:
        return 3
    return 2


def t_color_only(card, nxt):
    c, v = card
    if c == W:
        return 1 if v == WILD else 2
    return 0


def t_adaptive(card, nxt):
    # Hoard action cards, then unload them on a neighbour who is about to win.
    c, v = card
    if nxt <= 2:
        if v in (WD4, D2, SKIP):
            return 0
        if v == REV:
            return 1
        if v == WILD:
            return 3
        return 2
    return t_numbers_first(card, nxt)


def t_wilds_first(card, nxt):
    c, v = card
    if c == W:
        return 0
    return 1


STRATS = {
    # name: (tier function, prefer strongest colour?, pick wild colour smartly?)
    "random": (None, False, False),
    "random+smart_colour": (None, False, True),
    "numbers_first": (t_numbers_first, True, True),
    "actions_first": (t_actions_first, True, True),
    "all_out_attack": (t_all_out, True, True),
    "colour_keeper": (t_color_only, True, True),
    "wilds_first": (t_wilds_first, True, True),
    "adaptive": (t_adaptive, True, True),
}


def choose(strat, hand, legal, nxt, rng):
    tier, use_color, _ = STRATS[strat]
    if tier is None:
        return rng.choice(legal)
    cnt = color_counts(hand)
    best = None
    best_key = None
    for card in legal:
        c = card[0]
        key = (tier(card, nxt), -(cnt[c] if (use_color and c != W) else 0), rng.random())
        if best_key is None or key < best_key:
            best, best_key = card, key
    return best


def choose_color(strat, hand, rng):
    if not STRATS[strat][2]:
        return rng.randrange(4)
    cnt = color_counts(hand)
    m = max(cnt)
    return rng.choice([i for i in range(4) if cnt[i] == m])


# ---- game -------------------------------------------------------------------

def play(strats, rng):
    n = len(strats)
    deck = DECK[:]
    rng.shuffle(deck)
    hands = [[deck.pop() for _ in range(7)] for _ in range(n)]
    i = len(deck) - 1
    while deck[i][0] == W or deck[i][1] >= 10:
        i -= 1
    top = deck.pop(i)
    discard = [top]
    color, value = top
    cur = rng.randrange(n)
    start = cur
    direction = 1
    turns = 0

    def draw(player, k):
        nonlocal deck, discard
        for _ in range(k):
            if not deck:
                if len(discard) > 1:
                    deck = discard[:-1]
                    discard = discard[-1:]
                    rng.shuffle(deck)
                else:
                    return
            hands[player].append(deck.pop())

    while turns < 5000:
        turns += 1
        hand = hands[cur]
        nxt = (cur + direction) % n
        legal = legal_moves(hand, color, value)
        card = None
        if legal:
            card = choose(strats[cur], hand, legal, len(hands[nxt]), rng)
        else:
            before = len(hand)
            draw(cur, 1)
            if len(hand) > before:
                d = hand[-1]
                if legal_moves([d], color, value):
                    card = d
        if card is not None:
            hand.remove(card)
            discard.append(card)
            if not hand:
                return cur, start, turns
            c, v = card
            if c == W:
                color = choose_color(strats[cur], hand, rng)
            else:
                color = c
            value = v
            if v == SKIP:
                cur = (nxt + direction) % n
                continue
            if v == REV:
                if n == 2:
                    continue  # acts as a skip: same player goes again
                direction = -direction
                cur = (cur + direction) % n
                continue
            if v == D2 or v == WD4:
                draw(nxt, 2 if v == D2 else 4)
                cur = (nxt + direction) % n
                continue
        cur = nxt
    return -1, start, turns


def run_config(args):
    label, strats, games, seed = args
    rng = random.Random(seed)
    n = len(strats)
    wins = [0] * n
    wins_by_order = [0] * n  # 0 = the player who went first
    unfinished = 0
    total_turns = 0
    max_turns = 0
    for _ in range(games):
        w, start, turns = play(strats, rng)
        if w < 0:
            unfinished += 1
            continue
        wins[w] += 1
        wins_by_order[(w - start) % n] += 1
        total_turns += turns
        if turns > max_turns:
            max_turns = turns
    done = games - unfinished
    return {
        "label": label,
        "strats": list(strats),
        "games": games,
        "seat0_win_rate": wins[0] / done,
        "win_rate_by_seat": [x / done for x in wins],
        "win_rate_by_turn_order": [x / done for x in wins_by_order],
        "avg_turns": total_turns / done,
        "max_turns": max_turns,
        "unfinished": unfinished,
    }


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    names = [s for s in STRATS]
    configs = []
    seed = 1000
    # A) one player using strategy X against three random players
    for s in names:
        seed += 1
        configs.append((f"4p:{s} vs 3 random", (s, "random", "random", "random"), games, seed))
    # B) one player using strategy X against three 'numbers_first' players
    for s in names:
        seed += 1
        configs.append((f"4p:{s} vs 3 numbers_first", (s,) + ("numbers_first",) * 3, games, seed))
    # C) one player using strategy X against three 'adaptive' players
    for s in names:
        seed += 1
        configs.append((f"4p:{s} vs 3 adaptive", (s,) + ("adaptive",) * 3, games, seed))
    # D) two-player head to head, every pairing
    for a in names:
        for b in names:
            seed += 1
            configs.append((f"2p:{a} vs {b}", (a, b), games, seed))
    # E) identical players: does turn order matter?
    for n in (2, 3, 4, 6):
        seed += 1
        configs.append((f"order:{n} adaptive players", ("adaptive",) * n, games, seed))
        seed += 1
        configs.append((f"order:{n} random players", ("random",) * n, games, seed))

    t0 = time.time()
    with Pool(cpu_count()) as pool:
        results = pool.map(run_config, configs, chunksize=1)
    elapsed = time.time() - t0
    total_games = sum(c[2] for c in configs)
    out = {"games_per_config": games, "total_games": total_games,
           "seconds": round(elapsed, 1), "results": results}
    with open("uno_results.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"{total_games:,} games in {elapsed:.0f}s on {cpu_count()} cores")


if __name__ == "__main__":
    main()
