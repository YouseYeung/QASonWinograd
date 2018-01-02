import os
import string

fileName = 'output'
z3FileOutputName = 'z3_output'
#tokens: words
#pos tags: type of words
#ner tags: mark if a word is the type of person
#dependency children: words' dependency
parsingSymbol = ['Tokens:', 'Lemmatized tokens:', 'POS tags:', 'NER tags:', 'Dependecy children:']
parsingResult = {}
description = []
question = []
kb = []

wf = open(z3FileOutputName, 'w')

with open(fileName, 'r') as f:
	lastLine = ''
	gotQuestion = False
	isQuestion = False
	while True:
		content = f.readline()
		if not content:
			break

		#one \n marking for the end of one data in one question
		if content == '\n' and lastLine != '\n':
			if not gotQuestion:
				description.append(parsingResult)
			elif isQuestion:
				question.append(parsingResult)
			else:
				kb.append(parsingResult)
			parsingResult = {}

		#two \n marking for the end of one question
		if content == '\n' and lastLine == '\n':
			for i in xrange(len(question)):
				print i, question[i]
			for i in xrange(len(description)):
				print i, description[i]
			for i in xrange(len(kb)):
				print i, kb[i]

			gotQuestion = False
			isQuestion = False
			kb = []
			question = []
			description = []
			break
		for symbol in parsingSymbol:
			index = content.find(symbol)
			if index != -1:
				content = (content[index + len(symbol) + 1:])[1:-1]
				content = content.split(',')
				parsingResult[symbol] = []
				for val in content:
					val = val.strip()
					if val.isalpha() or val.isdigit():
						parsingResult[symbol].append(val)
				if symbol == "POS tags:":
					if 'WP' in parsingResult[symbol]:
						isQuestion = True
						gotQuestion = True
					else:
						isQuestion = False


				break
		lastLine = content

wf.close()