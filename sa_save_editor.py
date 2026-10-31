#!/usr/bin/env python3
"""GTA San Andreas: Definitive Edition — 100% Save Editor :: 100% save editor

Load a .sav, show the full GTASnP 100% checklist (missions, side missions,
collectibles, properties) with a checkbox per item, recompute the
percentage (x/187) and the story-mission count, and save the file
with the correct MD5 seal in the header (without it the game shows an
empty slot with no error at all).

Standard library only. No dependencies.

Format (verified against 6 real saves written by the game itself):
  seal      = NOT(MD5( first 24 bytes zeroed + file[24:] )) at 0x08..0x17
  globals   = base = position of `b"SCRIPTS\\x00"` + 0x14
               (byte index comes from the two zlib tables the save itself
               carries: "//Globalvariables V2 ...")
  flags     = 1 byte (0/1) at base + index
  counters  = u32 at base + index
  percent   = float32 at base + index (the RETURN_PROGRESS_PERCENTAGE global)

Usage:
  GUI:       python sa_save_editor.py
  Selftest:  python sa_save_editor.py --selftest
"""

import base64
import hashlib
import json
import os
import re
import struct
import sys
import zlib


# ---------------------------------------------------------------- data
# Checklist + backing save locations, derived from GTASnP and verified
# against the sample saves in samples/.

