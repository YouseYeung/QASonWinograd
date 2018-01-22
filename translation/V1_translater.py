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
        self.addedVerbs = []
        #z3 keywords, these words can not be declared as a rel, we have to add '_' in front of the word.
        self.keywords = ["repeat", "assert", "declare"]

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
                        relatedNounsIndex.append(index)
                if relatedNounsIndex != []:
                    nouns[i] = sorted(relatedNounsIndex)

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
                if "NN" in tags[i] or "PRP" in tags[i]:
                    relatedNounsIndex.append(i)
                #find more nouns in its related word's children
                if (_type == 'xcomp' and ("NN" in tags[i] or "PRP" in tags[i])) or (_type == 'advmod' and tags[i] == "IN"):
                    additiveNounsIndex = self.findRelatedNouns(library, i)
                    for ii in additiveNounsIndex:
                        relatedNounsIndex.append(ii)
                #find possesion noun
                if children[i].find("nmod:poss") != -1:
                    i = self.findIndexBySymbol(children[i], "nmod:poss")
                    relatedNounsIndex.append(i)

        return relatedNounsIndex

    #library: dict. It is descrption, kb or question
    def findVerbsAndItsRelatedNouns(self, library):
        existVar = ["somebody", "something", "sth", "sb", "he", "it"]
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        #{index: {"originalVerbName":str, combinedVerbName:str, "relatedNouns":[{"index":nounIndex, "sort":nounSort, "var":symbolOfVariable}] } }
        verbs = {}
        addedVerbsIndex = []
        i = -1
        for tag in tags:
            i += 1
            child = children[i]
            originalVerbName = tokens[i]
            if originalVerbName in self.keywords:
                originalVerbName += "_"
            combinedVerbName = tokens[i]

            #every form of verb as a binary or more parameter predciate
            if i not in addedVerbsIndex and (("VB" in tag and "AUX" not in tag) or "JJ" in tag or "RB" in tag):
                #be + adj as an unary predicate, be + adv
                if tag == "JJ" or tag == "RB":
                    if child.find("cop") == -1 and child.find("auxpass") == -1:
                        continue
                #combine prep or adv to get the combined form of verb.
                index = self.findIndexBySymbol(child, "advmod")
                if index != -1:
                    advName = tokens[index]
                    if advName != "then":
                        combinedVerbName += "_" + advName
                indexStart = child.find("nmod")
                if indexStart != -1:
                    indexEnd = child[indexStart:].find("->") + indexStart
                    prepName = child[indexStart + len("nmod:"):indexEnd]
                    combinedVerbName += "_" + prepName
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
                    if len(nounName) == 1 or nounName in existVar:
                        lastWordIndex = index - 1
                        nounInfo["sort"] = tokens[lastWordIndex]
                        nounInfo["var"] = True
                    else:
                        nounInfo["sort"] = "thing"
                        nounInfo["var"] = False
                    verbs[i]["relatedNouns"].append(nounInfo)

                verbs[i]["relatedNouns"] = sorted(verbs[i]["relatedNouns"], key = lambda x : x["index"], reverse = False)
                addedVerbsIndex.append(i)

                #combination of verb and verb, such as make sure to do, want to do, try to do
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
            #to get a form without prep
            if combinedVerbName != originalVerbName:
                if originalVerbName not in self.addedVerbs:
                    res += declareRel + originalVerbName + " ("
                    #remove last parameter
                    noun = info["relatedNouns"][0]
                    res += noun["sort"] + " "
                    res += "))\n"
                self.addedVerbs.append(originalVerbName)
        return res

    def addPrepVerbToVerbEntailment(self):
        addedVerbs = {}
        res = ""
        for kb in self.kbList:
            headString = "(assert (forall ("
            tokens = kb["Lemmatized tokens:"]
            verbs = self.findVerbsAndItsRelatedNouns(kb)
            for index, info in verbs.items():
                combinedVerbName = info["combinedVerbName"]
                originalVerbName = info["originalVerbName"]
                number = 0
                if combinedVerbName != originalVerbName and not addedVerbs.has_key(originalVerbName):
                    addedVerbs[originalVerbName] = True
                    res += headString
                    nouns = info["relatedNouns"]
                    combinedVerbString = "(" + combinedVerbName + " "
                    originalVerbString = "(" + originalVerbName + " "
                    for noun in nouns:
                        if noun["var"]:
                            pronoun = chr(ord('a') + number)
                            combinedVerbString += pronoun + " "
                            if number != len(nouns) - 1:
                                originalVerbString += pronoun + " "
                            res += "(" + pronoun + " " + noun["sort"] + ") "
                        else:
                            combinedVerbString += tokens[noun["index"]] + " "
                            if number != len(nouns) - 1:
                                originalVerbString += tokens[noun["index"]] + " "
                        number += 1
                    res += ") "
                    combinedVerbString += ") "
                    originalVerbString += ")"
                    res += "(=> " + combinedVerbString + originalVerbString + ")))\n"
        return res
    def getAntecedentAndSecedent(self, tokens):
        length = len(tokens)
        sepIndex = -1
        for i in range(length):
            if tokens[i] == "then":
                sepIndex = i
                break
        return sepIndex

    def getCompleteNounNameByIndex(self, nounIndex, relatedNounsMap, tokens):
        nounName = tokens[nounIndex]
        if relatedNounsMap.has_key(nounIndex):
            relatedNounsIndex = relatedNounsMap[nounIndex]
            for i in relatedNounsIndex:
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
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens)
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
            subjName = self.getCompleteNounNameByIndex(subjIndex, completeNouns, tokens)
            objName = self.getCompleteNounNameByIndex(objIndex, completeNouns, tokens)
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


    def addReality_Entailment(self, library, verbs, sepIndex, outputStr):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        antecedent = tokens[:sepIndex]
        secedent = tokens[sepIndex + 1:]
        entailmentType = self.findTypeOfEntailment(antecedent, secedent)
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
        declareVarString, pronoun_name_Map = self.addVariableDeclare(library, verbs)
        outputStr += declareVarString
        outputStr += self.addEntailment(library, verbs, entailmentType, sepIndex, pronoun_name_Map)
        return outputStr

    #return string and pronoun_name map
    def addVariableDeclare(self, library, verbs):
        headString = "(assert (forall ("
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        pronouns = []
        existVar = ["somebody", "something", "sth", "sb", "he", "it"]
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
                nounName = tokens[index]
                sort = noun["sort"]
                if nounName not in existVar and noun["var"]:
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens)
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

    def addEntailment(self, library, verbs, entailmentType, sepIndex, pronoun_name_Map):
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
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

        addedVerbsNum = 0
        #assure that verb occurs in order to get the right relation between verbs, such as conj:and, conj:or
        antecedent = sorted(antecedent, key = lambda x : x[0])
        secedent = sorted(secedent, key = lambda x : x[0])
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
        
        return "(=> " + antecedentString + " " + secedentString + "))))\n"

    def addRealityForOneVerb(self, library, theVerb, allVerbs, pronoun_name_Map, addedVerbsIndex):
        headString = ""
        tokens = library["Lemmatized tokens:"]
        tags = library["POS tags:"]
        children = library["Dependency children:"]
        completeNouns = self.findCompleteNouns(library)
        for index, info in theVerb.items():
            if index in addedVerbsIndex:
                continue
            nouns = info["relatedNouns"]
            verbName = info["combinedVerbName"]
            headString += "(" + verbName
            for noun in nouns:
                nounIndex = noun["index"]
                nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens)
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

        return headString

    def addPossesionReality(self):
       return "" 


    def addRules_ClosedReasonAssumption(self, library, verbs, outputStr):
        tokens = library["Lemmatized tokens:"]
        sepIndex  = self.getAntecedentAndSecedent(tokens)
        if sepIndex == -1:
            return self.addReality_IS_Relation(library, verbs, outputStr)
        else:
            return self.addReality_Entailment(library, verbs, sepIndex, outputStr)

    def translateToZ3(self):
        description = self.description
        kbList = self.kbList
        allVerbs = []
        nounSortMap = {}
        for kb in kbList:
            kbVerbs = self.findVerbsAndItsRelatedNouns(kb)
            allVerbs.append(kbVerbs)
            tokens = kb["Lemmatized tokens:"]
            combinedVerbNameToIndexMap = {}
            originalVerbNameToIndexMap = {}
            #{SortName: [noun1, noun2, ...]}
            completeNouns = self.findCompleteNouns(kb)
            descriptionVerbs = self.findVerbsAndItsRelatedNouns(description)
            #find nouns in kb
            for index, info in kbVerbs.items():
                nouns = info["relatedNouns"]
                combinedVerbNameToIndexMap[info["combinedVerbName"]] = index
                originalVerbNameToIndexMap[info["originalVerbName"]] = index
                for noun in nouns:
                    if not noun["var"]:
                        sort = noun["sort"]
                        index = noun["index"]
                        nounName = self.getCompleteNounNameByIndex(index, completeNouns, tokens)
                        if nounSortMap.has_key(sort):
                            if nounName not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName)
                        else:
                            nounSortMap[sort] = [nounName]

            #find nouns in description
            tokens = description["Lemmatized tokens:"]
            completeNouns = self.findCompleteNouns(description)
            for index, info in descriptionVerbs.items():
                verbName = info["combinedVerbName"]
                kbindex = -1
                #firstly, use combine name to get verb's info
                if combinedVerbNameToIndexMap.has_key(verbName):
                    kbindex = combinedVerbNameToIndexMap[verbName]
                #if not exists, use original name
                else:
                    verbName = info["originalVerbName"]
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
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens)
                        if nounSortMap.has_key(sort):
                            if nounName not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName)
                        else:
                            nounSortMap[sort] = [nounName]
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
            if i >= verbLength:
                verbs = {}
            else:
                verbs = allVerbs[i]
            res = self.addRules_ClosedReasonAssumption(kb, verbs, res)
            i += 1
        res += self.addPrepVerbToVerbEntailment()
        return res




def main():
    t = translater()
    t.load("test1")
    print t.translateToZ3()

if __name__ == '__main__':
    main()
