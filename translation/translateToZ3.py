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


    #True for person, False for thing
    def addDeclareSort(self, valList, thingOrPerson, outputStr):
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                         # need 1 )
        if not thingOrPerson:
            outputStr += declareSort + "thing" + ")\n"
            for val in valList:
                outputStr += declareConst + val + " thing" + ")\n"
        else:
            outputStr += declareSort + "person" + ")\n"
            for val in valList:
                outputStr += declareConst + val + " person" + ")\n"

        return outputStr

    def addRules_EntityNotEqual(self, valList, outputStr):
        objectNotEqual = "(assert (not (= "                      # need 2 )
        length = len(valList)
        i, j = 0, 1
        while i < length:
            while j < length:
                outputStr += objectNotEqual + valList[i] + ' ' + valList[j] + '))\n'
                j += 1
            i += 1

        return outputStr

    def addRules_EntityRange(self, valList, thingOrPerson, outputStr):
        objectThingRange = "(assert (forall ((x thing)) "         # need 3 )
        objectPersonRange = "(assert (forall ((x person)) "       # need 3 )
        length = len(valList)
        if length < 1:
            return outputStr
        else:
            if length == 1:
                if thingOrPerson:
                    return outputStr + objectPersonRange + "(= x " + valList[0] + ")))\n"
                else:
                    return outputStr + objectThingRange + "(= x " + valList[0] + ")))\n"
            else:
                if thingOrPerson:
                    outputStr += objectPersonRange + "(or "
                    for thing in valList:
                        outputStr += '(= x ' + thing + ') '
                else:
                    outputStr += objectThingRange +  "(or "
                    for person in valList:
                        outputStr += '(= x ' + person + ') '
                outputStr += ')))\n'
        return outputStr

    def addDeclareRel(self, valList, outputStr):
        declareRel = "(declare-rel "                            # need 1 )
        for verb, relatedNouns in valList.items():
            outputStr += declareRel + verb + " ("
            for noun in relatedNouns:
                if noun[1]:
                    outputStr += "person "
                else:
                    outputStr += "thing "
            outputStr += "))\n"

        return outputStr

    def translateIntoZ3(self):
        candidateAnswer_thing = []
        candidateAnswer_person = []
        verbs = []
        output = ""

        description = self.description
        children = description["Dependency children:"]
        tokens = description["Lemmatized tokens:"]
        verbs_nouns = self.findPersonNoun_Verbs()
        i = 0
        for word in tokens:
            #finding nouns
            if word in verbs_nouns.keys():
                relatedNounsIndex = self.findNounsRelatedToVerbs(children[i])
                j = 0
                for index in relatedNounsIndex:
                    noun = tokens[index]
                    personOrNot = verbs_nouns[word][j][1]
                    if personOrNot:
                        candidateAnswer_person.append(noun)
                    else:
                        candidateAnswer_thing.append(noun)
                    j += 1
            i += 1

        output = self.addDeclareSort(candidateAnswer_thing, False, output)
        output = self.addDeclareSort(candidateAnswer_person, True, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_thing, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_person, output)
        output = self.addRules_EntityRange(candidateAnswer_thing, False, output)
        output = self.addRules_EntityRange(candidateAnswer_person, True, output)
        output = self.addDeclareRel(verbs_nouns, output)
        print output

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.output)

test = translater()
test.load("test1")
test.findPersonNoun_Verbs()
test.translateIntoZ3()
#test.writeIntoFile("test1_output")


