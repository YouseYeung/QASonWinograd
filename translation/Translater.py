#coding=utf-8

import os
import string
import random
import platform
from Preprocessor import Preprocessor
from enum import Enum

class ErrorTypes(Enum):
    PREDICATE_NAME_ERROR = 0
    PREDICATE_PARAMETER_ERROR = 1
    ENTITY_NAME_ERROR = 2
    VAR_NAME_ERROR = 3

class Translater(object):
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
        self.addedVerbs = {}
        self.addedNouns = []
        #z3 keywords, these words can not be declared as a rel, we have to add '_' in front of the word.
        self.outputStr = ""
        self.possessionVerbs = []
        self.questionVerbNames = []
        self.loadFileName = ""
        #errorTypes: [{"type": str, "val" : str},]
        self.errorTypes = []
        self.VERB_SYMBOL = "Verb_"
        self.NOUN_SYMBOL = "Noun_"
        self.Possess_Person_Thing = "possess_pt"
        self.Possess_Thing_Thing = "possess_tt"
        self.TOKEN_TAG = "Tokens:"
        self.LEM_TOKEN_TAG = "Lemmatized tokens:"
        self.POS_TAG = "POS tags:"
        self.NER_TAG = "NER tags:"
        self.NER_VAL_TAG = "NER values:"
        self.CHILDREN_TAG = "Dependency children:"
        self.VERB_COMBINE_NAME_TAG = "combinedVerbName"
        self.VERB_ORIGIN_NAME_TAG = "originalVerbName"
        self.VERB_RELATION_NOUN_TAG = "relatedNouns"
        self.VERB_NOUN_SORT_TAG = "sort"
        self.VERB_NOUN_INDEX_TAG = "index"
        self.parsingSymbol = [self.TOKEN_TAG, self.LEM_TOKEN_TAG, self.POS_TAG, self.NER_TAG, self.NER_VAL_TAG, self.CHILDREN_TAG]
        self.z3_keywords = ["repeat", "assert", "declare", "map"]
        self.existVars = ["somebody", "something", "sth", "sb", "he", "it"]
        self.pronounList = ["it", "he", "she", "they", "I", "we", "you", "It", "He", "She", "They", "You", "We"]
        self.questionAnswerTags = ["WP", "WDT", "WRB", "WP$"]
        self.reverseKeywords = ["but", "although"]
        self.preprocessor = Preprocessor()
        self.inputFilePath_Win = "input/"
        self.outputFilePath_Win = "output/"
        self.inputFilePath_Linux = "input/"
        self.outputFilePath_Linux = "output/"

    def run(self):
        print "Enter 'f' to select file as input."
        print "Enter 'c' to select cmd as input."
        while True:
            cmd = ""
            cmd = raw_input()
            if cmd == 'f':
                self.setInputFileName()
                self.preprocessor.setInputFileName(self.loadFileName)
                self.preprocessor.setOutputFileName("temp")
                self.preprocessor.parsing()
                self.loadFromFile(self.preprocessor.getOutputFileName())
            elif cmd == 'c':
                print "Enter first line for description."
                print "Enter second line for knowledge base."
                print "Enter third line for question."
                self.loadFromCMD()

    def setInputFileName(self, fileName):
        if os.path.isfile(fileName):
            self.loadFileName = fileName
            return True
        else:
            print fileName + "does not exists."
            print "Please enter correct file name"
            return False

    def loadFromCMD(self):
        i = 0
        content = ""
        questionFileName = "question"
        with open(questionFileName, "w") as f:
            while True:
                content = raw_input()
                if not content:
                    break
                if content[-1] != '\n':
                    content += '\n'
                f.write(content)
        self.preprocessor.setInputFileName(questionFileName)
        self.preprocessor.setOutputFileName("outputTemp")
        self.preprocessor.parsing()
        self.loadFileName(self.preprocessor.getOutputFileName)

    def preprocessFile(self, fileName):
        if not self.setInputFileName(fileName):
            return ""
        self.preprocessor.setInputFileName(self.loadFileName)
        self.preprocessor.setOutputFileName("outputTemp")
        self.preprocessor.parsing()
        return self.preprocessor.getOutputFileName()

    def loadFromFile(self, fileName):
        systemType = platform.system()
        if "Win" in systemType:
            fileName = self.inputFilePath_Win + fileName
        else:
            fileName = self.inputFilePath_Linux + fileName

        with open(fileName, 'r') as f:
            lastLine = ''
            beginMark = False
            while True:
                content = f.readline()
                if not content:
                    #reach the end of wsc problems, then add the parsing result into question and then translate.
                    if self.parsingResult != {}:
                        self.question = self.parsingResult
                    return self.translateToZ3()
                    break

                if content.find("Example:") != -1:
                    self.context.append(content[len("Example: "):-3])
                    continue

                #one \n marking for the end of one data in one question
                if (content == '\r\n' or content == '\n') and (lastLine != '\n' and lastLine != '\r\n'):
                    if not beginMark:
                        self.description = self.parsingResult
                    else:
                        self.kbList.append(self.parsingResult)
                    self.parsingResult = {}
                    beginMark = True

                #two \n marking for the end of one question
                if (content == '\n' or content == '\r\n') and (lastLine == '\n' or lastLine == '\r\n'):
                    self.question = self.kbList[-1]
                    self.kbList = self.kbList[:-1]
                    self.translateToZ3()
                    self.kbList = []
                    self.question = {}
                    self.description = {}
                    self.context = []
                    self.addedVerbs = {}
                    self.addedNouns = []
                    self.possessionVerbs = []
                    self.questionVerbNames = []
                    self.outputStr = ""
                    self.errorTypes = []
                    beginMark = False

                for symbol in self.parsingSymbol:
                    index = content.find(symbol)
                    if index != -1:
                        content = (content[index + len(symbol) + 1:])
                        length = len(content)
                        lastBracketIndex = length
                        firstBracketIndex = 0
                        for i in range(length - 1, -1, -1):
                            if content[i] == ']':
                                lastBracketIndex = i
                                break
                        for i in range(length):
                            if content[i] == '[':
                                firstBracketIndex = i
                                break
                        content = content[firstBracketIndex + 1 : lastBracketIndex]
                        #for dependency, it can not just use split(',') to get te result
                        #'[,]' it is because one word's children result may have many ',' , 
                        # so it has to use to '[]' to seperate the result for each word 
                        if symbol == self.CHILDREN_TAG:
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

    #return noun's related nouns [{"tag" : str(the symbol of combination), "index" : int(index)}, ...]
    def findCompleteNouns(self, library):
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
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

    #return verb's related nouns, [relatedNounIndex1, relatedNounIndex2, ...]
    def findRelatedNouns(self, library, index):
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        verbChildren = children[index][1:-1].split(',')
        typeOfNoun = ['subj', 'iobj', 'dobj', 'nmod', 'xcomp', 'advmod']
        relatedNounsIndex = []
        #find obj related to a verb in a relative clause
        #I saw the man you love, relcl(man, love), relcl is man's children dependency
        nounClauseSymbol = "acl:relcl"
        i = 0
        for child in children:
            if child.find(nounClauseSymbol) != -1:
                relIndex = self.findIndexBySymbol(child ,nounClauseSymbol)
                if index == relIndex:
                    relatedNounsIndex.append(i)
                    break
            i += 1

        for _type in typeOfNoun:
            indexStart = 0
            verbChild = children[index]
            length = len(_type)
            while True:
                temp = verbChild[indexStart:].find(_type)
                if temp == -1:
                    break
                #neglect nmod:poss
                if _type == "nmod":
                    possIndex = verbChild[indexStart:].find(_type + ":poss")
                    if possIndex != -1:
                        indexStart += possIndex + length
                        continue

                i = self.findIndexBySymbol(verbChild[indexStart:], _type)
                indexStart += temp + length
                if i != -1:
                    nounChild = children[i]
                    tag = tags[i]
                    #add the word if it is a noun
                    if "NN" in tag or "PRP" in tag or tag in self.questionAnswerTags:
                        #insert subj's index at the first position
                        if _type == 'subj':
                            relatedNounsIndex.insert(0, i)
                        else:
                            relatedNounsIndex.append(i)
                    #find more nouns in its related word's children
                    if (_type == "xcomp" and ("NN" in tag or "PRP" in tag))\
                     or (_type == "advmod" and tag == "IN") \
                     or (_type == "dobj" and nounChild.find("nmod") != -1 and nounChild.find("nmod:poss") == -1) \
                     or (_type == "advcl" and nounChild.find("obj") != -1 and i > index and nounChild.find("mark") != -1):
                        additiveNounsIndex = self.findRelatedNouns(library, i)
                        for ii in additiveNounsIndex:
                            relatedNounsIndex.append(ii)

        return relatedNounsIndex

    #library: dict. It is descrption, kb or question
    #return {index: {self.VERB_ORIGIN_NAME_TAG:str, combinedVerbName:str, "relatedNouns":[{self.VERB_NOUN_INDEX_TAG:nounIndex, self.VERB_NOUN_SORT_TAG:nounSort, "var":symbolOfVariable}] } }
    def findVerbsAndItsRelatedNouns(self, library):
        existVars = self.existVars
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        #{index: {self.VERB_ORIGIN_NAME_TAG:str, combinedVerbName:str, "relatedNouns":[{self.VERB_NOUN_INDEX_TAG:nounIndex, self.VERB_NOUN_SORT_TAG:nounSort, "var":symbolOfVariable}] } }
        verbs = {}
        addedVerbsIndex = []
        i = -1
        tagLength = len(tags)
        for tag in tags:
            i += 1
            child = children[i]
            originalVerbName = tokens[i]
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
                
                verbs[i] = {self.VERB_ORIGIN_NAME_TAG:originalVerbName, self.VERB_COMBINE_NAME_TAG:combinedVerbName}
                relatedNounsIndex = self.findRelatedNouns(library, i)
                verbs[i]["relatedNouns"] = []
                unsortedNouns = []
                for index in relatedNounsIndex:
                    nounInfo = {self.VERB_NOUN_INDEX_TAG:index}
                    nounName = tokens[index]
                    #determine if noun name is a variable?
                    if len(nounName) == 1:
                        lastWordIndex = index - 1
                        nounInfo[self.VERB_NOUN_SORT_TAG] = tokens[lastWordIndex]
                        nounInfo["var"] = True

                    elif nounName in existVars:
                            
                        if nounName == "somebody" or nounName == "sb" or nounName == "he":
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "person"
                            nounInfo["var"] = True
                        elif nounName == "something" or nounName == "sth" or nounName == "it":
                            #address the condition of do something adj.
                            if nounName == "something" and children[index].find("amod") != -1:
                                nounInfo["var"] = False
                                nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                            else:
                                nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                                nounInfo["var"] = True

                    elif tags[index] in self.questionAnswerTags:
                        if nounName == "who" or nounName == "whom" or nounName == "whose":
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "person"
                        else:
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                        nounInfo["var"] = False

                    else:
                        nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                        nounInfo["var"] = False
                    unsortedNouns.append(nounInfo)

                #sort all nouns except the subject noun, it is because subject noun is always the first noun name.
                
                if unsortedNouns != []:
                    sortedNouns = sorted(unsortedNouns[1:], key = lambda x : x[self.VERB_NOUN_INDEX_TAG], reverse = False)
                    verbs[i]["relatedNouns"].append(unsortedNouns[0])
                    for noun in sortedNouns:
                        verbs[i]["relatedNouns"].append(noun)

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
                    verbs[index] = {self.VERB_ORIGIN_NAME_TAG:combinedVerbName, self.VERB_COMBINE_NAME_TAG:combinedVerbName}
                    verbs[index]["relatedNouns"] = [nsubj]
                    relatedNounsIndex = self.findRelatedNouns(library, index)
                    for ii in relatedNounsIndex:
                        nounInfo = {self.VERB_NOUN_INDEX_TAG:ii}
                        nounName = tokens[ii]
                        #determine if noun name is a variable?
                        if len(nounName) == 1:
                            lastWordIndex = ii - 1
                            nounInfo[self.VERB_NOUN_SORT_TAG] = tokens[lastWordIndex]
                            nounInfo["var"] = True
                        else:
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                            nounInfo["var"] = False
                        verbs[index]["relatedNouns"].append(nounInfo)

                    verbs[index]["relatedNouns"] = sorted(verbs[index]["relatedNouns"], key = lambda x : x[self.VERB_NOUN_INDEX_TAG], reverse = False)
                    addedVerbsIndex.append(index)
        return verbs

    def addDeclareSort(self, nounSortMap):
        if nounSortMap == {}:
            return ""
        declareSort = "(declare-sort "                           # need 1 )
        declareConst = "(declare-const "                         # need 1 )
        res = declareSort + "thing)\n"
        res += declareSort + "person)\n"
        addedName = {}
        nounSymbol = self.NOUN_SYMBOL
        for sortName, nouns in nounSortMap.iteritems():
            newLine = declareSort + sortName
            newLine = self.bracketCheck(newLine) + '\n'
            for name in nouns:
                if not addedName.has_key(name):
                    newLine = declareConst + nounSymbol + name + ' ' + sortName
                    newLine = self.bracketCheck(newLine) + '\n'
                    res += newLine
                    addedName[name] = True

        return res

    def addRules_EntityNotEqual(self, nounSortMap):
        objectNotEqual = "(assert (not (= "                      # need 2 )
        res = ""
        nounSymbol = self.NOUN_SYMBOL
        for index, nouns in nounSortMap.iteritems():
            i = 0
            length = len(nouns)
            while i < length:
                j = i + 1
                while j < length:
                    firstNoun = nounSymbol + nouns[i]
                    secondNoun = nounSymbol + nouns[j]
                    newLine = objectNotEqual + firstNoun + ' ' + secondNoun
                    newLine = self.bracketCheck(newLine) + '\n'
                    res += newLine
                    j += 1
                i += 1
        return res

    def addRules_NounAsVerbRange(self):
        res = ""
        headString = "(assert ("
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        nounSentence = ""
        for verbName in self.addedVerbs.keys():
            for nounName in self.addedNouns:
                if nounName.find(verbName) != -1:
                    res += headString + verbSymbol + verbName + " " + nounName + "))\n"
        return res

    def addRules_EntityRange(self, nounSortMap):
        res = ""
        nounSymbol = self.NOUN_SYMBOL
        for sort, nounList in nounSortMap.iteritems():
            length = len(nounList)
            if length < 1:
                continue
            else:
                res += "(assert (forall " + "((x " + sort + ")) "      # need 3 )
                if length == 1:
                    res += "(= x " + nounSymbol + nounList[0] + ")))\n"
                else:
                    res += "(or "
                    for noun in nounList:
                        res += '(= x ' + nounSymbol + noun + ') '
                    res += ')))\n'
        return res

    def addDeclareRel(self, verbs):
        declareRel = "(declare-rel "                            # need 1 )
        res = ""
        verbSymbol = self.VERB_SYMBOL
        for index, info in verbs.iteritems():
            combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
            originalVerbName = info[self.VERB_ORIGIN_NAME_TAG]

            '''
            if originalVerbName not in self.addedVerbs:
                nouns = info["relatedNouns"]
                res += declareRel + verbSymbol + originalVerbName + " ("
                num = 0
                for noun in nouns:
                    res += noun[self.VERB_NOUN_SORT_TAG] + " "
                    num += 1
                res += "))\n"
                #add all declared verbs into list addedverb
                self.addedVerbs[originalVerbName] = num
            '''

            if combinedVerbName not in self.addedVerbs:
                nouns = info["relatedNouns"]
                res += declareRel + verbSymbol + combinedVerbName + " ("
                num = 0
                for noun in nouns:
                    res += noun[self.VERB_NOUN_SORT_TAG] + " "
                    num += 1
                res += "))\n"
                #add all declared verbs and its number of parameters into list addedverb
                self.addedVerbs[combinedVerbName] = num

            #descending grade for verbs to get predicates with less parameter
            num = 1
            nouns = ""
            if combinedVerbName != originalVerbName:
                relatedNouns = info["relatedNouns"]
                for noun in relatedNouns:
                    lessPredicateVerbName = originalVerbName + "_" + str(num)
                    if lessPredicateVerbName in self.addedVerbs.keys():
                        continue
                    res += declareRel + verbSymbol + lessPredicateVerbName + " ("
                    nouns += noun[self.VERB_NOUN_SORT_TAG] + " "
                    res += nouns + "))\n"
                    self.addedVerbs[lessPredicateVerbName] = num
                    num += 1

            #additional verb for negative verb
            if "not" in combinedVerbName:
                indexStart = combinedVerbName.find("not_")
                newVerbName = combinedVerbName[indexStart + len("not_"):]
                if newVerbName not in self.addedVerbs.keys():
                    res += declareRel + verbSymbol + newVerbName + " ("
                    num = 0
                    for noun in info["relatedNouns"]:
                        res += noun[self.VERB_NOUN_SORT_TAG] + " "
                        num += 1
                    res += "))\n"
                    self.addedVerbs[newVerbName] = num

        return res

    def addPrepVerbToVerbEntailment(self):
        addedVerbs = {}
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        for kb in self.kbList:
            headString = "(assert (forall ("
            tokens = kb[self.LEM_TOKEN_TAG]
            verbs = self.findVerbsAndItsRelatedNouns(kb)
            completeNouns = self.findCompleteNouns(kb)
            for index, info in verbs.iteritems():
                combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
                originalVerbName = info[self.VERB_ORIGIN_NAME_TAG]
                if combinedVerbName != originalVerbName and not addedVerbs.has_key(originalVerbName):
                    addedVerbs[originalVerbName] = True
                    nouns = info["relatedNouns"]
                    length = len(nouns)
                    if length == 0:
                        continue

                    number = 1
                    combinedVerbString = "(" + verbSymbol + combinedVerbName + " "
                    lessParaPredicateString = []
                    addedNouns = ""
                    nounDeclareString = ""
                    for noun in nouns:
                        originalVerbString = "(" + verbSymbol + originalVerbName + "_" + str(number) + " "
                        if noun["var"]:
                            pronoun = chr(ord('a') + number)
                            addedNouns += pronoun + " "
                            nounDeclareString += "(" + pronoun + " " + noun[self.VERB_NOUN_SORT_TAG] + ") "
                        else:
                            addedNouns += nounSymbol + self.getCompleteNounNameByIndex(noun[self.VERB_NOUN_INDEX_TAG], \
                                completeNouns, tokens, True) + " "
                        lessParaPredicateString.append(originalVerbString + addedNouns + ")")
                        number += 1

                    combinedVerbString += addedNouns + ") "
                    nounDeclareString += ") "
                    entailmentTypeStr = "(=> "
                    number = 1
                    for string in lessParaPredicateString:
                        if number == length:
                            entailmentTypeStr = "(= "
                        newLine = headString + nounDeclareString + entailmentTypeStr + combinedVerbString + string
                        newLine = self.bracketCheck(newLine) + '\n'
                        res += newLine
                        number += 1
        return res

    #return -1 if there exists no entailment in the sentence,
    #return number(> 0), which is  the index of keyword 'then'
    def getAntecedentAndSecedent(self, tokens):
        length = len(tokens)
        sepIndex = -1
        for i in range(length):
            if tokens[i] == "then":
                sepIndex = i
                break
        return sepIndex

    #return complete noun name for a specific noun, which combines with prep, adv, poss and so on.
    def getCompleteNounNameByIndex(self, nounIndex, relatedNounsMap, tokens, possessionSymbol):
        nounName = tokens[nounIndex]
        if relatedNounsMap.has_key(nounIndex):
            relatedNounsIndex = relatedNounsMap[nounIndex]
            for info in relatedNounsIndex:
                i = info["index"]
                tag = info["tag"]
                #if it doesn't have to add possession noun, then neglect it
                if not possessionSymbol or tag != "nmod:poss":
                    if i < nounIndex:
                        nounName = tokens[i] + "_" + nounName
                    else:
                        nounName += "_" + tokens[i]
        return nounName

    #Add reality: sb. do sth. sth do sth.
    def addReality_OneVerb(self, library, verbs, outputStr):
        res = ""
        headString = "(assert "
        declareVarStr, pronoun_name_Map = self.addVariableDeclare(library, verbs)
        sentence = self.addRealityForOneVerb(library, verbs, verbs, pronoun_name_Map, [])
        if sentence != "":
            res = headString + sentence
            res = self.bracketCheck(res) + '\n'
        return outputStr + res

    #Add reality : sth is noun, sth is adj, sth is doing sth.
    def addReality_IS_Relation(self, library, verbs, outputStr):
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        headString = "(assert ("
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        sepIndex, i = -1, 0
        for tag in tags:
            if tag == "VBD-AUX" and tokens[i] == "be":
                sepIndex = i
                break
            i += 1

        i = 0
        completeNouns = self.findCompleteNouns(library)
        #sth is doing sth, sth is adj.
        if verbs != {}:
            for index, info in verbs.iteritems():
                nouns = info["relatedNouns"]
                verbName = info[self.VERB_COMBINE_NAME_TAG]
                if verbName not in self.addedVerbs.keys():
                    verbName = info[self.VERB_ORIGIN_NAME_TAG]
                    if verbName not in self.addedVerbs.keys():
                        verbExist = False
                        length = len(nouns)
                        for i in range(1, length + 1):
                            tempVerbName = verbName + "_" + str(i)
                            if tempVerbName in self.addedVerbs.keys():
                                verbName = tempVerbName
                                verbExist = True
                                break
                        if not verbExist:
                            continue
                res += headString + verbSymbol + verbName + " "
                for noun in nouns:
                    nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                    nounName = nounSymbol + self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                    res += nounName + " "
                res = self.bracketCheck(res) + "\n"

        #sth is sth
        else:
            #firstly, use "cop" dependency to find subj and obj
            length = len(children)
            subjIndex, objIndex = -1, -1
            for i in range(length - 1, -1, -1):
                child = children[i]
                if child.find("cop") != -1:
                    objIndex = i
                    subjIndex = self.findIndexBySymbol(child, "nsubj")
                    break
            #if it can't find subj or obj, use keyword "be" to find
            if subjIndex == -1 or objIndex == -1:
                subjIndex, objIndex = -1, -1
                subjName, objName = "", ""
                i = sepIndex - 1
                while i >= 0:
                    if "NN" in tags[i]:
                        subjIndex = i
                        break
                    i -= 1
                i =  length - 1
                while i > sepIndex:
                    if "NN" in tags[i]:
                        objIndex = i
                        break
                    i -= 1

            subjName = self.getCompleteNounNameByIndex(subjIndex, completeNouns, tokens, False)
            objName = self.getCompleteNounNameByIndex(objIndex, completeNouns, tokens, False)
            if subjName == "" or objName == "":
                self.errorTypes.append({"type" : ErrorTypes.PREDICATE_PARAMETER_ERROR, "val" : "be"})
                return outputStr

            subjName = nounSymbol + subjName
            objName = nounSymbol + objName

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

    #return [{self.VERB_ORIGIN_NAME_TAG: str, self.VERB_COMBINE_NAME_TAG: str}]
    def findAnswerPredicate(self):
        question = self.question
        verbs = self.findVerbsAndItsRelatedNouns(question)
        questionVerbs = []
        for index, info in verbs.iteritems():
            combinedName = info[self.VERB_COMBINE_NAME_TAG]
            originalName = info[self.VERB_ORIGIN_NAME_TAG]
            questionVerbs.append({self.VERB_COMBINE_NAME_TAG:combinedName, self.VERB_ORIGIN_NAME_TAG:originalName})
        
        return questionVerbs

    #return type of entailment
    def findTypeOfEntailment(self, antecedent, secedent):
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
        type_ABC2 = "AvB>C, C>A, C>B"
        questionVerbs = self.findAnswerPredicate()
        
        for verb in questionVerbs:
            orgAnsPreName = verb[self.VERB_ORIGIN_NAME_TAG]
            comAnsPreName = verb[self.VERB_COMBINE_NAME_TAG]
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
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        antecedent = tokens[:sepIndex]
        secedent = tokens[sepIndex + 1:]
        entailmentType = self.findTypeOfEntailment(antecedent, secedent)
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A"
        outputStr += self.addEntailment(library, verbs, entailmentType, sepIndex)
        return outputStr

    #return string and pronoun_name map
    def addVariableDeclare(self, library, verbs):
        res = ""
        headString = "(assert (forall ("
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        pronouns = []
        existVars = self.existVars
        existSentence = ""
        hasAddedStr_EXIST = False
        for i in range(26):
            pronouns.append(chr(ord('a') + i))
        numOfPronoun = 0
        pronoun_name_Map ={}
        addedPronoun = []
        sortNameMap = {}
        completeNouns = self.findCompleteNouns(library)
        for index, info in verbs.iteritems():
            nouns = info["relatedNouns"]
            for noun in nouns:
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                nounName = tokens[nounIndex]
                sort = noun[self.VERB_NOUN_SORT_TAG]
                
                if noun["var"]:
                    #remove "he" and "it"
                    if nounName == "he" or nounName == "it":
                        continue
                    if nounName not in existVars:
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                        if not pronoun_name_Map.has_key(nounName):
                            pronoun = pronouns[numOfPronoun]
                            addedPronoun.append(pronoun)
                            pronoun_name_Map[nounName] = pronoun
                            res += "(" + pronoun + " " + sort + ") " 
                            if sortNameMap.has_key(sort):
                                sortNameMap[sort].append(pronoun)
                            else:
                                sortNameMap[sort] = [pronoun]
                            numOfPronoun += 1
                    else:
                        pronoun = pronouns[numOfPronoun]
                        pronoun_name_Map[nounName] = pronoun
                        if nounName == "somebody" or nounName == "sb":
                            pronoun_name_Map["he"] = pronoun
                            if sortNameMap.has_key("person"): 
                                sortNameMap["person"].append(pronoun)
                            else:
                                sortNameMap["person"] = [pronoun]

                        elif nounName == "something" or nounName == "sth":
                            pronoun_name_Map["it"] = pronoun
                            if sortNameMap.has_key("thing"):
                                sortNameMap["thing"].append(pronoun)
                            else:
                                sortNameMap["thing"] = [pronoun]

                        numOfPronoun += 1
                        existSentence += self.addExistVarDeclaration(nounName, hasAddedStr_EXIST, pronoun_name_Map)
                        hasAddedStr_EXIST = True
                else:
                    #address the condit/ion of noun being added as a verb
                    if nounName in self.addedVerbs.keys():
                        res += "(" + pronouns[numOfPronoun] + " " + sort + ") "
                        pronoun_name_Map[nounName] = pronouns[numOfPronoun]
                        numOfPronoun += 1

                    #address the condition of possession
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
        if existSentence != "":
            existSentence += ") "
        
        if res == "":
            return "(assert (", pronoun_name_Map
        notEqualPairs = 0
        entityNotEqualString = ""
        for sort, names in sortNameMap.iteritems():
            length = len(names)
            if length > 1:
                for i in range(length):
                    for j in range(i + 1, length):
                        entityNotEqualString += "(not (= " + names[i] + " " + names[j] + ")) "
                        notEqualPairs += 1
        
        if notEqualPairs > 1:
            entityNotEqualString = "(=> (and " + entityNotEqualString + ") "
        elif notEqualPairs == 1:
            entityNotEqualString = "(=> " + entityNotEqualString

        return headString + res + ") " + existSentence + entityNotEqualString, pronoun_name_Map

    def addEntailment(self, library, verbs, entailmentType, sepIndex):
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        type_AB1, type_AB2, type_ABC1 = "A>B", "A=B", "A>B^C,B>A,C>A;A>BVC,B>A,C>A" 
        type_ABC2 = "AvB>C, C>A, C>B"
        antecedent = []
        secedent = []
        addedVerbsIndex = []        
        antecedentString = ""
        secedentString = ""
        for index, info in verbs.iteritems():
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
            
            #determine if there exists entity not equal string
            #if exists add one more right bracket
            rightBracket = ""
            if declareString.find("(not (=") != -1:
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
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        completeNouns = self.findCompleteNouns(library)
        addedNounName = []
        nounAsVerbSentence = ""
        for index, info in theVerb.iteritems():
            if index in addedVerbsIndex:
                continue
            nouns = info["relatedNouns"]
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            if verbName not in self.addedVerbs.keys():
                verbName = info[self.VERB_ORIGIN_NAME_TAG]
                if verbName not in self.addedVerbs.keys():
                    self.errorTypes.append({"type" : ErrorTypes.PREDICATE_NAME_ERROR, "val" : verbName})
                    continue

            headString += "(" + verbSymbol + verbName
            possessionStrs = []
            numOfNounsInVerb = self.addedVerbs[verbName]
            num = 0
            for noun in nouns:
                num += 1
                if num > numOfNounsInVerb:
                    break
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                posStr = self.addPossessionReality(library, nounIndex, pronoun_name_Map)
                if posStr != "":
                    possessionStrs.append(posStr)
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, True)
                    possessionName = ""
                    child = children[nounIndex]
                    index = self.findIndexBySymbol(child, "nmod:poss")
                    possessionName = tokens[index]
                    #if the verb is related to a possession noun, then add it into the list
                    self.possessionVerbs.append(verbName)
                    self.possessionVerbs.append(info[self.VERB_ORIGIN_NAME_TAG])
                    if possessionName not in addedNounName:
                        addedNounName.append(possessionName)

                addedNounName.append(nounName)
                isVar = noun["var"]
                if isVar:
                    if pronoun_name_Map.has_key(nounName):
                        headString += " " + pronoun_name_Map[nounName]
                    else:
                        print "[ERROR]: incorrect variable name:", nounName
                        errorType = ErrorTypes.VAR_NAME_ERROR
                        self.errorTypes.append({"type" : errorType, "val" : nounName})

                else:
                    #if noun is added as a verb, then transform verb noun into (and (verb x) (noun x))
                    if nounName in self.addedVerbs.keys():
                        headString += " " + pronoun_name_Map[nounName]
                        nounAsVerbSentence = "(" + verbSymbol + nounName + " " \
                                            + pronoun_name_Map[nounName] + ")"
                    else:
                        headString += " " + nounSymbol + nounName
            headString += ")"
            addedVerbsIndex.append(index)

            child = children[index]
            index = child.find("conj:")
            
            #get another verb related to this verb
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
                    errorType = ErrorTypes.PREDICATE_NAME_ERROR
                    self.errorTypes.append({"type" : errorType, "val" : verbName})

        
            #add possession reality and noun as verb sentence
            if possessionStrs != [] or nounAsVerbSentence != "":
                headString = "(and " + headString
                for posStr in possessionStrs:
                    headString += " " + posStr + " "
                if nounAsVerbSentence != "":
                    headString += " " + nounAsVerbSentence
                headString += ")"

        return headString

    def addDeclareRel_possession(self, library):
        children = library[self.CHILDREN_TAG]
        headString = "(declare-rel "
        res = ""
        added = False
        verbSymbol = self.VERB_SYMBOL
        for child in children:
            index = child.find("nmod:poss")
            if not added and index != -1:
                verbName = self.Possess_Person_Thing
                if verbName not in self.addedVerbs.keys():
                    res += headString + verbSymbol + verbName + " (person thing))\n"       
                    self.addedVerbs[verbName] = 2
                verbName = self.Possess_Thing_Thing
                if verbName not in self.addedVerbs.keys():
                    res += headString + verbSymbol + verbName + " (thing thing))\n"       
                    self.addedVerbs[verbName] = 2
                added = True
                break

        return res

    def addPossessionReality(self, library, index, pronoun_name_Map):
        children = library[self.CHILDREN_TAG]
        child = children[index]
        res = ""
        i = child.find("nmod:poss")
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        if i != -1:
            tokens = library[self.LEM_TOKEN_TAG]
            tags = library[self.POS_TAG]
            completeNouns = self.findCompleteNouns(library)
            objName = self.getCompleteNounNameByIndex(index, completeNouns, tokens, True)
            subjIndex = self.findIndexBySymbol(child, "nmod:poss")
            subjName = self.getCompleteNounNameByIndex(subjIndex, completeNouns, tokens, False)
            #subjname is a variable
            if subjName == "somebody" or subjName == "his":
                res += "(" + verbSymbol + self.Possess_Person_Thing + " " + pronoun_name_Map[subjName] \
                + " " + nounSymbol + objName + ")"
            elif subjName == "something" or subjName == "its":
                res += "(" + verbSymbol + self.Possess_Thing_Thing + " " + pronoun_name_Map[subjName] \
                + " " + nounSymbol + objName + ")"
            else:
                subjChild = children[subjIndex]
                i = subjChild.find("compound")
                if i != -1:
                    compoundIndex = self.findIndexBySymbol(subjChild, "compound")
                    compoundNoun = tokens[compoundIndex]
                    if compoundNoun == "person":
                        res += "(" + verbSymbol + self.Possess_Person_Thing + " " + pronoun_name_Map[subjName] + " " \
                            + nounSymbol + objName + ")"
                    elif compoundNoun == "thing":
                        res += "(" + verbSymbol + self.Possess_Thing_Thing + " " + pronoun_name_Map[subjName] + " " \
                            + nounSymbol + objName + ")"   
                    else:
                        self.errorTypes.append({"type" : ErrorTypes.PREDICATE_PARAMETER_ERROR, "val" : "posses"})
                        return ""
                #subjname is a constant
                else:
                    if subjName + "_p" in self.addedNouns:
                        res += "(" + verbSymbol + self.Possess_Person_Thing + " " + nounSymbol + subjName + "_p " \
                        + nounSymbol + objName + ") "
         
                    if subjName + "_t" in self.addedNouns:
                        res += "(" + verbSymbol + self.Possess_Thing_Thing + " " + nounSymbol + subjName + "_t " \
                        + nounSymbol + objName + ") "
        return res

    def addRules_ClosedReasonAssumption(self, library, verbs, outputStr):
        tokens = library[self.LEM_TOKEN_TAG]
        sepIndex  = self.getAntecedentAndSecedent(tokens)
        if sepIndex == -1:
            if "be" in tokens:
                return self.addReality_IS_Relation(library, verbs, outputStr)
            else:
                return self.addReality_OneVerb(library, verbs, outputStr)
        else:
            return self.addReality_Entailment(library, verbs, sepIndex, outputStr)

    def addRules_NegativeFormEntailment(self, library, verbs, outputStr):
        addedVerbs = []
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        for index, info in verbs.iteritems():
            combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
            if "not" in combinedVerbName and combinedVerbName not in addedVerbs:
                addedVerbs.append(combinedVerbName)
                i = combinedVerbName.find("not_")
                newVerbName = combinedVerbName[i + len("not_"):]
                newVerb = {}
                newVerb[index] = {self.VERB_COMBINE_NAME_TAG: newVerbName, self.VERB_ORIGIN_NAME_TAG: newVerbName, "relatedNouns": info["relatedNouns"]}
                varStr, pronoun_name_Map = self.addVariableDeclare(library, newVerb)
                realitySentece = self.addRealityForOneVerb(library, newVerb, newVerb, pronoun_name_Map, [])
                verbNameStart = realitySentece.find(newVerbName)
                if verbNameStart == -1:
                    continue
                negSentence = "(not (" + verbSymbol + combinedVerbName + realitySentece[verbNameStart + len(newVerbName):]
                rightBracket = ""
                if varStr.find("(not (=") != -1:
                    rightBracket = ")"
                if realitySentece.find("exists") != -1:
                    realitySentece = realitySentece[:verbNameStart - 2] + " (= (" + realitySentece[verbNameStart:-2]
                    newLine = varStr + realitySentece + " " +  negSentence + rightBracket
                    newLine = self.bracketCheck(newLine) + '\n'
                    res += newLine
                else:
                    newLine = varStr + "(= " + realitySentece + " " + negSentence + rightBracket
                    newLine = self.bracketCheck(newLine) + '\n'
                    res += newLine
        return outputStr + res

    #substitue the variable noun with the candidate answer noun
    def findAllAnswerSentence(self, addingNouns, nounList, sentences, string):
        nounSymbol = self.NOUN_SYMBOL
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
                self.findAllAnswerSentence(addingNouns[1:], newNounList, sentences, string + nounSymbol + noun + " ")
                end = len(noun) + 1
                j += 1
        else:
            self.findAllAnswerSentence(addingNouns[1:], nounList, sentences, string + nounSymbol + symbol + " ")

    def addRules_OnlyOneAnswer(self, nounSortMap):
        question = self.question
        tokens = question[self.LEM_TOKEN_TAG]
        tags = question[self.POS_TAG]
        headString = "(assert (= "
        res = ""
        nounSymbol = self.NOUN_SYMBOL
        verbSymbol = self.VERB_SYMBOL
        nounList = []
        if "who" in tokens or "whom" in tokens:
            if nounSortMap.has_key("person"):
                nounList = nounSortMap["person"]
        else:
            if nounSortMap.has_key("thing"):
                nounList = nounSortMap["thing"]

        verbs = self.findVerbsAndItsRelatedNouns(question)
        allQuestionVerbSentences = []
        for index, info in verbs.iteritems():
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            if verbName not in self.addedVerbs.keys():
                continue
            nouns = info["relatedNouns"]
            verbSentence = "(" + verbSymbol + verbName + " "
            addingNouns = []
            #determine if the noun is an variable
            for noun in nouns:
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
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
            allQuestionVerbSentences.append(sentences)
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

    def addDescription(self, library, nounSortMap):
        verbs = self.findVerbsAndItsRelatedNouns(library)
        answerTokens = self.question[self.LEM_TOKEN_TAG]
        descriptionTokens = self.description[self.LEM_TOKEN_TAG]
        headString = "(assert "
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        completeNouns = self.findCompleteNouns(self.description)
        number = 0
        possessionStrs = []
        for index, info in verbs.iteritems():
            originalVerbName = info[self.VERB_ORIGIN_NAME_TAG]
            combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
            if originalVerbName not in answerTokens:
                verbName = ""
                nouns = info["relatedNouns"]
                if combinedVerbName in self.addedVerbs.keys():
                    verbName = combinedVerbName
                elif originalVerbName in self.addedVerbs.keys():
                    verbName = originalVerbName
                else:
                    length = len(nouns)
                    for i in range(length,0,-1):
                        tempVerbName = originalVerbName + "_" + str(i)
                        if tempVerbName in self.addedVerbs.keys():
                            verbName = tempVerbName
                            break
                if verbName == "":
                    continue
                res += '(' + verbSymbol + verbName + ' '
                numOfNounsInVerb = self.addedVerbs[verbName]
                num = 0
                for noun in nouns:
                    num += 1
                    if num > numOfNounsInVerb:
                        break
                    nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, False)
                    #align description noun name to the noun name in kb
                    if verbName in self.possessionVerbs:
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, True)
                        possessionStrs.append(self.addPossessionReality(self.description, nounIndex, nounSortMap))
                    res += nounSymbol + nounName + ' '
                res += ') '
                number += 1
        if possessionStrs != []:
            number += 1
            for posStr in possessionStrs:
                res += " " + posStr

        if number >= 2:
            res = headString + "(and " + res + "))\n"
        elif number >= 1:
            res = headString + res + ")\n"
        
        return res

    def reasoning(self, nounSortMap, outputStr):
        question = self.question
        tokens = question[self.LEM_TOKEN_TAG]
        tags = question[self.POS_TAG]
        children = question[self.CHILDREN_TAG]
        verb = ""
        i = 0
        for tag in tags:
            if "VB" in tag and "AUX" not in tag:
                verb = tokens[i]
            i += 1

        headString = "(assert (not "
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        nounList = []
        #person answer
        if "who" in tokens or "whom" in tokens or "whose" in tokens:
            nounList = nounSortMap["person"]
        #thing answer
        if "what" in tokens:
            nounList.extend(nounSortMap["thing"])

        #deal with possesion question
        possessionStr = ""
        possessionSentences = []
        if "whose" in tokens:
            i = 0
            completeNouns = self.findCompleteNouns(question)
            for child in children:
                if child.find("poss") != -1:
                    nounName = self.getCompleteNounNameByIndex(i, completeNouns, tokens, False)
                    if nounName in nounSortMap["thing"]:
                        possessionStr = "(" + verbSymbol + self.Possess_Thing_Thing \
                                        + " WP " + nounSymbol + nounName
                    elif nounName in nounSortMap["person"]:
                        possessionStr = "(" + verbSymbol + self.Possess_Person_Thing \
                                        + " WP " + nounSymbol + nounName
                    else:
                        nounName = tokens[i]
                        if nounName in nounSortMap["thing"]:
                            possessionStr = "(" + verbSymbol + self.Possess_Thing_Thing \
                                            + " WP " + nounSymbol + nounName
                        elif nounName in nounSortMap["person"]:
                            possessionStr = "(" + verbSymbol + self.Possess_Person_Thing \
                                            + " WP " + nounSymbol + nounName
                        else:
                            self.errorTypes.append({"type" : ErrorTypes.ENTITY_NAME_ERROR, "val" : nounName})
                            return "", ""
                    break
                i += 1

            #replace "WP" with candidate noun words
            if possessionStr != "":
                index = possessionStr.find("WP")
                for noun in nounList:
                    if noun not in self.pronounList:
                        possessionSentences.append(possessionStr[:index] + nounSymbol \
                            + noun + possessionStr[index + len("WP"):])

        length = len(nounList)
        i = 0
        verbs = self.findVerbsAndItsRelatedNouns(question)
        answer = ""
        z3Content = ""
        verbSentencesList = []
        for index, info in verbs.iteritems():
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            nouns = info["relatedNouns"]
            length = len(nouns)
            if verbName not in self.addedVerbs.keys():
                number = length
                verbName = info[self.VERB_ORIGIN_NAME_TAG]
                for _ in range(length):
                    lessParaVerbName = verbName + "_" + str(number)
                    if lessParaVerbName in self.addedVerbs.keys():
                        verbName = lessParaVerbName
                        break
                    number -= 1
            if verbName not in self.addedVerbs.keys():
                print "[ERROR]: verb name:[" + verbName + "] not exists"
                errorType = ErrorTypes.PREDICATE_NAME_ERROR
                self.errorTypes.append({"type" : errorType, "val" : verbName})

                continue
            addingNouns = []
            #find the noun that is variable
            for noun in nouns:
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                tag = tags[nounIndex]
                if tag in self.questionAnswerTags:
                    addingNouns.append(tag)
                else:
                    addingNouns.append(tokens[nounIndex])
            sentences = []
            self.findAllAnswerSentence(addingNouns, nounList, sentences, "")
            verbSentencesList.append([verbName, sentences])
            i += 1
                
        i = 1
        #whose
        if possessionSentences != []:
            for posSentence in possessionSentences:
                stnNumber = 1
                tempStr = posSentence
                for verbName, verbSentences in verbSentencesList:
                    if verbSentences != []:
                        tempStr += " " + "(" + verbSymbol + verbName + " " + verbSentences[0] + ")"
                        stnNumber += 1
                if stnNumber > 1:
                    tempStr = "(and " + tempStr + ")"
                self.outputStr = outputStr + headString + tempStr + "))\n"
                self.outputStr += "(check-sat)\n"
                fileName = str(i) + "_output"
                self.writeIntoFile(fileName)
                #execute command line verification and get the output
                #the end char is  '\n', delete it
                var = os.popen("z3 " +  fileName).read()[:-1]
                print ("verification result:" + " " + tempStr + " : " + var)
                i += 1
                if str(var) == "unsat":
                    answer = tempStr
                    break

        #who or what
        else:
            def getAnswerSentence(sentenceList, string, completeSentences):
                if sentenceList == []:
                    if string != "":
                        completeSentences.append(string)
                    return
                for sentence in sentenceList[0][1]:
                    verbName = sentenceList[0][0]
                    temp = string + " " + "(" + verbSymbol + verbName + " " + sentence + ")"
                    if len(sentenceList) == 1:
                        completeSentences.append(temp)
                    else:
                        getAnswerSentence(sentenceList[1:], temp, completeSentences)

            answerSymbol = "unsat"
            reverseSymbol = False
            for reverseWord in self.reverseKeywords:
                if reverseSymbol:
                    break
                num = 0
                for token in self.description[self.LEM_TOKEN_TAG]:
                    if token == reverseWord:
                        answerSymbol = "sat"
                        reverseSymbol = True
                        break
                    num += 1

            answers = []
            getAnswerSentence(verbSentencesList, "", answers)
            verbNum = len(verbSentencesList)
            i = 1
            for answerSentence in answers:
                temp = ""
                if verbNum > 1:
                    temp = headString + "(and " + answerSentence
                    temp = self.bracketCheck(temp) + "\n"
                else:
                    temp += headString + answerSentence
                    temp = self.bracketCheck(temp) + "\n"
                self.outputStr = outputStr + temp + "(check-sat)\n"
                
                fileName = str(i) +  "_output"
                systemType = platform.system()
                if "Win" in systemType:
                    fileName = self.outputFilePath_Win + fileName
                else:
                    fileName = self.outputFilePath_Linux + fileName
                self.writeIntoFile(fileName)
                #execute command line verification and get the output
                #the end char is  '\n', delete it
                var = os.popen("z3 " +  fileName).read()
                print ("verification result:" + " " + answerSentence + " : " + var)
                i += 1
                if str(var).find(answerSymbol) == 0:
                    wordList = answerSentence.split(" ")
                    answer = ""
                    for word in wordList:
                        sepIndex, i = 0, 0
                        for c in word:
                            if c == '_':
                                sepIndex = i
                                break
                            i += 1
                        completeNounName = word[sepIndex + 1:]
                        if completeNounName in nounList:
                            answer += completeNounName + " "
                    z3Content = self.outputStr
                    break
        if answer == "":
            print "Guessing :"
            for noun in nounList:
                if noun not in self.pronounList:
                    answer = noun
                    break
        print "Answer :", answer
        return answer, z3Content

    def translateToZ3(self):
        self.z3keywordCheck()
        description = self.description
        kbList = self.kbList
        question = self.question
        allVerbs = []
        nounSortMap = {}
        descriptionVerbs = self.findVerbsAndItsRelatedNouns(description)
        questionVerbs = self.findVerbsAndItsRelatedNouns(question)
        questionVerbNames = []
        for index, info in questionVerbs.iteritems():
            questionVerbNames.append(info[self.VERB_COMBINE_NAME_TAG])
            questionVerbNames.append(info[self.VERB_ORIGIN_NAME_TAG])
        self.questionVerbNames = questionVerbNames
        for kb in kbList:
            kbVerbs = self.findVerbsAndItsRelatedNouns(kb)
            allVerbs.append(kbVerbs)
            tokens = kb[self.LEM_TOKEN_TAG]
            combinedVerbNameToIndexMap = {}
            originalVerbNameToIndexMap = {}
            #{SortName: [noun1, noun2, ...]}
            completeNouns = self.findCompleteNouns(kb)
            #find nouns in kb
            for index, info in kbVerbs.iteritems():
                nouns = info["relatedNouns"]
                combinedVerbNameToIndexMap[info[self.VERB_COMBINE_NAME_TAG]] = index
                originalVerbNameToIndexMap[info[self.VERB_ORIGIN_NAME_TAG]] = index
                for noun in nouns:
                    if not noun["var"]:
                        sort = noun[self.VERB_NOUN_SORT_TAG]
                        index = noun[self.VERB_NOUN_INDEX_TAG]
                        nounName1 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, False)
                        nounName2 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, True)
                        def addNounIntoMap(sort, name):
                            if name not in self.addedNouns:
                                if nounSortMap.has_key(sort):
                                    nounSortMap[sort].append(name)
                                else:
                                    nounSortMap[sort] = [name]
                                self.addedNouns.append(name)
                        
                        addNounIntoMap(sort, nounName1)
                        addNounIntoMap(sort, nounName2)
            
            #find nouns in description
            tokens = description[self.LEM_TOKEN_TAG]
            completeNouns = self.findCompleteNouns(description)
            for index, info in descriptionVerbs.iteritems():
                verbName = info[self.VERB_COMBINE_NAME_TAG]
                kbindex = -1
                #firstly, use combine name to get verb's info
                if combinedVerbNameToIndexMap.has_key(verbName):
                    kbindex = combinedVerbNameToIndexMap[verbName]
                #if not exists, use original name
                else:
                    verbName = info[self.VERB_ORIGIN_NAME_TAG]
                    if originalVerbNameToIndexMap.has_key(verbName):
                        kbindex = originalVerbNameToIndexMap[verbName]
                if kbindex != -1:
                    nouns = info["relatedNouns"]
                    kbinfo = kbVerbs[kbindex]
                    kbNounsInfo = kbinfo["relatedNouns"]
                    length = len(kbNounsInfo)
                    i = 0
                    for noun in nouns:
                        nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                        nounName = tokens[nounIndex]
                        sort = ""
                        if i < length:
                            sort = kbNounsInfo[i][self.VERB_NOUN_SORT_TAG]
                        else:
                            print "[ERROR]: Wrong number of predicate's parameter"
                            errorType = ErrorTypes.PREDICATE_PARAMETER_ERROR
                            self.errorTypes.append({"type" : errorType, "val" : verbName})

                            sort = nouns[i][self.VERB_NOUN_SORT_TAG]
                        nounName1 = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False)
                        nounName2 = self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, True)
                       
                        def addNounIntoMap(sort, name):
                            if name not in self.addedNouns:
                                if nounSortMap.has_key(sort):
                                    nounSortMap[sort].append(name)
                                else:
                                    nounSortMap[sort] = [name]
                                self.addedNouns.append(name)
                        
                        addNounIntoMap(sort, nounName1)
                        addNounIntoMap(sort, nounName2)
                       
                       #add possession noun into the sort map
                        nameList1 = nounName1.split("_")
                        nameList2 = nounName2.split("_")
                        possessionName = ""
                        for name in nameList1:
                            if name not in nameList2:
                                possessionName += name + "_"
                        if possessionName != "":
                            #constant noun name + _p presenting person noun, _t presenting thing noun
                            possessionName += "p"
                            addNounIntoMap("person", possessionName)
                            possessionName = possessionName[:-1] + "t"
                            addNounIntoMap("thing", possessionName)

                        i += 1

        res = ""
        res += self.addDeclareSort(nounSortMap)
        res += self.addRules_EntityNotEqual(nounSortMap)
        res += self.addRules_EntityRange(nounSortMap)
        
        #add rel declaration
        verbLength = 0
        for verbs in allVerbs:
            verbLength += 1
            res += self.addDeclareRel(verbs)
        res += self.addDeclareRel_possession(self.description)
        res += self.addDeclareRel_possession(self.question)
        i = 0
        for kb in kbList:
            res += self.addDeclareRel_possession(kb)
            if i >= verbLength:
                verbs = {}
            else:
                verbs = allVerbs[i]
            res = self.addRules_ClosedReasonAssumption(kb, verbs, res)
            res = self.addRules_NegativeFormEntailment(kb, verbs, res)
            i += 1

        #add entailment
        res += self.addPrepVerbToVerbEntailment()
        #res += self.addRules_NounAsVerbRange()
        res += self.addRules_OnlyOneAnswer(nounSortMap)
        res += self.addDescription(self.description, nounSortMap)
        if len(self.context) >= 3:
            print "Description", self.context[0]
            print "Knowledge",
            for kb in self.context[1:-1]:
                print kb,
            print ""
            print "Queseion", self.context[-1]
        return self.reasoning(nounSortMap, res)

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.outputStr)

    def z3keywordCheck(self):
        i = 0
        for token in self.question[self.LEM_TOKEN_TAG]:
            if token in self.z3_keywords:
                self.question[self.LEM_TOKEN_TAG][i] = "_" + token
            i += 1
        i = 0
        for token in self.description[self.LEM_TOKEN_TAG]:
            if token in self.z3_keywords:
                self.description[self.LEM_TOKEN_TAG][i] = "_" + token
            i += 1

        for i in range(len(self.kbList)):
            j = 0
            for token in self.kbList[i][self.LEM_TOKEN_TAG]:
                if token in self.z3_keywords:
                    self.kbList[i][self.LEM_TOKEN_TAG][j] = "_" + token
                j += 1

    def bracketCheck(self, string):
        num = 0
        for c in string:
            if c == "(":
                num += 1
            elif c == ")":
                num -= 1
        for i in range(num):
            string += ")"

        return string

    def getErrorInfo(self):
        errorInfo = {}
        errorInfo[ErrorTypes.ENTITY_NAME_ERROR] = "Entity doesn't exist"
        errorInfo[ErrorTypes.PREDICATE_NAME_ERROR] = "Predicate doesn't exist"
        errorInfo[ErrorTypes.PREDICATE_PARAMETER_ERROR] = "Wrong number of predicate's parameters"
        errorInfo[ErrorTypes.VAR_NAME_ERROR] = "Variable in knowledge doesn't exist"
        errorStr = ""
        for error in self.errorTypes:
            errorStr += errorInfo[error["type"]] + " : " + error["val"] + "\n"

        return errorStr

    def parsingSample(self):
        sampleQuestionContent = \
