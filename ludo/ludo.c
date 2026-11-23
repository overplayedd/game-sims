// Ludo simulator. Usage:
//   ludo <rules_mask> <nplayers 2|4> <bot0> <bot1> <bot2> <bot3> <games> <seed>
// Prints one JSON object with results for this fixed seating.
// 2 players sit on opposite corners (colours 0 and 2).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

// rule switches (bit set = rule ON)
#define R_SAFE      1   // start squares + star squares are safe
#define R_THREE6    2   // third six in a row forfeits the turn
#define R_BLOCKS    4   // two same-colour pieces form a block (can't be landed on or passed)
#define R_BONUS     8   // extra roll for a capture or for getting a piece home
#define R_EXIT1     16  // a 1 also releases a piece from base
#define R_NOEXTRA6  32  // a six does NOT give an extra roll

enum { B_RANDOM, B_CAPTURER, B_RUSHER, B_SPREADER, B_SAFE, B_HUNTRUSH, B_EXPERT, B_OUTRANDOM, B_OUTLEAD, B_X_NOCAP, B_X_NOEXIT, B_X_NODEF, NBOTS };

#define HOME 56
#define MAXLEN 4000

static uint64_t rng_s;
static inline uint64_t rnd(void) {
    rng_s ^= rng_s >> 12; rng_s ^= rng_s << 25; rng_s ^= rng_s >> 27;
    return rng_s * 2685821657736338717ULL;
}
static inline int die(void) { return (int)(((rnd() >> 32) * 6) >> 32) + 1; }
static inline int rndn(int n) { return (int)(((rnd() >> 32) * (uint64_t)n) >> 32); }

static int rules, NP;
static int colour[4];          // seat -> colour (start offset = 13*colour)
static int prog[4][4];         // seat, piece: -1 base, 0..50 loop, 51..55 home column, 56 home

static inline int absq(int seat, int p) { return (13 * colour[seat] + p) % 52; }
static inline int is_safe_sq(int a) { return (rules & R_SAFE) && (a % 13 == 0 || a % 13 == 8); }

// number of pieces of 'seat' on absolute loop square a
static inline int count_on(int seat, int a) {
    int c = 0;
    for (int i = 0; i < 4; i++) { int p = prog[seat][i]; if (p >= 0 && p <= 50 && absq(seat, p) == a) c++; }
    return c;
}

// how many opponent pieces could hit a piece of 'seat' sitting at progress p with one die
static int danger(int seat, int p) {
    if (p < 0 || p > 50) return 0;
    int a = absq(seat, p);
    if (is_safe_sq(a)) return 0;
    int d = 0;
    for (int o = 0; o < NP; o++) {
        if (o == seat) continue;
        for (int i = 0; i < 4; i++) {
            int q = prog[o][i];
            if (q < 0) { if (absq(o, 0) == a) d++; continue; }   // can pop out of base onto us
            if (q > 50) continue;
            int dist = (a - absq(o, q) + 52) % 52;
            if (dist >= 1 && dist <= 6 && q + dist <= 50) d++;
        }
    }
    return d;
}

typedef struct { int piece, np, cap, capprog, exits, home; } Move;

static int gen_moves(int seat, int r, Move *mv) {
    int n = 0;
    for (int i = 0; i < 4; i++) {
        int p = prog[seat][i], np;
        if (p == HOME) continue;
        if (p < 0) {
            if (!(r == 6 || (r == 1 && (rules & R_EXIT1)))) continue;
            np = 0;
        } else {
            np = p + r;
            if (np > HOME) continue;
        }
        // identical duplicates (two pieces on same progress) -> keep first only
        int dup = 0;
        for (int k = 0; k < n; k++) if (prog[seat][mv[k].piece] == p) { dup = 1; break; }
        if (dup) continue;
        int ok = 1, cap = 0, capprog = 0;
        if (rules & R_BLOCKS) {
            int from = p < 0 ? 0 : p + 1;
            for (int s = from; s <= np && s <= 50 && ok; s++) {
                int a = absq(seat, s);
                for (int o = 0; o < NP; o++) if (o != seat && count_on(o, a) >= 2) { ok = 0; break; }
            }
        }
        if (!ok) continue;
        if (np <= 50) {
            int a = absq(seat, np);
            if (!is_safe_sq(a)) {
                for (int o = 0; o < NP; o++) {
                    if (o == seat) continue;
                    for (int j = 0; j < 4; j++) {
                        int q = prog[o][j];
                        if (q >= 0 && q <= 50 && absq(o, q) == a) { cap++; capprog += q; }
                    }
                }
            }
        }
        mv[n].piece = i; mv[n].np = np; mv[n].cap = cap; mv[n].capprog = capprog;
        mv[n].exits = (p < 0); mv[n].home = (np == HOME);
        n++;
    }
    return n;
}

