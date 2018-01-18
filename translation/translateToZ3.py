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
        self.kbList = []
        self.context = []
        self.output = ""

    def load(self, fileName):
        with open(fileName, 'r') as f:
            lastLine = ''
            beginMark = False
            while True:
                content = f.readline()
                if not content:
                    #reach the end of wsc problems, then add the parsing result into question and then translate.
                    if self.parsingResult != {}:
                        self.question = self.parsingResult
                        self.translateIntoZ3()
                    break
                if content.find("Example:") != -1:
                    self.context.append(content[len("Example: "):-3])
                    continue

                #one \n marking for the end of one data in one question
                if content == '\n' and lastLine != '\n':
                    if not beginMark:
                        self.description = self.parsingResult
                    else:
                        self.kbList.append(self.parsingResult)
                    self.parsingResult = {}

                    beginMark = True
                #two \n marking for the end of one question
                if content == '\n' and lastLine == '\n':
                    self.question = self.kbList[-1]
                    self.kbList = self.kbList[:-1]
                    self.translateIntoZ3()
                    self.kbList = []
                    self.question = {}
                    self.description = {}
                    self.context = []
                    beginMark = False

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
    #children are all words' child, child is the specific word's child
    def findNounsRelatedToVerbs(self, tags, children, child):
        res = []
        relatedWords = child[1:-1].split(',')
        for rep in relatedWords:
            typeOfNoun = ['subj', 'iobj', 'dobj', 'nmod', 'xcomp']
            for _type in typeOfNoun:
                index = rep.find(_type)
                if index != -1:
                    indexStart = rep.find('->') + len('->')
                    index = int(rep[indexStart:])
                    #xcomp is complement for verb, so we have to get more nouns in xcomp word.
                    if _type == 'xcomp':
                        #if complement is a noun
                        if ("NN" in tags[index] or "PRP" in tags[index]):
                            additiveNounsIndex = self.findNounsRelatedToVerbs(tags, children, children[index])
                            for i in additiveNounsIndex:
                                res.append(i)
                            res.append(index)
                    else:
                        res.append(index)
        return res

    #finding if there exists a person noun, if there exists, find the related verbs.
    #return value: {number : {string, string, list}, 
    #number for verb's index, frist string for verb's original name(fit), second string for combined name(fit_into), list for verb's related nouns
    #list = [number, boolean, boolean], number for noun's index, 
    #the first boolean for the symbol marking if the noun a person or not, True for person, False for thing
    #the second boolean for the symbol marking if the noun is a variable or a constant
    def findVerbsNouns (self, semanticTree):
        tokens = semanticTree["Lemmatized tokens:"]
        tags = semanticTree["POS tags:"]
        children = semanticTree["Dependency children:"]
        length = len(tokens)
        i = 0
        relatedVerbs = {}
        addedVerbIndex = []
        while i < length:
            #find verbs and neglect auxiliary verbs
            verb = ""
            if (tags[i].find("VB") != -1 and tags[i].find("AUX") == -1) or tags[i] == "JJ":
                #judge whether there exists a "be" before JJ
                if tags[i] == "JJ":
                    #if there exists no "be", pass this JJ
                    if children[i].find("cop") == -1:
                        i += 1
                        continue
                verb = tokens[i]
                prep = ""
                #combine verb and prep to get a combination form of verb
                wordStart = children[i].find("nmod:")
                if wordStart != -1:
                    wordStart += len("nmod:")
                    wordEnd = children[i][wordStart:].find("->")
                    prep = '_' + children[i][wordStart:wordStart + wordEnd]

            if verb != "" and i not in addedVerbIndex:
                relatedNoun = []
                relatedNounsIndex = self.findNounsRelatedToVerbs(tags, children, children[i])
                for index in relatedNounsIndex:
                    noun = tokens[index]
                    if noun == 'somebody' or tokens[index - 1] == 'person':
                        relatedNoun.append([index, True, True])
                    elif noun == 'something' or tokens[index - 1] == 'thing':
                        relatedNoun.append([index, False, True])
                    else:
                        relatedNoun.append([index, False, False])                
                #if the verb has related nouns, then add it into the return results
                if relatedNoun != []:
                    #sort the related nouns by their index
                    relatedNoun = sorted(relatedNoun, key = lambda x:x[0], reverse = False)
                    relatedVerbs[i] = {"originalVerbName":verb, "combinedVerbName":verb + prep, "relatedNouns":relatedNoun}
                addedVerbIndex.append(i)
                
                #combination of verb and verb, such as make sure to do, want to do, try to do
                combinedVerbIndexStart = children[i].find("xcomp")
                if combinedVerbIndexStart != -1:
                    verbChildren = children[i][1:-1].split(',')
                    combinedVerbName = ""
                    nsubj = relatedNoun[0]
                    relatedNoun = [nsubj]
                    for child in verbChildren:
                        if "xcomp" in child:
                            index = child.find('->') + len('->')
                            combinedVerbIndex = int(child[index:])
                            #if complement is not a verb
                            if "VB" not in tags[combinedVerbIndex]:
                                #address condition such as "make sure to do" 
                                if "xcomp" in children[combinedVerbIndex]:
                                    start = children[combinedVerbIndex].find('xcomp') + len('xcomp->')
                                    index = ""
                                    for c in children[combinedVerbIndex][start:]:
                                        if c != ',' and c != ']':
                                            index += c
                                        else:
                                            break
                                    combinedVerbIndex = int(index)
                                else:
                                    break
                            combinedVerbName = tokens[combinedVerbIndex]
                            relatedNounsIndex = self.findNounsRelatedToVerbs(tags, children, children[combinedVerbIndex])
                            for index in relatedNounsIndex:
                                if noun == 'somebody' or tokens[index - 1] == 'person':
                                    relatedNoun.append([index, True, True])
                                elif noun == 'something' or tokens[index - 1] == 'thing':
                                    relatedNoun.append([index, False, True])
                                else:
                                    relatedNoun.append([index, False, False])                
                            #if the verb has related nouns, then add it into the return results
                            if relatedNoun != []:
                                #sort the related nouns by their index
                                relatedNoun = sorted(relatedNoun, key = lambda x:x[0], reverse = False)
                                relatedVerbs[combinedVerbIndex] = {"originalVerbName":combinedVerbName, "combinedVerbName":combinedVerbName, "relatedNouns":relatedNoun}
                            addedVerbIndex.append(combinedVerbIndex)
            i += 1
        return relatedVerbs

    #True for person, False for thing
    def addDeclareSort(self, nounList, thingOrPerson, outputStr):
        if nounList == []:
            return outputStr
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                         # need 1 )
        if not thingOrPerson:
            outputStr += declareSort + "thing" + ")\n"
            for val in nounList:
                outputStr += declareConst + val + " thing" + ")\n"
        else:
            outputStr += declareSort + "person" + ")\n"
            for val in nounList:
                outputStr += declareConst + val + " person" + ")\n"

        return outputStr

    def addRules_EntityNotEqual(self, nounList, outputStr):
        objectNotEqual = "(assert (not (= "                      # need 2 )
        length = len(nounList)
        i = 0
        while i < length:
            j = i + 1
            while j < length:
                outputStr += objectNotEqual + nounList[i] + ' ' + nounList[j] + ')))\n'
                j += 1
            i += 1

        return outputStr

    def addRules_EntityRange(self, nounList, thingOrPerson, outputStr):
        objectThingRange = "(assert (forall ((x thing)) "         # need 3 )
        objectPersonRange = "(assert (forall ((x person)) "       # need 3 )
        length = len(nounList)
        if length < 1:
            return outputStr
        else:
            if length == 1:
                if thingOrPerson:
                    return outputStr + objectPersonRange + "(= x " + nounList[0] + ")))\n"
                else:
                    return outputStr + objectThingRange + "(= x " + nounList[0] + ")))\n"
            else:
                if thingOrPerson:
                    outputStr += objectPersonRange + "(or "
                    for thing in nounList:
                        outputStr += '(= x ' + thing + ') '
                else:
                    outputStr += objectThingRange +  "(or "
                    for person in nounList:
                        outputStr += '(= x ' + person + ') '
                outputStr += ')))\n'
        return outputStr

    #all_kb_verbs: [{number : {string, string, list}]
    def addDeclareRel(self, all_kb_verbs, outputStr):
        declareRel = "(declare-rel "                            # need 1 )
        addedVerbName = []
        for verbInfo in all_kb_verbs:
            for verbIndex, relatedInfo in verbInfo.items():
                combinedVerbName =  relatedInfo["combinedVerbName"]
                if combinedVerbName not in addedVerbName:
                    outputStr += declareRel + combinedVerbName + " ("
                    for noun in relatedInfo["relatedNouns"]:
                        if noun[1]:
                            outputStr += "person "
                        else:
                            outputStr += "thing "
                    outputStr += "))\n"
                addedVerbName.append(combinedVerbName)

        return outputStr

    def addRules_ClosedReasonAssumption(self, kbList, verbList, outputStr):
        for i in range(len(kbList)):
            outputStr = self.addOneEntailmentSentence(kbList[i], verbList[i], outputStr)
        return outputStr

    def addOneEntailmentSentence(self, kb, verbs_nouns, outputStr):
        tokens = kb["Lemmatized tokens:"]
        children = kb["Dependency children:"]
        tokensToIndexMap = {}
        i = 0
        for token in tokens:
            tokensToIndexMap[token] = i
            i += 1

        #antecedent, secedent used to save the verbs' index
        antecedent = []
        secedent = []
        findThen = False

        #find tokens in verbs_nouns
        #originalVerbNameList used to record the original name of a verb
        originalVerbNameList = []
        for verbIndex, verbInfo in verbs_nouns.items():
            originalVerbName = verbInfo["originalVerbName"]
            originalVerbNameList.append(originalVerbName)

        for word in tokens:
            if findThen:
                if word in originalVerbNameList:
                    secedent.append(tokensToIndexMap[word])
            else:
                if word in originalVerbNameList:
                    antecedent.append(tokensToIndexMap[word])
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

        #antecedent is a dict, map original verb name to combined verb name
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
            addedVariable = []
            for index in antecedent:
                verbInfo = verbs_nouns[index]
                nouns = verbInfo["relatedNouns"]
                nums = len(nouns)
                for i in range(nums):
                    #nouns[i][2] is a boolean value, if it is true, this noun is a variable, else it is a constant
                    nounNameIndex = nouns[i][0]
                    nounName = tokens[nounNameIndex]
                    #combine "person" and "b" to get "b"'s full name
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
                    if nouns[i][2] and nounName not in addedVariable:
                        addedVariable.append(nounName)
                        if nouns[i][1]:
                            declareNounString += "(" + pronouns[number] + " person) "
                            persons.append(pronouns[number])
                        #false for thing
                        else:
                            declareNounString += "(" + pronouns[number] + " thing) "
                            things.append(pronouns[number])

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
                        valNotEqualStr += "(not (= " + persons[i] + ' ' + persons[j] + ')) '
                        notEqualPairs += 1

            if thingLength >= 2:
                for i in range(thingLength):
                    for j in range(i + 1, thingLength):
                        valNotEqualStr += "(not (= " + things[i] + ' ' + things[j] + ')) '
                        notEqualPairs += 1
            #if there exists more than one not equal pair, we should add 'and' to connect them
            if notEqualPairs >= 2:
                valNotEqualStr = "(and " + valNotEqualStr + ") "

            outputStr += valNotEqualStr

            #---adding reality sentences
            #addedVerbs record the verb's index when the verb is translated into z3
            addedVerbs = []
            realitySentence = "(=> "

            #verbsInSentence is antecedent or secedent
            #here, it is a list containing verbs' index
            def addingReality(verbsInSentence):
                realitySentence = ""
                #counts there exists how many verbs
                verbCounts = 0
                for verbIndex in verbsInSentence:
                    if verbIndex not in addedVerbs:
                        verbCounts += 1
                        hasOneVerb = True
                        originalVerbName = verbs_nouns[verbIndex]["originalVerbName"]
                        child = children[tokensToIndexMap[originalVerbName]]
                        index = child.find("conj:")
                        anotherVerbIndex = -1
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
                            addedVerbs.append(anotherVerbIndex)
                            addedVerbs.append(verbIndex)
                            #transform original verb name into combined verb name

                        #---adding sentence for verbs
                        def addVerbSentence(verbIndex):
                            if verbIndex == -1:
                                return ""
                            verbInfo = verbs_nouns[verbIndex]
                            verb = verbInfo["combinedVerbName"]
                            nouns = verbInfo["relatedNouns"]
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
                                    verbStr += tokens[noun[0]] + ' '
                            return verbStr + ') '

                        realitySentence += addVerbSentence(verbIndex)
                        realitySentence += addVerbSentence(anotherVerbIndex)
                        if relation != "":
                            realitySentence += ") "

                if verbCounts > 1:
                    realitySentence = "(and " + realitySentence + ") "
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
        verb_nouns = self.findVerbsNouns(question)
        for verbIndex, verbInfo in verb_nouns.items():
            verbName = verbInfo["combinedVerbName"]
            nouns = verbInfo["relatedNouns"]
            verbSentence = "(" + verbName + " "
            addingNouns = []
            #find the noun that is variable
            for noun in nouns:
                nounIndex = noun[0]
                tag = tags[nounIndex]
                if tag == "WP":
                    addingNouns.append("WP")
                else:
                    addingNouns.append(tokens[nounIndex])

            #substitue the variable noun with the candidate answer noun
            for i in range(length):
                trueSentence = "(" + verbName
                for symbol in addingNouns:
                    if symbol == "WP":
                        trueSentence += " " + nounList[i]
                    else:
                        trueSentence += " " + symbol
                trueSentence += ") "

                falseSentence = ""
                for j in range(length):
                    if i != j:
                        falseSentence += "(not (" + verbName
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
    
    def addDescription(self, outputStr):
        verb_nouns = self.findVerbsNouns(self.description)
        answerTokens = self.question["Lemmatized tokens:"]
        descriptionTokens = self.description["Lemmatized tokens:"]
        headString = "(assert ("
        for verbIndex, verbInfo in verb_nouns.items():
            originalVerbName = verbInfo["originalVerbName"]
            combinedVerbName = verbInfo["combinedVerbName"]
            if originalVerbName not in answerTokens:
                outputStr += headString + combinedVerbName + ' '
                nouns = verbInfo["relatedNouns"]
                for noun in nouns:
                    nounIndex = noun[0]
                    nounName = descriptionTokens[nounIndex]
                    outputStr += nounName + ' '
                outputStr += '))\n'

        
        return outputStr


    def reasoning(self, personNouns, thingNouns, outputStr):
        question = self.question
        tokens = question["Lemmatized tokens:"]
        tags = question["POS tags:"]
        verb = ""
        i = 0
        for tag in tags:
            if "VB" in tag and "AUX" not in tag:
                verb = tokens[i]
            i += 1

        headString = "(assert (not "
        nounList = []
        #person answer
        if "who" in tokens or "whom" in tokens:
            nounList = personNouns
        #thing answer
        else:
            nounList = thingNouns

        length = len(nounList)
        i = 0
        verbs = self.findVerbsNouns(question)
        answer = ""
        for verbIndex, verbInfo in verbs.items():
            addingNouns = []
            #find the noun that is variable
            for noun in verbInfo["relatedNouns"]:
                nounIndex = noun[0]
                tag = tags[nounIndex]
                if tag == "WP":
                    addingNouns.append("WP")
                else:
                    addingNouns.append(tokens[nounIndex])
            i = 0
            for noun in nounList:
                i += 1
                verbSentence = "(" + verbInfo["combinedVerbName"]
                for symbol in addingNouns:
                    if symbol == "WP":
                        verbSentence += " " + noun
                    else:
                        verbSentence += " " + symbol
                self.output = outputStr + headString + verbSentence + ')))\n'
                self.output += "(check-sat)\n"
                fileName = "testOutput_" + str(i)
                self.writeIntoFile(fileName)
                #execute command line verification and get the output
                #the end char is  '\n', delete it
                var = os.popen("z3 " +  fileName).read()[:-1]
                print ("verification result:" + noun + " " + var)
                if str(var) == "unsat":
                    answer = noun
        return answer
                


    def translateIntoZ3(self):
        all_thing_names = []
        all_person_names = []
        candidateAnswer_thing = []
        candidateAnswer_person = []
        all_kb_verbs = []
        output = ""

        description = self.description
        children = description["Dependency children:"]
        tokens = description["Lemmatized tokens:"]
        tags = description["POS tags:"]
        for kb in self.kbList:
            verbs = self.findVerbsNouns(kb)
            all_kb_verbs.append(verbs)
            i = 0
            verbTokens = {}
            for verbIndex, info in verbs.items():
                verbTokens[info["originalVerbName"]] = verbIndex 
            #find nouns in the description
            descriptionVerbInfo = self.findVerbsNouns(self.description)
            verbNameToIndexMap = {}
            for index, info in descriptionVerbInfo.items():
                verbNameToIndexMap[info["originalVerbName"]] = index
            for word in tokens:
                #finding nouns
                if word in verbTokens.keys():
                    relatedNouns = descriptionVerbInfo[verbNameToIndexMap[word]]["relatedNouns"]
                    j = 0
                    for nounInfo in relatedNouns:
                        index = nounInfo[0]
                        noun = tokens[index]
                        verbIndex = verbTokens[word]
                        personOrNot = verbs[verbIndex]["relatedNouns"][j][1]
                        if personOrNot:
                            if noun not in all_person_names:
                                #if noun is not a PRP, add it into candidateAnswer
                                if tags[index] != "PRP":
                                    candidateAnswer_person.append(noun)
                                all_person_names.append(noun)
                        else:
                            if noun not in all_thing_names:
                                if tags[index] != "PRP":
                                    candidateAnswer_thing.append(noun)
                                all_thing_names.append(noun)
                        j += 1
                i += 1
            #find nouns in the kb
            for verbIndex, verbInfo in verbs.items():
                for noun in verbInfo["relatedNouns"]:
                    nounIndex = noun[0]
                    nounName = kb['Lemmatized tokens:'][nounIndex]
                    #if noun is not a variable
                    if not noun[2]:
                        #if noun has not been added into candidate:
                        if nounName not in all_thing_names and nounName not in all_person_names:
                            #if noun is a person
                            if noun[1]:
                                all_person_names.append(nounNme)
                            else:
                                all_thing_names.append(nounName)
        output = self.addDeclareSort(all_thing_names, False, output)
        output = self.addDeclareSort(all_person_names, True, output)
        output = self.addDeclareRel(all_kb_verbs, output)
        output = self.addRules_EntityNotEqual(all_thing_names, output)
        output = self.addRules_EntityNotEqual(all_person_names, output)
        output = self.addRules_EntityRange(all_thing_names, False, output)
        output = self.addRules_EntityRange(all_person_names, True, output)
        output = self.addRules_ClosedReasonAssumption(self.kbList, all_kb_verbs, output)
        output = self.addRules_OnlyOneAnswer(candidateAnswer_person, candidateAnswer_thing, output)
        output = self.addDescription(output)
        self.output = output
        print ("Description" + self.context[0])
        print ("Added KB" + self.context[1])
        print ("Question" + self.context[2])
        answer = self.reasoning(candidateAnswer_person, candidateAnswer_thing, output)
        print ("Answer is " + answer)
    
    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.output)

test = translater()
test.load("test1")
test.writeIntoFile("test1_output")