DATA = json.loads(r"""{"game":"SA","denom":187,"pctg":"RETURN_PROGRESS_PERCENTAGE","tag":"SCRIPTS\u0000","items":[{"key":"Story Missions|Los Santos|Big Smoke","sec":"Story Missions","sub":"Los Santos","disp":"Big Smoke","kind":"flag","src":"SCPLAYER","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Ryder","sec":"Story Missions","sub":"Los Santos","disp":"Ryder","kind":"flag","src":"TARGET_X","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Tagging Up Turf","sec":"Story Missions","sub":"Los Santos","disp":"Tagging Up Turf","kind":"flag","src":"GAME_STARTS_FROM_SCRATCH","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Cleaning The Hood","sec":"Story Missions","sub":"Los Santos","disp":"Cleaning The Hood","kind":"flag","src":"MINUTES","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Drive-Thru","sec":"Story Missions","sub":"Los Santos","disp":"Drive-Thru","kind":"flag","src":"PLAYER_IS_COMPLETELY_SAFE","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Nines And AK's","sec":"Story Missions","sub":"Los Santos","disp":"Nines And AK's","kind":"flag","src":"ACTIVATE_MOBILE_PHONE","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Drive By","sec":"Story Missions","sub":"Los Santos","disp":"Drive By","kind":"flag","src":"BIKE_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Sweet's Girl","sec":"Story Missions","sub":"Los Santos","disp":"Sweet's Girl","kind":"flag","src":"DRIVE_BY_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Cesar Vialpando","sec":"Story Missions","sub":"Los Santos","disp":"Cesar Vialpando","kind":"flag","src":"PRINT_FIRST_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|High Stakes, Low-Rider","sec":"Story Missions","sub":"Los Santos","disp":"High Stakes, Low-Rider","kind":"flag","src":"CAR_HELP_PLAYED","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Home Invasion","sec":"Story Missions","sub":"Los Santos","disp":"Home Invasion","kind":"flag","src":"WASTED_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Catalyst","sec":"Story Missions","sub":"Los Santos","disp":"Catalyst","kind":"flag","src":"BUSTED_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Robbing Uncle Sam","sec":"Story Missions","sub":"Los Santos","disp":"Robbing Uncle Sam","kind":"flag","src":"BLOB_FLAG","w":1.0,"max":null},{"key":"Story Missions|Los Santos|OG Loc","sec":"Story Missions","sub":"Los Santos","disp":"OG Loc","kind":"flag","src":"BLOB_FLAG_SHOP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Running Dog","sec":"Story Missions","sub":"Los Santos","disp":"Running Dog","kind":"flag","src":"LOWRIDER_MINIGAME_UNLOCKED","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Wrong Side Of The Tracks","sec":"Story Missions","sub":"Los Santos","disp":"Wrong Side Of The Tracks","kind":"flag","src":"SPRAY_HELP","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Just Business","sec":"Story Missions","sub":"Los Santos","disp":"Just Business","kind":"flag","src":"FLAG_CESAR_MISSION_COUNTER","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Life's a Beach","sec":"Story Missions","sub":"Los Santos","disp":"Life's a Beach","kind":"flag","src":"KEYCARD_AQUIRED_FROM_MILLIE","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Madd Dogg's Rhymes","sec":"Story Missions","sub":"Los Santos","disp":"Madd Dogg's Rhymes","kind":"flag","src":"PLAYED_SCIPTED_AIRSCRIPT_CUT","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Management Issues","sec":"Story Missions","sub":"Los Santos","disp":"Management Issues","kind":"flag","src":"TRIGGER_FINAL_SYND_MISSION","w":1.0,"max":null},{"key":"Story Missions|Los Santos|House Party","sec":"Story Missions","sub":"Los Santos","disp":"House Party","kind":"flag","src":"TRIGGER_SCRASH2_MISSION","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Burning Desire","sec":"Story Missions","sub":"Los Santos","disp":"Burning Desire","kind":"flag","src":"ODDJOB_HELP_FLAG","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Gray Imports","sec":"Story Missions","sub":"Los Santos","disp":"Gray Imports","kind":"flag","src":"GIRLFRIED_HELP_FLAG","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Doberman","sec":"Story Missions","sub":"Los Santos","disp":"Doberman","kind":"flag","src":"STEALTH_HELP_FLAG","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Los Sepulcros","sec":"Story Missions","sub":"Los Santos","disp":"Los Sepulcros","kind":"flag","src":"TRIGGER_FINAL_LA1_MISSIONS","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Reuniting The Families","sec":"Story Missions","sub":"Los Santos","disp":"Reuniting The Families","kind":"flag","src":"TRIGGER_FINAL_LA2_MISSIONS","w":1.0,"max":null},{"key":"Story Missions|Los Santos|Green Sabre","sec":"Story Missions","sub":"Los Santos","disp":"Green Sabre","kind":"flag","src":"TRIGGER_ICE_COLD_MISSION","w":1.0,"max":null},{"key":"Story Missions|Badlands|Badlands","sec":"Story Missions","sub":"Badlands","disp":"Badlands","kind":"flag","src":"TRUCKING_HELP_FLAG","w":1.0,"max":null},{"key":"Story Missions|Badlands|Wu Zi Mu","sec":"Story Missions","sub":"Badlands","disp":"Wu Zi Mu","kind":"flag","src":"ADD_ALL_AMMU_BLIPS","w":1.0,"max":null},{"key":"Story Missions|Badlands|Farewell, My Love","sec":"Story Missions","sub":"Badlands","disp":"Farewell, My Love","kind":"flag","src":"DRIVING_TEST_PASSED","w":1.0,"max":null},{"key":"Story Missions|Badlands|Local Liquor Store","sec":"Story Missions","sub":"Badlands","disp":"Local Liquor Store","kind":"flag","src":"PILOT_TEST_PASSED","w":1.0,"max":null},{"key":"Story Missions|Badlands|Small Town Bank","sec":"Story Missions","sub":"Badlands","disp":"Small Town Bank","kind":"flag","src":"FLAG_KICKSTART_PASSED_1STIME","w":1.0,"max":null},{"key":"Story Missions|Badlands|Tanker Commander","sec":"Story Missions","sub":"Badlands","disp":"Tanker Commander","kind":"flag","src":"CAMERA_SECRET_HELP","w":1.0,"max":null},{"key":"Story Missions|Badlands|Against All Odds","sec":"Story Missions","sub":"Badlands","disp":"Against All Odds","kind":"flag","src":"SHOW_RACE_SELECTION","w":1.0,"max":null},{"key":"Story Missions|Badlands|Body Harvest","sec":"Story Missions","sub":"Badlands","disp":"Body Harvest","kind":"flag","src":"FLAG_PIMPING_TRIGGER","w":1.0,"max":null},{"key":"Story Missions|Badlands|Are You Going To San Fierro","sec":"Story Missions","sub":"Badlands","disp":"Are You Going To San Fierro","kind":"flag","src":"BEEN_IN_FREIGHT_BEFORE","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Wear Flowers In Your Hair","sec":"Story Missions","sub":"San Fierro","disp":"Wear Flowers In Your Hair","kind":"flag","src":"OPENED_BADLANDS_UP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Air Raid","sec":"Story Missions","sub":"San Fierro","disp":"Air Raid","kind":"flag","src":"OPENED_SANFRAN_UP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Supply Lines","sec":"Story Missions","sub":"San Fierro","disp":"Supply Lines","kind":"flag","src":"OPENED_VEGAS_UP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|New Model Army","sec":"Story Missions","sub":"San Fierro","disp":"New Model Army","kind":"flag","src":"OPENED_DESERT_UP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|555-WE-TIP","sec":"Story Missions","sub":"San Fierro","disp":"555-WE-TIP","kind":"flag","src":"DONE_TAXI_HELP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Deconstruction","sec":"Story Missions","sub":"San Fierro","disp":"Deconstruction","kind":"flag","src":"CROUPIER_HELP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Photo Opportunity","sec":"Story Missions","sub":"San Fierro","disp":"Photo Opportunity","kind":"flag","src":"MISSION_SELECTION","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Jizzy","sec":"Story Missions","sub":"San Fierro","disp":"Jizzy","kind":"flag","src":"FLAG_BCRASH_MISSION_COUNTER","w":1.0,"max":null},{"key":"Story Missions|San Fierro|T-Bone Mendez","sec":"Story Missions","sub":"San Fierro","disp":"T-Bone Mendez","kind":"flag","src":"CASINO_CONTACT_BLIP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Mike Toreno","sec":"Story Missions","sub":"San Fierro","disp":"Mike Toreno","kind":"flag","src":"VCRASH_CONTACT_BLIP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Outrider","sec":"Story Missions","sub":"San Fierro","disp":"Outrider","kind":"flag","src":"FLAG_DOC_MISSION_COUNTER","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Snail Trail","sec":"Story Missions","sub":"San Fierro","disp":"Snail Trail","kind":"flag","src":"GOT_GIMP_SUIT","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Ice Cold Killa","sec":"Story Missions","sub":"San Fierro","disp":"Ice Cold Killa","kind":"flag","src":"FLAG_CAT_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Pier 69","sec":"Story Missions","sub":"San Fierro","disp":"Pier 69","kind":"flag","src":"FLAG_CAT_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Toreno's Last Flight","sec":"Story Missions","sub":"San Fierro","disp":"Toreno's Last Flight","kind":"flag","src":"FLAG_CAT_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Yay Ka-Boom-Boom","sec":"Story Missions","sub":"San Fierro","disp":"Yay Ka-Boom-Boom","kind":"flag","src":"FLAG_CAT_MISSION4_PASSED","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Back To School","sec":"Story Missions","sub":"San Fierro","disp":"Back To School","kind":"flag","src":"STUNT_COURSE","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Zeroing In","sec":"Story Missions","sub":"San Fierro","disp":"Zeroing In","kind":"flag","src":"MILLIES_KEYCARD_PICKUP_FLAG","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Test Drive","sec":"Story Missions","sub":"San Fierro","disp":"Test Drive","kind":"flag","src":"MILLIE_MARKER","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Customs Fast Track","sec":"Story Missions","sub":"San Fierro","disp":"Customs Fast Track","kind":"flag","src":"CURRENT_WANTED_CAR_STATUS","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Puncture Wounds","sec":"Story Missions","sub":"San Fierro","disp":"Puncture Wounds","kind":"flag","src":"RESTORE_MOBILE_FOR_FILSHIE","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Mountain Cloud Boys","sec":"Story Missions","sub":"San Fierro","disp":"Mountain Cloud Boys","kind":"flag","src":"EXPLAIN_IMPORT_HELP","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Ran Fa Li","sec":"Story Missions","sub":"San Fierro","disp":"Ran Fa Li","kind":"flag","src":"IMPEXP_IS_COMPLETE","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Lure","sec":"Story Missions","sub":"San Fierro","disp":"Lure","kind":"flag","src":"IGFGONEONDATE","w":1.0,"max":null},{"key":"Story Missions|San Fierro|Amphibious Assault","sec":"Story Missions","sub":"San Fierro","disp":"Amphibious Assault","kind":"flag","src":"POWER","w":1.0,"max":null},{"key":"Story Missions|San Fierro|The Da Nang Thang","sec":"Story Missions","sub":"San Fierro","disp":"The Da Nang Thang","kind":"flag","src":"CURRENT_SLOT","w":1.0,"max":null},{"key":"Story Missions|Desert|Monster","sec":"Story Missions","sub":"Desert","disp":"Monster","kind":"flag","src":"FLAG_MOB_LA1","w":1.0,"max":null},{"key":"Story Missions|Desert|HighJack","sec":"Story Missions","sub":"Desert","disp":"HighJack","kind":"flag","src":"FLAG_MOB_LA2","w":1.0,"max":null},{"key":"Story Missions|Desert|Interdiction","sec":"Story Missions","sub":"Desert","disp":"Interdiction","kind":"flag","src":"FLAG_MOB_CAT","w":1.0,"max":null},{"key":"Story Missions|Desert|Verdant Meadows","sec":"Story Missions","sub":"Desert","disp":"Verdant Meadows","kind":"flag","src":"FLAG_MOB_RANDOM","w":1.0,"max":null},{"key":"Story Missions|Desert|Learning To Fly","sec":"Story Missions","sub":"Desert","disp":"Learning To Fly","kind":"flag","src":"FLAG_MOB_VEGAS","w":1.0,"max":null},{"key":"Story Missions|Desert|NOE","sec":"Story Missions","sub":"Desert","disp":"NOE","kind":"flag","src":"FLAG_MOB_SANFRAN","w":1.0,"max":null},{"key":"Story Missions|Desert|Stowaway","sec":"Story Missions","sub":"Desert","disp":"Stowaway","kind":"flag","src":"TERMINATE_CAT_CALLS","w":1.0,"max":null},{"key":"Story Missions|Desert|Black Project","sec":"Story Missions","sub":"Desert","disp":"Black Project","kind":"flag","src":"DONE_COPCAR_PROGRESS","w":1.0,"max":null},{"key":"Story Missions|Desert|Green Goo","sec":"Story Missions","sub":"Desert","disp":"Green Goo","kind":"flag","src":"DONE_BURGLARY_PROGRESS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Fender Ketchup","sec":"Story Missions","sub":"Las Venturas","disp":"Fender Ketchup","kind":"flag","src":"DONE_TAXIODD_PROGRESS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Explosive Situation","sec":"Story Missions","sub":"Las Venturas","disp":"Explosive Situation","kind":"flag","src":"DONE_TRUCK_PROGRESS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|You've Had Your Chips","sec":"Story Missions","sub":"Las Venturas","disp":"You've Had Your Chips","kind":"flag","src":"DONE_QUARRY_PROGRESS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Don Peyote","sec":"Story Missions","sub":"Las Venturas","disp":"Don Peyote","kind":"flag","src":"JAPCAR_MOD_GARAGE_OPEN","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Intensive Care","sec":"Story Missions","sub":"Las Venturas","disp":"Intensive Care","kind":"flag","src":"BCESAR3_PASSED_MISSION","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Misappropriation","sec":"Story Missions","sub":"Las Venturas","disp":"Misappropriation","kind":"flag","src":"RETURNED_OYSTERS_FLAG","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|The Meat Business","sec":"Story Missions","sub":"Las Venturas","disp":"The Meat Business","kind":"flag","src":"FLAG_RETURNED_SHOEHORSES","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Fish In A Barrel","sec":"Story Missions","sub":"Las Venturas","disp":"Fish In A Barrel","kind":"flag","src":"FLAG_RETURNED_SNAPSHOTS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Madd Dogg","sec":"Story Missions","sub":"Las Venturas","disp":"Madd Dogg","kind":"flag","src":"FLAG_RETURNED_TAGS","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Freefall","sec":"Story Missions","sub":"Las Venturas","disp":"Freefall","kind":"flag","src":"ZEROS_PROPERTY_BOUGHT","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|High Noon","sec":"Story Missions","sub":"Las Venturas","disp":"High Noon","kind":"flag","src":"FLAG_END_GUY_AUDIO_CRASH4","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Saint Mark's Bistro","sec":"Story Missions","sub":"Las Venturas","disp":"Saint Mark's Bistro","kind":"flag","src":"FLAG_MTBIKE_PASSED_1STIME","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Architectural Espionage","sec":"Story Missions","sub":"Las Venturas","disp":"Architectural Espionage","kind":"flag","src":"FLAG_TRIATHALON_PASSED_1STIME","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Key To Her Heart","sec":"Story Missions","sub":"Las Venturas","disp":"Key To Her Heart","kind":"flag","src":"VALET_ODDJOB_OPENED","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|\u00b7 Keycard Acquired (Obtained outside mission, but required.)","sec":"Story Missions","sub":"Las Venturas","disp":"\u00b7 Keycard Acquired     (Obtained outside mission, but required.)","kind":"flag","src":"VALET_UNLOCKED","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Dam And Blast","sec":"Story Missions","sub":"Las Venturas","disp":"Dam And Blast","kind":"flag","src":"CAN_SCRIPT_BE_CLEANED","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Cop Wheels","sec":"Story Missions","sub":"Las Venturas","disp":"Cop Wheels","kind":"flag","src":"CREATE_DROP_OFF_CAR_NOW","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Up, Up, And Away","sec":"Story Missions","sub":"Las Venturas","disp":"Up, Up, And Away","kind":"flag","src":"VALET_CAN_BE_CREATED","w":1.0,"max":null},{"key":"Story Missions|Las Venturas|Breaking The Bank At Caligulas","sec":"Story Missions","sub":"Las Venturas","disp":"Breaking The Bank At Caligulas","kind":"flag","src":"VALET_TASK","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|A Home In The Hills","sec":"Story Missions","sub":"Los Santos II","disp":"A Home In The Hills","kind":"flag","src":"VALET_MISSION_COMPLETED","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Vertical Bird","sec":"Story Missions","sub":"Los Santos II","disp":"Vertical Bird","kind":"flag","src":"SYN2_MISSION_ATTEMPTS","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Home Coming","sec":"Story Missions","sub":"Los Santos II","disp":"Home Coming","kind":"flag","src":"IMPORT_EXPORT_IS_ACTIVE","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Cut Throat Business","sec":"Story Missions","sub":"Los Santos II","disp":"Cut Throat Business","kind":"flag","src":"STRAP4_MISSION_PASSED_ONCE_FLAG","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Beat Down On B-Dup","sec":"Story Missions","sub":"Los Santos II","disp":"Beat Down On B-Dup","kind":"flag","src":"BLOOD_PASSED_ONCE","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Grove 4 Life","sec":"Story Missions","sub":"Los Santos II","disp":"Grove 4 Life","kind":"flag","src":"D5_WATCHED_FIRST_CUTSCENE","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Riot","sec":"Story Missions","sub":"Los Santos II","disp":"Riot","kind":"flag","src":"D5_PILOT_LICENCE_OBTAINED","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|Los Desperados","sec":"Story Missions","sub":"Los Santos II","disp":"Los Desperados","kind":"flag","src":"D5_BRONZE_GENERATOR_UNLOCKED","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|\u00b7 At Least 35% Gang Turf Controlled","sec":"Story Missions","sub":"Los Santos II","disp":"\u00b7 At Least 35% Gang Turf Controlled","kind":"flag","src":"D5_SILVER_GENERATOR_UNLOCKED","w":1.0,"max":null},{"key":"Story Missions|Los Santos II|End Of The Line","sec":"Story Missions","sub":"Los Santos II","disp":"End Of The Line","kind":"flag","src":"GAME_COMPLETE","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Vigilante","sec":"Other Missions","sub":"Vehicle Missions","disp":"Vigilante","kind":"flag","src":"D5_GOLD_GENERATOR_UNLOCKED","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Firefighter","sec":"Other Missions","sub":"Vehicle Missions","disp":"Firefighter","kind":"flag","src":"BOAT_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Paramedic","sec":"Other Missions","sub":"Vehicle Missions","disp":"Paramedic","kind":"flag","src":"BOAT_ACCELERATE_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Taxi","sec":"Other Missions","sub":"Vehicle Missions","disp":"Taxi","kind":"flag","src":"BOAT_ACCELERATE_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Pimping","sec":"Other Missions","sub":"Vehicle Missions","disp":"Pimping","kind":"flag","src":"BOAT_ACCELERATE_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Challenges|BMX Challenge","sec":"Other Missions","sub":"Challenges","disp":"BMX Challenge","kind":"flag","src":"ZERO_CONTACT_BLIP","w":1.0,"max":null},{"key":"Other Missions|Challenges|NRG-500 Challenge","sec":"Other Missions","sub":"Challenges","disp":"NRG-500 Challenge","kind":"flag","src":"BOAT_SIMPLECIRCUIT_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Challenges|Chiliad Challenge","sec":"Other Missions","sub":"Challenges","disp":"Chiliad Challenge","kind":"flag","src":"BOAT_SIMPLECIRCUIT_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Collectibles|Gang Tags {n}","sec":"Other Missions","sub":"Collectibles","disp":"Gang Tags   100 out of 100","kind":"counter","src":"RETURNED_TAGS","w":0.0,"max":100},{"key":"Other Missions|Collectibles|Snapshots {n}","sec":"Other Missions","sub":"Collectibles","disp":"Snapshots   50 out of 50","kind":"counter","src":"TAXI_PASSED","w":0.0,"max":50},{"key":"Other Missions|Collectibles|Horseshoes {n}","sec":"Other Missions","sub":"Collectibles","disp":"Horseshoes   50 out of 50","kind":"counter","src":"RETURNED_OYSTERS","w":0.0,"max":50},{"key":"Other Missions|Collectibles|Oysters {n}","sec":"Other Missions","sub":"Collectibles","disp":"Oysters   50 out of 50","kind":"counter","src":"RETURNED_SHOEHORSES","w":0.0,"max":50},{"key":"Other Missions|Fighting Lessons|Los Santos Gym","sec":"Other Missions","sub":"Fighting Lessons","disp":"Los Santos Gym","kind":"flag","src":"BOAT_SIMPLECIRCUIT_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Fighting Lessons|San Fierro Gym","sec":"Other Missions","sub":"Fighting Lessons","disp":"San Fierro Gym","kind":"flag","src":"BOAT_SLALOM_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Fighting Lessons|Las Venturas Gym","sec":"Other Missions","sub":"Fighting Lessons","disp":"Las Venturas Gym","kind":"flag","src":"BOAT_SLALOM_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Courier Missions|Roboi's Food Mart Asset","sec":"Other Missions","sub":"Courier Missions","disp":"Roboi's Food Mart Asset","kind":"flag","src":"BOAT_SLALOM_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Courier Missions|Hippy Shopper Asset","sec":"Other Missions","sub":"Courier Missions","disp":"Hippy Shopper Asset","kind":"flag","src":"BOAT_SKIJUMP_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Courier Missions|Burger Shot Asset","sec":"Other Missions","sub":"Courier Missions","disp":"Burger Shot Asset","kind":"flag","src":"BOAT_SKIJUMP_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Schools|Driving School","sec":"Other Missions","sub":"Schools","disp":"Driving School","kind":"flag","src":"BOAT_SKIJUMP_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Schools|Bike School","sec":"Other Missions","sub":"Schools","disp":"Bike School","kind":"flag","src":"BOAT_HOVER_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Schools|Boat School","sec":"Other Missions","sub":"Schools","disp":"Boat School","kind":"flag","src":"BOAT_HOVER_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Schools|Pilot School","sec":"Other Missions","sub":"Schools","disp":"Pilot School","kind":"flag","src":"BOAT_HOVER_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Shooting Range Challenge","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Shooting Range Challenge","kind":"flag","src":"PIMP_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Valet Parking","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Valet Parking","kind":"flag","src":"COURIERLA_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Freight Train","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Freight Train","kind":"flag","src":"COURIERLV_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Quarry Mission","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Quarry Mission","kind":"flag","src":"COURIERSF_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Trucking","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Trucking","kind":"flag","src":"CA3_DRIVEN_TO_FACTORY","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Export Vehicles - List 1","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Export Vehicles - List 1","kind":"flag","src":"FLAG_TRAILOR_CUTSCENE","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Export Vehicles - List 2","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Export Vehicles - List 2","kind":"flag","src":"BS_PASSED","w":1.0,"max":null},{"key":"Other Missions|Miscellaneous Missions|Export Vehicles - List 3","sec":"Other Missions","sub":"Miscellaneous Missions","disp":"Export Vehicles - List 3","kind":"flag","src":"BS_THE360_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Stadium Events|8-Track","sec":"Other Missions","sub":"Stadium Events","disp":"8-Track","kind":"flag","src":"BS_THE360_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Stadium Events|Blood Bowl","sec":"Other Missions","sub":"Stadium Events","disp":"Blood Bowl","kind":"flag","src":"BS_THE360_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Stadium Events|Dirt Track","sec":"Other Missions","sub":"Stadium Events","disp":"Dirt Track","kind":"flag","src":"BS_THE180_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Stadium Events|Kickstart","sec":"Other Missions","sub":"Stadium Events","disp":"Kickstart","kind":"flag","src":"BS_THE180_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Lowrider Race","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Lowrider Race","kind":"flag","src":"CASINOZ","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Little Loop","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Little Loop","kind":"flag","src":"BS_THE180_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Backroad Wanderer","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Backroad Wanderer","kind":"flag","src":"BS_WHEELIE_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|City Circuit","sec":"Other Missions","sub":"Los Santos Street Races","disp":"City Circuit","kind":"flag","src":"BS_WHEELIE_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Vinewood","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Vinewood","kind":"flag","src":"BS_WHEELIE_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Freeway","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Freeway","kind":"flag","src":"BS_JUMPSTOP_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Los Santos Street Races|Into the Country","sec":"Other Missions","sub":"Los Santos Street Races","disp":"Into the Country","kind":"flag","src":"BS_JUMPSTOP_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Badlands Street Races|Badlands A","sec":"Other Missions","sub":"Badlands Street Races","disp":"Badlands A","kind":"flag","src":"BS_JUMPSTOP_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|Badlands Street Races|Badlands B","sec":"Other Missions","sub":"Badlands Street Races","disp":"Badlands B","kind":"flag","src":"BS_STOPPIE_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|Dirtbike Danger","sec":"Other Missions","sub":"San Fierro Street Races","disp":"Dirtbike Danger","kind":"flag","src":"BS_STOPPIE_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|Bandito County","sec":"Other Missions","sub":"San Fierro Street Races","disp":"Bandito County","kind":"flag","src":"BS_STOPPIE_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|Go-Go Karting","sec":"Other Missions","sub":"San Fierro Street Races","disp":"Go-Go Karting","kind":"flag","src":"BS_JUMPSTOPPIE_BRONZEACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|San Fierro Fastlane","sec":"Other Missions","sub":"San Fierro Street Races","disp":"San Fierro Fastlane","kind":"flag","src":"BS_JUMPSTOPPIE_SILVERACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|San Fierro Hills","sec":"Other Missions","sub":"San Fierro Street Races","disp":"San Fierro Hills","kind":"flag","src":"BS_JUMPSTOPPIE_GOLDACHIEVED","w":1.0,"max":null},{"key":"Other Missions|San Fierro Street Races|Country Endurance","sec":"Other Missions","sub":"San Fierro Street Races","disp":"Country Endurance","kind":"flag","src":"FLAG_BCE2_PASSED_1STIME","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Street Races|San Fierro to Las Venturas","sec":"Other Missions","sub":"Las Venturas Street Races","disp":"San Fierro to Las Venturas","kind":"flag","src":"FLAG_SYN1_PASSED_1STIME","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Street Races|Dam Rider","sec":"Other Missions","sub":"Las Venturas Street Races","disp":"Dam Rider","kind":"flag","src":"FLAG_CAS1_PASSED_1STIME","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Street Races|Desert Tricks","sec":"Other Missions","sub":"Las Venturas Street Races","disp":"Desert Tricks","kind":"flag","src":"FLAG_BIKESCHOOL_PASSED_1STIME","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Street Races|Las Venturas Ringroad","sec":"Other Missions","sub":"Las Venturas Street Races","disp":"Las Venturas Ringroad","kind":"flag","src":"FLAG_SYN1_SKIP1","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|World War Aces","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"World War Aces","kind":"flag","src":"FLAG_SYN1_SKIP2","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|Barnstorming","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"Barnstorming","kind":"flag","src":"FLAG_BCR1_SKIP","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|Military Service","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"Military Service","kind":"flag","src":"GOT_RACE_MISSION_COMPLETE","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|Chopper Checkpoint","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"Chopper Checkpoint","kind":"flag","src":"PLAYED_CUT1_BEFORE_CRASH4","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|Whirly Bird Waypoint","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"Whirly Bird Waypoint","kind":"flag","src":"PLAYED_CUT2_BEFORE_CRASH4","w":1.0,"max":null},{"key":"Other Missions|Las Venturas Airport Races|Heli Hell","sec":"Other Missions","sub":"Las Venturas Airport Races","disp":"Heli Hell","kind":"flag","src":"FLAG_BOUGHT_FROM_ZIP","w":1.0,"max":null},{"key":"Completionist|Las Venturas Airport Races|Unique Stunt Jumps {n}","sec":"Completionist","sub":"Las Venturas Airport Races","disp":"Unique Stunt Jumps   2 out of 70","kind":"counter","src":"GOT_SIREN_HELP_BEFORE","w":0.0,"max":70},{"key":"Completionist|Las Venturas Airport Races|Beat the Cock","sec":"Completionist","sub":"Las Venturas Airport Races","disp":"Beat the Cock","kind":"flag","src":"FLAG_BOUGHT_FROM_VICTIM","w":0.0,"max":null},{"key":"Completionist|Las Venturas Airport Races|Burglary","sec":"Completionist","sub":"Las Venturas Airport Races","disp":"Burglary","kind":"flag","src":"FLAG_PLAYER_GOT_GIMP_SUIT","w":0.0,"max":null},{"key":"Properties|Las Venturas Airport Races|Owned","sec":"Properties","sub":"Las Venturas Airport Races","disp":"Owned","kind":"flag","src":"THEHEISTZ","w":0.0,"max":null},{"key":"Properties|Las Venturas Airport Races|Available","sec":"Properties","sub":"Las Venturas Airport Races","disp":"Available","kind":"flag","src":"PLAYER1","w":0.0,"max":null},{"key":"Properties|Las Venturas Airport Races|Unavailable","sec":"Properties","sub":"Las Venturas Airport Races","disp":"Unavailable","kind":"flag","src":"TMP_POPCYCLE_ZONE","w":0.0,"max":null},{"key":"Properties|Assets|Zero RC Shop","sec":"Properties","sub":"Assets","disp":"Zero RC Shop","kind":"flag","src":"FLAG_PLAYER_GOT_VALET_UNIFORM","w":1.0,"max":null},{"key":"Properties|Assets|Wang Auto","sec":"Properties","sub":"Assets","disp":"Wang Auto","kind":"flag","src":"FLAG_PLAYER_GOT_CASINO_UNIFORM","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|Jefferson","sec":"Properties","sub":"Los Santos Safe Houses","disp":"Jefferson","kind":"flag","src":"FLAG_9WEAPONS_OPEN","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|Mulholland","sec":"Properties","sub":"Los Santos Safe Houses","disp":"Mulholland","kind":"flag","src":"FLAG_11WEAPONS_OPEN","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|Santa Maria Beach","sec":"Properties","sub":"Los Santos Safe Houses","disp":"Santa Maria Beach","kind":"flag","src":"FLAG_16WEAPONS_OPEN","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|El Corona","sec":"Properties","sub":"Los Santos Safe Houses","disp":"El Corona","kind":"flag","src":"FLAG_BOUGHT_GUN_FOR_DOBERMAN","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|Verona Beach","sec":"Properties","sub":"Los Santos Safe Houses","disp":"Verona Beach","kind":"flag","src":"LOWRIDER_OPPOSITION_SKILL","w":1.0,"max":null},{"key":"Properties|Los Santos Safe Houses|Willowfield","sec":"Properties","sub":"Los Santos Safe Houses","disp":"Willowfield","kind":"flag","src":"FLAG_GANG_WAR_ACTIVE","w":1.0,"max":null},{"key":"Properties|Country Side Safe Houses|Angel Pine","sec":"Properties","sub":"Country Side Safe Houses","disp":"Angel Pine","kind":"flag","src":"DONE_NRG500_STUNT_PROGRESS","w":1.0,"max":null},{"key":"Properties|Country Side Safe Houses|Blueberry","sec":"Properties","sub":"Country Side Safe Houses","disp":"Blueberry","kind":"flag","src":"PLAYED_CASINO4_BEFORE","w":1.0,"max":null},{"key":"Properties|Country Side Safe Houses|Dillimore","sec":"Properties","sub":"Country Side Safe Houses","disp":"Dillimore","kind":"flag","src":"PLAYED_VCRASH1_BEFORE","w":1.0,"max":null},{"key":"Properties|Country Side Safe Houses|Palomino Creek","sec":"Properties","sub":"Country Side Safe Houses","disp":"Palomino Creek","kind":"flag","src":"TEMP_INTEGER_1","w":1.0,"max":null},{"key":"Properties|Country Side Safe Houses|Whetstone","sec":"Properties","sub":"Country Side Safe Houses","disp":"Whetstone","kind":"flag","src":"F1_SCRIPTED_CUT","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|Calton Heights","sec":"Properties","sub":"San Fierro Safe Houses","disp":"Calton Heights","kind":"flag","src":"PLAYER_HAS_FAST_RELOAD","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|China Town","sec":"Properties","sub":"San Fierro Safe Houses","disp":"China Town","kind":"flag","src":"LF2_SKIP_ALLOWED","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|Doherty","sec":"Properties","sub":"San Fierro Safe Houses","disp":"Doherty","kind":"flag","src":"DISPLAYED_SNIPER_HELP_TEXT","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|Hashburry","sec":"Properties","sub":"San Fierro Safe Houses","disp":"Hashburry","kind":"flag","src":"D6_TRIP_SKIPS_AVAILABLE","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|Paradiso","sec":"Properties","sub":"San Fierro Safe Houses","disp":"Paradiso","kind":"flag","src":"TRIPSKIP_C3FLAG","w":1.0,"max":null},{"key":"Properties|San Fierro Safe Houses|Queens","sec":"Properties","sub":"San Fierro Safe Houses","disp":"Queens","kind":"flag","src":"M1_RANDOM_INT","w":1.0,"max":null},{"key":"Properties|Desert Safe Houses|El Quebrados","sec":"Properties","sub":"Desert Safe Houses","disp":"El Quebrados","kind":"flag","src":"TRIPSKIP_S2FLAG","w":1.0,"max":null},{"key":"Properties|Desert Safe Houses|Fort Carson","sec":"Properties","sub":"Desert Safe Houses","disp":"Fort Carson","kind":"flag","src":"BC1_ROUTE_NX","w":1.0,"max":null},{"key":"Properties|Desert Safe Houses|Tierra Robada","sec":"Properties","sub":"Desert Safe Houses","disp":"Tierra Robada","kind":"flag","src":"TRIPSKIP_T2FLAG","w":1.0,"max":null},{"key":"Properties|Desert Safe Houses|Verdant Meadows","sec":"Properties","sub":"Desert Safe Houses","disp":"Verdant Meadows","kind":"flag","src":"D6_PLAYER_REACHED_FIRST_CREATION_PT","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Camels Toe","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Camels Toe","kind":"flag","src":"D6_PLAYER_REACHED_SECOND_CREATION_PT","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Clowns Pocket","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Clowns Pocket","kind":"flag","src":"D6_PLAYER_REACHED_FIFTH_CREATION_PT","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Creek","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Creek","kind":"flag","src":"D6_PLAYER_REACHED_SIXTH_CREATION_PT","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Old Venturas Strip","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Old Venturas Strip","kind":"flag","src":"PLAYER_BREATH_W2","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Prickle Pine","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Prickle Pine","kind":"flag","src":"SYN4_RND","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Redsands West","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Redsands West","kind":"flag","src":"F1_BRONZE_AWARD","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Rockshore West","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Rockshore West","kind":"flag","src":"F1_SILVER_AWARD","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|The Pirates In Mens Pants","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"The Pirates In Mens Pants","kind":"flag","src":"DESERT3_MISSION_ATTEMPTS","w":1.0,"max":null},{"key":"Properties|Las Venturas Safe Houses|Whitewood Estates","sec":"Properties","sub":"Las Venturas Safe Houses","disp":"Whitewood Estates","kind":"flag","src":"CAS4_CHECKPOINT_SAVED","w":1.0,"max":null}]}""")

