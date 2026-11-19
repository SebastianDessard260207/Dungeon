# Airport Dungeon
# Four passengers try to reach the gate before the airport stops them.
# The airport side is led by a commander: the Voice on the Speaker.
#
# How to run:
#   python airport.py          -> watch one game
#   python airport.py 5        -> watch the game with seed 5
#   python airport.py 5 off    -> seed 5, commander OFF
#   python airport.py bench    -> 100 games with commander ON and OFF

import random
import sys
import csv
import os
import time

WIDTH = 20
HEIGHT = 10
MAX_TURNS = 100
ESCAPES_NEEDED = 2      # passengers that must reach the gate to win
HIT_CHANCE = 0.85
RADIO_LOSS = 0.2        # 20% of radio messages get lost
STRAY_CHANCE = 0.1      # chance that a hit lands on a bystander (friendly fire)

# stats: name, hp, attack, reach, vision, discipline (how likely it obeys orders)
PASSENGERS = {
    "backpacker": ("Backpacker", 38, 4, 1, 4, 0),
    "attendant": ("Flight Attendant", 22, 2, 1, 4, 0),
    "business": ("Business Guy", 18, 5, 1, 4, 0),
    "tourist": ("Tourist", 16, 3, 3, 6, 0),
}
ENEMIES = {
    "guard": ("Security Guard", 14, 5, 1, 4, 0.9),
    "suitcase": ("Runaway Suitcase", 22, 3, 1, 3, 0.6),
}
SPEAKER = ("Voice on the Speaker", 30, 5, 1, 5, 0)
ENEMY_LIST = ["guard", "guard", "guard", "suitcase", "suitcase", "suitcase"]

LETTERS = {"backpacker": "B", "attendant": "F", "business": "$", "tourist": "T",
           "guard": "G", "suitcase": "S", "speaker": "V", "traitor": "X"}


class Unit:
    def __init__(self, uid, role, stats, side, pos, seed):
        self.uid = uid
        self.role = role
        self.name = stats[0]
        self.hp = stats[1]
        self.max_hp = stats[1]
        self.attack = stats[2]
        self.reach = stats[3]
        self.vision = stats[4]
        self.discipline = stats[5]
        self.side = side            # "passenger" or "airport"
        self.start_side = side
        self.pos = pos
        self.alive = True
        self.escaped = False
        self.rng = random.Random(seed)
        self.memory = {}            # what this unit remembers
        self.brain = None
        self.outbox = []            # messages this unit wants to send


