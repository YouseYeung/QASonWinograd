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
                    self.writeIntoFile("test1_output")
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
            index = {'subj':rep.find('subj'), 'iobj':rep.find('iobj'), 'dobj':rep.find('dobj'), 'nmod':rep.find('nmod')}
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
    def findPersonNoun_Verbs (self, kb):
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
                outputStr += objectNotEqual + valList[i] + ' ' + valList[j] + ')))\n'
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
        kb = self.kb
        tokens = kb["Lemmatized tokens:"]
        children = kb["Dependency children:"]
        tokensToIndexMap = {}
        i = 0
        for token in tokens:
            tokensToIndexMap[token] = i
            i += 1

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
        #determine the verb is with one entity or many entities
        #determine the verb is with another verb or alone
        #pronouns used to get a, b, c, and so on
        #nounsMap used to map tokens "person B" to variable "b"
        pronouns = []
        for i in range(26):
            pronouns.append(chr(ord('a') + i))
        def addSentence(antecedent, secedent):
            outputStr = ""
            nounsMap = {}
            length = len(antecedent)
            headString = "(assert (forall "
            outputStr += headString
            #persons list records the member of person variable
            #things list records the member of thing variable
            persons = []
            things = []
            declareNounString = ""
            number = 0
            #---adding variables declaration
            for verbName in antecedent:
                nouns = verbs[verbName][1]
                nums = len(nouns)
                for i in range(nums):
                    #nouns[i][2] is a boolean value, if it is true, this noun is a variable, else it is a constant
                    if nouns[i][2]:
                        if nouns[i][1]:
                            declareNounString += "(" + pronouns[number] + " person) "
                            persons.append(pronouns[number])
                        #false for thing
                        else:
                            declareNounString += "(" + pronouns[number] + " thing) "
                            things.append(pronouns[number])

                        #adding tokens "person B" to variable "b" maps
                        nounNameIndex = nouns[i][0]
                        nounName = tokens[nounNameIndex]
                        nounChild = children[nounNameIndex]
                        index = nounChild.find("compound")
                        if index != -1:
                            compoundNameIndex = ""
                            for c in nounChild[index + len("compound->"):]:
                                if c.isdigit():
                                    compoundNameIndex += c
                                else:
                                    break
                            nounName = tokens[int(compoundNameIndex)] + nounName
                        nounsMap[nounName] = pronouns[number]
                        number += 1

            outputStr += "(" + declareNounString + ") "
            outputStr += "(=> "
            #---adding variable not equal
            personLength = len(persons)
            thingLength = len(things)
            valNotEqualStr = ""
            notEqualPairs = 0
            if personLength >= 2:
                for i in range(personLength):
                    for j in range(i + 1, personLength):
                        valNotEqualStr += "(not (= " + persons[i] + ' ' + persons[j] + ') '
                        notEqualPairs += 1

            if thingLength >= 2:
                for i in range(thingLength):
                    for j in range(i + 1, thingLength):
                        valNotEqualStr += "( not (= " + thinsg[i] + ' ' + things[j] + ') '
                        notEqualPairs += 1
            #if there exists more than one not equal pair, we should add 'and' to connect them
            if notEqualPairs >= 2:
                valNotEqualStr = "(and " + valNotEqualStr + ") "

            outputStr += valNotEqualStr + ') '

            #---adding reality sentences
            addedVerbs = []
            realitySentence = "(=> "
            def addingReality(verbsInSentence):
                realitySentence = ""
                for verbName in verbsInSentence:
                    if verbName not in addedVerbs:
                        child = children[tokensToIndexMap[verbName]]
                        index = child.find("conj:")
                        anotherVerbName = ""
                        relation = ""
                        if index != -1:
                            index += len("conj:")
                            relation = child[index:index + 3]
                            if relation == "and":
                                relation = "and"
                            else:
                                relation = "or"
                            realitySentence += '(' + relation + ' '
                            anotherVerbIndex = ""
                            for c in child[index + len(relation + '->'):]:
                                if c.isdigit():
                                    anotherVerbIndex += c
                                else:
                                    break
                            anotherVerbIndex = int(anotherVerbIndex)
                            anotherVerbName = tokens[anotherVerbIndex]
                            addedVerbs.append(verbName)
                            addedVerbs.append(anotherVerbName)

                        #---adding sentence for verbs
                        def addVerbSentence(verb):
                            if verb == "":
                                return ""
                            nouns = verbs[verb][1]
                            verbStr = "(" + verb + " "
                            for noun in nouns:
                                #noun[2] is true, then the noun is a var
                                if noun[2]:
                                    nounNameIndex = noun[0]
                                    nounName = tokens[nounNameIndex]
                                    nounChild = children[nounNameIndex]
                                    index = nounChild.find("compound")
                                    if index != -1:
                                        compoundNameIndex = ""
                                        for c in nounChild[index + len("compound->"):]:
                                            if c.isdigit():
                                                compoundNameIndex += c
                                            else:
                                                break
                                        nounName = tokens[int(compoundNameIndex)] + nounName
                                    varName = nounsMap[nounName]
                                    verbStr += varName + ' '
                                else:
                                    verbStr += tokens[noun[0]]
                            return verbStr + ') '

                        realitySentence += addVerbSentence(verbName)
                        realitySentence += addVerbSentence(anotherVerbName)
                        if relation != "":
                            realitySentence += ") "

                return realitySentence

            realitySentence += addingReality(antecedent) + addingReality(secedent) + ')'
            if notEqualPairs >= 1:
                realitySentence += ')'
            
            #---adding closed reason assumption

            return outputStr + realitySentence + '))\n'

        return outputStr + addSentence(antecedent, secedent) + addSentence(secedent, antecedent)

    def addRules_OnlyOneAnswer(self, personNouns, thingNouns, outputStr):
        question = self.question
        tokens = question["Lemmatized tokens:"]
        tags = question["POS tags:"]
        verb = ""
        i = 0
        for tag in tags:
            if "VB" in tag and "AUX" not in tag:
                verb = tokens[i]
            i += 1

        headString = "(assert (= "
        nounList = []
        #person answer
        if "who" in tokens or "whom" in tokens:
            nounList = personNouns
        #thing answer
        else:
            nounList = thingNouns

        length = len(nounList)
        i = 0
        verbNouns = self.findPersonNoun_Verbs(question)
        for verbName, nouns in verbNouns.items():
            verbSentence = "(" + verbName + " "
            addingNouns = []
            #find the noun that is variable
            for noun in nouns[1]:
                nounIndex = noun[0]
                tag = tags[nounIndex]
                if tag == "WP":
                    addingNouns.append("WP")
                else:
                    addingNouns.append(tokens[nounIndex])

            #substitue the variable noun with the candidate answer noun
            for i in range(length):
                trueSentence = "(" + verb
                for symbol in addingNouns:
                    if symbol == "WP":
                        trueSentence += " " + nounList[i]
                    else:
                        trueSentence += " " + symbol
                trueSentence += ") "

                falseSentence = ""
                for j in range(length):
                    if i != j:
                        falseSentence += "(not (" + verb
                        for symbol in addingNouns:
                            if symbol == "WP":
                                falseSentence += " " + nounList[j]
                            else:
                                falseSentence += " " + symbol

                        falseSentence += ")) "
                if length > 2:
                    falseSentence = "(and " + falseSentence + ")"

                outputStr += headString + trueSentence + falseSentence + '))\n'
        return outputStr

    def translateIntoZ3(self):
        candidateAnswer_thing = []
        candidateAnswer_person = []
        verbs = []
        output = ""

        description = self.description
        children = description["Dependency children:"]
        tokens = description["Lemmatized tokens:"]
        verbs_nouns = self.findPersonNoun_Verbs(self.kb)
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

        for _, nouns in verbs_nouns.items():
            for noun in nouns[1]:
                nounIndex = noun[0]
                nounName = self.kb['Lemmatized tokens:'][nounIndex]
                #if noun is not a variable
                if not noun[2]:
                    #if noun has not been added into candidate:
                    if nounName not in candidateAnswer_person and nounName not in candidateAnswer_thing:
                        #if noun is a person
                        if noun[1]:
                            candidateAnswer_person.append(nounName)
                        else:
                            candidateAnswer_thing.append(nounName)

        output = self.addDeclareSort(candidateAnswer_thing, False, output)
        output = self.addDeclareSort(candidateAnswer_person, True, output)
        output = self.addDeclareRel(verbs_nouns, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_thing, output)
        output = self.addRules_EntityNotEqual(candidateAnswer_person, output)
        output = self.addRules_EntityRange(candidateAnswer_thing, False, output)
        output = self.addRules_EntityRange(candidateAnswer_person, True, output)
        output = self.addRules_ClosedReasonAssumption(verbs_nouns, output)
        output = self.addRules_OnlyOneAnswer(candidateAnswer_person, candidateAnswer_thing, output)
        self.output = output + "(check-sat)\n"

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.output)

test = translater()
test.load("test1")