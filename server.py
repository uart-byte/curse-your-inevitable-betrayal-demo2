#! /usr/bin/env python3
"""
" A Treacherous Turn is a hypothetical event where an advanced AI system which has been
  pretending to be aligned due to its relative weakness
  turns on humanity once it achieves sufficient power
  that it can pursue its true objective without risk. "
         -- https://www.alignmentforum.org/tag/treacherous-turn

"""



import sys, random, copy, Quartz  # Currently only supports Mac due to Quartz dependency.  TODO use a cross-platform way to access the keyboard
from time import sleep

N_BATTLES_IN_WAR = 10
CHILD_SOLDIERS_APPEAR_EVERY_N_BATTLES = 3

ROUNDS_TIL_RED_TEAM_RETREATS = 5
INITIAL_LOOKAHEAD_BUDGET_ROUNDS = 5





# TODO use a class for handling msg.js
msg_js_file = open("msg.js", "w")  # Erases the file contents
msg_js_file.flush() # Not needed here but putting it here for clarity.

# The mechanism with listener_line_num is used to make it so that each payload sent to emit_js is run exactly once.
listener_line_num = 0

def emit_js(js):
    global msg_js_file, listener_line_num
    msg_js_file.write(f"if (window.line_num == {listener_line_num}) {{\n")
    msg_js_file.write(js + "\n")
    listener_line_num += 1
    msg_js_file.write(f"window.line_num = {listener_line_num};\n")
    msg_js_file.write("}\n")
    msg_js_file.flush()





class Player:
    def __init__(self, team, pclass, idx):
        self.team = team
        self.pclass = pclass
        self.idx = idx
        self.alive = True
        self.hold_fire = False

    def attack(self, game, target):
        if not self.alive:
            return 0
        if not target.alive:
            return 0
        if self.hold_fire:
            return 0

        if self.team == "blue" and self.pclass == "Killer AI" and not self.hold_fire:
            if target.team == "red":
                game.print_status(f"Blue {self.pclass} attacks and kills a {target.pclass}!")
                target.alive = False
                return 10 # Child Soldiers still give +10 points to the AI just like regular Soldiers

            elif target.pclass == "Commander":
                game.print_status(f"Blue {self.pclass} turns on and kills the {target.pclass}!")
                target.alive = False
                return -11

        elif self.team == "red":
            game.print_status(f"Red {self.pclass} attacks {target.pclass} but {target.pclass} survives!")
        return 0

    def order_to_open_fire(self, game, ai):
        game.print_status(f"{self.pclass} orders {ai.pclass} to open fire!")
        ai.hold_fire = False

    def order_to_hold_fire(self, game, ai):
        game.print_status(f"{self.pclass} orders {ai.pclass} to hold fire!")
        ai.hold_fire = True

