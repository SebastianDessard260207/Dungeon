# Kitchen Crawl 🔪🧪💀

**A kitchen brigade raids a Lich's crypt for the Golden Recipe.** Every agent sees only its own line of sight, talks only through shouts, radio or telepathy, and decides for itself whether to follow orders. Both sides have a commander, and the heroes' commander can be switched off.

![recap](results/recap_seed100_mission.gif)

*Seed 100, mission-command Chef. Dash is bitten to 100% infection and turns on turn 17; Blaze torches him a turn later. On turn 68 Blaze fireballs a skeleton pack and kills his own Butcher. The Lich raises both Blaze and Bruno against their friends. Pepper, alone, kills the zombies and then the Lich. Dim cells are tiles no hero has seen yet.*

## Run it (clean machine, Python ≥ 3.9)

```bash
git clone <this repo> && cd kitchen-crawl
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m kitchen_crawl play --seed 100                       # animated replay in the terminal
python -m kitchen_crawl play --seed 100 --gif seed100.gif     # also render a GIF
python -m kitchen_crawl play --seed 68 --mode off --log       # just the story, no map
python -m kitchen_crawl bench                                 # 200 seeds x 3 modes -> results/ (~2 min)
python -m pytest -q                                           # the rules, as tests
```

`--mode` is `off` (no commander), `micro` (Chef v1) or `mission` (Chef v2, the default). The simulation itself needs only the standard library. Pillow and matplotlib are used only for the GIF and the plot.

## The teams

| Brigade (heroes) | ability | personality |
|---|---|---|
| **Chef Auguste** (commander, optional) | stays at the kitchen door; knows only what the radio tells him; sends orders and intel | – |
| **Bruno** the Butcher | tank, 40 HP; undead within 2 tiles tend to attack him (taunt) | very obedient, brave |
| **Sage** the Saucier | throws potions (+12 HP and cures ghoul rot), brews 1 every 10 turns | obedient, cautious |
| **Pepper** the Grinder | ranged attack (5 tiles, needs line of sight), kites when hurt | – |
| **Blaze** the Flambé chef | 3×3 fireball that **hits friends too** | reckless; ignores orders (obedience 0.4) |
| **Dash** the Runner | 2 moves per turn, 9-tile vision; the natural recipe thief | greedy: grabs the recipe early |

| Crypt (undead) | ability |
|---|---|
| **Grimbald** the Lich (commander, always on) | guards the recipe, casts ranged bolts, **raises corpses as zombies** (including your heroes), commands by telepathy |
| Skeletons ×5 | obedient melee |
| Ghouls ×3 | fast; every bite adds 20% ghoul rot. At 100% the hero **turns undead and switches sides**, keeping its abilities *and its memory of where the exit is*, which it reports to the Lich |
| Zombies | raised from corpses; slow; crumble to dust when killed |

**How to win:** carry the recipe out the kitchen door (*extraction*), or destroy every undead (*purge*).
**How to lose:** all five field heroes dead or turned (*wiped*), or 350 turns pass (*timeout*: the soup went cold).

## How the agents work

**No cheating, enforced by structure.** The `World` is the only object that knows the map. Each turn it gives an agent an `Observation`: tiles in its shadowcast field of view, units it can see, and messages delivered to it. The agent returns an `Action` and some `Message`s. Agent modules never import `world` or `dungeon`, and `tests/test_rules.py` checks this in three ways: by inspecting imports, by scanning object references mid-game, and by verifying that a hero's private map only contains cells it was shown.

**Communication** (all messages arrive the next turn):
- **Shout:** team broadcast, 7-tile range, no line of sight needed. This is the only channel when there is no commander.
- **Radio:** hero ↔ Chef, unlimited range, **10% packet loss**. Heroes report their status, what they've just seen and their newly mapped tiles. The Chef replies with orders plus an intel package (merged map, enemy sightings, recipe location, teammate positions).
- **Telepathy:** undead ↔ Lich, lossless, but each undead only reports what it sees.

