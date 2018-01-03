import os
import string

class translater(object):
    def __init__(self):

#tokens: words
#pos tags: type of words
#ner tags: mark if a word is the type of person
#dependency children: words' dependency
        self.parsingSymbol = ['Tokens:', 'Lemmatized tokens:', 'POS tags:', 'NER tags:', 'NER values:', 'Dependency children:']
        self.parsingResult = {}
        self.description = {}
        self.question = {}
        self.kb = {}
        self.output = ""

    def load(self, fileName):
        with open(fileName, 'r') as f:
            lastLine = ''
            i = 0
            while True:
                content = f.readline()
                if not content:
                    break

                #one \n marking for the end of one data in one question
                if content == '\n' and lastLine != '\n':
                    if i == 0:
                        self.description = self.parsingResult
                    elif i == 1:
                        self.kb = self.parsingResult
                    else:
                        self.question = self.parsingResult
                    self.parsingResult = {}

                    i = (i + 1) % 3
                #two \n marking for the end of one question
                if content == '\n' and lastLine == '\n':
                    self.translateIntoZ3()
                    self.writeIntoFIle()
                    self.kb = {}
                    self.question = {}
                    self.description = {}

                for symbol in self.parsingSymbol:
                    index = content.find(symbol)
                    if index != -1:
                        content = (content[index + len(symbol) + 1:])[1:-2]
                        #for dependency, it can not just use split(',') to get te result
                        #'[,]' it is because one word's children result may have many ',' , 
                        # so it has to use to '[]' to seperate the result for each word 
                        if symbol == 'Dependency children:':
                            oneWordResult = ""
                            hasLeftBracket = False
                            allWordsResult = []
                            for c in content:
                                if hasLeftBracket:
                                    oneWordResult += c
                                    if c == ']':
                                        allWordsResult.append(oneWordResult)
                                        oneWordResult = ""
                                        hasLeftBracket = False
                                elif c == '[':
                                    oneWordResult += '['
                                    hasLeftBracket = True
                            content = allWordsResult  
                            
                        else:
                            content = content.split(', ')
                            res = []
                            for val in content:
                                res.append(val)
                            content = res
                        self.parsingResult[symbol] = []
                        for val in content:
                            val = val.strip()
                            self.parsingResult[symbol].append(val)
                        break

                lastLine = content
    #return the relation nouns' index
    def findNounsRelatedToVerbs(self, children):
        res = []
        relatedWords = children[1:-1].split(',')
        for rep in relatedWords:
            index = {'subj':rep.find('subj'), 'obj':rep.find('obj'), 'nmod':rep.find('nmod')}
            for typeOfNoun, index in index.items():
                if index != -1:
                    indexStart = index + len(typeOfNoun + '->')
                    index = int(rep[indexStart:])
                    res.append(index)

        return res

    #finding if there exists a person noun, if there exists, find the related verbs.
    def findPersonNoun_Verbs (self):
        kb = self.kb
        tokens = kb["Lemmatized tokens:"]
        tags = kb["POS tags:"]
        children = kb["Dependency children:"]
        length = len(tokens)
        i = 0
        relatedVerbs = {}
        while i < length:
            #find verbs and neglect auxiliary verbs
            if tags[i].find("VB") != -1 and tags[i].find("AUX") == -1:
                verb = tokens[i]
                relatedNoun = []
                relatedNounsIndex = self.findNounsRelatedToVerbs(children[i])
                for index in relatedNounsIndex:
                    noun = tokens[index]
                    if noun == 'somebody' or tokens[index - 1] == 'person':
                        relatedNoun.append([index, True])  # True = person
                    else:
                        relatedNoun.append([index, False]) # False = thing
                
                relatedVerbs[verb] = relatedNoun

            i += 1
        return relatedVerbs

                
    def translateIntoZ3(self):
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                         # need 1 )
        declareRel = "(declare-rel )"                            # need 1 )
        objectNotEqual = "(assert (not (= "                      # need 2 )
        objectThingRange = "(assert (forall ((x thing)) (or "    # need 3 )
        objectPersonRange = "(assert (forall ((x person)) (or "  # need 3 )
        candidateAnswer_thing = []
        candidateAnswer_person = []
        verbs = []
        output = ""

        description = self.description
        children = description["Dependency children:"]
        tokens = description["Lemmatized tokens:"]
        verbs_dict = self.findPersonNoun_Verbs()
        i = 0
        for word in tokens:
            #finding nouns
            if word in verbs_dict.keys():
                relatedNounsIndex = self.findNounsRelatedToVerbs(children[i])
                j = 0
                for index in relatedNounsIndex:
                    noun = tokens[index]
                    personOrNot = verbs_dict[word][j][1]
                    if personOrNot:
                        candidateAnswer_person.append(noun)
                    else:
                        candidateAnswer_thing.append(noun)
                    j += 1
            i += 1

        print(candidateAnswer_thing)
        print(candidateAnswer_person)
        return
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
test.findPersonNoun_Verbs()
test.translateIntoZ3()
#test.writeIntoFile("test1_output")


