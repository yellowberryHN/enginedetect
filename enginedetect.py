# enginedetect.py - a dirty hacky script to detect game engines
# By Yellowberry
# https://github.com/YellowberryHN/enginedetect

import os, sys, mmap, struct, array, json, zipfile, argparse, platform, gc

args = {"engine": "", "dir": "", "game": "", "verbose": 0}
if __name__=="__main__":

	if platform.system() != "Windows":
		print("WARNING: This script is currently only designed for a Windows environment and Windows games! You may run into issues.")
		input("Press ENTER to run anyway!")

	parser = argparse.ArgumentParser()
	parser.add_argument("-e", metavar="ENGINE", help="filter specific game engines")
	parser.add_argument("-d", metavar="DIR", help="specifies directory to scan, defaults to working directory")
	parser.add_argument("-g", metavar="GAME", help="scan directory GAME inside of DIR as a game")
	parser.add_argument("-v", help="display verbose info", action="count")
	arg = parser.parse_args()
	args = {
		"engine": arg.e if arg.e else "",
		"dir": arg.d if arg.d else "",
		"game": arg.g if arg.g else "",
		"verbose": arg.v if arg.v else 0
	}

engineDict = {} # Used for counting games
gameDir = []

filterEngine = args["engine"] # Engine to filter results

def incDict(name):
	if not name in engineDict.keys():
		engineDict[name] = 0
	engineDict[name] += 1

def in_list(string, sList=None): # return all string in list that match
	if not sList: sList = gameDir
	return [i for i in sList if i.lower() == string.lower()]

def in_list_starts(string, sList=None): # return all string in list that match
	if not sList: sList = gameDir
	return [i for i in sList if i.lower().startswith(string.lower())]

def in_list_ends(string, sList=None):
	if not sList: sList = gameDir
	return [i for i in sList if i.lower().endswith(string.lower())]

def pj(*args): # path join
	return "/".join(list(args))

def dotClean(gameDir):
	if any(in_list_starts(".")):
		for x in in_list_starts("."):
			gameDir.remove(x)
	return gameDir

def recurseDir(dirName, gameDir): # recurses through directories to find one that actually has stuff in it.
	gameDir = dotClean(gameDir)
	i = 0
	while len(gameDir) < 2:
		if i == 5 or len(gameDir) < 1:
			return (dirName, gameDir)
		if len(gameDir) == 1 and os.path.isdir(pj(dirName,gameDir[0])):
			dirName = pj(dirName,gameDir[0])
			gameDir = dotClean(os.listdir(dirName)) # If directory only has one folder, assume game data is in here.
		i += 1

	return (dirName, gameDir)

