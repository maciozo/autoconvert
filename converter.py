import glob
import subprocess
import os
import threading
import queue
import time
import sys

# 0 = skip conversion, 1 = rename new, 2 = overwrite
onDuplicate = 0

# Extenstions to convert from
filetypes = ["flac", "wma", "wav", "ogg", "tta", "tak", "alac", "aac", "m4a"]

# Codec to convert to
newCodec = "libmp3lame"
newExtension = "mp3"
bitrate = "320k"
samplerate = "48000"

# Remove source files after conversion. Leftover files will have a "_" at the end of their names.
removeOld = True

# Set to os.cpu_count() for best converstion speed. Set to a lower value to reduce resource usage when converting.
numberOfThreads = os.cpu_count()

files = queue.Queue()
toPrint = queue.Queue()
cwd = os.getcwd()
busyThreads = []

def main():
	threads = []
	
	typeString = ""
	for type in filetypes:
		if type != filetypes[-1]:
			typeString += "%s|" % type
		else:
			typeString += type
	
	print("ffmpeg: -i file.<%s> -c:a %s -b:a %s -ar %s%s file.%s" % (typeString, newCodec, bitrate, samplerate, " -y" if onDuplicate == 2 else "", newExtension))

	for i in range(numberOfThreads):
		busyThreads.append(False)
		threads.append(threading.Thread(target = worker, args = (i,), daemon = True))
		threads[i].start()
		
	printThread = threading.Thread(target = printer, daemon = True)
	printThread.start()
	
	titleThread = threading.Thread(target = title, daemon = True)
	titleThread.start()
	
	while (1):
		for type in filetypes:
			for file in glob.glob("%s/*.%s" % (cwd, type)):
				try:
					toPrint.put("Main: Adding %s to queue" % file.replace("%s\\" % cwd, ""))
					os.rename(file, "%s_" % file) # Renaming to make sure that the file doesn't get added to the queue again
					files.put(["%s_" % file, type])
				except PermissionError:
					toPrint.put("Main: Permission error")
					pass
				
		for thread in threads:
			if not thread.is_alive():
				thread = threading.Thread(target = printer, daemon = True)
				thread.start()
				
		if not printThread.is_alive():
			printThread = threading.Thread(target = printer, daemon = True)
			printThread.start()
			
		if not titleThread.is_alive():
			titleThread = threading.Thread(target = title, daemon = True)
			titleThread.start()
			
		time.sleep(1)
			
	
def worker(threadID):
	print("Worker %i started" % threadID)
	FNULL = open(os.devnull, 'w')
	while (1):
		try:
			busyThreads[threadID] = False
			filedata = files.get()
			busyThreads[threadID] = True
			file = filedata[0]
			type = filedata[1]
			toPrint.put("Thread %i: Converting %s" % (threadID, file.replace("%s\\" % cwd, "")))
			
			if onDuplicate == 0: # Skip
				if (not os.path.isfile(file.replace("%s_" % type, "mp3"))):
					subprocess.run(["ffmpeg.exe", "-i", file, "-c:a", newCodec, "-b:a", bitrate, "-ar", samplerate, file.replace("%s_" % type, newExtenstion)], stdout=FNULL, stderr=subprocess.STDOUT)
					toPrint.put("Thread %i: Done" % threadID)
				else:
					toPrint.put("Thread %i: %s already exists" % (threadID, file.replace("%s_" % type, newExtenstion).replace(cwd, "")))
				if removeOld:
					os.remove(file)
					
			elif onDuplicate == 1: # Rename
				if os.path.isfile(file.replace("%s_" % type, newExtenstion)):
					fnumber = 1
					while os.path.isfile(file.replace("%s_" % type, newExtenstion).replace(".%s" % newExtenstion, " (%i).%s" % (fnumber, newExtenstion))):
						fnumber += 1
					oldFile = file
					newFile = file.replace("%s_" % type, "mp3").replace(".%s" % newExtenstion, " (%i).%s" % (fnumber, newExtenstion))
				else:
					oldFile = file
					newFile = file.replace("%s_" % type, newExtenstion)
				subprocess.run(["ffmpeg.exe", "-i", oldFile, "-c:a", newCodec, "-b:a", bitrate, "-ar", samplerate, newFile], stdout=FNULL, stderr=subprocess.STDOUT)
				toPrint.put("Thread %i: Done" % threadID)
				if removeOld:
					os.remove(oldFile)
				
			elif onDuplicate == 2: # Overwrite
				subprocess.run(["ffmpeg.exe", "-i", file, "-c:a", newCodec, "-b:a", bitrate, "-ar", samplerate, "-y", file.replace("%s_" % type, newExtenstion)], stdout=FNULL, stderr=subprocess.STDOUT)
				toPrint.put("Thread %i: Done" % threadID)
				if removeOld:
					os.remove(file)
			
		except PermissionError:
			toPrint.put("Thread %i: Permission error - putting file back in queue" % threadID)
			files.put(filedata)
		
def printer():
	while (1):
		print(toPrint.get().encode(sys.stdout.encoding, errors='replace'))
		
def title():
	while (1):
		activeThreads = 0
		for thread in busyThreads:
			if thread == True:
				activeThreads += 1
				
		newtitle = "Converter: %i files in queue - %i/%i active workers" % (files.qsize(), activeThreads, numberOfThreads)
		os.system("title %s" % newtitle)
		
		time.sleep(0.1)
		
main()