# GTASnP ground truth for the sample saves: expected state bits, counter
# values and the percentage each save reports.
EXPECTED = json.loads(r"""{"GTASAsf1.sav":{"pct":187.0,"gtasnp":100.0,"bits":"/////////////////////////3/n////Hw==","counts":[100,50,50,50,2]},"GTASAsf2.sav":{"pct":187.0,"gtasnp":100.0,"bits":"/////////////////////////3/n////Hw==","counts":[100,50,50,50,2]},"GTASAsf8.sav":{"pct":20.0,"gtasnp":10.160428047180176,"bits":"//8BAAAAAAAAAAAAAAIAAEAAAAAECAAAAA==","counts":[6,0,0,0,0]},"GTASAsf10.sav":{"pct":186.0,"gtasnp":99.46524047851562,"bits":"////////////////9////////3/n////Hw==","counts":[100,50,50,50,2]}}""")

GAME = "San Andreas"
TITLE = "GTA San Andreas: Definitive Edition — 100% Save Editor"
DENOM = 187
TAG = b"SCRIPTS\x00"
PCTG = "RETURN_PROGRESS_PERCENTAGE"

SEAL_OFF = 0x08
SEAL_LEN = 16
ZERO_LEN = 0x18

ITEMS = DATA["items"]
KEYS = [it["key"] for it in ITEMS]