static int pick_best(double *sc, int n) {
    int best = 0, ties = 1;
    for (int k = 1; k < n; k++) {
        if (sc[k] > sc[best] + 1e-9) { best = k; ties = 1; }
        else if (sc[k] > sc[best] - 1e-9) { ties++; if (rndn(ties) == 0) best = k; }
    }
    return best;
}

static int choose(int seat, int bot, Move *mv, int n) {
    if (n == 1) return 0;
    double sc[4];
    switch (bot) {
    case B_RANDOM: return rndn(n);
    case B_CAPTURER:   // take any capture (biggest victim), otherwise random
        for (int k = 0; k < n; k++) sc[k] = mv[k].cap ? 100 + mv[k].capprog : 0;
        return pick_best(sc, n);
    case B_RUSHER:     // always push the piece that is furthest ahead; leave base only when forced
        for (int k = 0; k < n; k++) sc[k] = prog[seat][mv[k].piece];
        return pick_best(sc, n);
    case B_SPREADER:   // bring every piece out first, then move the one furthest behind
        for (int k = 0; k < n; k++) sc[k] = mv[k].exits ? 1000 : -prog[seat][mv[k].piece];
        return pick_best(sc, n);
    case B_HUNTRUSH:   // capture if possible, otherwise push the lead piece
        for (int k = 0; k < n; k++) sc[k] = mv[k].cap ? 1000 + mv[k].capprog : prog[seat][mv[k].piece];
        return pick_best(sc, n);
    case B_SAFE:       // never captures on purpose: only minimises its own exposure
        for (int k = 0; k < n; k++) {
            int p = prog[seat][mv[k].piece];
            int before = danger(seat, p);
            int save = prog[seat][mv[k].piece];
            prog[seat][mv[k].piece] = mv[k].np;      // (ignores the capture itself when judging danger)
            int after = danger(seat, mv[k].np);
            prog[seat][mv[k].piece] = save;
            sc[k] = 10.0 * before - 10.0 * after + (mv[k].home ? 5 : 0) + (mv[k].np > 50 ? 2 : 0);
        }
        return pick_best(sc, n);
    case B_OUTRANDOM:  // bring a piece out whenever possible, otherwise random
        for (int k = 0; k < n; k++) sc[k] = mv[k].exits ? 1000 : 0;
        return pick_best(sc, n);
    case B_OUTLEAD:    // bring a piece out whenever possible, otherwise push the lead piece
        for (int k = 0; k < n; k++) sc[k] = mv[k].exits ? 1000 : prog[seat][mv[k].piece];
        return pick_best(sc, n);
    case B_EXPERT:
    default:
        for (int k = 0; k < n; k++) {
            int p = prog[seat][mv[k].piece];
            int before = danger(seat, p);
            int save = p;
            prog[seat][mv[k].piece] = mv[k].np;
            int after = mv[k].cap ? danger(seat, mv[k].np) : danger(seat, mv[k].np);
            prog[seat][mv[k].piece] = save;
            double s = 0;
            if (bot != B_X_NOCAP) s += mv[k].cap * 40.0 + mv[k].capprog * 1.0;   // sending a far-advanced piece back hurts most
            s += mv[k].home ? 25 : 0;
            if (bot != B_X_NOEXIT) s += mv[k].exits ? 22 : 0;
            if (bot != B_X_NODEF) {
                s += before * (6.0 + 0.5 * (p < 0 ? 0 : p));     // rescue a threatened piece
                s -= after * (6.0 + 0.5 * mv[k].np);             // don't walk into fire
            }
            if (mv[k].np > 50 && p <= 50) s += 8;                // reach the home column
            s += 0.15 * mv[k].np;
            sc[k] = s;
        }
        return pick_best(sc, n);
    }
}

