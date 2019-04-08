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

ids = ["Division", "Title", "Subtitle", "Part", "Subpart", "Chapter", "Subchapter", "Section"]
levels = [["LEGISLATIVE HISTORY", "DIVISION"], ["TITLE"], ["Subtitle"], ["PART"], ["SUBPART"], ["CHAPTER"], ["SUBCHAPTER", "Subchapter"], ["SECTION", "SEC."]]

class Section:
	def __init__(self):
		self.level = 0
		self.number = "??"
		self.name = ""
		self.note = ""
		self.elems = []

	def __str__(self):
		result = "  "*self.level
		if self.level < len(levels):
			result += ids[self.level] + " " + self.number + ": "
		else:
			result += "Subsection: "
		result += self.name + "\n"
		#result += "\n"

		for elem in self.elems:
			if isinstance(elem, Section):
				result += str(elem)
			#else:
			#	result += "  "*(self.level+1) + elem + "\n"
		#result += "\n\n\n"
		return result

class Bill:
	def __init__(self):
		self.name = ""
		self.intro = []
		self.sections = []

	def __str__(self):
		result = self.name + "\n"
		for section in self.sections:
			result += str(section)
		return result

def isUnlabelledHeader(text, start, width):
	idx = start
	if idx > 0 and idx < len(text) and len(text[idx-1].strip()) > 0:
		return False

	while idx < len(text):
		line = text[idx]
		left_margin = len(re.match("^ *", line).group(0))
		right_margin = width-len(line.rstrip())
		if len(line.strip()) == 0:
			return idx > start
		elif (line.strip()[0] == "(" and line.strip()[2] == ")") or line.strip()[0] == "\"" or "." in line or "---" in line or abs(left_margin - right_margin) > 4 or min(left_margin, right_margin) <= 2:
			return False
		
		#for word in line.strip().split(' '):
		#	if len(word) > 4 and word[0] in "abcdefghijklmnopqrstuvwxyz\"\'":
		#		return False

		idx += 1
	return True

def process_unlabelledHeader(text, start, width):
	idx = start
	header = ""
	while idx < len(text):
		line = text[idx]
		left_margin = len(re.match("^ *", line).group(0))
		right_margin = width-len(line.rstrip())
		if len(line.strip()) == 0:
			break
		else:
			if len(header) > 0:
				header += " "
			header += line.strip()

		idx += 1

	return (header, idx-start)
	
def isheader(line, start=0, end=-1):
	test = line.strip()
	if end < 0:
		end += len(levels)
	for level in levels[start:end+1]:
		for name in level:
			if test.startswith(name):
				return True
	return False

def process_header(text, start = 0, width = 80):
	idx = start
	note = False
	header = ""
	first = False
	allCaps = True
	if re.match(".*[a-z]+", text[start]) != None:
		allCaps = False

	while idx < len(text):
		line = text[idx]
		#left_margin = len(re.match("^ *", line).group(0))
		#right_margin = width-len(line.rstrip())
		#print(str(left_margin) + "\t" + str(right_margin))

		if allCaps:
			if "<<" in line and re.match(".*[a-z]+", line[0:line.index("<<")]) == None:
				note = True
			
			if re.match(".*[a-z]+", line) != None and not note:
				break
			if isheader(line) and len(text[idx-1].strip()) == 0:
				if not first:
					first = True
				else:
					break
		elif len(line.strip()) == 0:
			break

		if len(line.strip()) > 0:
			if len(header) > 0:
				header += " "
			header += line.strip()

		if allCaps:
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

	kind, num, name = re.match("([a-zA-Z\.]+) +([^ \.]+)\.?( +([^$]*))?", header).group(1, 2, 4)
	if name is None:
		name = ""
	else:
		name = name.strip()
		while name[-1] in ['.', '-', ':']:
			name = name[0:-1]
			name = name.strip()
		name = titlecase(name)
	note = note[8:-2]

	return (kind, num, name, note, idx-start)

def process_item(text, level, start = 0, width = 80):
	section = Section()
	section.level = level
	idx = start

	if idx >= len(text):
		return (section, idx-start)

	section.name, offset = process_unlabelledHeader(text, idx, width)
	idx += offset
		
	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line) or isUnlabelledHeader(text, idx, width):
			break
		elif len(line.strip()) > 0:
			section.elems.append(line)
	
		idx += offset
	return (section, idx-start)

def process_section(text, level, start = 0, width = 80):
	section = Section()
	section.level = level
	idx = start

	if idx >= len(text):
		return (section, idx-start)

	if isheader(text[idx], level, level):
		_, section.number, section.name, section.note, offset = process_header(text, idx, width)
		idx += offset
		
	table_contents = False
	first_title = ""
	if "Table of Contents" in section.name or "Table of Titles" in section.name:
		table_contents = True

	if level+1 < len(levels):
		elem, offset = process_section(text, level+1, idx, width)
		if len(elem.elems) > 0:
			section.elems.append(elem)
		idx += offset

	while idx < len(text):
		line = text[idx]

		offset = 1
		if isheader(line, 0, level):
			if table_contents:
				kind, num, name, _, _ = process_header(text, idx, width)
				if not first_title:
					first_title = (kind, num, name)
				elif first_title == (kind, num, name):
					break
			else:
				break
		elif isheader(line, level+1):
			elem, offset = process_section(text, level+1, idx, width)
			section.elems.append(elem)
		elif level >= len(levels)-1 and isUnlabelledHeader(text, idx, width):
			elem, offset = process_item(text, level+1, idx, width)
			section.elems.append(elem)
		elif len(line.strip()) > 0:
			section.elems.append(line)
	
		idx += offset

	if len(section.elems) == 1 and isinstance(section.elems[0], Section) and not section.elems[0].name:
		section.elems = section.elems[0].elems

	return (section, idx-start)

def process_bill(text, start = 0):
	bill = Bill()
	idx = start
	width = max([len(line) for line in text])

	section, offset = process_section(text, len(levels)-1, idx, width)
	bill.sections.append(section)
	idx += offset


	#while idx < len(text):
	#	line = text[idx]
	#	if isheader(line):
	#		break
	#
	#	bill.intro.append(line)
	#	idx += 1

	while idx < len(text):
		line = text[idx]
		
		offset = 1
		if isheader(line):
			section, offset = process_section(text, 0, idx, width)
			bill.sections.append(section)
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
