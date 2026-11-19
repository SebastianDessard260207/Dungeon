# AI_LOG

Tool: Claude (claude.ai chat). All the code and documents in this repo were
written by Claude from our requests. We are not hiding that. Read the TODO at
the end: each of us still has to add what we did ourselves.

## What we asked, what we kept, what we threw away

| What we asked | What we kept | What we threw away, and why |
|---|---|---|
| A plan for the challenge | Rule-based agents, fixed seeds, commander ON/OFF with the same seeds, CSV + README + AI_LOG | Agents powered by an LLM: 200+ games would be slow and could not be repeated exactly |
| Lots of theme ideas | At first IKEA, then Paladins vs Undead, and finally **Airport** | The other themes (fridge, wedding, school, etc.) |
| A full IKEA project | Nothing in the final repo | Too big and too hard for us to explain (maze, line of sight, many files) |
| A very simple Paladins project | The structure: one file, brains that only see an `obs`, commander with orders, a benchmark with the same seeds | The theme (we changed to airport) |
| An Airport version in one file with simple code | `airport.py`, README, benchmark | n/a |
| Balance | Raised passenger HP: the first version gave only 35% win rate | Original HP values |

## Result

The commander made no measurable difference (55% vs 49%, 21 seeds won only with
the commander and 15 only without). We reported it as it came out and did not
tune the commander to make it look better.

## TODO (each person fills this in)

- [ ] [NAME 1]: what I changed, tested or learned.
- [ ] [NAME 2]: same.
- [ ] Say what surprised us when we read the code.
- [ ] If we change anything (new role, different numbers), write the before and after results.
