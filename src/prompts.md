Write me a function that takes in a json in its input (in the form of a dictionary), and return a data object.
Use wpp+planning.md for additional definition of data structure. Make sure the dataclass adheres to the definition.

Some of my input pipeline would have missing ports information (the entry will be there, but empty). The tiles entry captures the ports information. Write me a function that generates the ports dictionary by parsing through tiles. For detailed definition, see wpp+planning and the image for which port in tiles corresponds to which ports in the actual ports dict

There is also a chance that the data is wrong in the sense that the port information captured by "tiles" and "ports" are different. Write a function to check whether the port informations are valid. Focus on 3 things: 1. does access nodes of the same port have the same port type? 2. does the port count match? (4 general 3:1 and one of each type). 3. does the port info captured by "tiles" and "ports" the same? Look at wpp planning for detailed implementation

Now use the two functions you just built to repair/validate the json input. Your parsing function should: take the input, check if "ports" is empty. If so generate port info. After that, validate the port info. Then return if it is validated. Otherwise throw error

In some source of the json, "players" may be empty. Edit your json to pydemic code such that if "players" is an empty list, initialize 4 players in a "default" way. Analyze WPP+Planning.md to figure out what is appropriate for a default player 


THe board display need some major update to show player stat, roads, settlements. Search the internet for stuff like CLI catan game, ASCII catan board, or anything that helps you. If you find a good implementation that allows visualization of the board, settles, roads, and player info, change the implementation. If not, use your knowledge of catan to implement a way to display all of these extra element. Refer to the sample json to see how road/settle info is stored.






Create me a scoring function that takes in the data object and a settlement spot (see data object definition for the format). It should output the score of that settlement spot

Parameters: make them obvious to adjust by me later.
base resource strength: 5 element array
relative strength dampning: some param decide by what exact dampning 
port bonus: float.
prime variate bonus: float.
evaluation weighting: 4 floats.


Outline of algorithm:
1. Calculate production of each type of resource. this will yield you with the total productivity of each resource in points. (in that 2 is 1 point, 3 is 2 point, ... 6 is 5 point, 8 is 5 point, ... 11 is 2 point, 12 is 1 point)
1.1. Use the relative yield to calculate a relative strength of each resources. The strength is the sum of: base resource strength, which is a constant; overall strength, which is 1 / total_productivity_of_resource; pairwise strength, which is its production / its complement's production. Note: wood and brick are complements, wheat and ore are complements, sheep is nobody's complement.
After obtaining the relative strength, apply some variable dampning method so the model won't overvalue a resource like crazy.
2. find out all open settlement spots, calculate spot's production, which should be an array of 5 elements, capturing how much production of each resource will the tile bring. 
2.1. the total production of the tile is the first evaluation metric
2.2. the sum of item-wise product of tile's per resource production and the relative strength of resources is the second evaluation metric

Definition of port strength for 2:1s: normalize each resources' total yield  after dampning such that the second highest is 1. this is the relative strength of the ports. 3:1 has strength 1.

Port bonus is the third metric. If the settlement has a port on it, port bonus is port strength times port bonus (parameter). else 0

prime variate bonus is the 4th metric: if the tile's total production is >= 10, and it has 3 different resources, apply prime variate bonus.

multiply evaluation weighting of each metric to the value of the metric, sum them, that is the total score of the settlement.

Task: implement this algorithm, leaving the parameters easy to be adjusted by me.
Do so in a new file called settle_eval_simple.py




Create me a function called in game_state.py that when called, run the previously defined evaluation algorithm on every single valid settlement spots. NOTE: YOU MUST CAREFULLY CONFIRM THE SET OF VALID SETTLEMENT SPOTS. 


Create me a simple settlement decision algorithm. It should take in a board data object. and output the best settlements and road for the next player (see data object definition as to the format). Your result should be in the form of a 3-tuple of ((settle_spot, road_spot): probability). Note that you cannot place a settlement next to another settlement, your road must be next to the current settlement you placed, and that all catan rules are applied. Another thing to note is that the data structure technically allows placing roads in the ocean, but you MUST NOT do that as it is not a legal placement.

Parameter:
K

To decide: pick the top 3 options, subtract each by (K * third_score). apply softmax on the results to be the probability of each.
Road: point it to: a settlement less than 4 roads away, are not the top 9 scoring, and are the highest scoring amongst settlements that match previous req.

Note, for ((settle_spot, road_spot): probability), road is not a direction, but a 2-tuple like how road is supposed to 


python manual_processing/visualize_board.py src/sample.json --score


