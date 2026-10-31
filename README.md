# GTA San Andreas: Definitive Edition — 100% Save Editor

```
--==========-----------------=-----------=---========---------------------------
-===========------=-------::.             :--========---------------------------
--========-----------..    :=*#%########%*:. .:-====----------------------------
------------------:  :=*%@@@@@@@@@@@@@@@@@@@@*-..--==---------------------------
---------------:  :#@@@@@@@@@@@%%%%%####**##@@@@+:.-----------------------------
-------------- .+@@@@@%###***+++++++++++++++==+#@@%.----------------------------
--==--------: *@@@@*+=+++++++++++**+++*********++*@* ---------------------------
--==-------:.@@@#+==++++****+++++**++************++@+ --------------------------
----------- @@@#=++**********+*********++++********#@- -------------------------
----------- @@%++*******++++++++*+*++++*****#####***%@:.---===------------------
----------:.@@#****************************+****++*#*@@ -======-----------------
----------.-@@#+*****####*****+********+===----==++*#%@-.======-----------------
---------- *@@%+***#*+++==---====++++++===+*#%@@@@@%##@# ======-----------------
--------== %@@@+**#+=+++++++**++++=++++#%%@@@@@@@%%@%#@@ -=====-----------------
---------- *@@@***+*@@@@@@@@@@@@@%#***#@@@@@@@@@@@@@@%%@..:--==-----------------
----------.:@@@****%%%%%%%%@@@@@@@@%##%@@@@@@%@@@%%@@@%@=.-::-=-----------------
----------: @@%***#%@@@@@@@@@@@@@%##**#%%%%%%#**##%##%%@@#%@+:=-----------------
----------- %@%*##@@@@##@@#*###*+***+=+**+==+*#%@%#=+%%%@@@@#.=-----------------
---------:. =@#*###%*+*####%*+==++++=--+++*+===++***#%%#%@@@.:------------------
--------.=*++%%*#*#%*-=*###+==+++*+++===+***+===+*###%%#%@@* -------------------
-------:=@@@%*%##*##%*++++==+=++***+=-=--+****+++**#%%%%%@@+ -------------------
--------:@@%@@%########****+++*#*=+-      -+*%%#*+*%%%%%@@@+ -------------------
--------: #@@@%#########*+++**##==++++++#%@@@%###*#%%%%%@@@-.-------=====-------
---------: *@@@@##%%%#%##*+**#**%@@@@@@@@@@%#+=++*#%%%%%@@@ :--------===--------
----------: @@%@%%%%%%%%%##***+=+**###%%#******#*+*#%%%%@+ :--------------------
-----------..@@@@@%%#%##%%#*+++###*+++++=+****+*%%##%%%%@+ ---------------------
------------..@@@%@%%#######*#%%++*#%%##*%@@@@@@@@@%#%%@@::---------------------
-------------..: .@@%%#######%%#@@@@@@@@@@@@@@@@@@@@%%%@# ----------------------
---------------::.+@@%%#####%%%@@%%#+++*+=-::--=%@@@@@@% :------------==--------
------------------ .@@@%##%%%%%%#+--:::-::-==+#@@@@@@@@*.------------====-------
-------------------: +@@@@%%%%@@@@@@%%%@@@@@@@@@@@@@@#*%::-----------===--------
--------------------:.*#@@@@@@@@@@@@@@@@@@%%%%#%@@@@*+*@-:-----------===--------
---------------------:**+#%@@@@@@@%***+=-===*#%%@@%****%=:----------====--------
------------------==-:-##**##%@@@@@%%%%%%##@@@@@@%*****%*.------------==--------
--=--------------===-.-*#%*###*#%@@@@@@@@@@@@@@@#*##***#%-:==---------=---------
--==------------==-::+#++%#**%%**##%%@@@@@@@@@@#*#%#****%%::--------------------
-===----------=--::-*#*++#@#**%%###%%###%%@%@@%**%#*****#%#.::::---=------------
-===------=--:::-=+#**+*#%%%%#*#%##%@@@@@%%%%%**####*****###*++=---=+++====-----
--==--==--::-=+*###**+*%%%%%###**#%%##*######****##%#*******#####%=  :-==+++=::-
--===+++-+*####******#%%%%%#####**##########**######%#***********%#         +#=-
++++=:.  @@#*******#%%%%#%%%%%%#**##*##*###***##%%%####**********%+          %@#
=:       :%@#################%%#**##########**##%%#####********#%@.           #%
           *@%#####*#*******#%%#**#####*####**##%%##**********##@+            -@
            =@%####***##***###%##*#####*####**##%##****#**+***#%+              @
             -%%****####***######*##########**#####***#####%@@@+               +
              .#@%##############***#########**##########%%@@@#:
               :#@@%%%###%###*****#########***###########%%#+.
                 -*###########******######********###*****=.
```

>*Carl "CJ" Johnson — rendered from his in-game portrait.*
A small Windows app that finishes the last few items of your *GTA
San Andreas: Definitive Edition* save so you can unlock the **100% completion**
achievement without replaying a long game.

Tick a checkbox, save, done.

## Download

Grab **`GTA-SA-DE-Save-Editor.exe`** from the
[latest release](https://github.com/Haddy18/sa-de-save-editor/releases/latest)
and double-click it — no installation, no dependencies.

## Related projects

Same family, other two games:

- [GTA III: Definitive Edition — 100% Save Editor](https://github.com/Haddy18/gta3-de-save-editor)
- [GTA Vice City: Definitive Edition — 100% Save Editor](https://github.com/Haddy18/vc-de-save-editor)

## How to use

1. **Back up your save.** It lives in
   `Documents\Rockstar Games\GTA San Andreas Definitive Edition\Profiles\<PROFILE>\GTASAsf1.sav`.
2. Open the app and press **Open .sav...**
3. Tick whatever your save is still missing: story missions, schools, races and challenges, gym lessons, courier and vehicle missions, stadium events, vehicle exports, safe houses and assets, gang tags, snapshots, horseshoes, oysters and unique stunt jumps.
4. The counters at the bottom update live: **Progress x/187** and
   **Missions x/100** are the real numbers the game uses for 100%.
5. Press **Save**. The save is written with a valid checksum, so the
   game loads it without complaining.

If the Rockstar launcher reports a cloud-sync conflict, pick **Local** —
that's normal for any edited save.

You can verify the result yourself by uploading the file to
[GTASnP](https://gtasnp.com) — everything should show green.

## Notes

- Works with any slot (`GTASAsf1.sav`, `GTASAsf2.sav`, …) and finds
  everything by structure, so it isn't tied to one specific playthrough.
- Single-player only. It edits your local save file; it does not touch
  online services. Still — always keep a backup.
- Missing a feature or found a bug? Open an issue.

## For developers

The whole editor is a single standard-library Python file:

```
python sa_save_editor.py            # GUI
python sa_save_editor.py --selftest # 27 checks against real saves
```

Releases are built automatically by GitHub Actions when a release is
published (PyInstaller, Windows).