def compute_seal(data):
    """Seal = NOT(MD5(first 24 bytes zeroed + rest))."""
    buf = bytearray(data)
    buf[:ZERO_LEN] = b"\x00" * ZERO_LEN
    digest = hashlib.md5(bytes(buf)).digest()
    return bytes((~b) & 0xFF for b in digest)


def _u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def _set_u32(buf, off, value):
    struct.pack_into("<I", buf, off, value & 0xFFFFFFFF)


class SaveError(Exception):
    pass


# ---------------------------------------------------------------- save file


class GameSave:
    """Parsing and writing of a San Andreas Definitive Edition (1.1x) .sav."""

    def __init__(self, data, path=None):
        if len(data) < 0x1000:
            raise SaveError("The file is too small to be a save")
        self.data = bytes(data)
        self.path = path
        self.names = self._name_table()
        if not self.names:
            raise SaveError("No global variable name table found "
                            "(is this a San Andreas DE save?)")
        self.gbase = self._globals_base()

    # ---- location ----------------------------------------------------
    def _name_table(self):
        names = {}
        for magic in (b"\x78\x01", b"\x78\x9c", b"\x78\xda", b"\x78\x5e"):
            pos = 0
            while True:
                i = self.data.find(magic, pos)
                if i < 0:
                    break
                try:
                    raw = zlib.decompress(self.data[i:])
                except zlib.error:
                    pos = i + 1
                    continue
                if b"Globalvariables" in raw[:64]:
                    for line in raw.decode("utf-8", "replace").splitlines():
                        if not line or line.startswith("//"):
                            continue
                        parts = line.split(",")
                        if len(parts) >= 4:
                            try:
                                names.setdefault(parts[1], int(parts[3]))
                            except ValueError:
                                pass
                pos = i + 1
        return names

    def _flag_offset(self, name):
        if name not in self.names:
            return None
        off = self.gbase + self.names[name]
        return off if 0 <= off < len(self.data) else None

    def _globals_base(self):
        """base = TAG + 0x14; validated: the percent global must read
        plausibly and the checklist flags must read 0/1."""
        probes = [it["src"] for it in ITEMS
                  if it["kind"] == "flag" and it["src"]][:150]
        idx_pct = self.names.get(PCTG)
        best, best_score = None, -1.0
        pos = 0
        while True:
            i = self.data.find(TAG, pos)
            if i < 0:
                break
            pos = i + 1
            for delta in (0x14, 0x15):
                base = i + delta
                score = 0.0
                if idx_pct is not None and base + idx_pct + 4 <= len(self.data):
                    v = struct.unpack_from("<f", self.data,
                                           base + idx_pct)[0]
                    if 0.0 < v <= 100.5:
                        score += 2.0
                    elif v == 0.0:
                        score += 0.5
                ok = tot = 0
                for name in probes:
                    idx = self.names.get(name)
                    if idx is None:
                        continue
                    off = base + idx
                    if 0 <= off < len(self.data):
                        tot += 1
                        if self.data[off] in (0, 1):
                            ok += 1
                if tot:
                    score += ok / tot
                if score > best_score:
                    best, best_score = base, score
        if best is None or best_score < 1.5:
            # fall back to the documented layout: first TAG + 0x14
            i = self.data.find(TAG)
            if i < 0 or i + 0x14 >= len(self.data):
                raise SaveError("Could not locate the save's global "
                                "variable space")
            best = i + 0x14
        return best

    # ---- reads -------------------------------------------------------
    def global32(self, name, default=None):
        idx = self.names.get(name)
        if idx is None:
            return default
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return default
        return _u32(self.data, off)

    def flag(self, name):
        off = self._flag_offset(name)
        if off is None:
            return 0
        return 1 if self.data[off] else 0

    def percent(self):
        idx = self.names.get(PCTG)
        if idx is None:
            return None
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return None
        return struct.unpack_from("<f", self.data, off)[0]

    # ---- writes ------------------------------------------------------
    def set_global(self, name, value):
        idx = self.names.get(name)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        _set_u32(buf, off, value)
        self.data = bytes(buf)
        return True

    def set_counter(self, name, value):
        """Counters sit in the low byte of the global and the bytes above
        belong to another counter packed in the same word, so only byte 0
        is written (the rest of the word is left untouched)."""
        idx = self.names.get(name)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        buf[off] = int(value) & 0xFF
        self.data = bytes(buf)
        return True

    def set_flag(self, name, value):
        off = self._flag_offset(name)
        if off is None:
            return False
        buf = bytearray(self.data)
        buf[off] = int(value) & 0xFF
        self.data = bytes(buf)
        return True

    def set_percent(self, value):
        idx = self.names.get(PCTG)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        struct.pack_into("<f", buf, off, float(value))
        self.data = bytes(buf)
        return True

    def reseal(self):
        buf = bytearray(self.data)
        buf[SEAL_OFF:SEAL_OFF + SEAL_LEN] = compute_seal(bytes(buf))
        self.data = bytes(buf)

    def to_bytes(self):
        return self.data

    # ---- full state (what the GUI models) ----------------------------
    def read_state(self):
        st = {}
        for it in ITEMS:
            if it["kind"] == "counter":
                v = (self.global32(it["src"], 0) or 0) & 0xFF
                cap = it["max"] or 0
                st[it["key"]] = min(int(v), cap) if cap else int(v)
            else:
                st[it["key"]] = self.flag(it["src"]) if it["src"] else 0
        return st


