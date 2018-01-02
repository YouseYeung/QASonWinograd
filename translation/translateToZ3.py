import os
import string

class translater(object):
    def __init__(self):

#tokens: words
#pos tags: type of words
#ner tags: mark if a word is the type of person
#dependency children: words' dependency
        self.parsingSymbol = ['Tokens:', 'Lemmatized tokens:', 'POS tags:', 'NER tags:', 'Dependecy children:']
        self.parsingResult = {}
        self.description = []
        self.question = []
        self.kb = []
        self.output = ""

    def load(self, fileName):
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
                        self.description.append(self.parsingResult)
                    elif isQuestion:
                        self.question.append(self.parsingResult)
                    else:
                        kb.append(self.parsingResult)
                    self.parsingResult = {}

                #two \n marking for the end of one question
                if content == '\n' and lastLine == '\n':
                    self.translateIntoZ3()
                    self.writeIntoFIle()
                    for i in xrange(len(self.question)):
                        print i, self.question[i]
                    for i in xrange(len(self.description)):
                        print i, self.description[i]
                    for i in xrange(len(self.kb)):
                        print i, self.kb[i]

                    gotQuestion = False
                    isQuestion = False
                    kb = []
                    self.question = []
                    self.description = []

                for symbol in self.parsingSymbol:
                    index = content.find(symbol)
                    if index != -1:
                        content = (content[index + len(symbol) + 1:])[1:-1]
                        content = content.split(',')
                        self.parsingResult[symbol] = []
                        for val in content:
                            val = val.strip()
                            if val.isalpha() or val.isdigit():
                                self.parsingResult[symbol].append(val)
                            if symbol == "POS tags:":
                                if 'WP' in self.parsingResult[symbol]:
                                    isQuestion = True
                                    gotQuestion = True
                                else:
                                    isQuestion = False
                        break

                lastLine = content

    def translateIntoZ3(self):
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                          # need 1 )
        declareRel = "(declare-rel )"                            # need 1 )
        objectNotEqual = "(assert (not (= "                      # need 2 )
        objectThingRange = "(assert (forall ((x thing)) (or "    # need 3 )
        objectPersonRange = "(assert (forall ((x person)) (or "  # need 3 (
        candidateAnswer_thing = []
        candidateAnswer_person = []
        verbs = []
        output = ""
        i = 0

        description = self.description[0]
        for posTag in description['POS tags:']:
            #finding nouns
            if posTag == "NN":
                candidateAnswer_thing.append(description['Lemmatized tokens:'][i])
            elif posTag == "NNP":
                candidateAnswer_person.append(description['Lemmatized tokens:'][i])
            #finding verbs
            elif posTag == "VB":
                neg = False
                dependencyWords = description['Dependecy children:'][i]
                verbs.append(description['Lemmatized tokens:'][i])
            
            i += 1
        #adding declare
        if candidateAnswer_thing != []:
            output += declareSort + "thing" + ")\n"
            for val in candidateAnswer_thing:
                output += declareConst + val + " thing" + ")\n"
        if candidateAnswer_person != []:
            output += declareSort + "person" + ")\n"
            for val in candidateAnswer_person:
                output += declareConst + val + " person" + ")\n"

        
        #adding rules
        #rule_one objects are not the same
        i = 0
        j = 1
        length = len(candidateAnswer_thing)
        while i < length:
            while j < length:
                output += objectNotEqual + candidateAnswer_thing[i] + ' ' + candidateAnswer_thing[j] + '))\n'
                j += 1
            i += 1
      
        i = 0
        j = 1
        length = len(candidateAnswer_person)
        while i < length:
            while j < length:
                output += objectNotEqual + candidateAnswer_person[i] + ' ' + candidateAnswer_person[j] + '))\n'
                j += 1
            i += 1
        
        
        #rule_two objects can only be the one that appear in the sentences
        if candidateAnswer_thing != []:
            output += objectThingRange
            for thing in candidateAnswer_thing:
                output += '(= x ' + thing + ') '
            output += ')))\n'

        if candidateAnswer_person != []:
            output += objectPersonRange
            for person in candidateAnswer_person:
                output += '(= x ' + person + ')'
            output += ')))\n'
        self.output = output

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.output)

test = translater()
test.load("test1")
test.translateIntoZ3()
test.writeIntoFile("test1_output")


