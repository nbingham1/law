#!/usr/bin/python3

import sys
import http.client as httplib
import urllib
import requests
import json
import os
import nltk
import re
from titlecase import titlecase
from textblob import *

class Section:
	def __init__(self):
		self.number = "??"
		self.name = ""
		self.note = ""
		self.lines = []

	def __str__(self):
		result = "        Section " + self.number + ": " + self.name + "\n"
		#result += "\n"
		#for line in self.lines:
		#	result += "          " + line + "\n"
		#result += "\n\n\n"

		return result

class Chapter:
	def __init__(self):
		self.number = "??"
		self.name = ""
		self.note = ""
		self.intro = []
		self.sections = []

	def __str__(self):
		result = "      Chapter " + self.number + ": " + self.name + "\n"
		for section in self.sections:
			result += str(section)
		return result

class Subtitle:
	def __init__(self):
		self.number = "??"
		self.name = ""
		self.note = ""
		self.intro = []
		self.chapters = []

	def __str__(self):
		result = "    Subtitle " + self.number + ": " + self.name + "\n"
		for chapter in self.chapters:
			result += str(chapter)
		return result

class Title:
	def __init__(self):
		self.number = "??"
		self.name = ""
		self.note = ""
		self.intro = []
		self.subtitles = []

	def __str__(self):
		result = "  Title " + self.number + ": " + self.name + "\n"
		for subtitle in self.subtitles:
			result += str(subtitle)
		return result

class Division:
	def __init__(self):
		self.number = "??"
		self.name = ""
		self.note = ""
		self.intro = []
		self.titles = []

	def __str__(self):
		result = "Division " + self.number + ": " + self.name + "\n"
		for title in self.titles:
			result += str(title)
		return result

class Bill:
	def __init__(self):
		self.name = ""
		self.intro = []
		self.divisions = []

	def __str__(self):
		result = self.name + "\n"
		for division in self.divisions:
			result += str(division)
		return result

def isheader(line, start="div", end="all"):
	types = [["LEGISLATIVE HISTORY", "DIVISION"], ["TITLE"], ["Subtitle"], ["CHAPTER", "PART"], ["SECTION", "SEC."]]
	index = {"div": 0, "title": 1, "subtitle": 2, "chapt": 3, "sect": 4, "all": len(types)-1}

	test = line.strip()
	for t in types[index[start]:index[end]+1]:
		for s in t:
			if test[0:len(s)] == s:
				return True
	return False

def process_header(text, start = 0, width = 80):
	idx = start
	note = False
	header = ""
	first = False
	while idx < len(text):
		line = text[idx]
		#left_margin = len(re.match("^ *", line).group(0))
		#right_margin = width-len(line.rstrip())
		#print(str(left_margin) + "\t" + str(right_margin))

		if "<<" in line and re.match(".*[a-z]+", line[0:line.index("<<")]) == None:
			note = True
		
		if re.match(".*[a-z]+", line) != None and not note:
			break
		if isheader(line):
			if not first:
				first = True
			else:
				break

		if len(line.strip()) > 0:
			if len(header) > 0:
				header += " "
			header += line.strip()

		if ">>" in line:
			note = False
		if "<<" in line and (">>" not in line or line.rindex(">>") < line.rindex("<<")):
			note = True

		idx += 1

	header = header.replace("--", " ")
	note = re.match(".*(<<[^>]*>>)", header)
	if note is not None:
		note = note.group(1)
	else:
		note = ""
	header = re.sub("<<[^>]*>>", "", header)

	kind, num, name = re.match("([A-Z\.]+) +([^ \.]+)\.? +([^$]*)", header).group(1, 2, 3)
	name = name.strip()
	while name[-1] in ['.', '-', ':']:
		name = name[0:-1]
		name = name.strip()
	name = titlecase(name)
	note = note[8:-2]

	return (kind, num, name, note, idx-start)

def process_subheader(text, start = 0, width = 80):
	idx = start
	header = ""
	while idx < len(text):
		line = text[idx]
		#left_margin = len(re.match("^ *", line).group(0))
		#right_margin = width-len(line.rstrip())
		#print(str(left_margin) + "\t" + str(right_margin))

		if len(line.strip()) == 0:
			break

		if len(header) > 0:
			header += " "
		header += line.strip()

		idx += 1

	header = header.replace("--", " ")
	note = re.match(".*(<<[^>]*>>)", header)
	if note is not None:
		note = note.group(1)
	else:
		note = ""
	header = re.sub("<<[^>]*>>", "", header)

	kind, num, name = re.match("([a-zA-Z\.]+) +([^ \.]+)\.? +([^$]*)", header).group(1, 2, 3)
	name = name.strip()
	while name[-1] in ['.', '-', ':']:
		name = name[0:-1]
		name = name.strip()
	name = titlecase(name)
	note = note[8:-2]

	return (kind, num, name, note, idx-start)

