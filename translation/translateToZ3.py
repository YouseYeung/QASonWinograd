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
    #return value: [number, list], number for verb's index, list for verb's related nouns
    #list = [number, boolean, boolean], number for noun's index, 
    #the first boolean for the symbol marking if the noun a person or not, True for person, False for thing
    #the second boolean for the symbol marking if the noun is a variable or a constant
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
                        relatedNoun.append([index, True, True]) 
                    elif noun == 'something' or tokens[index - 1] == 'thing':
                        relatedNoun.append([index, False, True])
                    else:
                        relatedNoun.append([index, False, False])
                
                relatedVerbs[verb] = [i, relatedNoun]

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
        i = 0
        while i < length:
            j = i + 1
            while j < length:
            	print (valList[i], valList[j])
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
            for noun in relatedNouns[1]:
                if noun[1]:
                    outputStr += "person "
                else:
                    outputStr += "thing "
            outputStr += "))\n"

        return outputStr

    def addRules_ClosedReasonAssumption(self, verbs, outputStr):
        #(assert (forall ((x person) (y person)) (=> (not (= x y))
        # (=> (and (fear x vlc) (advocate y vlc)) (refuse x y)))))
        #(assert (forall ((x person) (y person)) (=> (not (= x y))
        # (=> (refuse x y) (and (fear x vlc) (advocate y vlc))))))
        print verbs
        headString = "(assert (forall "
        andEntailmentString = "and"
        orEntailmentString = "or"
        kb = self.kb
        tokens = kb["Lemmatized tokens:"]
        antecedent = []
        secedent = []
        findThen = False
        for word in tokens:
            if findThen:
                if word in verbs.keys():
                    secedent.append(word)
            else:
                if word in verbs.keys():
                    antecedent.append(word)
                elif word == 'then':
                    findThen = True
        
        #parsing antecedent
        outputStr += headString
        #determine the verb is with one entity or many entities
        #determine the verb is with another verb or alone
        #nounMap used to map "person B" to a, or "person C" to b
        #pronouns used to get a, b, c, and so on
        nounMap = {}
        pronouns = []
        for i in range(26):
            pronouns.append(chr(ord('a') + i))

        length = len(antecedent)
        numsOfPronoun = 0
        preVerb = antecedent[0]
        #remaining work: 蕴含式子的翻译
        #only one verb
        if length == 1:
            nouns = verbs[preVerb][1]
            nums = len(nouns)
            declareNounString = ""
            for i in range(nums):
                #nouns[i][2] is a boolean value, if it is true, this noun is a variable, else it is a constant
                if nouns[i][2]:
                    #true for person
                    if nouns[i][1]:
                        declareNounString += "(" + pronouns[i] + " person) "
                    #false for thing
                    else:
                        declareNounString += "(" + pronouns[i] + " thing) "
            outputStr += "(" + declareNounString + ") "
        #two or more verbs
        else:
            declareNounString = ""
            number = 0
            for verb in antecedent:
                nouns = verbs[preVerb][1]
                nums = len(nouns)
                for i in range(nums):
                    #nouns[i][2] is a boolean value, if it is true, this noun is a variable, else it is a constant
                    if nouns[i][2]:
                        if nouns[i][1]:
                            declareNounString += "(" + pronouns[number] + " person) "
                        #false for thing
                        else:
                            declareNounString += "(" + pronouns[number] + " thing) "
                        number += 1
            outputStr += "(" + declareNounString + ") "

        #parsing secedent

        print antecedent
        print secedent
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
                    personOrNot = verbs_nouns[word][1][j][1]
                    if personOrNot:
                        candidateAnswer_person.append(noun)
                    else:
                        candidateAnswer_thing.append(noun)
                    j += 1
            i += 1

        output = self.addDeclareSort(candidateAnswer_thing, False, output)
        output = self.addDeclareSort(candidateAnswer_person, True, output)
        output = self.addDeclareRel(verbs_nouns, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_thing, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_person, output)
        output = self.addRules_EntityRange(candidateAnswer_thing, False, output)
        output = self.addRules_EntityRange(candidateAnswer_person, True, output)
        output = self.addRules_ClosedReasonAssumption(verbs_nouns, output)
        self.output = output

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.output)

test = translater()
test.load("test1")
test.findPersonNoun_Verbs()
test.translateIntoZ3()
test.writeIntoFile("test1_output")