# Game detection
def detectGame(dirName, fastParse=False):
	# fastParse: Parse extremely quickly, just based on files and folders (highly discouraged)

	global gameDir
	gameName = dirName
	dirName = pj(args["dir"],dirName) if args["dir"] else dirName
	gameDir = os.listdir(dirName)
	engineType = "Unknown"
	engineSet = False # Used for engines which might trigger multiple detections
	subGames = [] # Used for GoldSrc
	
	dirName, gameDir = recurseDir(dirName, gameDir)

	if any(in_list("application_info.json")):
		dirName = pj(dirName,"content")
		gameDir = os.listdir(dirName) # Discord Games

	if len(gameDir) < 1:
		return

	if any(in_list("game.pak")):
		ver_num = [0, 0]
		with open(pj(dirName,"game.pak"), "rb") as file:
			file.read(8) # skip things we don't know
			old_ind = 133 # hardcoded beginning
			while True:
				begin_ind = file.read(1)[0]
				if begin_ind - 1 != old_ind:
					old_ind = begin_ind
					break
				file.read(2)
				old_ind = begin_ind
				file.read(1) # go away 00
			if old_ind == 8:
				file.read(7) # we don't need the other shit
				# Check pak version number
				ver_num[0] = int(struct.unpack("<H",file.read(2))[0]/16)
				file.read(2)
				ver_num[1] = int(struct.unpack("<H",file.read(2))[0]/16)
				file.read(2)
				if ver_num[0] == ver_num[1]:
					engineType = "Raycasting Game Maker"
					if   ver_num[0] == 25: engineType += " 4"
					elif ver_num[0] == 31: engineType += " 5"
			file.close()

	elif any(in_list_starts("data.")):
		if any(in_list("Data.wolf")):
			engineType = "WOLF RPG Editor"
		else:
			dataFiles = [in_list_starts("data.")]
			for g in dataFiles:
				with open(pj(dirName,g[0]),"rb") as fi:
					if fi.read(4) == b'FORM':
						engineType = "GameMaker Studio"
					fi.close()

	elif any(in_list("Common.dll")):
		with open(pj(dirName,"Common.dll"), "r+b") as f:
			mmw = mmap.mmap(f.fileno(), 0)
			f.close()
		if mmw.find('Visual RPG Studio'.encode('utf-16be')) > 0:
			engineType = "Visual RPG Studio"

	elif any(in_list("libpanda.dll")):
		engineType = "Panda3D"
		engineSet = True

	elif any(in_list_ends(".RPG")):
		dataFiles = [in_list_ends(".RPG")]
		for g in dataFiles:
			with open(pj(dirName,g[0]),"rb") as fi:
				if fi.read(12) == b'RPG Maker 95':
					engineType = "RPG Maker 95"
				fi.close()

	elif any(in_list_ends(".rpf")):
		engineType = "RAGE"

	elif any(in_list_ends(".pck")):
		engineType = "Godot"

	elif any(in_list_ends(".grp")):
		engineType = "Build Engine"
	
	elif any(in_list("nw.pak")):
		if any(in_list("package.nw")) and zipfile.is_zipfile(pj(dirName,"package.nw")):
			with zipfile.ZipFile("package.nw","r") as nwpak:
				if any(in_list("data.json",nwpak.namelist())):
					engineType = "Construct 3"
				else:
					engineType = "Construct 2"
		try:
			with open(pj(dirName,"package.json"), "r") as file:
				jn = json.load(file)
			if jn["name"] == "KADOKAWA/RPGMV":
				engineType = "RPG Maker MV"
			else:
				engineType = "nw.js"
		except:
			engineType = "nw.js"

	elif any(in_list("resources.pak")):
		try:
			with open(pj(dirName,"package.json"), "r") as file:
				jn = json.load(file)
			if jn["name"] == "rmmz-game":
				engineType = "RPG Maker MZ"
			else:
				engineType = "nw.js"
		except:
			engineType = "nw.js"

	elif any(in_list("renpy")):
		engineType = "Ren'Py"
		engineSet = True

	elif any(in_list("q1")):
		# I should check for .pak files, but some only have the folder as compat
		engineType = "id Tech 2 [Quake]"

	elif any(in_list("baseq2")):
		# I should check for .pak files, but some only have the folder as compat
		engineType = "id Tech 2 [Quake 2]"

	elif any(in_list("baseq3")):
		# I should check for .pak files, but some only have the folder as compat
		engineType = "id Tech 3 [Quake 3]"

	elif any(in_list("3DRad_res")):
		engineType = "3D Rad"

	elif any(in_list("Program")) and any(in_list("Songs")):
		engineType = "StepMania"

	elif any(in_list("Adobe AIR")):
		if any(in_list_ends(".swf")): # that's a pretty fucking bold assumption, fix this later.
			engineType = "Adobe AIR"

	elif any(in_list("packages")) and os.path.isdir(pj(dirName,"packages")):
		if any(in_list("textures",os.listdir(pj(dirName,"packages")))) and os.path.isdir(pj(dirName,"packages","textures")):
			if any(in_list("notexture.png",os.listdir(pj(dirName,"packages","textures")))):
				engineType = "Cube 2"

	elif any(in_list("Engine")) and os.path.isdir(pj(dirName,"Engine")):
		if any(in_list("Binaries", os.listdir(pj(dirName,"Engine")))) or any(in_list("Config", os.listdir(pj(dirName,"Engine")))):
			engineType = "Unreal Engine 4"

	elif any(in_list_starts("Data")):
		eee = in_list_starts("Data")[0]
		if os.path.isdir(pj(dirName,eee)):
			dataDir = os.listdir(pj(dirName,eee))
			if any(in_list_ends(".rxdata",dataDir)):
				engineType = "RPG Maker XP"
			if any(in_list_ends(".esm",dataDir)):
				engineType = "Creation Engine [GameBryo]"

	exeList = in_list_ends(".exe")
	dirList = [i for i in gameDir if os.path.isdir(pj(dirName,i))]

	# Dirty hack to sort the exes by filesize, since games usually have higher byte count exes than their launchers
	# not superhot tho... stupid dumb idiot balls.
	if len(exeList) > 1:
		exeSize = []
		for exe in exeList:
			size = os.path.getsize(pj(dirName,exe))
			exeSize.append((size, exe))
		exeSize.sort(key=lambda s: s[0])
		exeSize.reverse()
		exeList.clear()
		for pair in exeSize:
			exeList.append(pair[1])

	detectExe = ""

	for g in dirList:
		if any(in_list_ends(".vpk",os.listdir(pj(dirName,g)))):
			engineType = "Source Engine"

	if not (fastParse and engineType=="Unknown") and engineType=="Unknown": # If fast mode, only run deep scan when we haven't found another engine
		for exe in exeList:
			exeName = exe[:-4]
			exeType = None
			exeArch = None
			if exeName == "dosbox":
				engineType = "DOSbox"
				detectExe = exe
				continue

			elif exeName.startswith("UnityCrashHandler") or "unins" in exeName.lower():
				continue

			elif any(in_list(exeName+".rgss2a")) or any(in_list(exeName+".rvproj")):
				engineType = "RPG Maker VX"
				detectExe = exe
				continue

			elif any(in_list(exeName+".rgss3a")) or any(in_list(exeName+".rvproj2")):
				engineType = "RPG Maker VX Ace"
				detectExe = exe
				continue

			elif exeName.startswith("th") and any(i for i in gameDir if (i.lower().endswith(".dat") and i.lower().startswith(exeName))):
				engineType = "Touhou"
				detectExe = exe
				continue

			elif any(in_list(exeName+"_Data")):
				engineType = "Unity"
				detectExe = exe
				continue

			elif exeName == "hl": # hardcoding is bad
				engineType = "GoldSrc"
				detectExe = exe
				
				for g in dirList:
					if any(in_list("dlls", os.listdir(pj(dirName,g)))):
						subGames.append(g)
						if not args["game"]: incDict(engineType)
				continue

			# slow shit beyond this point
			else:
				try:
					with open(pj(dirName,exe), "r+b") as f:
						mm = mmap.mmap(f.fileno(), 0)
						f.close() # not really needed, makes me feel better.
					if mm.find(b'Microsoft.Xna.Framework')>0:
						engineType = "XNA"
						detectExe = exe
						continue
					elif mm.find('Pixel Game Maker MV'.encode('utf-16be'))>0:
						engineType = "Pixel Game Maker MV"
						detectExe = exe
						continue
					elif mm.find('Clickteam Fusion'.encode('utf-16be'))>0:
						engineType = "Clickteam Fusion 2.5"
						detectExe = exe
						continue
					elif mm.find('Multimedia Fusion'.encode('utf-16be'))>0:
						engineType = "Multimedia Fusion 2"
						detectExe = exe
						continue
					elif mm.find('FPSC'.encode('utf-16be'))>0:
						engineType = "FPS Creator"
						detectExe = exe
						continue
					elif mm.find('Game Guru'.encode('utf-16be'))>0:
						engineType = "GameGuru"
						detectExe = exe
						continue
					elif mm.find('Godot'.encode('utf-16be'))>0:
						engineType = "Godot"
						detectExe = exe
						continue
					elif mm.find('ZeroEngine'.encode('utf-16be'))>0:
						engineType = "ZeroEngine"
						detectExe = exe
						continue
					elif mm.find('RPG Maker 95'.encode('utf-16be'))>0:
						engineType = "RPG Maker 95"
						detectExe = exe
						continue
					elif mm.find('RPG Maker 2000'.encode('utf-16be'))>0:
						engineType = "RPG Maker 2000"
						detectExe = exe
						continue
					elif mm.find('RPG Maker 2003'.encode('utf-16be'))>0:
						engineType = "RPG Maker 2003"
						detectExe = exe
						continue
					elif mm.find(b'RPG Paper Maker')>0:
						engineType = "RPG Paper Maker"
						detectExe = exe
						continue
					elif mm.find(b':heGame')>0:
						engineType = "Hacker Evolution"
						detectExe = exe
						continue
					elif mm.find(b'hedGame:')>0:
						engineType = "Hacker Evolution: Duality"
						detectExe = exe
						continue
					elif mm.find(b'@Sexy@')>0:
						engineType = "Sexy"
						detectExe = exe
						continue
					elif mm.find(b'gamemaker')>0 and engineType != "GameMaker Studio":
						engineType = "GameMaker Legacy"
						detectExe = exe
						continue
					elif mm.find(b'pygame')>0:
						engineType = "PyGame"
						detectExe = exe
						continue
					elif mm.find(b'\x00python')>0 and not engineSet:
						engineType = "PyGame"
						detectExe = exe
						continue
					elif mm.find(b'HaxeFlixel')>0:
						engineType = "HaxeFlixel"
						detectExe = exe
						continue
					elif mm.find('electron.app'.encode('utf-16be'))>0:
						engineType = "Electron [Web App]" # TODO: Detect CEF icudtl.dat
						detectExe = exe
						continue
					elif zipfile.is_zipfile(pj(dirName,exe)):
						with zipfile.ZipFile(pj(dirName,exe), 'r') as exeZip:
							if any(in_list("main.lua",exeZip.namelist())):
								engineType = "LOVE"
							elif any(in_list("gdx.dll",exeZip.namelist())) or any(in_list("gdx64.dll",exeZip.namelist())):
								engineType = "libGDX"
							elif any(in_list("META-INF",exeZip.namelist())):
								exeType = "Java"
								exeArch = "Universal"
							exeZip.close() # again, not needed.

					if engineType == "Unknown": # If we still come up with nothing matched, just output some info about the executable
						if not exeType and not exeArch:
							mm.seek(mm.find(b'PE\x00\x00')+4)
							fileArch = struct.unpack("<H", mm.read(2))[0]
							if fileArch == 332:
								exeArch = "32-bit"
								mm.seek(226, 1)
								exeType = "Win32" if struct.unpack("<I", mm.read(4))[0] == 0 else ".NET"
							elif fileArch == 34404:
								exeArch = "64-bit"
								mm.seek(242, 1)
								exeType = "Win32" if struct.unpack("<I", mm.read(4))[0] == 0 else ".NET"
						if exeType and exeArch: engineType += " [%s, %s]" % (exeType, exeArch)

						detectExe = exe
					del mm
					gc.collect() # this might cause problems, but it might make it faster
				except:
					print("Error reading %s! Moving on." % (exe))
	if engineType == "Unknown" and not fastParse:
		if any(in_list("bin")) and os.path.isdir(pj(dirName,"bin")):
			if args["verbose"] > 0: print("* %s - TODO: bin folder present, might contain something." % gameName)
			return
		else:
			return # At this point, if we don't know what it is, it's probably not a game at all.

	if not args["game"]: incDict(engineType)
	return [gameName, engineType, subGames, detectExe]
		
def detectClean(game, list):
	info = detectGame(game)
	if not info: return
	if filterEngine == "" or filterEngine.lower() in info[1].lower():
		if list:
			pfmt = "- %s (%s) [%s]" if args["verbose"] > 0 else "- %s (%s)"
		else:
			pfmt = "%s (%s) [%s]" if args["verbose"] > 0 else "%s (%s)"
		print(pfmt % (info[0], info[1], info[3] if info[3] else "N/A") if args["verbose"] > 0 else pfmt % (info[0], info[1]) )
		if len(info[2]) > 0: print("  - Sub-games: %s" % str(info[2])[1:-1])

if __name__=="__main__":
	# Gather all game directories
	if not args["game"]:
		gamedirs = next(os.walk(args["dir"] if args["dir"] else '.'))[1]

		print("== Games ==")
		for game in gamedirs:
			detectClean(game, True)
	else:
		detectClean(args["game"], False)

	if not args["game"]: 
		eCount = {k: v for k, v in sorted(engineDict.items(), reverse=True, key=lambda item: item[1])}
		print("\n== Engine Count ==")
		for x,y in eCount.items():
			print("%s: %s" % (x, y))