def process_section(text, start = 0, width = 80):
	section = Section()
	idx = start

	if isheader(text[idx], "sect", "sect"): 
		_, section.number, section.name, section.note, offset = process_header(text, idx, width)
		idx += offset

	table_contents = False
	first_title = ""
	if "Table of Contents" in section.name or "Table of Titles" in section.name:
		table_contents = True

	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, "div", "title"):
			if table_contents:
				kind, num, name, _, _ = process_header(text, idx, width)
				if not first_title:
					first_title = (kind, num, name)
				elif first_title == (kind, num, name):
					break
			else:
				break
		elif isheader(line, "subtitle", "subtitle"):
			if table_contents:
				kind, num, name, _, _ = process_subheader(text, idx, width)
				if not first_title:
					first_title = (kind, num, name)
				elif first_title == (kind, num, name):
					break
			else:
				break
		elif isheader(line, "chapt"):
			break

		section.lines.append(line)
		
		idx += offset

	return (section, idx-start)

def process_chapter(text, start = 0, width = 80):
	chapter = Chapter()
	idx = start
	
	if isheader(text[idx], "chapt", "chapt"):
		_, chapter.number, chapter.name, chapter.note, offset = process_header(text, idx, width)
		idx += offset

	section, offset = process_section(text, idx, width)
	chapter.sections.append(section)
	idx += offset
	
	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, "div", "chapt"):
			break
		elif isheader(line, "sect"):
			section, offset = process_section(text, idx, width)
			chapter.sections.append(section)
		
		idx += offset

	return (chapter, idx-start)

def process_subtitle(text, start = 0, width = 80):
	subtitle = Subtitle()
	idx = start

	if isheader(text[idx], "subtitle", "subtitle"):
		_, subtitle.number, subtitle.name, subtitle.note, offset = process_subheader(text, idx, width)
		idx += offset

	chapter, offset = process_chapter(text, idx, width)
	subtitle.chapters.append(chapter)
	idx += offset

	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, "div", "subtitle"):
			break
		elif isheader(line, "chapt"):
			chapter, offset = process_chapter(text, idx, width)
			subtitle.chapters.append(chapter)
		
		idx += offset

	return (subtitle, idx-start)

def process_title(text, start = 0, width = 80):
	title = Title()
	idx = start

	if isheader(text[idx], "title", "title"):
		_, title.number, title.name, title.note, offset = process_header(text, idx, width)
		idx += offset

	subtitle, offset = process_subtitle(text, idx, width)
	title.subtitles.append(subtitle)
	idx += offset

	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, "div", "title"):
			break
		elif isheader(line, "subtitle"):
			subtitle, offset = process_subtitle(text, idx, width)
			title.subtitles.append(subtitle)
		
		idx += offset

	return (title, idx-start)

def process_division(text, start = 0, width = 80):
	division = Division()
	idx = start

	if idx >= len(text):
		return (division, idx-start)

	if isheader(text[idx], "div", "div"):
		_, division.number, division.name, division.note, offset = process_header(text, idx, width)
		idx += offset

	title, offset = process_title(text, idx, width)
	division.titles.append(title)
	idx += offset

	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, "div", "div"):
			break
		elif isheader(line, "title"):
			title, offset = process_title(text, idx, width)
			division.titles.append(title)
		
		idx += offset

	return (division, idx-start)


def process_bill(text, start = 0):
	bill = Bill()
	idx = start
	width = max([len(line) for line in text])

	while idx < len(text):
		line = text[idx]
		if isheader(line):
			break

		bill.intro.append(line)
		idx += 1

	division, offset = process_division(text, idx, width)
	bill.divisions.append(division)
	idx += offset

	while idx < len(text):
		line = text[idx]
		
		offset = 1
		if isheader(line):
			division, offset = process_division(text, idx, width)
			bill.divisions.append(division)
		idx += offset

	#print(bill.intro)

	return bill

	#blob = TextBlob(text)
	#nouns = dict()
	#for sentence in blob.sentences:
	#	sent = sentence.sentiment
	#	for tag in sentence.tags:
	#		if tag[1][0:2] == "NN":
	#			print(tag)
	#			noun = tag[0].lower()
	#			if noun in nouns:
	#				nouns[noun][0] += 1
	#				nouns[noun][1] += sent.polarity
	#				nouns[noun][2] += sent.subjectivity
	#			else:
	#				nouns[noun] = [1, sent.polarity, sent.subjectivity]
	#for noun in sorted(zip(nouns.values(), nouns.keys())):
	#	print(noun)