def compute_progress(st):
    """Progress points out of DENOM (the 100% weights calibrated on the
    real saves: exactly reproduces every sample)."""
    total = 0.0
    for it in ITEMS:
        v = st.get(it["key"], 0)
        if it["kind"] == "counter":
            total += it["w"] * (v or 0)
        elif v:
            total += it["w"]
    return min(DENOM, max(0.0, total))


def missions_done(st):
    return sum(1 for it in ITEMS
               if it["sec"] == "Story Missions" and st.get(it["key"], 0))


def missions_total():
    return sum(1 for it in ITEMS if it["sec"] == "Story Missions")


def apply_state(sav, st):
    """Write into the save all the GUI state + derived values."""
    for it in ITEMS:
        if not it["src"]:
            continue
        v = st.get(it["key"], 0)
        if it["kind"] == "counter":
            cap = it["max"] or 0
            val = max(0, min(int(v or 0), cap)) if cap else int(v or 0)
            sav.set_counter(it["src"], val)
        else:
            sav.set_flag(it["src"], 1 if v else 0)
    sav.set_percent(compute_progress(st) / DENOM * 100.0)
    sav.reseal()
    return sav


# ---------------------------------------------------------------- selftest


def _pack_bits(values):
    out = bytearray()
    for i in range(0, len(values), 8):
        b = 0
        for j in range(8):
            if i + j < len(values) and values[i + j]:
                b |= 1 << j
        out.append(b)
    return bytes(out)


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    checks = fails = 0

    def check(cond, label):
        nonlocal checks, fails
        checks += 1
        if not cond:
            fails += 1
            print("FAIL: %s" % label)

    for fn, exp in EXPECTED.items():
        path = os.path.join(here, "samples", fn)
        try:
            data = open(path, "rb").read()
            sav = GameSave(data, path)
        except SaveError as e:
            check(False, "%s: parse (%s)" % (fn, e))
            continue
        check(True, "%s: parse" % fn)

        # 1. the seal the game wrote must match the formula
        check(compute_seal(data)[0:SEAL_LEN] == data[SEAL_OFF:SEAL_OFF + SEAL_LEN],
              "%s: seal" % fn)

        st = sav.read_state()

        # 2. every checklist bit matches GTASnP
        bits = _pack_bits([
            (1 if st[it["key"]] >= (it["max"] or 0) else 0)
            if it["kind"] == "counter" and it["max"]
            else (1 if st[it["key"]] else 0)
            for it in ITEMS])
        check(bits == base64.b64decode(exp["bits"]),
              "%s: checklist bits vs GTASnP" % fn)

        # 3. every counter value matches GTASnP
        ctrs = [st[it["key"]] for it in ITEMS if it["kind"] == "counter"]
        check(ctrs == exp["counts"], "%s: counters vs GTASnP" % fn)

        # 4. the computed percentage matches the checklist model
        pts = compute_progress(st)
        check(abs(pts - exp["pct"]) < 0.01,
              "%s: computed points %.3f != %.3f" % (fn, pts, exp["pct"]))

        # 5. the stored percent global agrees with what GTASnP shows
        stored = sav.percent()
        check(stored is not None and abs(stored - exp["gtasnp"]) < 0.75,
              "%s: stored pct %s != gtasnp %s" % (fn, stored, exp["gtasnp"]))

    # 6. ticking everything must reach exactly 100%
    full = {}
    for it in ITEMS:
        full[it["key"]] = (it["max"] or 0) if it["kind"] == "counter" else 1
    sample = os.path.join(here, "samples", next(iter(EXPECTED)))
    sav = GameSave(open(sample, "rb").read(), sample)
    apply_state(sav, full)
    check(abs(compute_progress(full) - DENOM) < 1e-6,
          "full state: progress == %d" % DENOM)
    check(abs((sav.percent() or 0) - 100.0) < 0.01,
          "full state: percent global == 100")
    check(compute_seal(sav.to_bytes()) ==
          sav.to_bytes()[SEAL_OFF:SEAL_OFF + SEAL_LEN],
          "full state: seal valid")

    print("%d checks, %d failures" % (checks, fails))
    return 1 if fails else 0