Build me a function that comes up with a list of X settle spots. Requirements:
(Note, this is to simulate the setup stage)
1. they must be open as of the current board state (not taken, not immediately next to a taken spot, not invalid by rule of catan), but it's ok if they interfere against each other.
2. your pick should be the top X scoring spots according to the augmented settle scoring list.
3. write an extend_option function that takes in the entire data object, and returns a list of extra settle spots. You should combine its output with your existing list, then return the bigger list. You are to leave the function blank (return empty) and write clear comment that this is a placeholder for future implementation.

write it in settle_options.py


build me two ai query function, inside the ai folder.
One is normal, the other one is async.
Make sure it's easy to add credential from different AI provider, then choose both provider and model to query on runtime.
The function itself doesn't need many fancy action, just relay the request to the right AI and return the response.
Make use of default values such that the function is callable with minimal extra params while also callable with specific AI models, etc.

Expected use case: a function need to query AI. Instead of doing it directly, it calls one of these functions depending on sync/async. It gets the response relayed.

---

With the settle option generator and settle decider, build me a settle simulator that use the settle option generator to generate a list of likely cases for my current settle, then simulate where everyone else settles for each of my possible settle cases. Note for probabilistic analysis, the goal is to compare these options. Do not attempt to calculate their relatively likelihood in this function.

Parameter:

X: same param as the number of settles decided by the settle options function, don't redefine here
max_window: maximum number of case per settle option

Input: a board state
Output: a list of X ((current settle option, current road option), list-of-max_window(placeout result))
explain: placeout result is a board data object that capture the state after all 4 players placed their 2 settles.

Procedure:
1. use settle option generator to generate a list of possible option that I can settle on
2. for each option: assume I settled there, use settle predictor to predict where will the next person will settle (this gives 3 subcases per case).
If there are more than max_window cases after the operation: only keep the top max_window likely case by probability, then normalize the probability of these cases so they sum to 1. 
Then, for each case of his possible placement, simulate the next placement assume I placed where I did and the previous person placed where he did (for each case after the previous simulation/normalization), normalize if total cases > max_window, then repeat till all 8 settlements are placed. 

Keep track of the combined probability by multiplication. You must not take into consideration the probability of the first set of placement determined by the settle option generator for myself (we are simulating for each case so its probability would be 1)

This gives a list of max_window possible place-outs, each with their probability, per settle option.

Create a list with each settle option paired with the list of (place-out, probability)s. Return that
build this function in settle_sim.py








run the tests in an MCP server and confirm the following:
1. the prob of all cases under each options add to 1
2. no settlements in any cases are in conflict with each other (there is a pre-defined settlement checker)



Write me a simple robber prediction algorithm for me that takes in a board data object and return a list (length 4 since 4 players) of robber preference
Each robber preference is a list of 3 (location, probability), and the 3 probabilities sum to 1.

Parameters: Make them easily accessed and changed. Do not allow overwrites.
- base resource strength: 5 element array of how strong each resoureces are, it is already defined somewhere, use that.
- raw power preference: how much robbing care about the raw prod over rare resources.
- strength to probability parameters.


Procedure/algorithm:
Each tile produces (number of point) * (number of settlement adjacent) amount of resources expected
Generate a map of tile - expected prod
Generate a total resource-wise prod (sum of all tiles of the same resources) that is resource weight.
normalize the weights so average is 1.

calculate a relative strength of each resources. The strength is the sum of: base resource strength, which is a constant; overall strength, which is 1 / total_productivity_of_resource; pairwise strength, which is its production / its complement's production. Note: wood and brick are complements, wheat and ore are complements, sheep is nobody's complement.
After obtaining the relative strength, apply some variable dampning method so the model won't overvalue a resource like crazy.
NOTE: this part is basically the same as a segment in settle scoring. You can reuse the code. For any parameter, define it as required above
Add raw_power_preference to each to get balanced_preferences. 
Each tile's score is its expected_prod * balanced_preferences[resource_type]

For each player, pick the top 3 tiles to rob by:
1. they must not have a settle on the tile
2. of those eligible, get the top 3 scoring.

To get the probability, use the same strength to probability algorithm as the settle decision, which is already implemented. Use a separate set of parameters as they are not the same model. Put it in the parameter section for me to tune later.
Return the result in the shape required


---


Build me a non-ai init board state evaluator

Parameters: you are to make them easy to adjust by me, there must not be any overwriting of them to avoid mistakes
wb-bonus
ows-bonus
extreme-bonus
prod-pair bonus

total-multiplier
total-valued-multiplier

portability bonus

