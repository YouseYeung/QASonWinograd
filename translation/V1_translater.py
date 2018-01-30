import os
import string

class translater(object):
    def __init__(self):
        #tokens: words
        #pos tags: type of words
        #ner tags: mark if a word is the type of person
        #dependency children: words' dependency
        self.parsingResult = {}
        self.description = {}
        self.question = {}
        self.kbList = []
        self.context = []
        self.addedVerbs = []
        #z3 keywords, these words can not be declared as a rel, we have to add '_' in front of the word.
        self.outputStr = ""
        self.possesionVerbs = []
        self.questionVerbNames = []
        self.parsingSymbol = ['Tokens:', 'Lemmatized tokens:', 'POS tags:', 'NER tags:', 'NER values:', 'Dependency children:']
        self.keywords = ["repeat", "assert", "declare"]
        self.existVars = ["somebody", "something", "sth", "sb", "he", "it"]
        self.pronounList = ["it", "he", "she", "they", "I", "you", "It", "He", "She", "They", "You"]
        self.questionAnswerTags = ["WP", "WDT", "WRB", "WP$"]
        self.reverseKeywords = ["but", "although"]

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
                    self.addedVerbs = []
                    self.possesionVerbs = []
                    self.questionVerbNames = []
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

    def findIndexBySymbol(self, child, symbol):
        indexStart = child.find(symbol)
        if indexStart == -1:
            return -1
        else:
            indexStart += child[indexStart:].find('->') + len('->')
            index = ""
            for c in child[indexStart:]:
                if c.isdigit():
                    index += c
                else:
                    break
            if index == "":
                return -1
            return int(index)

    #return {its index : [its related nouns' index]}
    def findCompleteNouns(self, library):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        #{nounIndex: [relatedNounsIndex1, relatedNounsIndex2, ...]}
        nouns = {}
        i = 0
        for tag in tags:
            if "NN" in tag:
                child = children[i]
                #adj noun
                symbols = ["amod", "compound", "nmod:poss"]
                relatedNounsIndex = []
                for symbol in symbols:
                    index = self.findIndexBySymbol(child, symbol)
                    if index != -1:
                        relatedNounsIndex.append({"tag":symbol, "index":index})
                if relatedNounsIndex != []:
                    nouns[i] = sorted(relatedNounsIndex, key = lambda x : x["index"])

            i += 1

        return nouns

    def findRelatedNouns(self, library, index):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        verbChildren = children[index][1:-1].split(',')
        typeOfNoun = ['subj', 'iobj', 'dobj', 'nmod', 'xcomp', 'advmod']
        relatedNounsIndex = []
        for _type in typeOfNoun:
            i = self.findIndexBySymbol(children[index], _type)
            if i != -1:
                #add the word if it is a noun
                if "NN" in tags[i] or "PRP" in tags[i] or tags[i] in self.questionAnswerTags:
                    relatedNounsIndex.append(i)
                #find more nouns in its related word's children
                if (_type == 'xcomp' and ("NN" in tags[i] or "PRP" in tags[i])) or (_type == 'advmod' and tags[i] == "IN"):
                    additiveNounsIndex = self.findRelatedNouns(library, i)
                    for ii in additiveNounsIndex:
                        relatedNounsIndex.append(ii)

        return relatedNounsIndex

    #library: dict. It is descrption, kb or question
    def findVerbsAndItsRelatedNouns(self, library):
        existVars = self.existVars
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        #{index: {"originalVerbName":str, combinedVerbName:str, "relatedNouns":[{"index":nounIndex, "sort":nounSort, "var":symbolOfVariable}] } }
        verbs = {}
        addedVerbsIndex = []
        i = -1
        tagLength = len(tags)
        for tag in tags:
            i += 1
            child = children[i]
            originalVerbName = tokens[i]
            if originalVerbName in self.keywords:
                originalVerbName = "_" + originalVerbName
            combinedVerbName = originalVerbName
            #every form of verb as a binary or more parameter predciate
            if i not in addedVerbsIndex and ("VB" in tag or "JJ" in tag or "RB" in tag or "NN" in tag):
                #determine whether a vbd-aux has to be added as a verb.
                #do better than => add it.
                #does study good => negelect it
                #is good, => negelect it
                if tag == "VBD-AUX":
                    #if it is "be"
                    if tokens[i] == "be":
                        continue
                    if i + 1 < tagLength:
                        #if it is does + vb
                        if "VB" in tags[i + 1]:
                            continue
                        #if it is does +
                        if "not" == tokens[i + 1]:
                            continue
                #be + adj as an unary predicate, be + adv
                if "JJ" in tag or"RB" in tag or "NN" in tag:
                    if child.find("cop") == -1 and child.find("auxpass") == -1:
                        continue
                #find negative form
                if "neg" in child:
                    combinedVerbName = "not_" + combinedVerbName

                #combine prep or adv to get the combined form of verb.
                index = self.findIndexBySymbol(child, "advmod")
                if index != -1:
                    advName = tokens[index]
                    if advName != "then":
                        combinedVerbName += "_" + advName
                index = self.findIndexBySymbol(child, "amod")
                if index != -1:
                    adjName = tokens[index]
                    combinedVerbName += "_" + adjName

                index = self.findIndexBySymbol(child, "xcomp")
                if index != -1 and ("JJ" in tags[index] or "RB" in tags[index]):
                    advName = tokens[index]
                    if advName != "then":
                        combinedVerbName += "_" + advName

                indexStart = child.find("nmod")
                if indexStart != -1:
                    indexEnd = child[indexStart:].find("->") + indexStart
                    prepName = child[indexStart + len("nmod:"):indexEnd]
                    combinedVerbName += "_" + prepName

                #address the condition: do better than
                index = self.findIndexBySymbol(child, "obj")
                if index != -1:
                    if "JJ" in tags[index]:
                        adjName = tokens[index]
                        combinedVerbName += "_" + adjName
                #if verb is the form of "not" + prep
                #change originalVerbName into a combinedVerbName
                if originalVerbName == "not":
                    originalVerbName = combinedVerbName
                verbs[i] = {"originalVerbName":originalVerbName, "combinedVerbName":combinedVerbName}
                
                relatedNounsIndex = self.findRelatedNouns(library, i)
                verbs[i]["relatedNouns"] = []
                for index in relatedNounsIndex:
                    nounInfo = {"index":index}
                    nounName = tokens[index]
                    #determine if noun name is a variable?
                    if len(nounName) == 1:
                        lastWordIndex = index - 1
                        nounInfo["sort"] = tokens[lastWordIndex]
                        nounInfo["var"] = True
                    elif nounName in existVars:
                        if nounName == "somebody" or nounName == "sb":
                            nounInfo["sort"] = "person"
                            nounInfo["var"] = True
                        elif nounName == "something" or nounName == "sth":
                            nounInfo["sort"] = "thing"
                            nounInfo["var"] = True
                    elif tags[index] in self.questionAnswerTags:
                        if nounName == "who" or nounName == "whom" or nounName == "whose":
                            nounInfo["sort"] = "person"
                        else:
                            nounInfo["sort"] = "thing"
                        nounInfo["var"] = False
                    else:
                        nounInfo["sort"] = "thing"
                        nounInfo["var"] = False
                    verbs[i]["relatedNouns"].append(nounInfo)

                verbs[i]["relatedNouns"] = sorted(verbs[i]["relatedNouns"], key = lambda x : x["index"], reverse = False)
                addedVerbsIndex.append(i)

                #combination of verb and verb, such as make sure to do, want to do, try to do, has to do
                combinedindexStart = children[i].find("xcomp")
                if combinedindexStart != -1:
                    nsubj = verbs[i]["relatedNouns"][0]
                    index = self.findIndexBySymbol(children[i], "xcomp")
                    #if complement is not a verb
                    if "VB" not in tags[index]:
                        #address condition such as "make sure to do" 
                        if children[index].find("xcomp") != -1:
                            index = self.findIndexBySymbol(children[index], "xcomp")
                        else:
                            continue
                    if index in addedVerbsIndex:
                        continue
                    combinedVerbName = tokens[index]
                    verbs[index] = {"originalVerbName":combinedVerbName, "combinedVerbName":combinedVerbName}
                    verbs[index]["relatedNouns"] = [nsubj]
                    relatedNounsIndex = self.findRelatedNouns(library, index)
                    for ii in relatedNounsIndex:
                        nounInfo = {"index":ii}
                        nounName = tokens[ii]
                        #determine if noun name is a variable?
                        if len(nounName) == 1:
                            lastWordIndex = ii - 1
                            nounInfo["sort"] = tokens[lastWordIndex]
                            nounInfo["var"] = True
                        else:
                            nounInfo["sort"] = "thing"
                            nounInfo["var"] = False
                        verbs[index]["relatedNouns"].append(nounInfo)
                    verbs[index]["relatedNouns"] = sorted(verbs[index]["relatedNouns"], key = lambda x : x["index"], reverse = False)
                    addedVerbsIndex.append(index)
        return verbs

    def addDeclareSort(self, nounSortMap):
        if nounSortMap == {}:
            return ""
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                         # need 1 )
        res = ""
        addedName = {}
        for sortName, nouns in nounSortMap.items():
            res += declareSort + sortName + ")\n"
            for name in nouns:
                if not addedName.has_key(name):
                    res += declareConst + name + ' ' + sortName + ")\n"
                    addedName[name] = True

        return res
    def addRules_EntityNotEqual(self, nounSortMap):
        objectNotEqual = "(assert (not (= "                      # need 2 )
        res = ""
        for index, nouns in nounSortMap.items():
            i = 0
            length = len(nouns)
            while i < length:
                j = i + 1
                while j < length:
                   res += objectNotEqual + nouns[i] + ' ' + nouns[j] + ')))\n'
                   j += 1
                i += 1
        return res
    def addRules_EntityRange(self, nounSortMap):
        res = ""
        for sort, nounList in nounSortMap.items():
            length = len(nounList)
            if length < 1:
                continue
            else:
                res += "(assert (forall " + "((x " + sort + ")) "      # need 3 )
                if length == 1:
                    res += "(= x " + nounList[0] + ")))\n"
                else:
                    res += "(or "
                    for noun in nounList:
                        res += '(= x ' + noun + ') '
                    res += ')))\n'
        return res

    def addDeclareRel(self, verbs):
        declareRel = "(declare-rel "                            # need 1 )
        res = ""
        for index, info in verbs.items():
            combinedVerbName =  info["combinedVerbName"]
            originalVerbName = info["originalVerbName"]
            if combinedVerbName not in self.addedVerbs:
                res += declareRel + combinedVerbName + " ("
                for noun in info["relatedNouns"]:
                    res += noun["sort"] + " "
                res += "))\n"
                #add all declared verbs into list addedverb
                self.addedVerbs.append(combinedVerbName)

            #descending grade for verbs to get predicates with less parameter
            number = 1
            nouns = ""
            if combinedVerbName != originalVerbName:
                if originalVerbName not in self.addedVerbs:
                    #remove last parameter
                    for noun in info["relatedNouns"][:-1]:
                        lessPredicateVerbName = originalVerbName + "_" + str(number)
                        if lessPredicateVerbName in self.addedVerbs:
                            continue
                        res += declareRel + lessPredicateVerbName + " ("
                        nouns += noun["sort"] + " "
                        res += nouns + "))\n"
                        self.addedVerbs.append(lessPredicateVerbName)
                        number += 1

            #additional verb for negative verb
            if "not" in combinedVerbName:
                newVerbName = combinedVerbName[len("not_"):]
                if newVerbName not in self.addedVerbs:
                    res += declareRel + newVerbName + " ("
                    for noun in info["relatedNouns"]:
                        res += noun["sort"] + " "
                    res += "))\n"
                    self.addedVerbs.append(newVerbName)

        return res

    def addPrepVerbToVerbEntailment(self):
        addedVerbs = {}
        res = ""
        for kb in self.kbList:
            headString = "(assert (forall ("
            tokens = kb["Lemmatized tokens:"]
            verbs = self.findVerbsAndItsRelatedNouns(kb)
            completeNouns = self.findCompleteNouns(kb)
            for index, info in verbs.items():
                combinedVerbName = info["combinedVerbName"]
                originalVerbName = info["originalVerbName"]
                if combinedVerbName != originalVerbName and not addedVerbs.has_key(originalVerbName):
                    addedVerbs[originalVerbName] = True
                    nouns = info["relatedNouns"]
                    number = 1
                    combinedVerbString = "(" + combinedVerbName + " "
                    lessParaPredicateString = []
                    addedNouns = ""
                    nounDeclareString = ""
                    for noun in nouns:
                        originalVerbString = "(" + originalVerbName + "_" + str(number) + " "
                        if noun["var"]:
                            pronoun = chr(ord('a') + number)
                            addedNouns += pronoun + " "
                            nounDeclareString += "(" + pronoun + " " + noun["sort"] + ") "
                        else:
                            addedNouns += self.getCompleteNounNameByIndex(noun["index"], completeNouns, tokens, True) + " "
                        if number != len(nouns):
                            lessParaPredicateString.append(originalVerbString + addedNouns + ")")
                        number += 1
                    combinedVerbString += addedNouns + ") "
                    nounDeclareString += ") "
                    for string in lessParaPredicateString:
                        res += headString + nounDeclareString + "(=> " + combinedVerbString + string + ")))\n"
        return res
    def getAntecedentAndSecedent(self, tokens):
        length = len(tokens)
        sepIndex = -1
        for i in range(length):
            if tokens[i] == "then":
                sepIndex = i
                break
        return sepIndex

    def getCompleteNounNameByIndex(self, nounIndex, relatedNounsMap, tokens, possesionSymbol):
        nounName = tokens[nounIndex]
        if relatedNounsMap.has_key(nounIndex):
            relatedNounsIndex = relatedNounsMap[nounIndex]
            for info in relatedNounsIndex:
                i = info["index"]
                tag = info["tag"]
                #if it doesn't have to add possesion noun, then neglect it
                if not possesionSymbol or tag != "nmod:poss":
                    if i < nounIndex:
                        nounName = tokens[i] + "_" + nounName
                    else:
                        nounName += "_" + tokens[i]
        return nounName

    #Add reality : sth is noun, sth is adj, sth is doing sth.
    def addReality_IS_Relation(self, library, verbs, outputStr):
        res = ""
        headString = "(assert ("
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        sepIndex, i = -1, 0
        for tag in tags:
            if tag == "VBD-AUX":
                sepIndex = i
                break
            i += 1
        i = 0
        completeNouns = self.findCompleteNouns(library)
        #sth is doing sth, sth is adj.
        if verbs != {}:
            for index, info in verbs.items():
                verbName = info["combinedVerbName"]
                if verbName not in self.addedVerbs:
                    verbName = info["originalVerbName"]
                    if verbName not in self.addedVerbs:
                        continue
                nouns = info["relatedNouns"]
                res += headString + verbName + " "
                for noun in nouns:
                    nounIndex = noun["index"]
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                    res += nounName + " "
                res += "))\n"
        #sth is sth
        else:
            subjIndex, objIndex = -1, -1
            subjName, objName = "", ""
            i = sepIndex - 1
            while i >= 0:
                if "NN" in tags[i]:
                    subjIndex = i
                    break
                i -= 1
            i = sepIndex + 1
            while i < len(tags):
                if "NN" in tags[i]:
                    objIndex = i
                    break
                i += 1
            subjName = self.getCompleteNounNameByIndex(subjIndex, completeNouns, tokens, False)
            objName = self.getCompleteNounNameByIndex(objIndex, completeNouns, tokens, False)
            res += headString + "= " + subjName + " " + objName + "))\n"
            #revision of the rule of the inequality of entities
            entityNotEqualStr1 = "(assert (not (= " + subjName + " " + objName + ")))\n"
            entityNotEqualStr2 = "(assert (not (= " + objName + " " + subjName + ")))\n"
            index = outputStr.find(entityNotEqualStr1)
            if index != -1:
                outputStr = outputStr[:index] + outputStr[index + len(entityNotEqualStr1):]
            index = outputStr.find(entityNotEqualStr2)
            if index != -1:
                outputStr = outputStr[:index] + outputStr[index + len(entityNotEqualStr2):]
        return outputStr + res

    def findAnswerPredicate(self):
        question = self.question
        verbs = self.findVerbsAndItsRelatedNouns(question)
        combinedName = ""
        originalName = ""
        for index, info in verbs.items():
            combinedName = info["combinedVerbName"]
            originalName = info["originalVerbName"]
        return originalName, combinedName

    def findTypeOfEntailment(self, antecedent, secedent):
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
        type_ABC2 = "AvB>C, C>A, C>B"
        orgAnsPreName, comAnsPreName = self.findAnswerPredicate()
        #answer predicate in antecedent
        if orgAnsPreName in antecedent or comAnsPreName in antecedent:
            if "and" in secedent or "or" in secedent:
                return type_ABC1
            elif "or" in antecedent:
                return type_ABC2
            else:
                return type_AB2
        #answer predicate in secedent
        elif orgAnsPreName in secedent or comAnsPreName in secedent:
            if "or" in secedent:
                return type_ABC1
            else:
                return type_AB1
        return type_AB2
    def addReality_Entailment(self, library, verbs, sepIndex, outputStr):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        antecedent = tokens[:sepIndex]
        secedent = tokens[sepIndex + 1:]
        entailmentType = self.findTypeOfEntailment(antecedent, secedent)
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
        outputStr += self.addEntailment(library, verbs, entailmentType, sepIndex)
        return outputStr

    #return string and pronoun_name map
    def addVariableDeclare(self, library, verbs):
        headString = "(assert (forall ("
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        pronouns = []
        existVars = self.existVars
        for i in range(26):
            pronouns.append(chr(ord('a') + i))
        numOfPronoun = 0
        pronoun_name_Map ={}
        addedPronoun = []
        sortNameMap = {}
        completeNouns = self.findCompleteNouns(library)
        for index, info in verbs.items():
            nouns = info["relatedNouns"]
            for noun in nouns:
                nounIndex = noun["index"]
                nounName = tokens[nounIndex]
                sort = noun["sort"]
                if noun["var"]:
                    if nounName not in existVars:
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                        if not pronoun_name_Map.has_key(nounName):
                            pronoun = pronouns[numOfPronoun]
                            addedPronoun.append(pronoun)
                            pronoun_name_Map[nounName] = pronoun
                            headString += "(" + pronoun + " " + sort + ") " 
                            if sortNameMap.has_key(sort):
                                sortNameMap[sort].append(pronoun)
                            else:
                                sortNameMap[sort] = [pronoun]
                            numOfPronoun += 1
                    else:
                        pronoun_name_Map[nounName] = pronouns[numOfPronoun]
                        if nounName == "somebody" or nounName == "sb":
                            pronoun_name_Map["he"] = pronouns[numOfPronoun]
                        elif nounName == "something" or nounName == "sth":
                            pronoun_name_Map["it"] = pronouns[numOfPronoun]
                        numOfPronoun += 1
                else:
                    #address the condition of possesion
                    child = children[nounIndex]
                    i = child.find("nmod:poss")
                    if i != -1:
                        i = self.findIndexBySymbol(child, "nmod:poss")
                        name = tokens[i]
                        if not pronoun_name_Map.has_key(name):
                            pronoun = pronouns[numOfPronoun]
                            if name == "somebody":
                                numOfPronoun += 1
                                pronoun_name_Map[name] = pronoun
                                pronoun_name_Map["he"] = pronoun
                            elif name == "something":
                                numOfPronoun += 1
                                pronoun_name_Map[name] = pronoun
                                pronoun_name_Map["it"] = pronoun
                            else:
                                i = children[i].find("compound")
                                if i != -1:
                                    i = self.findIndexBySymbol(children[i], "compound")
                                    compoundNoun = tokens[i]
                                    compoundNounName = compoundNoun + "_" + name
                                    if compoundNoun == "person":
                                        numOfPronoun += 1
                                        pronoun_name_Map[compoundNounName] = pronoun
                                    elif compoundNoun == "thing":
                                        numOfPronoun += 1
                                        pronoun_name_Map[compoundNounName] = pronoun
        headString += ") "
        notEqualPairs = 0
        entityNotEqualString = ""
        for sort, names in sortNameMap.items():
            length = len(names)
            if length > 1:
                for i in range(length):
                    for j in range(i + 1, length):
                        entityNotEqualString += "(not (= " + names[i] + " " + names[j] + ")) "
                notEqualPairs += 1
        if notEqualPairs > 1:
            entityNotEqualString += "(=> (and " + entityNotEqualString + ") "
        elif notEqualPairs == 1:
            entityNotEqualString = "(=> " + entityNotEqualString
        return headString + entityNotEqualString, pronoun_name_Map

    def addEntailment(self, library, verbs, entailmentType, sepIndex):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A" 
        type_ABC2 = "AvB>C, C>A, C>B"
        antecedent = []
        secedent = []
        addedVerbsIndex = []        
        antecedentString = ""
        secedentString = ""
        for index, info in verbs.items():
            if index < sepIndex:
                antecedent.append([index, info])
            else:
                secedent.append([index, info])

        antecedent = sorted(antecedent, key = lambda x : x[0])
        secedent = sorted(secedent, key = lambda x : x[0])
        def addRealityByAntAndSec(antecedent, secedent, verbs):
            newVerbs = {}
            for verb in antecedent:
                newVerbs[verb[0]] = verb[1]
            for verb in secedent:
                newVerbs[verb[0]] = verb[1]
            
            declareString, pronoun_name_Map = self.addVariableDeclare(library, newVerbs)
            addedVerbsNum = 0
            #assure that verb occurs in order to get the right relation between verbs, such as conj:and, conj:or
            antecedentString = ""
            secedentString = ""
            for verb in antecedent:
                newString = self.addRealityForOneVerb(library, {verb[0]:verb[1]}, verbs, pronoun_name_Map, addedVerbsIndex)
                if newString != "":
                    antecedentString += newString + " "
                    addedVerbsNum += 1
            if addedVerbsNum > 1:
                antecedentString = "(and " + antecedentString + ")"
            addedVerbsNum = 0
            for verb in secedent:
                newString = self.addRealityForOneVerb(library, {verb[0]:verb[1]}, verbs, pronoun_name_Map, addedVerbsIndex) 
                if newString != "":
                    secedentString += newString + " "
                    addedVerbsNum += 1
            if addedVerbsNum > 1:
                secedentString = "(and " + secedentString + ")"
            variableNum = len(pronoun_name_Map.keys())
            rightBracket = ""
            if variableNum > 1:
                rightBracket = ")"
            return declareString, antecedentString + " " + secedentString + ")))" + rightBracket + "\n"

        if type_AB1 == entailmentType:
            res = ""
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            res = declareString + "(=> " + realityString
            return res
        elif type_AB2 == entailmentType:
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            return declareString + "(= " + realityString

        elif type_ABC1 == entailmentType:
            res = ""
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            res = declareString + "(=> " + realityString
            #revision of the all verbs
            newVerbs = {}
            for verb in antecedent:
                newVerbs[verb[0]] = verb[1]
            for verb in secedent:
                addedVerbsIndex = []
                tempVerbs = newVerbs
                tempVerbs[verb[0]] = verb[1]
                declareString, realityString = addRealityByAntAndSec([verb], antecedent, tempVerbs)
                res += declareString + "(=> " + realityString
            return res
        elif type_ABC2 == entailmentType:
            res = ""
            #neglect the answer antecedent to get description secendent
            #just use description secedent to get answer antecedent
            #example: sculpture roll_off shelf
            #declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            #res = declareString + "(=> " + realityString
            newVerbs = {}
            for verb in secedent:
                newVerbs[verb[0]] = verb[1]
            for verb in antecedent:
                addedVerbsIndex = []
                tempVerbs = newVerbs
                tempVerbs[verb[0]] = verb[1]
                declareString, realityString = addRealityByAntAndSec(secedent[:], [verb], tempVerbs)
                res += declareString + "(=> " + realityString
            return res

    def addExistVarDeclaration(self, token, addedExist, pronoun_name_Map):
        headString = ""
        if "somebody" == token:
            if addedExist:
                headString += " (" + pronoun_name_Map["somebody"] + " person )"
            else:
                headString = "(exists ((" + pronoun_name_Map["somebody"] + " person)"
                addedExist = True
        if "sb" == token:
            if addedExist:
                headString += " (" + pronoun_name_Map["sb"] + " person)"
            else:
                headString = "(exists ((" + pronoun_name_Map["sb"] + " person)"
                addedExist = True
        if "something" == token:
            if addedExist:
                headString += " (" + pronoun_name_Map["something"] + " thing)"
            else:
                headString = "(exists ((" + pronoun_name_Map["something"] + " thing)"
                addedExist = True
        if "sth" == token:
            if addedExist:
                headString += " (" + pronoun_name_Map["sth"] + " thing)"
            else:
                headString = "(exists ((" + pronoun_name_Map["sth"] + " thing)"
                addedExist = True
        return headString

    def addRealityForOneVerb(self, library, theVerb, allVerbs, pronoun_name_Map, addedVerbsIndex):
        headString = ""
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        completeNouns = self.findCompleteNouns(library)
        addedNounName = []
        for index, info in theVerb.items():
            if index in addedVerbsIndex:
                continue
            nouns = info["relatedNouns"]
            verbName = info["combinedVerbName"]
            headString += "(" + verbName
            possesionStrs = []
            for noun in nouns:
                nounIndex = noun["index"]
                nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                posStr = self.addPossesionReality(library, nounIndex, pronoun_name_Map)
                if posStr != "":
                    possesionStrs.append(posStr)
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, True)
                    possesionName = ""
                    child = children[nounIndex]
                    index = self.findIndexBySymbol(child, "nmod:poss")
                    possesionName = tokens[index]
                    #if the verb is related to a possesion noun, then add it into the list
                    self.possesionVerbs.append(verbName)
                    self.possesionVerbs.append(info["originalVerbName"])
                    if possesionName not in addedNounName:
                        addedNounName.append(possesionName)

                addedNounName.append(nounName)
                isVar = noun["var"]
                if isVar:
                    if pronoun_name_Map.has_key(nounName):
                        headString += " " + pronoun_name_Map[nounName]
                    else:
                        print "[ERROR]: incorrect variable name:", nounName
                else:
                    headString += " " + nounName
            headString += ")"
            addedVerbsIndex.append(index)

            child = children[index]
            index = child.find("conj:")
            if index != -1:
                indexStart = index + len("conj:")
                indexEnd = child[indexStart:].find("->") + indexStart
                relation = child[indexStart:indexEnd]
                verbIndex = self.findIndexBySymbol(child, "conj:")
                if allVerbs.has_key(verbIndex):
                    if relation == "and" or relation == "or":
                        headString = "(" + relation + " " + headString + " " + self.addRealityForOneVerb(library, {verbIndex:allVerbs[verbIndex]}, allVerbs, pronoun_name_Map, addedVerbsIndex) + ")"
                else:
                    print "[ERROR]: Verb name and its related verb's index doesn't not exist:", verbName, verbIndex
        
            #add possesion reality
            if possesionStrs != []:
                headString = "(and " + headString
                for posStr in possesionStrs:
                    headString += " " + posStr + " "
                headString += ")"

        #add exist variable
        existDeclareString = ""
        addedExist = False
        for nounName in addedNounName:
            #neglect "he" and "it"
            if nounName in self.existVars[:-2]:
                existDeclareString = self.addExistVarDeclaration(nounName, addedExist, pronoun_name_Map)
                addedExist = True
        if addedExist:
            existDeclareString += ") "
            return existDeclareString + headString + ") "
        else:
            return headString

    def addDeclareRel_Possesion(self, library):
        children = library["Dependency children:"]
        headString = "(declare-rel "
        res = ""
        added = False
        for child in children:
            index = child.find("nmod:poss")
            if not added and index != -1:
                #tt for thing thing, tp for thing person
                paraTags = ["tt", "pt"]
                tagNounMap = {"t" : "thing", "p": "person"}
                for pTag in paraTags:
                    verbName = "posses" + "_" + pTag
                    if verbName not in self.addedVerbs:
                        res += headString + verbName + " (" + tagNounMap[pTag[0]] + " " + tagNounMap[pTag[1]] + "))\n"       
                        self.addedVerbs.append(verbName)
        return res

    def addPossesionReality(self, library, index, pronoun_name_Map):
        children = library["Dependency children:"]
        child = children[index]
        res = ""
        i = child.find("nmod:poss")
        if i != -1:
            tokens = library["Lemmatized tokens:"]
            tags = library["POS tags:"]
            completeNouns = self.findCompleteNouns(library)
            objName = self.getCompleteNounNameByIndex(index, completeNouns, tokens, True)

            subjIndex = self.findIndexBySymbol(child, "nmod:poss")
            subjName = self.getCompleteNounNameByIndex(subjIndex, completeNouns, tokens, False)
            #subjname is a variable
            if subjName == "somebody" or subjName == "his":
                res += "(posses_pt " + pronoun_name_Map[subjName] + " " + objName + ")"
            elif subjName == "something" or subjName == "its":
                res += "(posses_tt " + pronoun_name_Map[subjName] + " " + objName + ")"
            else:
                subjChild = children[subjIndex]
                i = subjChild.find("compound")
                if i != -1:
                    compoundIndex = self.findIndexBySymbol(subjChild, "compound")
                    compoundNoun = tokens[compoundIndex]
                    if compoundNoun == "person":
                        res += "(posses_pt " + pronoun_name_Map[subjName] + " " + objName + ")"
                    else:
                        res += "(posses_tt " + pronoun_name_Map[subjName] + " " + objName + ")"   
                #subjname is a constant
                else:
                    res += "(posses_pt "+ subjName + "_p " + objName + ") "
                    res += "(posses_tt " + subjName + "_t " + objName + ") "   
        return res

    def addRules_ClosedReasonAssumption(self, library, verbs, outputStr):
        tokens = library["Lemmatized tokens:"]
        sepIndex  = self.getAntecedentAndSecedent(tokens)
        if sepIndex == -1:
            return self.addReality_IS_Relation(library, verbs, outputStr)
        else:
            return self.addReality_Entailment(library, verbs, sepIndex, outputStr)

    def addRules_NegativeFormEntailment(self, library, verbs, outputStr):
        addedVerbs = []
        res = ""
        for index, info in verbs.items():
            combinedVerbName = info["combinedVerbName"]
            if "not" in combinedVerbName and combinedVerbName not in addedVerbs:
                addedVerbs.append(combinedVerbName)
                i = combinedVerbName.find("not")
                newVerbName = combinedVerbName[i + len("not_"):]
                newVerb = {}
                newVerb[index] = {"combinedVerbName": newVerbName, "originalVerbName": newVerbName, "relatedNouns": info["relatedNouns"]}
                varStr, pronoun_name_Map = self.addVariableDeclare(library, newVerb)
                res += varStr + "(= (not " + self.addRealityForOneVerb(library, newVerb, newVerb, pronoun_name_Map, []) + ")"
                res += " " + self.addRealityForOneVerb(library, {index:info}, {index:info}, pronoun_name_Map, []) + "))))\n"
        return outputStr + res

    #substitue the variable noun with the candidate answer noun
    def findAllAnswerSentence(self, addingNouns, nounList, sentences, string):
        if nounList == [] or addingNouns == []:
            if string not in sentences:
                sentences.append(string)
            return
        symbol = addingNouns[0]
        if symbol in self.questionAnswerTags:
            j = 0
            for noun in nounList:
                newNounList = nounList[:j]
                newNounList[0:0] = nounList[j + 1:]
                self.findAllAnswerSentence(addingNouns[1:], newNounList, sentences, string + noun + " ")
                end = len(noun) + 1
                j += 1
        else:
            string += symbol + " "


    def addRules_OnlyOneAnswer(self, nounSortMap):
        question = self.question
        tokens = question["Lemmatized tokens:"]
        tags = question["POS tags:"]
        headString = "(assert (= "
        res = ""
        nounList = []
        if "who" in tokens or "whom" in tokens:
            if nounSortMap.has_key("person"):
                nounList = nounSortMap["person"]
        else:
            if nounSortMap.has_key("thing"):
                nounList = nounSortMap["thing"]

        verbs = self.findVerbsAndItsRelatedNouns(question)
        for index, info in verbs.items():
            verbName = info["combinedVerbName"]
            if verbName not in self.addedVerbs:
                continue
            nouns = info["relatedNouns"]
            verbSentence = "(" + verbName + " "
            addingNouns = []
            #determine if the noun is an variable
            for noun in nouns:
                nounIndex = noun["index"]
                tag = tags[nounIndex]
                if tag in self.questionAnswerTags:
                    addingNouns.append(tag)
                else:
                    addingNouns.append(tokens[nounIndex])
            
            string = ""
            sentences = []
            removePronounNounList = []
            for noun in nounList:
                if noun not in self.pronounList:
                    removePronounNounList.append(noun)
            nounList = removePronounNounList
            self.findAllAnswerSentence(addingNouns, nounList[:], sentences, string)
            i, length = 0, len(sentences)
            for i in range(length):
                trueSentence = verbSentence + sentences[i] + ") "
                falseSentence = ""
                completeSen = ""
                for j in range(length):
                    if i != j:
                        falseSentence += "(not " + verbSentence + sentences[j] + ")) "
                if length > 2:
                    falseSentence = "(and " + falseSentence + ")"
                res += headString + trueSentence + falseSentence + "))\n"
        return res

    def addDescription(self, nounSortMap):
        verbs = self.findVerbsAndItsRelatedNouns(self.description)
        answerTokens = self.question["Lemmatized tokens:"]
        descriptionTokens = self.description["Lemmatized tokens:"]
        headString = "(assert "
        res = ""
        completeNouns = self.findCompleteNouns(self.description)
        number = 0
        possesionStrs = []
        for index, info in verbs.items():
            originalVerbName = info["originalVerbName"]
            combinedVerbName = info["combinedVerbName"]
            if originalVerbName not in answerTokens:
                verbName = ""
                if combinedVerbName in self.addedVerbs:
                    verbName = combinedVerbName
                elif originalVerbName in self.addedVerbs:
                    verbName = originalVerbName
                else:
                    continue
                res += '(' + verbName + ' '
                nouns = info["relatedNouns"]
                for noun in nouns:
                    nounIndex = noun["index"]
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, False)
                    if verbName in self.possesionVerbs:
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, True)
                        possesionStrs.append(self.addPossesionReality(self.description, nounIndex, nounSortMap))
                    res += nounName + ' '
                res += ') '
                number += 1
        if possesionStrs != []:
            number += 1
            for posStr in possesionStrs:
                res += " " + posStr

        if number >= 2:
            res = headString + "(and " + res + "))\n"
        else:
            res = headString + res + ")\n"
        
        return res

    def reasoning(self, nounSortMap, outputStr):
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
            nounList = nounSortMap["person"]
        #thing answer
        else:
            nounList = nounSortMap["thing"]

        length = len(nounList)
        i = 0
        verbs = self.findVerbsAndItsRelatedNouns(question)
        answer = ""
        for index, info in verbs.items():
            verbName = info["combinedVerbName"]
            nouns = info["relatedNouns"]
            length = len(nouns)
            if verbName not in self.addedVerbs:
                number = length
                verbName = info["originalVerbName"]
                if verbName in self.keywords:
                    verbName = "_" + verbName
                for _ in range(length - 1):
                    lessParaVerbName = verbName + "_" + str(number)
                    if lessParaVerbName in self.addedVerbs:
                        verbName = lessParaVerbName
                        break
                    number -= 1
            if verbName not in self.addedVerbs:
                print "[ERROR]: verb name:[" + verbName + "] not exists"
                continue
            addingNouns = []
            #find the noun that is variable
            for noun in nouns:
                nounIndex = noun["index"]
                tag = tags[nounIndex]
                if tag in self.questionAnswerTags:
                    addingNouns.append(tag)
                else:
                    addingNouns.append(tokens[nounIndex])
            sentences = []
            self.findAllAnswerSentence(addingNouns, nounList, sentences, "")
            for verbSentence in sentences:
                i += 1
                self.outputStr = outputStr + headString + "(" + verbName + " " + verbSentence + ')))\n'
                self.outputStr += "(check-sat)\n"
                fileName = "testOutput_" + str(i)
                self.writeIntoFile(fileName)
                #execute command line verification and get the output
                #the end char is  '\n', delete it
                var = os.popen("z3 " +  fileName).read()[:-1]
                print ("verification result:" + "(" + verbName + " " + verbSentence + ") " + var)
                if str(var) == "unsat":
                    answer = noun
                    break
        print "Answer:", answer
        return answer

    def translateToZ3(self):
        description = self.description
        kbList = self.kbList
        question = self.question
        allVerbs = []
        nounSortMap = {}
        descriptionVerbs = self.findVerbsAndItsRelatedNouns(description)
        questionVerbs = self.findVerbsAndItsRelatedNouns(question)
        questionVerbNames = []
        for index, info in questionVerbs.items():
            questionVerbNames.append(info["combinedVerbName"])
            questionVerbNames.append(info["originalVerbName"])
        self.questionVerbNames = questionVerbNames
        for kb in kbList:
            kbVerbs = self.findVerbsAndItsRelatedNouns(kb)
            allVerbs.append(kbVerbs)
            tokens = kb["Lemmatized tokens:"]
            combinedVerbNameToIndexMap = {}
            originalVerbNameToIndexMap = {}
            #{SortName: [noun1, noun2, ...]}
            completeNouns = self.findCompleteNouns(kb)
            #find nouns in kb
            for index, info in kbVerbs.items():
                nouns = info["relatedNouns"]
                combinedVerbNameToIndexMap[info["combinedVerbName"]] = index
                originalVerbNameToIndexMap[info["originalVerbName"]] = index
                for noun in nouns:
                    if not noun["var"]:
                        sort = noun["sort"]
                        index = noun["index"]
                        nounName1 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, False)
                        nounName2 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, True)
                        if nounSortMap.has_key(sort):
                            if nounName1 not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName1)
                            if nounName2 not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName2)
                        else:
                            if nounName1 == nounName2:
                                nounSortMap[sort] = [nounName1]
                            else:
                                nounSortMap[sort] = [nounName1, nounName2]

            #find nouns in description
            tokens = description["Lemmatized tokens:"]
            completeNouns = self.findCompleteNouns(description)
            for index, info in descriptionVerbs.items():
                verbName = info["combinedVerbName"]
                #if the name of verb is the question verb, pass it
                if verbName in questionVerbNames:
                    continue
                kbindex = -1
                #firstly, use combine name to get verb's info
                if combinedVerbNameToIndexMap.has_key(verbName):
                    kbindex = combinedVerbNameToIndexMap[verbName]
                #if not exists, use original name
                else:
                    verbName = info["originalVerbName"]
                    if verbName in questionVerbNames:
                        continue
                    if originalVerbNameToIndexMap.has_key(verbName):
                        kbindex = originalVerbNameToIndexMap[verbName]
                if kbindex != -1:
                    nouns = info["relatedNouns"]
                    kbinfo = kbVerbs[kbindex]
                    kbNounsInfo = kbinfo["relatedNouns"]
                    length = len(kbNounsInfo)
                    i = 0
                    for noun in nouns:
                        nounIndex = noun["index"]
                        nounName = tokens[nounIndex]
                        if i < length:
                            sort = kbNounsInfo[i]["sort"]
                        else:
                            print "[ERROR]: Wrong number of predicate's parameter"
                            sort = nouns[i]["sort"]
                        nounName1 = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                        nounName2 = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, True)
                        if nounSortMap.has_key(sort):
                            if nounName1 not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName1)
                            if nounName2 not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName2)
                        else:
                            if nounName1 == nounName2:
                                nounSortMap[sort] = [nounName1]
                            else:
                                nounSortMap[sort] = [nounName1, nounName2]
                        #add possesion noun into the sort map
                        nameList1 = nounName1.split("_")
                        nameList2 = nounName2.split("_")
                        possesionName = ""
                        for name in nameList1:
                            if name not in nameList2:
                                possesionName += name + "_"
                        if possesionName != "":
                            #constant noun name + _p presenting person noun, _t presenting thing noun
                            possesionName += "p"
                            if nounSortMap.has_key("person") and possesionName not in nounSortMap["person"]:
                                nounSortMap["person"].append(possesionName)
                            possesionName = possesionName[:-1] + "t"
                            if nounSortMap.has_key("thing") and possesionName not in nounSortMap["thing"]:
                                nounSortMap["thing"].append(possesionName)
                        
                        i += 1

        res = ""
        res += self.addDeclareSort(nounSortMap)
        res += self.addRules_EntityNotEqual(nounSortMap)
        res += self.addRules_EntityRange(nounSortMap)
        
        verbLength = 0
        for verbs in allVerbs:
            verbLength += 1
            res += self.addDeclareRel(verbs)
        i = 0
        for kb in kbList:
            res += self.addDeclareRel_Possesion(kb)
            if i >= verbLength:
                verbs = {}
            else:
                verbs = allVerbs[i]
            res = self.addRules_ClosedReasonAssumption(kb, verbs, res)
            res = self.addRules_NegativeFormEntailment(kb, verbs, res)
            i += 1

        res += self.addPrepVerbToVerbEntailment()
        res += self.addRules_OnlyOneAnswer(nounSortMap)
        res += self.addDescription(nounSortMap)
        if len(self.context) >= 3:
            print "Description:", self.context[0]
            print "Knowledge:",
            for kb in self.context[1:-1]:
                print kb,
            print ""
            print "Quesstion:", self.context[-1]
        self.reasoning(nounSortMap, res)

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.outputStr)


def main():
    t = translater()
    t.load("test1")
    t.translateToZ3()

if __name__ == '__main__':
    main()
