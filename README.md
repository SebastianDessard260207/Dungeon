# Airport Dungeon

A dungeon game where four passengers try to reach their gate while the airport
fights back. Every character is an agent: it decides by itself what to do, and
it only knows what it can see or what it was told.

This was a challenge for our university programming course (Dungeons Challenge).

## How to run

You need Python 3.9 or newer. The game itself does not need to install anything.

```
python airport.py          # watch one game in the terminal
python airport.py 5        # watch the game with seed 5 (same seed = same game)
python airport.py 5 off     # same seed, but the commander is OFF
python airport.py bench    # run 100 games with commander ON and 100 with OFF
```

If `python` does not work, try `python3` or `py`.

The benchmark writes `results/results.csv` and `results/summary.md`. It also
makes `results/plot.png`, but only if matplotlib is installed
(`pip install -r requirements.txt`). Without matplotlib everything else works.

Map letters: B backpacker, F flight attendant, $ business guy, T tourist,
G security guard, S runaway suitcase, V voice on the speaker, = gate.

## The game

The map is 20 x 10. The passengers start on the left and the gate is on the right
wall. The passengers win when 2 of the 4 reach the gate. The airport wins when
there are not enough passengers left to get 2 to the gate. After 100 turns it
is a timeout (counts as a loss for the passengers).

### Passengers (no commander)

| Agent | What it does |
|---|---|
| Backpacker | Tank with lots of HP. Runs towards enemies and never flees. |
| Flight Attendant | Heals friends that are close to her. Stays near the group. |
| Business Guy | Hits hard. If he is hurt and sees a guard he can get bribed and **betray** the team. |
| Tourist | Attacks from 3 tiles away and sees farther (6 tiles). |

### Airport (with a commander)

| Agent | What it does |
|---|---|
| Security Guard x3 | Obeys orders most of the time (90%). |
| Runaway Suitcase x3 | Stubborn, obeys only 60% of the time. |
| Voice on the Speaker | The **commander**. It does not move, and it gives orders. |

## How the agents work

- Each agent has a "brain" function. The brain receives only an `obs`
  dictionary: the units inside its vision range, the gate if it is close, and
  the messages it received. It never reads the real game state or the whole map.
- Messages arrive one turn late. Passengers shout `GATE` and `ENEMY` to friends
  nearby. Airport staff shout `ALERT` nearby, and send `SIGHT` and `STATUS`
  reports to the commander by radio (20% of the radio messages are lost).
- The commander builds a list of recent sightings from the radio and sends a
  `HUNT` order to each unit with the position of the closest sighting.
- **Each unit decides if it obeys.** It accepts the order with a chance equal to
  its discipline (half of that if it is hurt). Even if it accepts, it drops the
  order when it sees an enemy, because fighting comes first. We count these cases.
- With the commander OFF, the Speaker still stands there and fights, but it gives no
  orders and gets no reports. The staff can still warn each other.
- Chaos: a hit can land on a bystander (friendly fire, 10%), the Business Guy can
  betray, and when the Speaker is knocked out the staff panic for 10 turns.

## Benchmark results

100 games per mode, seeds 0 to 99. The same seeds are used with and without the
commander, so each seed is a fair comparison. Raw data is in `results/results.csv`
(one row per game) and the full table in `results/summary.md`.

| metric | commander ON | commander OFF |
|---|---|---|
| **Win rate (passengers)** | 55% | 49% |
| Average turns (all games) | 36.8 | 38.0 |
| Passengers lost per game | 1.73 | 1.96 |
| Healing per game | 28.9 | 26.6 |
| Friendly fire per game | 2.68 | 2.58 |
| Betrayals per game | 0.34 | 0.37 |
| Chaos index | 3.70 | 3.69 |
| Messages per game | 121 | 54 |
| Order obedience rate | 67% | - |

Extra things we measured: who dies first (the Business Guy most often),
survival rate per role (Tourist survives most, 79%), and how many orders were
dropped because of a fight (about 26 per game).

### Does the commander make a difference?

Not a measurable one. The passengers win 55% with the commander and 49% without
it, but that is the opposite of what a helpful commander would do for the airport.
Out of 100 seeds, 21 were won by the passengers only with the commander and 15 only
without it. With only 100 games per mode, a gap of 6 points is within the normal
random noise (a sign test gives p = 0.4).

Ideas for why (we did not prove these):
1. About 26 orders per game are dropped because the unit sees an enemy, so the
   local vision decides most of what the agents do.
2. The reports are one turn old and some get lost, so the orders point to places
   where the passengers already left.
3. The map is small (20 x 10), so there is not much distance for coordination to save.
4. The passengers walk straight to the gate, so the staff close to the gate fight
   them anyway, with or without orders.

## Files

```
airport.py          the whole game and the benchmark
results/            results.csv, summary.md, plot.png
requirements.txt    only matplotlib (optional, for the plot)
AI_LOG.md           how we used AI
```

## Known limitations

- The map is empty (no walls), and vision is a simple distance, not line of sight.
- Agents follow simple rules, there is no LLM inside them.
- The numbers (HP, damage) were tuned by hand until the win rate was near 50%.
