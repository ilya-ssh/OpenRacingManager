# OpenRacingManager 🏎️

Open Racing Manager is a classic, F1-inspired racing management game built with [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. 
Designed to capture the challenging simulation and strategy of motorsport management, the game focuses on deep gameplay mechanics and difficulty over graphical detail.
## About
This is an open-source passion project with plans to make something similar to Motorsport Manager/F1 Manager but with deeper progression and strategies.  

Mostly the project is influenced by aformentioned games but also by Dwarf Fortress because of its visual simplicity but overall depth.
For now the main "engine" is python and pyxel, though some other libraries used (see requirements.txt), however we may switch to Lua or Godot if such need arises.   
Currently, we want to stick with very simplistic visual style, almost reminiscent to Atari or NES, maximizing the gameplay elements and depth.
Feel free to contribute to the project, but first contact main developer.

## Changelog
### Current version - Pre-alpha 0.0.3
_0.0.1_ Basic race engine introduced, no interpolation in the corners, basic grid. Speed based on the length of a segment.

_0.0.1t_ Trackbuilder introduced.

_0.0.2_ Smooth corners introduced, custom starting positions, ability to retract changes, 
implemented basic race loop with leaderboard, implemented states (main menu and race loop),
implemented dummy car class with tyres and stats, implement track loading from .json trackbuilder with smoothing. Speed calculated from corners and angles.

_0.0.3_ Pitstops introduced as well as some changes in balance. Cars now will pitstop when having destroyed tyres. Pitstops can be built using Trackbuilder. Leaderboard is now scrollable. Introduced announcements class for race announcements.
Utilities.py removed.

_0.0.3a_ Fixed leaderboard and interval race menu.

## Major bugs
**TLDR The game is in pre-alpha state and basically not playable**
1. Lap count set incorrectly
2. Speed decrease from tyre degradation is way too much
3. Visualization bugs with leaderboard
4. Max laps is getting from constants, but from track file
5. Aero is incredibly strong
6. No differenece between tyre compounds
## trackbuilder.py
Build your own tracks to race your cars on.
![Game Demo](/gifs/trackbuilder.gif)
## Race engine
Racing with 100 cars
![Game Demo](/gifs/game.gif)
## TO DO
- [x] Create trackbuilder with smooth corners, custom starting pos, ability to retract changes
- [x] Implement basic race loop with leaderboard 
- [x] Implement states (main menu and race loop)
- [x] Implement dummy car class with tyres and stats
- [x] Implement track loading from .json trackbuilder with smoothing. Calculate speed for corners from track
- [ ] Fix palette differences, handle palettes responsibly
- [ ] Fix car stats (partly done)
- [x] Add pits to trackbuilder and to race. Add the ability to pit and change tyres
- [ ] Add safety car spawn from pits
- [ ] Add dummy drivers, load from .json with stats
- [ ] Add dummy teams, load from .json with stats
- [ ] Add qualifying state before race
- [ ] Add more comprehensive readme
- [ ] .... more to come