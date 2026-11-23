import json, collections
J=[json.loads(l) for l in open('jobs.jsonl')]
assert sum(j['games'] for j in J)==10_000_000 and all(j['capped']==0 for j in J)
res={"total_games":10_000_000,"sections":{}}
def hero(sec):
    g=collections.defaultdict(lambda:{"games":0,"wins":0,"by_seat":{}})
    for j in J:
        if j['section']!=sec or '|seat' not in j['label']: continue
        name,seat=j['label'].rsplit('|seat',1); seat=int(seat)
        w=j['wins'][seat]; g[name]["games"]+=j['games']; g[name]["wins"]+=w
        g[name]["by_seat"][seat]=round(100*w/j['games'],2)
    for v in g.values(): v["win_pct"]=round(100*v["wins"]/v["games"],2)
    return dict(g)
def table(j):
    n=j['games']; npl=j['np']
    return {"games":n,"seat_win_pct":[round(100*w/n,2) for w in j['wins'][:npl]],
      "avg_rounds":round(j['tot_rounds']/n,1),"p50":j['p50'],"p90":j['p90'],"p99":j['p99'],"shortest":j['min'],"longest":j['max'],
      "avg_rolls":round(j['tot_rolls']/n,1),"avg_captures":round(j['tot_caps']/n,2),
      "winner_caps_made":round(j['win_caps_made']/n,2),"winner_caps_suffered":round(j['win_caps_taken']/n,2),
      "loser_caps_made":round(j['lose_caps_made']/n/(npl-1),2),"loser_caps_suffered":round(j['lose_caps_taken']/n/(npl-1),2),
      "winner_never_captured_pct":round(100*j['winner_zero_taken']/n,2),
      "first_piece_home_wins_pct":round(100*j['first_home_wins']/n,2),
      "first_capture_wins_pct":round(100*j['first_cap_wins']/max(1,j['games_with_cap']),2)}
for sec in ["vs_random","vs_expert","house_rules","two_player"]: res["sections"][sec]={"hero":hero(sec)}
for j in J:
    if '|seat' in j['label']: continue
    res["sections"].setdefault(j['section'],{}).setdefault("tables",{})[j['label']]=table(j)
res["longest_game_rounds"]=max(j['max'] for j in J); res["shortest_game_rounds"]=min(j['min'] for j in J)
json.dump(res,open('ludo_results.json','w'),indent=1)
for sec in ["vs_random","vs_expert","house_rules","two_player"]:
    print('==',sec)
    for k,v in sorted(res["sections"][sec]["hero"].items(),key=lambda x:-x[1]["win_pct"]): print(f"  {k:55s}{v['win_pct']:6.2f}  {v['by_seat']}")
for sec,v in res["sections"].items():
    for k,t in v.get("tables",{}).items(): print(sec,k,t)
print(res["longest_game_rounds"],res["shortest_game_rounds"])