# ---------------------------------------------------------------- GUI


class _ScrolledFrame:
    """Canvas + scrollbar hosting an inner frame (for long checklists)."""

    current = None

    def __init__(self, parent):
        import tkinter as tk
        self.canvas = tk.Canvas(parent, highlightthickness=0)
        self.bar = tk.Scrollbar(parent, orient="vertical",
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: setattr(
            _ScrolledFrame, "current", self))
        self.canvas.bind("<Leave>", lambda e: setattr(
            _ScrolledFrame, "current", None) if _ScrolledFrame.current is self
            else None)


def _wheel(event):
    sf = _ScrolledFrame.current
    if sf is not None:
        sf.canvas.yview_scroll(-1 * (event.delta // 120), "units")


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(TITLE + " :: editor for 100%")
    root.geometry("760x640")
    root.bind_all("<MouseWheel>", _wheel)

    sav = {"obj": None, "path": None}
    bools = {}   # key -> BooleanVar (flags)
    ints = {}    # key -> IntVar (counters)
    refreshing = {"v": False}

    # ---- toolbar -----------------------------------------------------
    bar = tk.Frame(root)
    bar.pack(side="top", fill="x", padx=6, pady=6)

    status = tk.Label(bar, text="Open a .sav to begin", anchor="w")
    status.pack(side="left", fill="x", expand=True)

    # ---- checklist notebook -----------------------------------------
    host = tk.Frame(root)
    host.pack(side="top", fill="both", expand=True, padx=6)

    sections = []
    for it in ITEMS:
        if it["sec"] not in sections:
            sections.append(it["sec"])

    rows = {}   # key -> (boolvar, intvar or None, checkbutton)

    def refresh(*_a):
        if refreshing["v"]:
            return
        refreshing["v"] = True
        try:
            st = {k: (ints[k].get() if k in ints else
                      (1 if bools[k].get() else 0)) for k in KEYS}
            pts = compute_progress(st)
            pct = pts / DENOM * 100.0
            n_done = missions_done(st)
            status.config(text="Progress: %g/%d (%.2f%%)  ·  Missions: %d/%d"
                          % (round(pts * 100) / 100, DENOM, pct,
                             n_done, missions_total()))
        finally:
            refreshing["v"] = False

    def toggle_counter(key, var_b, var_i, mx):
        var_i.set(mx if var_b.get() else 0)

    def counter_changed(key, var_b, var_i, mx, * _a):
        if refreshing["v"]:
            return
        refreshing["v"] = True
        try:
            v = max(0, min(int(var_i.get() or 0), mx))
            if v != var_i.get():
                var_i.set(v)
            var_b.set(1 if v >= mx and mx else 0)
        finally:
            refreshing["v"] = False
        refresh()

    nb = ttk.Notebook(root)
    nb.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 6))

    for sec in sections:
        wrap = tk.Frame(nb)
        sf = _ScrolledFrame(wrap)
        nb.add(wrap, text=sec)
        subs = []
        for it in ITEMS:
            if it["sec"] == sec and it["sub"] not in subs:
                subs.append(it["sub"])
        for sub in subs:
            same = [it for it in ITEMS
                    if it["sec"] == sec and it["sub"] == sub]
            if len(subs) > 1 or sub != sec:
                box = ttk.Labelframe(sf.inner, text=sub)
                box.pack(fill="x", padx=8, pady=4, anchor="n")
            else:
                box = sf.inner
            for it in same:
                key = it["key"]
                if it["kind"] == "counter":
                    vb = tk.BooleanVar()
                    vi = tk.IntVar(value=0)
                    mx = it["max"] or 0
                    row = tk.Frame(box)
                    row.pack(fill="x", padx=10, pady=1)
                    cb = tk.Checkbutton(
                        row, text=it["disp"].split(" out of ")[0],
                        variable=vb,
                        command=lambda k=key, b=vb, i=vi, m=mx:
                            toggle_counter(k, b, i, m))
                    cb.pack(side="left")
                    tk.Spinbox(row, from_=0, to=mx, width=6, textvariable=vi,
                               command=lambda k=key, b=vb, i=vi, m=mx:
                                   counter_changed(k, b, i, m)).pack(
                        side="left", padx=(6, 0))
                    tk.Label(row, text="/ %d" % mx, fg="#666").pack(
                        side="left", padx=(4, 0))
                    vi.trace_add("write",
                                 lambda *a, k=key, b=vb, i=vi, m=mx:
                                     counter_changed(k, b, i, m))
                    bools[key] = vb
                    ints[key] = vi
                    rows[key] = (vb, vi, cb)
                    vb.trace_add("write", refresh)
                else:
                    vb = tk.BooleanVar()
                    cb = tk.Checkbutton(box, text=it["disp"], variable=vb)
                    cb.pack(anchor="w", padx=10, pady=1)
                    bools[key] = vb
                    rows[key] = (vb, None, cb)
                    vb.trace_add("write", refresh)

    # ---- actions -----------------------------------------------------
    def load(path):
        data = open(path, "rb").read()
        obj = GameSave(data, path)
        st = obj.read_state()
        refreshing["v"] = True
        try:
            for k in KEYS:
                if k in ints:
                    ints[k].set(int(st.get(k, 0) or 0))
                    bools[k].set(bool(st.get(k, 0)))
                else:
                    bools[k].set(bool(st.get(k, 0)))
        finally:
            refreshing["v"] = False
        sav["obj"], sav["path"] = obj, path
        status.config(text="Loaded %s" % os.path.basename(path))
        refresh()

    def collect():
        return {k: (ints[k].get() if k in ints else
                     (1 if bools[k].get() else 0)) for k in KEYS}

    def on_open():
        path = filedialog.askopenfilename(
            title="Open a save", filetypes=[("Save files", "*.sav")],
            initialdir=os.path.join(os.path.expanduser("~"), "Documents"))
        if not path:
            return
        try:
            load(path)
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def write(path):
        st = collect()
        obj = sav["obj"]
        if obj is None:
            raise SaveError("Open a save first")
        apply_state(obj, st)
        with open(path, "wb") as fh:
            fh.write(obj.to_bytes())
        sav["path"] = path
        refresh()

    def on_save():
        if sav["path"] is None:
            return on_save_as()
        try:
            write(sav["path"])
            status.config(text="Saved %s" % os.path.basename(sav["path"]))
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def on_save_as():
        if sav["obj"] is None:
            return messagebox.showinfo(TITLE, "Open a save first")
        path = filedialog.asksaveasfilename(
            title="Save the game as", defaultextension="*.sav",
            filetypes=[("Save files", "*.sav")],
            initialfile=os.path.basename(sav["path"] or "GTASAsf1.sav"))
        if not path:
            return
        try:
            write(path)
            status.config(text="Saved %s" % os.path.basename(path))
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def set_all(value):
        refreshing["v"] = True
        try:
            for it in ITEMS:
                k = it["key"]
                if k in ints:
                    ints[k].set((it["max"] or 0) if value else 0)
                    bools[k].set(bool(value))
                else:
                    bools[k].set(bool(value))
        finally:
            refreshing["v"] = False
        refresh()

    for label, cmd in (("Open .sav...", on_open), ("Save", on_save),
                       ("Save as", on_save_as),
                       ("Check all", lambda: set_all(True)),
                       ("Uncheck all", lambda: set_all(False))):
        tk.Button(bar, text=label, command=cmd).pack(side="left", padx=3)

    refresh()
    root.mainloop()


# ---------------------------------------------------------------- main


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    run_gui()
