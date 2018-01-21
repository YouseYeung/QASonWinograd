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
                    if len(nounName) == 1 or nounName == "something" or nounName == "somebody" or nounName == "sth" or nounName == "sb":
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
                    nsubjIndex = verbs[i]["relatedNouns"][0]["index"]
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
                    relatedNounsIndex = self.findRelatedNouns(library, index)
                    relatedNounsIndex.append(nsubjIndex)
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
                    verbs[index]["relatedNouns"] = sorted(verbs[index]["relatedNouns"], key = lambda x : x[0], reverse = False)
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
                    res += "(x = " + nounList[0] + ")))\n"
                else:
                    res += "(or "
                    for noun in nounList:
                        res += '(= x ' + noun + ') '
                    res += ')))\n'
        return res

    def addDeclareRel(self, verbs):
        declareRel = "(declare-rel "                            # need 1 )
        addedVerbName = {}
        res = ""
        for index, info in verbs.items():
            combinedVerbName =  info["combinedVerbName"]
            originalVerbName = info["originalVerbName"]
            if not addedVerbName.has_key(combinedVerbName):
                res += declareRel + combinedVerbName + " ("
                for noun in info["relatedNouns"]:
                    res += noun["sort"] + " "
                res += "))\n"
                addedVerbName[combinedVerbName] = True
                #add all declared verbs into list addedverb
                self.addedVerbs.append(combinedVerbName)
            #to get a form without prep
            if combinedVerbName != originalVerbName:
                if not addedVerbName.has_key(originalVerbName):
                    res += declareRel + originalVerbName + " ("
                    #remove last parameter
                    noun = info["relatedNouns"][0]
                    res += noun["sort"] + " "
                    res += "))\n"
                addedVerbName[originalVerbName] = True
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
                                originalVerbString += tokens[noun["index"]]
                        number += 1
                    res += ") "
                    combinedVerbString += ") "
                    originalVerbString += ")"
                    res += "(=> " + combinedVerbString + originalVerbString + ")))\n"
        return res

    def translateToZ3(self):
        description = self.description
        kbList = self.kbList
        allVerbs = []
        for kb in kbList:
            kbVerbs = self.findVerbsAndItsRelatedNouns(kb)
            allVerbs.append(kbVerbs)
            tokens = kb["Lemmatized tokens:"]
            combinedVerbNameToIndexMap = {}
            originalVerbNameToIndexMap = {}
            #{SortName: [noun1, noun2, ...]}
            nounSortMap = {}
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
                        nounName = tokens[index]
                        if completeNouns.has_key(index):
                            relatedNounsList = completeNouns[index]
                            for i in relatedNounsList:
                                if i < index:
                                    nounName = tokens[i] + "_" + nounName
                                else:
                                    nounName += "_" + tokens[i]
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
                    i = 0
                    for noun in nouns:
                        nounIndex = noun["index"]
                        nounName = tokens[nounIndex]
                        sort = kbNounsInfo[i]["sort"]
                        if completeNouns.has_key(nounIndex):
                            for i in completeNouns[nounIndex]:
                                if i < index:
                                    nounName = tokens[i] + "_" + nounName
                                else:
                                    nounName += "_" + tokens[i]
                        if nounSortMap.has_key(sort):
                            if nounName not in nounSortMap[sort]:
                                nounSortMap[sort].append(nounName)
                        else:
                            nounSortMap[sort] = [nounName]


        res = ""
        res += self.addDeclareSort(nounSortMap)
        res += self.addRules_EntityNotEqual(nounSortMap)
        res += self.addRules_EntityRange(nounSortMap)
        for verbs in allVerbs:
            res += self.addDeclareRel(verbs)
        res += self.addPrepVerbToVerbEntailment()
        return res




def main():
    t = translater()
    t.load("test1")
    print t.translateToZ3()

if __name__ == '__main__':
    main()