def distance(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def make_message(scope, kind, data, radius=0, to=None):
    return {"scope": scope, "kind": kind, "data": data, "radius": radius, "to": to}


def neighbors(pos):
    result = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            x = pos[0] + dx
            y = pos[1] + dy
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                result.append((x, y))
    return result


def step_toward(unit, target, taken):
    best = None
    best_score = (distance(unit.pos, target), abs(unit.pos[0] - target[0]) + abs(unit.pos[1] - target[1]))
    for n in neighbors(unit.pos):
        if n in taken:
            continue
        score = (distance(n, target), abs(n[0] - target[0]) + abs(n[1] - target[1]))
        if score < best_score:
            best = n
            best_score = score
    if best is None:
        return ("wait",)
    return ("move", best)


def step_away(unit, danger_positions, taken):
    best = None
    best_dist = min([distance(unit.pos, d) for d in danger_positions])
    for n in neighbors(unit.pos):
        if n in taken:
            continue
        d = min([distance(n, p) for p in danger_positions])
        if d > best_dist:
            best = n
            best_dist = d
    if best is None:
        return ("wait",)
    return ("move", best)


def wander(unit, taken):
    options = [n for n in neighbors(unit.pos) if n not in taken]
    if len(options) == 0:
        return ("wait",)
    return ("move", unit.rng.choice(options))


# ---------------------------------------------------------------
# BRAINS
# Each brain gets only the observation (what the unit can see and
# the messages it heard). It never looks at the real game state.
# ---------------------------------------------------------------

def passenger_brain(unit, obs, turn):
    mem = unit.memory
    taken = []
    for v in obs["allies"] + obs["foes"]:
        taken.append(v["pos"])

    # read the messages
    for msg in obs["messages"]:
        if msg["kind"] == "GATE":
            mem["gate"] = msg["data"]
        if msg["kind"] == "ENEMY":
            mem["enemy"] = (msg["data"], msg["turn"])

    # did I just see the gate? tell everybody
    if obs["gate"] is not None and "gate" not in mem:
        mem["gate"] = obs["gate"]
        unit.outbox.append(make_message("near", "GATE", obs["gate"], 8))

    foes = sorted(obs["foes"], key=lambda f: distance(unit.pos, f["pos"]))
    if len(foes) > 0 and turn - mem.get("shouted", -9) >= 3:
        unit.outbox.append(make_message("near", "ENEMY", foes[0]["pos"], 6))
        mem["shouted"] = turn

    # the business guy can get bribed with a first class upgrade
    if unit.role == "business" and unit.hp < 0.4 * unit.max_hp:
        for f in foes:
            if f["role"] == "guard" and unit.rng.random() < 0.2:
                return ("betray",)

    # the flight attendant heals people close to her
    if unit.role == "attendant":
        hurt = []
        for a in obs["allies"]:
            if a["hp"] <= 0.6 * a["max_hp"] and distance(unit.pos, a["pos"]) <= 2:
                hurt.append(a)
        if len(hurt) > 0:
            weakest = min(hurt, key=lambda a: a["hp"])
            return ("heal", weakest["id"])

    # almost at the gate: just run
    gate = mem.get("gate")
    if gate is not None and distance(unit.pos, gate) <= 2:
        return step_toward(unit, gate, taken)

    if len(foes) > 0:
        # weak passengers run away when hurt (the backpacker never does)
        if unit.hp < 0.35 * unit.max_hp and unit.role != "backpacker":
            return step_away(unit, [f["pos"] for f in foes], taken)
        in_reach = [f for f in foes if distance(unit.pos, f["pos"]) <= unit.reach]
        if len(in_reach) > 0:
            target = min(in_reach, key=lambda f: f["hp"])
            return ("attack", target["id"])
        # the backpacker is the tank, he goes and fights
        if unit.role == "backpacker":
            return step_toward(unit, foes[0]["pos"], [t for t in taken if t != foes[0]["pos"]])

    if gate is not None:
        return step_toward(unit, gate, taken)

    # if a friend shouted about an enemy, the backpacker goes there
    enemy = mem.get("enemy")
    if unit.role == "backpacker" and enemy is not None and turn - enemy[1] <= 6:
        return step_toward(unit, enemy[0], taken)

    # the attendant stays close to the group
    if unit.role == "attendant" and len(obs["allies"]) > 0:
        closest = min(obs["allies"], key=lambda a: distance(unit.pos, a["pos"]))
        if distance(unit.pos, closest["pos"]) > 2:
            return step_toward(unit, closest["pos"], taken)

    # the gate is somewhere in the east, so go east and look around
    if unit.rng.random() < 0.3:
        return wander(unit, taken)
    target = (WIDTH - 2, unit.rng.randrange(HEIGHT))
    return step_toward(unit, target, taken)


def airport_brain(unit, obs, turn):
    mem = unit.memory
    taken = []
    for v in obs["allies"] + obs["foes"]:
        taken.append(v["pos"])
    commander_on = mem.get("commander_on", False)

    # read messages and orders
    for msg in obs["messages"]:
        if msg["kind"] == "ORDER" and msg["data"]["id"] > mem.get("last_order", -1):
            mem["last_order"] = msg["data"]["id"]
            chance = unit.discipline
            if unit.hp < 0.4 * unit.max_hp:
                chance = chance / 2      # hurt units listen less
            if unit.rng.random() < chance:
                mem["order"] = msg["data"]
                unit.notes.append("obeyed")
            else:
                mem["order"] = None
                unit.notes.append("ignored")
        if msg["kind"] == "ALERT":
            mem["alert"] = (msg["data"], msg["turn"])
        if msg["kind"] == "SPEAKER_DOWN":
            mem["panic_until"] = turn + 10
            mem["order"] = None

    foes = sorted(obs["foes"], key=lambda f: distance(unit.pos, f["pos"]))

    # tell friends and the commander what I see
    if len(foes) > 0:
        if turn - mem.get("alerted", -9) >= 2:
            unit.outbox.append(make_message("near", "ALERT", foes[0]["pos"], 5))
            mem["alerted"] = turn
        if commander_on and turn - mem.get("reported", -9) >= 2:
            unit.outbox.append(make_message("radio", "SIGHT", foes[0]["pos"]))
            mem["reported"] = turn
    if commander_on and turn - mem.get("pinged", -9) >= 4:
        unit.outbox.append(make_message("radio", "STATUS", unit.uid))
        mem["pinged"] = turn

    # leaderless panic
    if turn < mem.get("panic_until", -1) and unit.rng.random() < 0.5:
        return wander(unit, taken)

    if len(foes) > 0:
        if mem.get("order") is not None:
            unit.notes.append("override")    # saw an enemy, forgot the order
        in_reach = [f for f in foes if distance(unit.pos, f["pos"]) <= unit.reach]
        if len(in_reach) > 0:
            target = min(in_reach, key=lambda f: f["hp"])
            return ("attack", target["id"])
        return step_toward(unit, foes[0]["pos"], [t for t in taken if t != foes[0]["pos"]])

    order = mem.get("order")
    if order is not None:
        if distance(unit.pos, order["pos"]) <= 1:
            mem["order"] = None
            return ("wait",)
        return step_toward(unit, order["pos"], taken)

    alert = mem.get("alert")
    if alert is not None and turn - alert[1] <= 8 and distance(unit.pos, alert[0]) > 1:
        return step_toward(unit, alert[0], taken)

    return wander(unit, taken)


def speaker_brain(unit, obs, turn):
    # The commander. It does not move. It only knows what it sees
    # and what the radio tells it (and 20% of the radio is lost).
    mem = unit.memory
    foes = sorted(obs["foes"], key=lambda f: distance(unit.pos, f["pos"]))
    action = ("wait",)
    if len(foes) > 0 and distance(unit.pos, foes[0]["pos"]) <= unit.reach:
        action = ("attack", foes[0]["id"])
    if not mem.get("commander_on"):
        return action

    if "sightings" not in mem:
        mem["sightings"] = []
        mem["roster"] = {}
        mem["sent"] = {}
        mem["order_id"] = 0
    for msg in obs["messages"]:
        if msg["kind"] == "SIGHT":
            mem["sightings"].append((msg["data"], msg["turn"]))
        if msg["kind"] == "STATUS":
            mem["roster"][msg["data"]] = msg["turn"]
    for f in foes:
        mem["sightings"].append((f["pos"], turn))
    # forget old sightings
    mem["sightings"] = [s for s in mem["sightings"] if turn - s[1] <= 8]

    if turn % 2 == 0 and len(mem["sightings"]) > 0:
        target = min(mem["sightings"], key=lambda s: distance(s[0], unit.pos))[0]
        for uid in mem["roster"]:
            if turn - mem["roster"][uid] > 10:
                continue
            old = mem["sent"].get(uid)
            if old is not None and distance(old[0], target) <= 1 and turn - old[1] < 6:
                continue    # same order as before, do not repeat
            mem["sent"][uid] = (target, turn)
            mem["order_id"] += 1
            order = {"id": mem["order_id"], "kind": "HUNT", "pos": target}
            unit.outbox.append(make_message("to", "ORDER", order, 0, uid))
    return action


# ---------------------------------------------------------------
# GAME
# ---------------------------------------------------------------

class Game:
    def __init__(self, seed, commander_on=True):
        self.seed = seed
        self.commander_on = commander_on
        self.rng = random.Random(seed)
        self.units = []
        self.mail = {}          # (turn, uid) -> list of messages
        self.log = []
        self.turn = 0
        self.winner = None
        self.escaped = 0

        # counters for the results
        self.damage_passengers = 0
        self.damage_airport = 0
        self.healed = 0
        self.friendly_fire = 0
        self.betrayals = 0
        self.messages_sent = 0
        self.orders_issued = 0
        self.orders_obeyed = 0
        self.orders_ignored = 0
        self.overrides = 0
        self.enemies_killed = 0
        self.first_blood = None
        self.first_death_role = ""
        self.speaker_dead_turn = None
        self.damage_by_role = {}
        self.heal_by_role = {}

        # the gate is on the east wall
        self.gate = (WIDTH - 1, self.rng.randrange(HEIGHT))

        # passengers start on the west side
        ys = self.rng.sample(range(HEIGHT), 4)
        i = 0
        for role in PASSENGERS:
            pos = (self.rng.choice([0, 1]), ys[i])
            self.add_unit(role, PASSENGERS[role], "passenger", pos, passenger_brain)
            i += 1
        self.passenger_roles = {}
        for u in self.units:
            self.passenger_roles[u.uid] = u.role

        # airport units start in the middle / east
        cells = []
        for x in range(8, WIDTH - 4):
            for y in range(HEIGHT):
                cells.append((x, y))
        spots = self.rng.sample(cells, len(ENEMY_LIST))
        for role, pos in zip(ENEMY_LIST, spots):
            self.add_unit(role, ENEMIES[role], "airport", pos, airport_brain)
        self.speaker = self.add_unit("speaker", SPEAKER, "airport", (WIDTH - 3, self.gate[1]), speaker_brain)

        for u in self.units:
            u.memory["commander_on"] = commander_on

    def add_unit(self, role, stats, side, pos, brain):
        u = Unit(len(self.units), role, stats, side, pos, self.seed * 100 + len(self.units))
        u.brain = brain
        u.notes = []
        self.units.append(u)
        return u

    def say(self, text):
        self.log.append("[turn " + str(self.turn) + "] " + text)

    def living(self, side=None):
        result = []
        for u in self.units:
            if u.alive and not u.escaped:
                if side is None or u.side == side:
                    result.append(u)
        return result

    def observe(self, u):
        # build what this unit is allowed to know
        allies = []
        foes = []
        for v in self.living():
            if v is u:
                continue
            if distance(u.pos, v.pos) <= u.vision:
                view = {"id": v.uid, "role": v.role, "pos": v.pos, "hp": v.hp, "max_hp": v.max_hp}
                if v.side == u.side:
                    allies.append(view)
                else:
                    foes.append(view)
        gate = None
        if distance(u.pos, self.gate) <= u.vision:
            gate = self.gate
        messages = self.mail.pop((self.turn, u.uid), [])
        return {"allies": allies, "foes": foes, "gate": gate, "messages": messages}

    def send_messages(self, u):
        for m in u.outbox:
            self.messages_sent += 1
            msg = {"kind": m["kind"], "data": m["data"], "turn": self.turn}
            if m["scope"] == "near":
                for v in self.living(u.side):
                    if v is not u and distance(u.pos, v.pos) <= m["radius"]:
                        self.mail.setdefault((self.turn + 1, v.uid), []).append(msg)
            elif m["scope"] == "radio":
                if self.commander_on and self.speaker.alive and self.rng.random() >= RADIO_LOSS:
                    self.mail.setdefault((self.turn + 1, self.speaker.uid), []).append(msg)
            elif m["scope"] == "to":
                if self.commander_on:
                    self.orders_issued += 1
                    self.mail.setdefault((self.turn + 1, m["to"]), []).append(msg)
        u.outbox = []

    def hurt(self, attacker, victim, amount, note=""):
        victim.hp -= amount
        if attacker.side == "passenger":
            self.damage_passengers += amount
        else:
            self.damage_airport += amount
        if attacker.start_side == "passenger":
            self.damage_by_role[attacker.role] = self.damage_by_role.get(attacker.role, 0) + amount
        if self.first_blood is None:
            self.first_blood = self.turn
        if attacker.side == victim.side:
            self.friendly_fire += 1
            self.say("FRIENDLY FIRE! " + attacker.name + " hits " + victim.name + " (-" + str(amount) + ")")
        else:
            self.say(attacker.name + " " + note + "hits " + victim.name + " (-" + str(amount) + ")")
        if victim.hp <= 0:
            victim.alive = False
            self.say("*** " + victim.name + " is out ***")
            if victim.start_side == "passenger":
                if self.first_death_role == "":
                    self.first_death_role = self.passenger_roles[victim.uid]
            else:
                self.enemies_killed += 1
            if victim.role == "speaker":
                self.speaker_dead_turn = self.turn
                self.say("The speaker goes silent. The airport staff panic!")
                for e in self.living("airport"):
                    self.mail.setdefault((self.turn + 1, e.uid), []).append(
                        {"kind": "SPEAKER_DOWN", "data": None, "turn": self.turn})

    def do_attack(self, attacker, victim):
        if self.rng.random() > HIT_CHANCE:
            self.say(attacker.name + " misses " + victim.name)
            return
        amount = attacker.attack + self.rng.randint(-1, 1)
        if amount < 1:
            amount = 1
        # sometimes the hit lands on someone standing next to the victim
        bystanders = []
        for x in self.living():
            if x is not attacker and x is not victim and distance(x.pos, victim.pos) <= 1:
                bystanders.append(x)
        if len(bystanders) > 0 and self.rng.random() < STRAY_CHANCE:
            self.hurt(attacker, self.rng.choice(bystanders), amount, "(stray hit) ")
        else:
            self.hurt(attacker, victim, amount)

    def do_action(self, u, action):
        if action[0] == "move":
            new_pos = action[1]
            for v in self.living():
                if v.pos == new_pos:
                    return
            if new_pos == self.gate:
                if u.side == "passenger":
                    u.escaped = True
                    self.escaped += 1
                    self.say(u.name + " reaches the gate!")
                return      # airport units are not allowed on the gate
            u.pos = new_pos
        elif action[0] == "attack":
            v = self.units[action[1]]
            if v.alive and not v.escaped and v.side != u.side and distance(u.pos, v.pos) <= u.reach:
                self.do_attack(u, v)
        elif action[0] == "heal":
            v = self.units[action[1]]
            amount = min(5, v.max_hp - v.hp)
            if v.alive and v.side == u.side and distance(u.pos, v.pos) <= 2 and amount > 0:
                v.hp += amount
                self.healed += amount
                self.heal_by_role[u.role] = self.heal_by_role.get(u.role, 0) + amount
                self.say(u.name + " helps " + v.name + " (+" + str(amount) + ")")
        elif action[0] == "betray":
            self.betrayals += 1
            u.side = "airport"
            u.role = "traitor"
            u.name = "Business Guy (TRAITOR)"
            u.brain = airport_brain
            u.discipline = 0
            u.memory = {"commander_on": False}
            self.say("The Business Guy got upgraded to first class and joins the airport!")

    def check_end(self):
        if self.escaped >= ESCAPES_NEEDED:
            return "passengers"
        still_trying = 0
        for u in self.units:
            if u.start_side == "passenger" and u.alive and not u.escaped and u.side == "passenger":
                still_trying += 1
        if self.escaped + still_trying < ESCAPES_NEEDED:
            return "airport"
        return None

    def run(self, show=None):
        for self.turn in range(1, MAX_TURNS + 1):
            order = self.living()
            self.rng.shuffle(order)
            for u in order:
                if not u.alive or u.escaped:
                    continue
                obs = self.observe(u)
                action = u.brain(u, obs, self.turn)
                for note in u.notes:
                    if note == "obeyed":
                        self.orders_obeyed += 1
                    elif note == "ignored":
                        self.orders_ignored += 1
                    else:
                        self.overrides += 1
                u.notes = []
                self.send_messages(u)
                self.do_action(u, action)
            if show is not None:
                show(self)
            self.winner = self.check_end()
            if self.winner is not None:
                break
        if self.winner is None:
            self.winner = "timeout"
        return self.results()

    def draw(self):
        grid = []
        for y in range(HEIGHT):
            grid.append(["."] * WIDTH)
        grid[self.gate[1]][self.gate[0]] = "="
        for u in self.living():
            grid[u.pos[1]][u.pos[0]] = LETTERS[u.role]
        lines = []
        for row in grid:
            lines.append("".join(row))
        return "\n".join(lines)

    def results(self):
        lost = 0
        for u in self.units:
            if u.start_side == "passenger":
                if (not u.alive) or u.side != "passenger":
                    lost += 1
        best_role = ""
        best_score = -1
        for role in PASSENGERS:
            score = self.damage_by_role.get(role, 0) + self.heal_by_role.get(role, 0)
            if score > best_score:
                best_score = score
                best_role = role
        row = {
            "seed": self.seed,
            "commander": "on" if self.commander_on else "off",
            "winner": self.winner,
            "turns": self.turn,
            "escaped": self.escaped,
            "passengers_lost": lost,
            "enemies_killed": self.enemies_killed,
            "damage_passengers": self.damage_passengers,
            "damage_airport": self.damage_airport,
            "healed": self.healed,
            "friendly_fire": self.friendly_fire,
            "betrayals": self.betrayals,
            "chaos_index": self.friendly_fire + 3 * self.betrayals,
            "messages_sent": self.messages_sent,
            "orders_issued": self.orders_issued,
            "orders_obeyed": self.orders_obeyed,
            "orders_ignored": self.orders_ignored,
            "order_overrides": self.overrides,
            "first_blood_turn": self.first_blood if self.first_blood is not None else "",
            "first_death_role": self.first_death_role,
            "speaker_dead_turn": self.speaker_dead_turn if self.speaker_dead_turn else "",
            "mvp_role": best_role,
        }
        for uid in self.passenger_roles:
            u = self.units[uid]
            survived = 0
            if u.alive and u.side == "passenger":
                survived = 1
            row["survived_" + self.passenger_roles[uid]] = survived
        return row


# ---------------------------------------------------------------
# BENCHMARK
# ---------------------------------------------------------------

def average(values):
    if len(values) == 0:
        return 0
    return sum(values) / len(values)


def run_benchmark(games=100):
    rows = []
    for mode in ["on", "off"]:
        for seed in range(games):      # same seeds for both modes
            game = Game(seed, mode == "on")
            rows.append(game.run())

    if not os.path.exists("results"):
        os.makedirs("results")
    with open("results/results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    on = [r for r in rows if r["commander"] == "on"]
    off = [r for r in rows if r["commander"] == "off"]

    lines = []
    lines.append("Results with " + str(games) + " games per mode (seeds 0 to " + str(games - 1) + ")")
    lines.append("")
    lines.append("| metric | commander ON | commander OFF |")
    lines.append("|---|---|---|")

    def add(name, key, only_wins=False, percent=False):
        a = [float(r[key]) for r in on if r[key] != "" and (not only_wins or r["winner"] == "passengers")]
        b = [float(r[key]) for r in off if r[key] != "" and (not only_wins or r["winner"] == "passengers")]
        if percent:
            lines.append("| " + name + " | " + str(round(100 * average(a))) + "% | " + str(round(100 * average(b))) + "% |")
        else:
            lines.append("| " + name + " | " + str(round(average(a), 2)) + " | " + str(round(average(b), 2)) + " |")

    wins_on = len([r for r in on if r["winner"] == "passengers"])
    wins_off = len([r for r in off if r["winner"] == "passengers"])
    lines.append("| **Win rate (passengers)** | " + str(100 * wins_on // games) + "% | " + str(100 * wins_off // games) + "% |")
    add("Average turns (all games)", "turns")
    add("Average turns (only wins)", "turns", only_wins=True)
    add("Passengers lost per game", "passengers_lost")
    add("Passengers escaped per game", "escaped")
    add("Enemies knocked out per game", "enemies_killed")
    add("Healing per game", "healed")
    add("Friendly fire per game", "friendly_fire")
    add("Betrayals per game", "betrayals")
    add("Chaos index (friendly fire + 3 x betrayals)", "chaos_index")
    add("Messages per game", "messages_sent")
    add("First blood turn", "first_blood_turn")
    obeyed = sum([int(r["orders_obeyed"]) for r in on])
    ignored = sum([int(r["orders_ignored"]) for r in on])
    lines.append("| Orders issued per game | " + str(round(average([float(r["orders_issued"]) for r in on]), 1)) + " | 0 |")
    lines.append("| Order obedience rate | " + str(round(100 * obeyed / max(1, obeyed + ignored))) + "% | - |")
    lines.append("| Orders dropped because of a fight (per game) | " + str(round(average([float(r["order_overrides"]) for r in on]), 1)) + " | - |")

    lines.append("")
    lines.append("| passenger | survival ON | survival OFF | died first ON | died first OFF |")
    lines.append("|---|---|---|---|---|")
    for role in PASSENGERS:
        s_on = round(100 * average([float(r["survived_" + role]) for r in on]))
        s_off = round(100 * average([float(r["survived_" + role]) for r in off]))
        f_on = len([r for r in on if r["first_death_role"] == role])
        f_off = len([r for r in off if r["first_death_role"] == role])
        lines.append("| " + role + " | " + str(s_on) + "% | " + str(s_off) + "% | " + str(f_on) + " | " + str(f_off) + " |")

    # paired comparison: same seed, only the commander changes
    only_on = 0
    only_off = 0
    for a, b in zip(on, off):
        if a["winner"] == "passengers" and b["winner"] != "passengers":
            only_on += 1
        if b["winner"] == "passengers" and a["winner"] != "passengers":
            only_off += 1
    lines.append("")
    lines.append("Seeds won only with commander: " + str(only_on))
    lines.append("Seeds won only without commander: " + str(only_off))
    text = "\n".join(lines)
    with open("results/summary.md", "w") as f:
        f.write(text + "\n")
    print(text)

    # simple plot (needs matplotlib, skipped if it is not installed)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].bar(["ON", "OFF"], [100 * wins_on / games, 100 * wins_off / games], color=["blue", "orange"])
        axes[0].set_title("Passenger win rate (%)")
        axes[0].set_ylim(0, 100)
        roles = list(PASSENGERS.keys())
        x = range(len(roles))
        axes[1].bar([i - 0.2 for i in x], [100 * average([float(r["survived_" + k]) for r in on]) for k in roles], 0.4, label="ON", color="blue")
        axes[1].bar([i + 0.2 for i in x], [100 * average([float(r["survived_" + k]) for r in off]) for k in roles], 0.4, label="OFF", color="orange")
        axes[1].set_xticks(list(x))
        axes[1].set_xticklabels(roles)
        axes[1].set_title("Survival by role (%)")
        axes[1].legend()
        plt.tight_layout()
        plt.savefig("results/plot.png")
        print("\nSaved results/plot.png")
    except ImportError:
        print("\n(matplotlib is not installed, no plot)")
    print("Saved results/results.csv and results/summary.md")


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0 and args[0] == "bench":
        run_benchmark()
    else:
        seed = random.randrange(1000)
        if len(args) > 0 and args[0].isdigit():
            seed = int(args[0])
        commander_on = "off" not in args
        game = Game(seed, commander_on)

        def show(g):
            os.system("cls" if os.name == "nt" else "clear")
            print("AIRPORT DUNGEON | seed", seed, "| commander", "ON" if commander_on else "OFF", "| turn", g.turn)
            print("Passengers at the gate:", g.escaped, "/", ESCAPES_NEEDED)
            print()
            print(g.draw())
            print()
            for line in g.log[-5:]:
                print(line)
            time.sleep(0.15)

        result = game.run(show)
        print()
        print("WINNER:", result["winner"], "| turns:", result["turns"], "| lost:", result["passengers_lost"])
        print("(B backpacker, F attendant, $ business guy, T tourist | G guard, S suitcase, V speaker, = gate)")