def getfile(filename, url):
	opener = urllib.request.build_opener()
	opener.addheaders = [
			('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.21 (KHTML, like Gecko) Chrome/19.0.1042.0 Safari/535.21'),
			("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
	]
	result = ""
	if os.path.isfile(filename):
		result = open(filename, 'r')
	else:
		result = opener.open(url).read().decode('utf-8')
		with open(filename, 'w') as fptr:
			fptr.write(result)
		result = result.splitlines()
	return result

def process_entry(entry):
	result = getfile(entry["date"] + " " + entry["id"] + " Roll.html", entry["roll"])
	total = dict()
	for line in result:
		if line:
			sp = line.replace(">", "<").replace("<<", "<").split("<")[1:-1]
			if sp[0] == "recorded-vote":
				spl = sp[1].split(" ")
				for s in spl:
					if s[0:5] == "party":
						party = s[7:-1]

				for i in range(len(sp)):
					if sp[i] == "vote":
						vote = sp[i+1]				
				
				if party not in total:
					total[party] = [0, 0, 0]
				if vote == "Nay" or vote == "No":
					total[party][0] += 1
				elif vote == "Aye" or vote == "Yea":
					total[party][1] += 1
				elif vote == "Not Voting" or vote == "Present":
					total[party][2] += 1
				else:
					print(vote)
	if "D" not in total or "R" not in total:
		print(total)
	else:
		title = entry["id"];
		text = [];
		billStart = False
		if entry["url"]:
			textfile = getfile(entry["date"] + " " + entry["id"] + " Text.html", entry["url"] + "/text?format=txt")
			for line in textfile:
				if line:
					if "legDetail" in line:
						sp = line.replace(">", "<").replace("<<", "<").split("<")[1:]
						title = sp[1]
					elif "<pre id=\"billTextContainer\">" in line:
						billStart = True
					elif billStart and "</pre>" not in line:
						line = re.sub("\[\[[^\]]*\]\]", "", line)
						line = re.sub("[\n\r]+", "", line)
						line = line.replace("``", "\"").replace("''", "\"").replace("`", "'").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
						text.append(line)
					else:
						billStart = False

		dem = total["D"][0]/(total["D"][0] + total["D"][1] + total["D"][2])
		rep = total["R"][0]/(total["R"][0] + total["R"][1] + total["R"][2])

		#if "Medic" in "\n".join(text):# and abs(dem - rep) > 0.9:
		print("[" + entry["date"] + "\t" + title + "](" + entry["url"] + ")")
		print("||**No**|**Yes**|")
		print("|:-|:-|:-|")
		print("|**Democrats**|" + str(total["D"][0]) + "|" + str(total["D"][1]) + "|")	
		print("|**Republicans**|" + str(total["R"][0]) + "|" + str(total["R"][1]) + "|")
		print(process_bill(text))
		print()


entry = dict()
library = dict()
year = ""
if len(sys.argv) > 1:
	with open(sys.argv[1]) as fptr:
		idx = 0
		for line in fptr:
			if line:
				sp = line.replace(">", "<").replace("<<", "<").split("<")[1:-1]
				if sp and sp[0][0:4] == "META":
					year = sp[0][70:74]

				if sp and sp[0] == "TR":
					if entry:
						library[entry["date"] + entry["url"]] = entry
						entry = dict()
						idx = 0
					del sp[0]

				if sp and sp[0] == "TD":
					if idx == 0:
						if len(sp[1]) > 12 and sp[1][8:12] == "http":
							entry["roll"] = sp[1][8:-1]
						else:
							entry["roll"] = ""
					elif idx == 1:
						entry["date"] = sp[2] + "-" + year
					elif idx == 2:
						if sp[3] != "/FONT":
							entry["id"] = sp[3]
						else:
							entry["id"] = "Unnamed "
						if len(sp[2]) > 12 and sp[2][8:12] == "http":
							entry["url"] = sp[2][8:-1]
						else:
							entry["url"] = ""
					elif idx == 3:
						entry["title"] = sp[2]
					idx += 1


for entry in library.values():
	process_entry(entry)