"Susan knows about Ann's personal problems because she is nosy.\n\
If person B is nosy, then person B will know about somebody's personal problems.\n\
If person B is indiscreet, then somebody will know about person B's personal problems.\n\
Who is nosy?"

        sampleParsingContent = " Parser.parse: parse {\
                Parser.ensureExecuted \
              } \
              Parser.setEvaluation: 0 candidates \
              Example: Susan knows about Ann's personal problems. because she is nosy {\
                Tokens: [susan, knows, about, ann, 's, personal, problems, ., because, she, is, nosy]\
                Lemmatized tokens: [Susan, know, about, Ann, 's, personal, problem, ., because, she, be, nosy]\
                POS tags: [NNP, VBZ, IN, NNP, POS, JJ, NNS, ., IN, PRP, VBD-AUX, JJ]\
                NER tags: [PERSON, O, O, PERSON, O, O, O, O, O, O, O, O]\
                NER values: [null, null, null, null, null, null, null, null, null, null, null, null]\
                Dependency children: [[], [nsubj->0, nmod:about->6, punct->7], [], [case->4], [], [], \
                [case->2, nmod:poss->3, amod->5], [], [], [], [], [cop->10, mark->8, nsubj->9]]\
              }\
            \
              Parser.parse: parse {\
                Parser.ensureExecuted\
              }\
              Parser.setEvaluation: 0 candidates \
              Example: If person B is nosy, then person B will know about somebody’s personal problems {\
                Tokens: [if, person, b, is, nosy, ,, then, person, b, will, know, about, somebody, 's, personal, problems]\
                Lemmatized tokens: [if, person, b, be, nosy, ,, then, person, b, will, know, about, somebody, 's, personal,\
                 problem]\
                POS tags: [IN, NN, NN, VBD-AUX, JJ, ,, RB, NN, NN, VBD-AUX, VB, IN, NN, POS, JJ, NNS]\
                NER tags: [O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O]\
                NER values: [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null]\
                Dependency children: [[], [], [compound->1], [], [mark->0, nsubj->2, cop->3, punct->5, parataxis->10], [], \
                [], [], [compound->7], [], [nmod:about->15, advmod->6, nsubj->8, aux->9], [], [case->13], [], [], [case->11,\
                 nmod:poss->12, amod->14]]\
              }\
            \
              Parser.parse: parse {\
                Parser.ensureExecuted \
              }\
              Parser.setEvaluation: 0 candidates \
              Example: If person B is indiscreet, then somebody will know about person B’s personal problems {\
                Tokens: [if, person, b, is, indiscreet, ,, then, somebody, will, know, about, person, b, 's, \
                personal, problems]\
                Lemmatized tokens: [if, person, b, be, indiscreet, ,, then, somebody, will, know, about, person\
                , b, 's, personal, problem]\
                POS tags: [IN, NN, NN, VBD-AUX, JJ, ,, RB, NN, VBD-AUX, VB, IN, NN, NN, POS, JJ, NNS]\
                NER tags: [O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O]\
                NER values: [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null]\
                Dependency children: [[], [], [compound->1], [], [mark->0, nsubj->2, cop->3], [], [], [advmod->6], [], \
                [nmod:about->15, advcl->4, punct->5, nsubj->7, aux->8], [], [], [compound->11, case->13], [], [], \
                [case->10, nmod:poss->12, amod->14]]\
              }\
            \
              Parser.parse: parse {\
                Parser.ensureExecuted \
              }\
              Parser.setEvaluation: 0 candidates \
              Example: Who is nosy {\
                Tokens: [who, is, nosy]\
                Lemmatized tokens: [who, be, nosy]\
                POS tags: [WP, VBD-AUX, JJ]\
                NER tags: [O, O, O]\
                NER values: [null, null, null]\
                Dependency children: [[], [], [nsubj->0, cop->1]]\
              }"

        sampleZ3Content = "(declare-sort thing)\n \
            (declare-sort person)\n\
            (declare-const Noun_personal_somebody_problem thing)\n\
            (declare-const Noun_personal_problem thing)\n\
            (declare-const Noun_personal_Ann_problem thing)\n\
            (declare-const Noun_Ann_t thing)\n\
            (declare-const Noun_personal_b_problem thing)\n\
            (declare-const Noun_Susan person)\n\
            (declare-const Noun_Ann_p person)\n\
            (declare-const Noun_she person)\n\
            (assert (not (= Noun_personal_somebody_problem Noun_personal_problem)))\n\
            (assert (not (= Noun_personal_somebody_problem Noun_personal_Ann_problem)))\n\
            (assert (not (= Noun_personal_somebody_problem Noun_Ann_t)))\n\
            (assert (not (= Noun_personal_somebody_problem Noun_personal_b_problem)))\n\
            (assert (not (= Noun_personal_problem Noun_personal_Ann_problem)))\n\
            (assert (not (= Noun_personal_problem Noun_Ann_t)))\n\
            (assert (not (= Noun_personal_problem Noun_personal_b_problem)))\n\
            (assert (not (= Noun_personal_Ann_problem Noun_Ann_t)))\n\
            (assert (not (= Noun_personal_Ann_problem Noun_personal_b_problem)))\n\
            (assert (not (= Noun_Ann_t Noun_personal_b_problem)))\n\
            (assert (not (= Noun_Susan Noun_Ann_p)))\n\
            (assert (not (= Noun_Susan Noun_she)))\n\
            (assert (not (= Noun_Ann_p Noun_she)))\n\
            (assert (forall ((x thing)) (or (= x Noun_personal_somebody_problem)\
             (= x Noun_personal_problem) (= x Noun_personal_Ann_problem) (= x Noun_Ann_t)\
              (= x Noun_personal_b_problem) )))\n\
            (assert (forall ((x person)) (or (= x Noun_Susan) (= x Noun_Ann_p) (= x Noun_she) )))\n\
            (declare-rel Verb_know (person thing ))\n\
            (declare-rel Verb_know_about (person thing ))\n\
            (declare-rel Verb_know_1 (person ))\n\
            (declare-rel Verb_know_2 (person thing ))\n\
            (declare-rel Verb_nosy (person ))\n\
            (declare-rel Verb_indiscreet (person ))\n\
            (declare-rel Verb_possess_pt (person thing))\n\
            (declare-rel Verb_possess_tt (thing thing))\n\
            (assert (forall ((a person) ) (= (Verb_nosy a)\
              (exists ((b person)) (and (Verb_know_about a Noun_personal_problem)\
               (Verb_possess_pt b Noun_personal_problem) ))  )))\n\
            (assert (forall ((b person) ) (= (Verb_indiscreet b)  \
            (exists ((a person)) (and (Verb_know_about a Noun_personal_problem) \
            (Verb_possess_pt b Noun_personal_problem) ))  )))\n\
            (assert (forall ((b person) ) (=> (Verb_know_about b Noun_personal_problem ) \
            (Verb_know_1 b ))))\n\
            (assert (forall ((b person) ) (= (Verb_know_about b Noun_personal_problem )\
             (Verb_know_2 b Noun_personal_problem ))))\n\
            (assert (= (Verb_nosy Noun_Susan ) (not (Verb_nosy Noun_Ann_p )) ))\n\
            (assert (= (Verb_nosy Noun_Ann_p ) (not (Verb_nosy Noun_Susan )) ))\n\
            (assert (and (Verb_know_about Noun_Susan Noun_personal_problem )   \
            (Verb_possess_pt Noun_Ann_p Noun_personal_problem) \
            (Verb_possess_tt Noun_Ann_t Noun_personal_problem) ))\n\
            (assert (not  (Verb_nosy Noun_Susan )))\n\
            (check-sat)\n"
        systemType = platform.system()
        fileName = "sample"
        if "Win" in systemType:
            fileName = self.outputFilePath_Win + fileName
        else:
            fileName = self.outputFilePath_Linux + fileName
        with open(fileName, "w") as f:
            f.write(sampleZ3Content)
        var = os.popen("z3 " +  fileName).read()
        print "Sample Question:"
        print sampleQuestionContent
        if "unsat" in var:
            print "Answer: " + sampleZ3Content.split('\n')[-3].strip()
        else:
            print "Unable to solve."

def main():
    t = Translater()
    t.loadFromFile("outputTemp")
    #t.parsingSample()

if __name__ == '__main__':
    main()
