# AI_LOG

**Tool:** Claude (Anthropic), in a claude.ai chat with a Linux sandbox. Claude wrote all the code, ran every experiment and wrote these docs. The human's input was the challenge text plus one word: "continue" (the first session ran out of tool calls before packaging).

Every number below came from actually running the code. Unless marked *held-out*, numbers come from **dev seeds 1000–1059 or 1000–1099**. The benchmark seeds (0–199) were run once, at the end, after the code was frozen.

## What was asked

> The full challenge prompt: a living network of agents with different abilities, coordinated by a commander; agents decide for themselves how to carry out orders; enemies must have a commander; no map reading; teams fight; 100+ fixed-seed games with win rate, turns, agents lost and more; commander on vs off, and explain if it makes no difference; a git repo with a README, the CSV plus a plot, and this log.

## Design decisions kept

| decision | why |
|---|---|
| Theme: kitchen brigade vs a Lich's crypt | Gives distinct roles with real trade-offs: tank, healer, ranged, area damage that hits friends, fast scout. |
| `World` hands out `Observation`s only; agent modules can't import it | Makes "no cheating" a structural property, checked by tests, instead of a promise. |
| Orders as one weighted candidate goal among several | This is literally "the commander gives orders, each agent decides how". It also makes disobedience measurable rather than scripted. |
| Ghoul rot turns heroes into turncoats who keep their memory | Produces emergent betrayal: a turncoat tells the Lich where the exit is, and the Lich sends undead to camp the kitchen door. This happened in 17–28% of games. |
| Friendly-fire fireball with a "recklessness" weight | Produces the second kind of betrayal, which the agent decides on knowingly ("2 skeletons are worth singeing Bruno"). |
| Three channels: shout (short range), radio (lossy), telepathy | Gives the commander a real, imperfect information advantage to test. |
| Same map per seed in every mode; dev and benchmark seeds separated | Paired statistics, and guards against tuning to the test set. As it turned out, this mattered. |

## Iteration log: what broke, and what was thrown away

1. **First run: commander 5% win, no commander 30%** (60 dev seeds). Traced a timeout game: the whole brigade sat in the starting room for 350 turns.
   - **Cause:** a one-tile doorway, with the Saucier "escorting" the Butcher while standing in it, and nobody allowed to pass.
   - **Fix kept:** allies may swap places (standard roguelike behavior). Commander: 18%, no commander: 27%.
2. **Ghouls turned the Butcher by turn 9–19,** before the Saucier could react.
   - **Fix kept:** infection per bite went 35 → 25 → 20, and the Saucier reacts from the first bite. The Chef's HP went 20 → 30.
3. **Survivors ping-ponged** between "regroup" and "explore" once the Butcher died. Each one thought somebody else led.
   - **Fix kept:** a deterministic chain of command each agent computes from what it knows. Commander and no commander now at parity: 33% / 32%.
4. **Lossy radio left permanent holes in the Chef's map,** so he kept ordering Bruno to "explore" cells Bruno had already mapped.
   - **Fixes kept:** heroes resend their full map every 10 turns, and agents now *ignore* explore orders their own memory proves stale. That second fix is a nice example of an agent overriding its commander with better local knowledge.
5. **Balance:** the Lich did ~60% of all hero kills, and zombies could be re-raised forever ("Zombie Zombie Dash").
   - **Fixes kept:** zombies crumble to dust; Lich bolt 5 → 4 damage.
   - **Result: commander 43%, no commander 60%.** The commander was now clearly *harmful*.
6. **Ablation of the commander** (60 dev seeds): full 45%, **intel relay only 60%**, movement orders only 38%. Removing escort orders and explore orders each helped.
   - **Conclusion:** the Chef's micromanagement hurt, and the information sharing helped.
   - **Kept** that v1 doctrine as `--mode micro`, so the finding stays in the benchmark.
7. **Wrote a "mission command" doctrine:** share all intel; order only what no single agent can decide (the carrier's route home, the scout's sector, a team-wide "storm the room" call, and triage). It scored 54% against 58%, and timeouts persisted.
8. **Timeouts turned out to be another navigation bug,** not doctrine. Teammates crowding a doorway made each explorer's "nearest frontier" flip west/east every turn.
   - **Fix kept:** commit to one exploration target; plan through teammates, since they swap.
   - **Result** (100 dev seeds): no commander 70%, micro 39%, mission 73%.
9. **Ablated mission command:** triage orders were *worse* than the Saucier's own triage (76% without them), and focus-fire orders were also worse (79% without). Intel-only scored 82%.
   - **Thrown away:** triage and focus fire.
   - **Kept:** extraction route, scout sector, and the storm-the-room call (79%, fastest wins, fewest losses). Intel-only was within noise of this, and a commander that never commands doesn't meet the brief.
10. **Froze the code and ran the held-out benchmark once:** no commander 75.5%, micro 44.5%, mission 72.5%.
    - The dev-seed advantage of mission command (+9 points) **did not replicate** (p = 0.56). Its 18.7-turn speed advantage did (CI 9–29).
    - Steps 6–9 compared several doctrine variants on the *same* 100 dev seeds, so the gap was partly selection noise. The README reports the held-out numbers and says so plainly.
11. **One test failed** after packaging: "a hero's memory ⊆ the cells it saw". This was *not* a leak. The test recorded positions at the start of a turn, but a teammate's swap can move a hero before it acts.
    - **Thrown away:** that version of the test.
    - **Kept:** a stronger version that records exactly what the referee hands each agent.

## Things considered and not built

- **Pygame live viewer.** The terminal replay plus GIF covers "see results" with no extra dependency, which keeps the clean-machine run trivial.
- **LLM-driven agents.** 600 benchmark games of ~15 agents over ~120 turns would mean about a million model calls. Utility-based agents keep it deterministic and runnable in 2 minutes. The `decide(Observation) -> (Action, [Message])` interface is where an LLM brain would plug in.
- **More doctrine tuning.** Pointless without a fresh seed set. Tuning further against seeds 0–199 would just repeat the overfitting described in step 10.