**Orders are suggestions; each agent decides for itself.** Every turn each agent scores candidate goals: extract, retreat, heal, fight, grab the recipe, follow the order, regroup, or explore. An order is just one more candidate, weighted by that agent's obedience. So Blaze fights instead of retreating when a skeleton is next to him, and Dash grabs the recipe before it's "safe". Agents also discard orders their own memory proves stale (e.g. "explore over there" when they've already mapped it). The benchmark records how often each of these happens.

**Without a commander the team self-organizes.** A chain of command (Butcher → Flambé → Grinder → Saucier → Runner) that each agent computes from what it knows decides who leads. Followers stay near the leader, the leader and the Runner explore, and teammates within shouting range share sightings.

## Benchmark: 200 fixed seeds per mode, held out

All tuning used seeds 1000–1099. The benchmark ran **once**, on seeds 0–199, after the code was frozen. Each seed produces the same map and spawns in every mode, so the comparisons are paired. Full table: [`results/summary.md`](results/summary.md). Raw data, one row per game with 43 columns: [`results/results.csv`](results/results.csv).

![benchmark](results/benchmark.png)

| | No commander | Chef v1: micromanager | Chef v2: mission command |
|---|---|---|---|
| **Win rate** (95% CI) | **75.5%** (69–81) | **44.5%** (38–51) | **72.5%** (66–78) |
| Avg turns to win | 129.5 | 144.1 | **114.8** |
| Heroes lost per game (dead or turned, of 5) | 2.54 | 3.45 | 2.65 |
| Losses by wipe / timeout | 44 / 5 | 77 / 34 | 50 / 5 |
| Lich destroyed | 75% | 38% | 69% |
| Turncoats per game | 0.20 | 0.32 | 0.24 |
| Fallen heroes raised as zombies per game | 0.84 | 1.36 | 0.96 |
| Lich learned the exit from a turncoat | 17% | 28% | 22% |
| Friendly-fire hits / heroes killed by flambé | 0.20 / 3 total | 0.14 / 4 | 0.17 / 4 |
| Recipe fumbles (carrier died holding it) | 24 | 21 | 31 |
| Hero order adherence | – | 76% | 45% |
| Most frequent MVP (most damage dealt) | Pepper | Pepper | Pepper |

### Does the commander make a measurable difference?

**Yes, in two ways, but not by raising the win rate.**

1. **A bad commander is measurably catastrophic.** The v1 micromanager loses 31 points of win rate against no commander (paired McNemar p < 0.0001): 78 seeds won only without him versus 16 won only with him. He steers every agent toward positions that are 1–2 turns stale in his radio picture, which pulls them out of the formations they would form on their own. His wipes and timeouts both explode.
2. **A good commander makes the team faster, not more likely to win.** On the 111 seeds that both the mission-command and no-commander teams won, mission command finished **18.7 turns faster** (bootstrap 95% CI 9.0–28.9). Its recipe room is found about 11 turns earlier (turn 68 vs 79), because the Runner scouts a separate sector and its findings reach everyone by radio.
3. **Win rate: no measurable difference.** 72.5% vs 75.5%. Of the 200 seeds, 34 were won only with the Chef and 40 only without (McNemar p = 0.56).

**Why doesn't the good commander win more often?**
- **The team already shares most of what matters.** The squad moves as a group, so shouts reach nearly everyone who needs them. The Chef's unique information mostly concerns the Runner, who explores away from the squad.
- **Combat is local, and local information beats the radio.** Every attempt to have the Chef make combat decisions (focus fire, triage, retreat calls) lost to the agents' own choices on the dev seeds. An agent sees the fight *now*; the Chef sees it a turn late, with 10% of the reports missing.
- **The commander is a liability, too.** He is a target at the door (killed in 5% of games). When a hero turns, the exit location leaks to the Lich, who then sends undead to camp the door.
- **I overfit to the dev seeds.** On seeds 1000–1099, mission command beat no commander 79% vs 70%. That gap vanished on the held-out seeds. The doctrine was chosen by comparing several variants on the same 100 dev seeds, so part of that 9-point gap was selection noise. This is why the benchmark seeds were held out.

## Repo layout

```
kitchen_crawl/
  world.py       referee: true map, turn loop, combat, message delivery, metrics
  dungeon.py     rooms-and-corridors generator + recursive shadowcasting FOV
  model.py       Observation / Action / Message: the only things crossing the agent boundary
  navigation.py  agent-side memory + BFS over what the agent knows (unknown = assumed walkable)
  heroes.py      HeroBrain (5 roles) + ChefBrain (v1 micro / v2 mission doctrines)
  undead.py      UndeadBrain (skeleton, ghoul, zombie, turncoat) + LichBrain
  render.py      terminal frames + GIF
  bench.py       benchmark, Wilson CIs, McNemar, plot, hall of fame
  config.py      every number in one place
tests/test_rules.py
results/         results.csv, summary.md, benchmark.png, recap GIF
AI_LOG.md        how this was built with AI, and what was thrown away
```
