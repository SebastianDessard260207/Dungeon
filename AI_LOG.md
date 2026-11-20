# AI_LOG

Tool that we used: Claude (claude.ai chat). All the code and must part of the documents were made with help of Claude. Each of us still has to add what we did ourselves.

## What we asked, what we kept, what we threw away

At the beginning we asked a plan for the challenge, we decided to keep the rule-based agents, fixed seeds, commander ON/OFF with the same seeds, CSV + README and we threw away Agents powered byy an LLM: 200+ games would be running so slow and if we wanted to repeat the games that wouldn't be posible.

Secondly, we asked for lots of theme ideas, we started with the idea of an Ikea since they are huge in real life and it can be a maze, then Paladins vs Undead and then we thought of a basic dungeon called Kitchen-Krawl but the code was really complex to understand and decided to do something easier. On this one we threw away other themes like fridge, wedding, school and as mentioned before, the kitchen krawl.

In the third place, we also asked for a full IKEA project but we kept nothing from this repo because we didn't make the idea really clear, and we threw it away because it was too difficult to explain.

Then we asked for the paladins project and we kept the structure, commander with orders and a benchmark with the same seeds and we threw away the theme and change to kitchen krawl.

In the next place we worked with the kitchen krawl project but we had problems pulling documents since the code made no sense for us so we decided to change the theme to the airport one.

Finally, we just asked for Balance and we kept the raised passenger HP because in the first version gave only 35% win rate so we threw away the original HP values.

## Result

The commander made no measurable difference (55% vs 49%, 21 seeds won only with
the commander and 15 only without). We reported it as it came out and did not
tune the commander to make it look better.

## TODO

- Sebastian Dessard: I created the GitHub repo and I mainly worked on pulling and pushing documents to the repo, I worked together with Dion and Claude trying to always give the best ideas and giving my honest opinion of what we were doing. I corrected some problems we encountered during the coding and ejecution of the project. My main task was making good prompts for Claude to let her help us in the best way possible, I needed to read every requirement the challenge has to meet so we can have the best score possible.
- Dion Van Den Haak: I was the one who gave instructions of the tasks that we needed to complete, also I was checking that the work met the requirements to get a good grade. Me and Sebastian worked with Claude and decided which idea was good and what we should keep from them and what things to throw away.
- How complex it was, without AI we definetely couldn't be able to work on something like this (yet), we need to prepare more and put more effort on Python so one day this can be a piece of cake. Even tho we worked with Claude, she had some minor problems in the code and we had to look where it was failing and tell her to change it.
- The first version had the passengers winning too rarely, so the benchmark
was not very interesting.

| | Backpacker HP | Attendant HP | Business Guy HP | Tourist HP | Win rate ON | Win rate OFF |
|---|---|---|---|---|---|---|
| Before | 30 | 18 | 14 | 12 | 32% | 37% |
| After | 38 | 22 | 18 | 16 | 55% | 49% |

We raised the HP to get a win rate close to 50%. We did not change the
commander to make the results look better. In both versions the commander made
no measurable difference.

We didn't make any other change.