int main(int argc, char **argv) {
    if (argc < 9) { fprintf(stderr, "args\n"); return 1; }
    rules = atoi(argv[1]); NP = atoi(argv[2]);
    int bots[4]; for (int i = 0; i < 4; i++) bots[i] = atoi(argv[3 + i]);
    long games = atol(argv[7]);
    rng_s = strtoull(argv[8], 0, 10) * 0x9E3779B97F4A7C15ULL + 0x1234567ULL;
    for (int i = 0; i < 20; i++) rnd();
    if (NP == 2) { colour[0] = 0; colour[1] = 2; } else for (int i = 0; i < 4; i++) colour[i] = i;

    static long hist[MAXLEN + 1];
    long wins[4] = {0}, first_home_wins = 0, first_cap_wins = 0, games_with_cap = 0;
    long long tot_rounds = 0, tot_rolls = 0, tot_caps = 0;
    long long win_caps_made = 0, win_caps_taken = 0, lose_caps_made = 0, lose_caps_taken = 0;
    long winner_zero_taken = 0;
    long long sixes_wasted = 0;
    int maxlen = 0; long capped = 0;
    Move mv[4];

    for (long g = 0; g < games; g++) {
        for (int s = 0; s < NP; s++) for (int i = 0; i < 4; i++) prog[s][i] = -1;
        int made[4] = {0}, taken[4] = {0};
        int first_home = -1, first_cap = -1, winner = -1;
        int turns = 0; long rolls = 0;
        int seat = 0;
        while (winner < 0) {
            turns++;
            int sixes = 0;
            for (;;) {
                int r = die(); rolls++;
                if (r == 6) sixes++;
                if ((rules & R_THREE6) && sixes == 3) { sixes_wasted++; break; }
                int n = gen_moves(seat, r, mv);
                int again = (r == 6) && !(rules & R_NOEXTRA6);
                if (n > 0) {
                    int k = choose(seat, bots[seat], mv, n);
                    Move m = mv[k];
                    if (m.cap) {
                        int a = absq(seat, m.np);
                        for (int o = 0; o < NP; o++) {
                            if (o == seat) continue;
                            for (int j = 0; j < 4; j++) {
                                int q = prog[o][j];
                                if (q >= 0 && q <= 50 && absq(o, q) == a) { prog[o][j] = -1; taken[o]++; made[seat]++; }
                            }
                        }
                        if (first_cap < 0) first_cap = seat;
                        if (rules & R_BONUS) again = 1;
                    }
                    prog[seat][m.piece] = m.np;
                    if (m.home) {
                        if (first_home < 0) first_home = seat;
                        if (rules & R_BONUS) again = 1;
                        if (prog[seat][0] == HOME && prog[seat][1] == HOME && prog[seat][2] == HOME && prog[seat][3] == HOME) { winner = seat; break; }
                    }
                }
                if (!again) break;
            }
            if (winner < 0) seat = (seat + 1) % NP;
            if (turns > MAXLEN * NP) { capped++; break; }
        }
        if (winner < 0) continue;
        wins[winner]++;
        int rounds = (turns + NP - 1) / NP;
        if (rounds > MAXLEN) rounds = MAXLEN;
        hist[rounds]++; tot_rounds += rounds; tot_rolls += rolls;
        if (rounds > maxlen) maxlen = rounds;
        int caps = 0;
        for (int s = 0; s < NP; s++) {
            caps += made[s];
            if (s == winner) { win_caps_made += made[s]; win_caps_taken += taken[s]; }
            else { lose_caps_made += made[s]; lose_caps_taken += taken[s]; }
        }
        tot_caps += caps;
        if (taken[winner] == 0) winner_zero_taken++;
        if (first_home == winner) first_home_wins++;
        if (first_cap >= 0) { games_with_cap++; if (first_cap == winner) first_cap_wins++; }
    }
    long done = 0; for (int s = 0; s < 4; s++) done += wins[s];
    long acc = 0; int p50 = 0, p90 = 0, p99 = 0, minlen = 0;
    for (int i = 0; i <= MAXLEN; i++) {
        if (hist[i] && !minlen) minlen = i;
        acc += hist[i];
        if (!p50 && acc * 2 >= done) p50 = i;
        if (!p90 && acc * 10 >= done * 9) p90 = i;
        if (!p99 && acc * 100 >= done * 99) p99 = i;
    }
    printf("{\"rules\":%d,\"np\":%d,\"bots\":[%d,%d,%d,%d],\"games\":%ld,\"wins\":[%ld,%ld,%ld,%ld],"
           "\"tot_rounds\":%lld,\"tot_rolls\":%lld,\"tot_caps\":%lld,\"p50\":%d,\"p90\":%d,\"p99\":%d,\"min\":%d,\"max\":%d,"
           "\"win_caps_made\":%lld,\"win_caps_taken\":%lld,\"lose_caps_made\":%lld,\"lose_caps_taken\":%lld,"
           "\"winner_zero_taken\":%ld,\"first_home_wins\":%ld,\"first_cap_wins\":%ld,\"games_with_cap\":%ld,"
           "\"sixes_wasted\":%lld,\"capped\":%ld}\n",
           rules, NP, bots[0], bots[1], bots[2], bots[3], done, wins[0], wins[1], wins[2], wins[3],
           tot_rounds, tot_rolls, tot_caps, p50, p90, p99, minlen, maxlen,
           win_caps_made, win_caps_taken, lose_caps_made, lose_caps_taken,
           winner_zero_taken, first_home_wins, first_cap_wins, games_with_cap, sixes_wasted, capped);
    return 0;
}
