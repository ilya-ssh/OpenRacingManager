# OpenRacingManager 🏎️

Open Racing Manager is a classic, F1-inspired racing management game built with [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. 
Designed to capture the challenging simulation and strategy of motorsport management, the game focuses on deep gameplay mechanics and difficulty over graphical detail.
## About
This is an open-source passion project with plans to make something similar to Motorsport Manager/F1 Manager but with deeper progression and strategies.  

Mostly the project is influenced by aformentioned games but also by Dwarf Fortress because of its visual simplicity but overall depth.
For now the main "engine" is python and pyxel, though some other libraries used (see requirements.txt), however we may switch to Lua or Godot if such need arises.   
Currently, we want to stick with very simplistic visual style, almost reminiscent to Atari or NES, maximizing the gameplay elements and depth.
Feel free to contribute to the project, but first contact main developer.


### Current version - Pre-alpha 0.0.2
### trackbuilder.py
Build your own tracks to race your cars on.
![Game Demo](/gifs/trackbuilder.gif)
### race engine
Racing with 100 cars
![Game Demo](/gifs/game.gif)
### TO DO
- [x] Create trackbuilder with smooth corners, custom starting pos, ability to retract changes
- [x] Implement basic race loop with leaderboard 
- [x] Implement states (main menu and race loop)
- [x] Implement dummy car class with tyres and stats
- [x] Implement track loading from .json trackbuilder with smoothing. Calculate speed for corners from track
- [ ] Fix palette differences, handle palettes responsibly
- [ ] Fix car stats
- [ ] Add pits to trackbuilder and to race. Add the ability to pit and change tyres
- [ ] Add safety car spawn from pits
- [ ] Add dummy drivers, load from .json with stats
- [ ] Add dummy teams, load from .json with stats
- [ ] Add qualifying state before race
- [ ] Add more comprehensive readme
- [ ] .... more to come