The process:
1. run simple rob prediction. divide all probability numbers by 4.
2. for each tile, sum all mentions of it in the 4 players' rob prediction (take the sume of the probability after dividing by 4). This is the tile's rob attractiveness.
3. The tile's actual production is (1 - rob_attractiveness) * productivity_points.
4. with that, calculate each player's total actual production by resource type (result is 4 arrays each of len 5)
5. Sum all 4 and get total actual production of the board by resource type.
6. calculate wb/ows relative power: total actual prod of ((min(wood, brick) + 2) / (min(ore, wheat, sheep))  + 2) * 1.1
7. use the relative strength calculation used by robber prediction to get relative strength

for each person, determine whether they have a production pair: (wood brick) or (wheat ore) of the same number. If so, both of the tiles' production points is multiplied by prod-pair bonus when calculating anything related to prod FOR THAT PLAYER ONLY.

for each person, determine their major strategy by a float between 0 and 1. 0 is pure wood brick, 1 is pure ows. Note, use the min calculation idea above. call this strategy-index. Note, relative strength is irrelevant in this case

the person with lowest strat index gets wb-bonus 
the person with highest strat index gets ows bonus
the person with the most extreme strat index get extreme bonus

each person get (total_post-robber_prod * total-multiplier)

multiply total post robber prod with relative strength, each person get total strength * total-valued-multiplier.

a person gets portability bonus if all of:
- there is a settlement with a port that is still open that they are 2 or 3 roads away.
- the port is either a 3:1 or the player produce 5 or more points of such resource after robber but ignoring prod pair bonus

- compute actual prod
- determine strat
- best road guy get extra
- best city guy get extra
- unique guy gets one extra
- total pips
- potential open major port
- compute wb vs ows combo-wise weight
- paired numbers of the same group


add a componet near the end of your algorithm for the board state evaluator:
for each player, find out their target by the following criteria in order of importance. 
1. the strongest player with the same strategy as them (they are wb if less than 0.5, else ows).
2. in case of a close call or nobody stronger than the player in the category, the player with the highest eval outcome.

add a param called target, subtract that from each person's target (if a player is multiple player's target, subtract that multiple times).



write me a function that takes in a data object and return a list of cards the player hold, assuming that they just finished setting up the board and that the order of settlement is the order of settlements being listed



---



Write me a simple AI agent that analyze a catan board (at the time when everyone finished placing their initial settles, and before the game begins). It should take in the board object, first perform the simple settle eval to it, then feed its result and every players' starting hand (cards) and any information that can be obtained by calling an analysis function I built into a simple AI agent structure. Note: for each thing the agent passes in, it must clearly explain what it is and how to interpret it. The ai agent should analyze the following:

- First analyze the core objective for each player as of what must they do ASAP to greatly boost their game (like securing spots with rare resources for road players, or making sure they have a spot to eventually settle for development card players). In other words, identify what a player must do to "fully activate" their setup. Analyze the difficulty of these objectives.

- identify races (two people wanting the same/mutual exclusive spot), they "fight" for it.
- get what card someone is holding
- identify who wins each races. 
- identify exploits others can make from the race (like trading a brick for multiple cards so one player wins the race)
- simulate what will happend when each number rolls. Will someone get good trades when a number roll? 
Example: someone producing a lot of wood, but another player produce multiple brick on the same number with no wood. So when that number gets rolled this player will likely get the trade he need.

- geopolitical factor: who will be targeted after the first few round? (if you win a race, you become the center of attention for a bit, etc)
- activation time frame: how long does it take for someone to complete their core objective (like building at a port). If it would take a long time, their game will be hindered.
- building space: for road players, how many potential spots do they have and can they secure before being taken by others.

It should perform the complete analysis in up to 3 consecutive AI api call, with possible data processing inbetween. The result of this call should be a relative win probability (4-tuple) that sums to 1.

The agent function must be async, but you should call the ai apis in a sync order to utilize the output of one and allow better process flow.

Build this simple agent for me. BEWARE that you must prompt engineer carefully to avoid bad output, you must analyze all of the following, and that you can assume that the initial algorithmic analysis is a decent one but without much complexity and with limitation. Read through the code for the analysis and other functions for a better understanding on how they work


Now i got everything I need to build the perfect settle bot. Here is the workflow using the tools I built.
1. ingest a json and make it a data object.
2. run settle sim, which gives you a 20 playout simulation for each case, along with probability.
3. make an async scoring orchestrator.
- for the top X most likely, run the full analysis that uses AI. Make sure to deal with async await properly. 
- for the rest, run the simple analysis. Async is optional here.
after every analysis returns, sum (case_probability * player_0_chance_of_winning). This the score of this settle option
return the one with the highest score.

make x a tunable param, set it to 5