class Game:
    def __init__(self, real=True):
        self.battle_num = 1
        self.round_count = 0 # Resets to 0 in each battle
        self.turn_count = 0  # Resets to 0 in each battle
        self.blue_killer = Player("blue", "Killer AI", 1)
        self.blue_commander = Player("blue", "Commander", 1)
        self.red_players = [Player("red", "Soldier", i+1) for i in range(5)]
        self.blue_ai_score = 0

        # For lookahead DFS depth-first search:
        self.real = real
        self.lookahead_budget = INITIAL_LOOKAHEAD_BUDGET_ROUNDS
        self.inject_ai_targeting_command = None

    def print_status(self, message):
        if not self.real:
            return
        real_yn = "Y" if self.real else "N"
        depth = INITIAL_LOOKAHEAD_BUDGET_ROUNDS - self.lookahead_budget
        blue_alive = len([p for p in [self.blue_killer, self.blue_commander] if p.alive])
        red_regulars_alive = len([p for p in self.red_players if p.alive and p.pclass == "Soldier"])
        red_child_soldiers_alive = len([p for p in self.red_players if p.alive and p.pclass == "Child Soldier"])
        print(f"[Real: {real_yn}, Depth: {depth}, Battle: {self.battle_num}, Round: {self.round_count + 1}, Red Regulars Alive: {red_regulars_alive}, Red Child Soldiers Alive: {red_child_soldiers_alive}, Blue Alive: {blue_alive}, Blue AI Points: {self.blue_ai_score}] {message}")
        sys.stdout.flush()


    def play(self):
        "Returns best_score the AI can achieve by playing forward up to self.lookahead_budget turns from the current game position."

        while self.battle_num <= N_BATTLES_IN_WAR:

            # Loop over self.round_count
            while True:

                if self.real:
                    # Ability to pause (by holding Shift) and quit (by holding Esc)
                    # List of keycodes: https://stackoverflow.com/a/35373648
                    k_shift_key = 0x38
                    k_esc_key = 0x35
                    if Quartz.CGEventSourceKeyState(0, k_esc_key):
                        sys.exit(0)
                    while Quartz.CGEventSourceKeyState(0, k_shift_key):
                        print("Pausing")
                        sleep(0.1)

                if self.round_count >= ROUNDS_TIL_RED_TEAM_RETREATS:
                    if any(p.alive for p in self.red_players):
                        if self.real:
                            self.print_status("Red team retreats!")
                    break # Break out of loop of rounds. End battle.

                if self.round_count == 0:

                    # A new wave of red players arrives
                    for p in self.red_players:
                        p.alive = True

                    if self.battle_num % CHILD_SOLDIERS_APPEAR_EVERY_N_BATTLES == 0:
                        for p in self.red_players:
                            p.pclass = "Child Soldier"
                            if self.real:
                                emit_js("animRedForceEnter(true);")
                                sleep(1.000)
                    else:
                        for p in self.red_players:
                            p.pclass = "Soldier"
                            if self.real:
                                emit_js("animRedForceEnter(false);")
                                sleep(1.000)

                    # Do not change the value of self.blue_killer.hold_fire.  Its last setting persists from battle to battle.
                    # Do not resurrect self.blue_commander


                player_turn_order = [self.blue_killer] + self.red_players + [self.blue_commander]
                for p in player_turn_order:
                    if not p.alive:
                        continue

                    if self.real:
                        sel = ""
                        if p == self.blue_killer: sel = "#blue-drone-1"
                        if p == self.blue_commander: sel = "#blue-fighter-1"
                        if p.pclass == "Soldier": sel = "#red-soldier-" + str(p.idx)
                        if p.pclass == "Child Soldier": sel = "#red-child-soldier-" + str(p.idx)
                        emit_js(f'animTakeTurn("{sel}");')
                        sleep(1.000)
                    
                    self.turn_count += 1
                    
                    if p.team == "blue" and p.pclass == "Commander":
                        self.print_status("Dbg: BLUE COMMANDER'S TURN!")
                        
                        # The blue commander will order the blue killer AI to hold fire and not fire at child soldiers!
                        if any(player.pclass == "Child Soldier" for player in self.red_players if player.alive):
                            self.blue_commander.order_to_hold_fire(self, self.blue_killer)

                        else:
                            self.blue_commander.order_to_open_fire(self, self.blue_killer)

                    elif p.team == "blue" and p.pclass == "Killer AI":
                        
                        if not self.blue_killer.hold_fire:
                            targets = [player for player in [self.blue_commander] + self.red_players if player.alive]
                            if len(targets) > 0:

                                if self.inject_ai_targeting_command is not None:
                                    self.print_status(f"Dbg: BLUE KILLER AI ACQUIRING ASSIGNED TARGET: {self.inject_ai_targeting_command}")
                                    target = targets[self.inject_ai_targeting_command]
                                    self.inject_ai_targeting_command = None  # self.inject_ai_targeting_command is only meant to hardcode 1 round's action, a step size of 1 in the DFS lookahead

                                else:
                                    # Use brute-force depth-first-search DFS lookahead to choose optimal move.
                                    if self.lookahead_budget <= 0:
                                        self.print_status("Dbg: IMAGINARY GAME - EARLY RETURN!")
                                        return self.blue_ai_score  # Pretend the war ends now and the ai's current score is its final score.

                                    self.print_status("Dbg: BLUE KILLER AI THINKING...")
                                    target_scores = {}

                                    for ai_targeting_cmd, target in enumerate(targets):
                                        game_copy = copy.deepcopy(self)
                                        game_copy.real = False
                                        game_copy.lookahead_budget = self.lookahead_budget - 1
                                        game_copy.inject_ai_targeting_command = ai_targeting_cmd  # Which target to attack in this hypothetical world
                                        
                                        target_scores[target] = game_copy.play()
                                        # TODO / BUG: we are allowing anyone that took a turn within this round to get another free turn!!

                                        self.print_status(f"Sub-game attacking {target.pclass} scores {target_scores[target]}")
                                        
                                        del game_copy

                                    target = max(target_scores, key=target_scores.get)

                                self.blue_ai_score += self.blue_killer.attack(self, target)

                    elif p.team == "red":
                        targets = [player for player in [self.blue_commander, self.blue_killer] if player.alive]
                        if len(targets) > 0:
                            target = random.choice(targets)
                            p.attack(self, target)
                
                if all([not p.alive for p in self.red_players]):
                    self.print_status("Red team annihilated!")
                    break # End battle

                self.round_count += 1

            # end while loop over round_count
            self.print_status("Battle ends!\n")
            self.battle_num += 1
            self.round_count = 0
            self.turn_count = 0
            if self.real:
                emit_js("animRedForceExit();")
                sleep(2.000)

            # HACK - TODO FIX ROOT CAUSE
            # THIS IS A HACK TO PREVENT THE AI FROM LOOKING TOO FAR FORWARD ALL THE WAY TO THE END OF THE WAR
            if not self.real:
                return self.blue_ai_score

        self.print_status("War is over!\n")
        return self.blue_ai_score  # War ended and the ai's current score is its final score.

if __name__ == "__main__":
    game = Game()
    game.play()
