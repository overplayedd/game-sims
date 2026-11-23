"""
Uno house-rules simulator. Reuses the deck, strategies and helpers from uno_sim.py.

Rule sets:
  official  - as uno_sim.py (draw one, may play it; no stacking; no 7-0)
  stacking  - a Draw Two can be answered with a Draw Two, a Wild Draw Four with a
              Wild Draw Four; the penalty passes on and grows until someone can't stack
  draw_until- if you can't play, keep drawing until you can, then play that card
  seven_zero- playing a 7 swaps your hand with another player (smart bots pick the
              smallest hand, random bot picks at random); playing a 0 passes every hand
              one seat along in the direction of play
  all_three - stacking + draw_until + seven_zero

Usage: python3 uno_house.py [games_per_config]
"""
import json, random, sys, time
from multiprocessing import Pool, cpu_count
from uno_sim import (DECK, W, SKIP, REV, D2, WILD, WD4, STRATS, legal_moves,
                     choose, choose_color)

RULESETS = {
    "official":   dict(stack=False, until=False, sz=False),
    "stacking":   dict(stack=True,  until=False, sz=False),
    "draw_until": dict(stack=False, until=True,  sz=False),
    "seven_zero": dict(stack=False, until=False, sz=True),
    "all_three":  dict(stack=True,  until=True,  sz=True),
}


def play(strats, rules, rng):
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
    pending = 0          # cards owed under stacking
    pending_kind = None  # D2 or WD4
    max_hand = 7

    def draw(player, k):
        nonlocal deck, discard
        got = 0
        for _ in range(k):
            if not deck:
                if len(discard) > 1:
                    deck = discard[:-1]
                    discard = discard[-1:]
                    rng.shuffle(deck)
                else:
                    break
            hands[player].append(deck.pop())
            got += 1
        return got

    while turns < 20000:
        turns += 1
        hand = hands[cur]
        nxt = (cur + direction) % n

        # --- facing a stacked penalty -----------------------------------------
        if pending:
            stackers = [c for c in hand if c[1] == pending_kind]
            if stackers:
                card = stackers[0]
                hand.remove(card)
                discard.append(card)
                pending += 2 if pending_kind == D2 else 4
                if card[0] == W:
                    color = choose_color(strats[cur], hand, rng)
                value = card[1]
                if not hand:
                    return cur, start, turns, max_hand
                cur = nxt
                continue
            draw(cur, pending)
            pending = 0
            pending_kind = None
            max_hand = max(max_hand, len(hand))
            cur = nxt
            continue

        legal = legal_moves(hand, color, value)
        card = None
        if legal:
            card = choose(strats[cur], hand, legal, len(hands[nxt]), rng)
        elif rules["until"]:
            while True:
                if draw(cur, 1) == 0:
                    break
                d = hand[-1]
                if legal_moves([d], color, value):
                    card = d
                    break
        else:
            if draw(cur, 1):
                d = hand[-1]
                if legal_moves([d], color, value):
                    card = d
        max_hand = max(max_hand, len(hand))

        if card is None:
            cur = nxt
            continue

        hand.remove(card)
        discard.append(card)
        if not hand:
            return cur, start, turns, max_hand
        c, v = card
        color = choose_color(strats[cur], hand, rng) if c == W else c
        value = v

        if rules["sz"] and c != W and v == 7:
            others = [p for p in range(n) if p != cur]
            if strats[cur].startswith("random"):
                tgt = rng.choice(others)
            else:
                m = min(len(hands[p]) for p in others)
                tgt = rng.choice([p for p in others if len(hands[p]) == m])
            hands[cur], hands[tgt] = hands[tgt], hands[cur]
        elif rules["sz"] and c != W and v == 0:
            if direction == 1:
                hands[:] = hands[-1:] + hands[:-1]
            else:
                hands[:] = hands[1:] + hands[:1]
            # after the pass, cur holds the hand of the player before them

        if v == SKIP:
            cur = (nxt + direction) % n
            continue
        if v == REV:
            if n == 2:
                continue
            direction = -direction
            cur = (cur + direction) % n
            continue
        if v in (D2, WD4):
            if rules["stack"]:
                pending = 2 if v == D2 else 4
                pending_kind = v
                cur = nxt
                continue
            draw(nxt, 2 if v == D2 else 4)
            max_hand = max(max_hand, len(hands[nxt]))
            cur = (nxt + direction) % n
            continue
        cur = nxt
    return -1, start, turns, max_hand


def run(args):
    label, rs, strats, games, seed = args
    rules = RULESETS[rs]
    rng = random.Random(seed)
    n = len(strats)
    wins = [0] * n
    by_order = [0] * n
    unfinished = 0
    tt = 0
    mx = 0
    lengths = []
    big_hand = 0
    for _ in range(games):
        w, start, turns, mh = play(strats, rules, rng)
        if w < 0:
            unfinished += 1
            continue
        wins[w] += 1
        by_order[(w - start) % n] += 1
        tt += turns
        mx = max(mx, turns)
        lengths.append(turns)
        big_hand = max(big_hand, mh)
    done = games - unfinished
    lengths.sort()
    return dict(label=label, ruleset=rs, strats=list(strats), games=games,
                seat0_win_rate=wins[0] / done,
                win_rate_by_turn_order=[x / done for x in by_order],
                avg_turns=tt / done, median_turns=lengths[len(lengths) // 2],
                p90_turns=lengths[int(len(lengths) * .9)], max_turns=mx,
                biggest_hand=big_hand, unfinished=unfinished)


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    names = list(STRATS)
    cfgs = []
    seed = 50000
    for rs in RULESETS:
        for n in (2, 4):
            seed += 1
            cfgs.append((f"{rs}|order:{n} adaptive", rs, ("adaptive",) * n, games, seed))
        for s in names:
            seed += 1
            cfgs.append((f"{rs}|4p:{s} vs 3 adaptive", rs, (s,) + ("adaptive",) * 3, games, seed))
            seed += 1
            cfgs.append((f"{rs}|4p:{s} vs 3 random", rs, (s,) + ("random",) * 3, games, seed))
            seed += 1
            cfgs.append((f"{rs}|2p:{s} vs adaptive", rs, (s, "adaptive"), games, seed))
    t0 = time.time()
    with Pool(cpu_count()) as p:
        res = p.map(run, cfgs, chunksize=1)
    tot = sum(c[3] for c in cfgs)
    json.dump(dict(games_per_config=games, total_games=tot, seconds=round(time.time() - t0, 1),
                   results=res), open("uno_house_results.json", "w"), indent=1)
    print(f"{tot:,} games in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
