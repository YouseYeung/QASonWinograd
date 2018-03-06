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
    def __init__(self, symbol):
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
        #noun name and its sort map
        self.addedNouns = {}
        self.candidateAnswers = []
        self.givenAnswerTokens = []
        self.provedAnswers = []
        #z3 keywords, these words can not be declared as a rel, we have to add '_' in front of the word.
        self.outputStr = ""
        self.possessionVerbs = []
        self.questionVerbNames = []
        self.nounAsVerbs = []
        self.loadFileName = ""
        self.hasCandidateAnswerSymbol = symbol
        #errorTypes: [{"type": str, "val" : str},]
        self.errorTypes = []
        self.VERB_SYMBOL = "Verb_"
        self.NOUN_SYMBOL = "Noun_"
        self.Possess_Person_Thing = "possess_pt"
        self.Possess_Thing_Thing = "possess_tt"
        self.EXAMPLE_TAG = "Example:"
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
        self.VERB_NOUN_VAR_TAG = "var"
        self.parsingSymbol = [self.TOKEN_TAG, self.LEM_TOKEN_TAG, self.POS_TAG, self.NER_TAG, self.NER_VAL_TAG, self.CHILDREN_TAG]
        self.z3_keywords = ["repeat", "assert", "declare", "map"]
        self.existVars = ["somebody", "something", "sth", "sb", "he", "it"]
        self.pronounList = ["it", "he", "she", "they", "I", "we", "you", "It", "He", "She", "They", "You", "We"]
        self.questionAnswerTags = ["WP", "WDT", "WRB", "WP$"]
        self.reverseKeywords = ["although", "though"]
        self.preprocessor = Preprocessor()
        self.answerFileName = "answers.txt"
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

    def getCandidateAnswerFromString(self, answersString):
        self.givenAnswerTokens = answersString[self.EXAMPLE_TAG][:-2].split("/")
        answerTokens = answersString[self.LEM_TOKEN_TAG]
        temp = set()
        #remove "Answers" and ":"
        if len(answerTokens) > 3:
            answerTokens = answerTokens[2:]
        for answer in answerTokens:
            if answer.isalpha() and answer != "the":
                temp.add(answer)
        self.candidateAnswers = list(temp)

    def loadFromFile(self, fileName):
        systemType = platform.system()
        if "Win" in systemType:
            fileName = self.inputFilePath_Win + fileName
        else:
            fileName = self.inputFilePath_Linux + fileName


        i, solvingNum = 0, 10
        with open(fileName, 'r') as f:
            lastLine = ''
            beginMark = False
            while True:
                content = f.readline()
                if not content or i > solvingNum:
                    #reach the end of wsc problems, then add the parsing result into question and then translate.
                    if self.parsingResult != {}:
                        if self.hasCandidateAnswerSymbol:
                            self.question = self.kbList[-1]
                            self.kbList = self.kbList[:-1]
                            self.getCandidateAnswerFromString(self.parsingResult)
                        else:
                            self.question = self.parsingResult
                    return self.translateToZ3()
                    break

                if content.find(self.EXAMPLE_TAG) != -1:
                    if content.find("Answers:") == -1:
                        self.context.append(content[len(self.EXAMPLE_TAG) + 1:-3])
                    else:
                        self.parsingResult[self.EXAMPLE_TAG] = content[len(self.EXAMPLE_TAG) + 3 + len("Answers:"):]
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
                if (content.strip() == "") and (lastLine.strip() == ""):
                    if self.hasCandidateAnswerSymbol:
                        self.question = self.kbList[-2]
                        self.getCandidateAnswerFromString(self.kbList[-1])
                        self.kbList = self.kbList[:-2]
                    else:
                        self.question = self.kbList[-1]
                        self.kbList = self.kbList[:-1]
                    if i <= solvingNum:
                        self.translateToZ3()
                    i += 1
                    self.description = {}
                    self.question = {}
                    self.kbList = []
                    self.context = []
                    self.addedVerbs = {}
                    self.addedNouns = {}
                    self.candidateAnswers = []
                    self.nounAsVerbs = []
                    self.outputStr = ""
                    self.possessionVerbs = []
                    self.questionVerbNames = []
                    self.errorTypes = []
                    self.parsingResult = {}
                    self.givenAnswerTokens = []
                    beginMark = False
                    continue

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
        addedIndex = []
        for tag in tags:
            if "NN" in tag:
                child = children[i]
                #adj noun
                symbols = ["amod", "compound", "nmod:poss"] 
                relatedNounsIndex = []
                for symbol in symbols:
                    index = self.findIndexBySymbol(child, symbol)
                    if index != -1 and index not in addedIndex and ("VB" not in tags[index]):
                        relatedNounsIndex.append({"tag":symbol, "index":index})
                        addedIndex.append(index)
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
        typeOfNoun = ['subj', 'iobj', 'dobj', 'nmod', 'xcomp', 'ccomp', 'advmod']
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
                    if _type == "ccomp":
                        if index + 1 < length:
                            #complement clause
                            if tokens[index + 1] == "that":
                                relatedNounsIndex.append(index + 1)
                        continue

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
    #return {index: {self.VERB_ORIGIN_NAME_TAG:str, combinedVerbName:str, self.VERB_RELATION_NOUN_TAG:[{self.VERB_NOUN_INDEX_TAG:nounIndex, self.VERB_NOUN_SORT_TAG:nounSort, self.VERB_NOUN_VAR_TAG:symbolOfVariable}] } }
    def findVerbsAndItsRelatedNouns(self, library):
        existVars = self.existVars
        tokens = library[self.LEM_TOKEN_TAG]
        tags = library[self.POS_TAG]
        children = library[self.CHILDREN_TAG]
        #{index: {self.VERB_ORIGIN_NAME_TAG:str, combinedVerbName:str, self.VERB_RELATION_NOUN_TAG:[{self.VERB_NOUN_INDEX_TAG:nounIndex, self.VERB_NOUN_SORT_TAG:nounSort, self.VERB_NOUN_VAR_TAG:symbolOfVariable}] } }
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
            if i not in addedVerbsIndex and ("VB" in tag or "JJ" in tag or "RB" in tag or "NN" in tag or "IN" in tag):
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
                #be + adj, be + adv, be + prep, as an unary predicate, be + adv
                if "JJ" in tag or"RB" in tag or "NN" in tag or "IN" in tag:
                    if child.find("cop") == -1 and child.find("auxpass") == -1:
                        continue
                    #if noun is parsed as a verb, then add it into self.nounAsVerbs list
                    elif "NN" in tag:
                        self.nounAsVerbs.append(tokens[i])
                #find negative form
                if "neg" in child:
                    combinedVerbName = "not_" + combinedVerbName

                #combine prep or adv to get the combined form of verb.
                #a verb may be combined with many adverbs.
                indexStart = 0
                while True:
                    index = self.findIndexBySymbol(child[indexStart:], "advmod")
                    indexStart = child.find("advmod", indexStart) + 1
                    if index != -1:
                        advName = tokens[index]
                        if advName != "then":
                            combinedVerbName += "_" + advName
                    else:
                        break
                
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
                    if prepName != "poss":
                        combinedVerbName += "_" + prepName

                #address the condition: do better than
                #address the condition: sb sees sth1 through sth2, sth2 occurs at sth1's children with the form: "nmod:prep->" 
                index = self.findIndexBySymbol(child, "obj")
                if index != -1:
                    if "JJ" in tags[index]:
                        adjName = tokens[index]
                        combinedVerbName += "_" + adjName
                    elif "NN" in tags[index] or "PRP" in tags[index]:
                        child = children[index]
                        indexStart = child.find("nmod")
                        if indexStart != -1:
                            indexEnd = child[indexStart:].find("->") + indexStart
                            prepName = child[indexStart + len("nmod:"):indexEnd]
                            if prepName != "poss":
                                combinedVerbName += "_" + prepName

                #address the condition: go out, get back, get up
                index = self.findIndexBySymbol(child, "compound:prt")
                if index != -1:
                    advName = tokens[index]
                    combinedVerbName += "_" + advName
                
                #if verb is the form of "not" + prep
                #change originalVerbName into a combinedVerbName
                if originalVerbName == "not":
                    originalVerbName = combinedVerbName
                
                verbs[i] = {self.VERB_ORIGIN_NAME_TAG:originalVerbName, self.VERB_COMBINE_NAME_TAG:combinedVerbName}
                relatedNounsIndex = self.findRelatedNouns(library, i)
                verbs[i][self.VERB_RELATION_NOUN_TAG] = []
                unsortedNouns = []
                for index in relatedNounsIndex:
                    nounInfo = {self.VERB_NOUN_INDEX_TAG:index}
                    nounName = tokens[index]
                    #determine if noun name is a variable?
                    if len(nounName) == 1:
                        lastWordIndex = index - 1
                        nounInfo[self.VERB_NOUN_SORT_TAG] = tokens[lastWordIndex]
                        nounInfo[self.VERB_NOUN_VAR_TAG] = True

                    elif nounName in existVars: 
                        if nounName == "somebody" or nounName == "sb" or nounName == "he":
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "person"
                            nounInfo[self.VERB_NOUN_VAR_TAG] = True
                        elif nounName == "something" or nounName == "sth" or nounName == "it":
                            #address the condition of do something adj.
                            if nounName == "something" and children[index].find("amod") != -1:
                                nounInfo[self.VERB_NOUN_VAR_TAG] = False
                                nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                            else:
                                nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                                nounInfo[self.VERB_NOUN_VAR_TAG] = True

                    elif tags[index] in self.questionAnswerTags:
                        if nounName == "who" or nounName == "whom" or nounName == "whose":
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "person"
                        else:
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                        nounInfo[self.VERB_NOUN_VAR_TAG] = False

                    else:
                        nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                        nounInfo[self.VERB_NOUN_VAR_TAG] = False
                    unsortedNouns.append(nounInfo)

                #sort all nouns except the subject noun, it is because subject noun is always the first noun name.
                
                if unsortedNouns != []:
                    sortedNouns = sorted(unsortedNouns[1:], key = lambda x : x[self.VERB_NOUN_INDEX_TAG], reverse = False)
                    verbs[i][self.VERB_RELATION_NOUN_TAG].append(unsortedNouns[0])
                    for noun in sortedNouns:
                        verbs[i][self.VERB_RELATION_NOUN_TAG].append(noun)

                addedVerbsIndex.append(i)

                #combination of verb and verb, such as make sure to do, want to do, try to do, has to do
                combinedindexStart = children[i].find("xcomp")
                if combinedindexStart != -1:
                    nsubj = ""
                    if verbs[i][self.VERB_RELATION_NOUN_TAG] != []:
                        nsubj = verbs[i][self.VERB_RELATION_NOUN_TAG][0]
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
                    if nsubj != "":
                        verbs[index][self.VERB_RELATION_NOUN_TAG] = [nsubj]
                    else:
                        verbs[index][self.VERB_RELATION_NOUN_TAG] = []
                    relatedNounsIndex = self.findRelatedNouns(library, index)
                    for ii in relatedNounsIndex:
                        nounInfo = {self.VERB_NOUN_INDEX_TAG:ii}
                        nounName = tokens[ii]
                        #determine if noun name is a variable?
                        if len(nounName) == 1:
                            lastWordIndex = ii - 1
                            nounInfo[self.VERB_NOUN_SORT_TAG] = tokens[lastWordIndex]
                            nounInfo[self.VERB_NOUN_VAR_TAG] = True
                        else:
                            nounInfo[self.VERB_NOUN_SORT_TAG] = "thing"
                            nounInfo[self.VERB_NOUN_VAR_TAG] = False
                        verbs[index][self.VERB_RELATION_NOUN_TAG].append(nounInfo)

                    verbs[index][self.VERB_RELATION_NOUN_TAG] = sorted(verbs[index][self.VERB_RELATION_NOUN_TAG], key = lambda x : x[self.VERB_NOUN_INDEX_TAG], reverse = False)
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
            for nounName in self.addedNouns.keys():
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
            nounStr = ""
            num = 0
            if combinedVerbName not in self.addedVerbs.keys():
                nouns = info[self.VERB_RELATION_NOUN_TAG]
                res += declareRel + verbSymbol + combinedVerbName + " ("
                for noun in nouns:
                    nounStr += noun[self.VERB_NOUN_SORT_TAG] + " "
                    num += 1
                res += nounStr + "))\n"
                #add all declared verbs and its number of parameters into list addedverb
                self.addedVerbs[combinedVerbName] = num
            else:
                continue

            #descending grade for verbs to get predicates with less parameter
            lessNum = 1
            nouns = ""
            relatedNouns = info[self.VERB_RELATION_NOUN_TAG]
            for noun in relatedNouns:
                lessPredicateVerbName = originalVerbName + "_" + str(lessNum)
                if lessPredicateVerbName in self.addedVerbs.keys():
                    continue
                res += declareRel + verbSymbol + lessPredicateVerbName + " ("
                nouns += noun[self.VERB_NOUN_SORT_TAG] + " "
                res += nouns + "))\n"
                self.addedVerbs[lessPredicateVerbName] = lessNum
                lessNum += 1

            #additional verb for positive verb
            if "not" in combinedVerbName:
                posVerbName = ""
                verbNames = combinedVerbName.split("_")
                for name in verbNames:
                    if name != "not":
                        posVerbName += name + "_"
                posVerbName = posVerbName[:-1]
                if posVerbName not in self.addedVerbs.keys():
                    res += declareRel + verbSymbol + posVerbName + " (" + nounStr + "))\n"
                    self.addedVerbs[posVerbName] = num
            #additional verb for negative verb
            if "not" not in combinedVerbName:
                newVerbName = "not_" + combinedVerbName
                if not self.addedVerbs.has_key(newVerbName):
                    res += declareRel + verbSymbol + newVerbName + " (" + nounStr + "))\n"
                    self.addedVerbs[newVerbName] = num

        return res

    def addPrepVerbToVerbEntailment(self):
        addedVerbs = {}
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        for kb in self.kbList:
            headString = "(assert "
            tokens = kb[self.LEM_TOKEN_TAG]
            verbs = self.findVerbsAndItsRelatedNouns(kb)
            completeNouns = self.findCompleteNouns(kb)
            for index, info in verbs.iteritems():
                combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
                originalVerbName = info[self.VERB_ORIGIN_NAME_TAG]
                if not addedVerbs.has_key(originalVerbName):
                    addedVerbs[originalVerbName] = True
                    nouns = info[self.VERB_RELATION_NOUN_TAG]
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
                        if noun[self.VERB_NOUN_VAR_TAG]:
                            pronoun = chr(ord('a') + number)
                            addedNouns += pronoun + " "
                            nounDeclareString += "(" + pronoun + " " + noun[self.VERB_NOUN_SORT_TAG] + ") "
                        else:
                            addedNouns += nounSymbol + self.getCompleteNounNameByIndex(noun[self.VERB_NOUN_INDEX_TAG], \
                                completeNouns, tokens, True) + " "
                        lessParaPredicateString.append(originalVerbString + addedNouns + ")")
                        number += 1

                    combinedVerbString += addedNouns + ") "
                    if nounDeclareString != "":
                        nounDeclareString = "(forall (" + nounDeclareString + ") "
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
    def addReality_NoEntailment(self, library, verbs, outputStr):
        res = ""
        headString = "(assert "
        declareVarStr, pronoun_name_Map = self.addVariableDeclare(library, verbs)
        tokens = library[self.LEM_TOKEN_TAG]
        addedExist = False
        existSentence = ""
        for index, info in verbs.iteritems():
            nouns = info[self.VERB_RELATION_NOUN_TAG]
            for noun in nouns:
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                nounName = tokens[nounIndex]
                if nounName in self.existVars[:-2]:
                    temp = self.addExistVarDeclaration(nounName, addedExist, pronoun_name_Map)
                    if temp != "":
                        addedExist = True
                        existSentence += temp

        sentence = self.addRealityForOneVerb(library, verbs, verbs, pronoun_name_Map, [])
        if existSentence != "":
            existSentence += ")"
        if sentence != "":
            res = headString + existSentence + sentence
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
                nouns = info[self.VERB_RELATION_NOUN_TAG]
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
        type_AB1, type_AB2 = "A>B", "A=B"
        type_ANT_ABC1 = "A>BVC, A>B^C, C>A, B>A"
        type_ANT_ABC2 = "AvB>C, C>A, C>B"
        type_SEC_ABC3 = "A>BVC, A>B, A>C"
        questionVerbs = self.findAnswerPredicate()
        
        for verb in questionVerbs:
            orgAnsPreName = verb[self.VERB_ORIGIN_NAME_TAG]
            comAnsPreName = verb[self.VERB_COMBINE_NAME_TAG]
            #answer predicate in antecedent
            if orgAnsPreName in antecedent or comAnsPreName in antecedent:
                if "and" in secedent or "or" in secedent:
                    return type_ANT_ABC1
                elif "or" in antecedent:
                    return type_ANT_ABC2
                else:
                    return type_AB2

            #answer predicate in secedent
            elif orgAnsPreName in secedent or comAnsPreName in secedent:
                if "or" in secedent:
                    return type_SEC_ABC3
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
            nouns = info[self.VERB_RELATION_NOUN_TAG]
            for noun in nouns:
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                nounName = tokens[nounIndex]
                sort = noun[self.VERB_NOUN_SORT_TAG]
                
                if noun[self.VERB_NOUN_VAR_TAG]:
                    #remove "he" and "it"
                    if nounName == "he" or nounName == "it":
                        continue
                    if nounName not in existVars:
                        #if it is a variable, find its compound noun
                        nounChild = children[nounIndex]
                        if nounChild.find("compound") != -1:
                            compoundIndex = self.findIndexBySymbol(nounChild, "compound")
                            compoundNounName = tokens[compoundIndex]
                            nounName = compoundNounName + "_"+ nounName
                        
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
                            if "he" in tokens:
                                if sortNameMap.has_key("person"): 
                                    sortNameMap["person"].append(pronoun)
                                else:
                                    sortNameMap["person"] = [pronoun]

                        elif nounName == "something" or nounName == "sth":
                            pronoun_name_Map["it"] = pronoun
                            if "it" in tokens:
                                if sortNameMap.has_key("thing"):
                                    sortNameMap["thing"].append(pronoun)
                                else:
                                    sortNameMap["thing"] = [pronoun]

                        numOfPronoun += 1
                        #determine whether to add existence declaration in this position
                        if (nounName == "somebody" and "he" in tokens) \
                            or (nounName == "something" and "it" in tokens):
                            existSentence += self.addExistVarDeclaration(nounName, hasAddedStr_EXIST, pronoun_name_Map)
                            hasAddedStr_EXIST = True
                else:
                    #address the condition of noun being added as a verb
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
            return "(assert ", pronoun_name_Map
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
        type_AB1, type_AB2 = "A>B", "A=B"
        #ANT marks for answer in antecedent,
        #SEC marks for answer in secedent.
        type_ANT_ABC1 = "A>BVC, A>B^C, C>A, B>A"
        type_ANT_ABC2 = "AvB>C, C>A, C>B"
        type_SEC_ABC3 = "A>BVC, A>B, A>C"
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
            #transform verb list into dict
            for verb in antecedent:
                newVerbs[verb[0]] = verb[1]
            for verb in secedent:
                newVerbs[verb[0]] = verb[1]
            
            declareString, pronoun_name_Map = self.addVariableDeclare(library, newVerbs)
            #determine whether to add existence declaration in this position
            shouldAddExist = True
            #if existence declaration has been added
            if declareString.find("exists ((") != -1:
                shouldAddExist = False
            
            #assure that verb occurs in order to get the right relation between verbs, such as conj:and, conj:or
            antecedentString = ""
            secedentString = ""

            addedVerbsNum = 0
            existSentence = ""
            addedExist = False
            addedExistVars = []
            for verb in antecedent:
                newString = self.addRealityForOneVerb(library, {verb[0]:verb[1]}, verbs, pronoun_name_Map, addedVerbsIndex)
                if newString != "":
                    antecedentString += newString + " "
                    addedVerbsNum += 1
                if shouldAddExist:
                    for noun in verb[1][self.VERB_RELATION_NOUN_TAG]:
                        nounIndex = noun[self.VERB_NOUN_INDEX_TAG]    
                        nounName = tokens[nounIndex]
                        if nounName in self.existVars[:-2] and nounName not in addedExistVars:
                            temp = self.addExistVarDeclaration(nounName, addedExist, pronoun_name_Map)
                            if temp != "":
                                existSentence += temp
                                addedExist = True
                                addedExistVars.append(nounName)
                        #address the existence variable of possesion noun
                        nounChild = children[nounIndex]
                        if nounChild.find("nmod:poss") != -1:
                            i = self.findIndexBySymbol(nounChild, "nmod:poss")
                            possName = tokens[i]
                            if possName in self.existVars[:-2] and possName not in addedExistVars:
                                temp = self.addExistVarDeclaration(possName, addedExist, pronoun_name_Map)
                                if temp != "":
                                    addedExist = True
                                    existSentence += temp
                                    addedExistVars.append(possName)

            if addedVerbsNum > 1:
                antecedentString = "(and " + antecedentString + ")"
            if existSentence != "":
                antecedentString = existSentence + ") " + antecedentString + ")"

            addedVerbsNum = 0
            existSentence = ""
            addedExist = False
            addedExistVars = []
            for verb in secedent:
                newString = self.addRealityForOneVerb(library, {verb[0]:verb[1]}, verbs, pronoun_name_Map, addedVerbsIndex) 
                if newString != "":
                    secedentString += newString + " "
                    addedVerbsNum += 1
                if shouldAddExist:
                    for noun in verb[1][self.VERB_RELATION_NOUN_TAG]:
                        nounIndex = noun[self.VERB_NOUN_INDEX_TAG]    
                        nounName = tokens[nounIndex]
                        if nounName in self.existVars[:-2] and nounName not in addedExistVars:
                            temp = self.addExistVarDeclaration(nounName, addedExist, pronoun_name_Map)
                            if temp != "":
                                addedExist = True
                                existSentence += temp
                                addedExistVars.append(nounName)

                        #address the existence variable of possesion noun
                        nounChild = children[nounIndex]
                        if nounChild.find("nmod:poss") != -1:
                            i = self.findIndexBySymbol(nounChild, "nmod:poss")
                            possName = tokens[i]
                            #if somebody or something has been added, then neglect
                            if possName in self.existVars[:-2] and possName not in addedExistVars:
                                temp = self.addExistVarDeclaration(possName, addedExist, pronoun_name_Map)
                                if temp != "":
                                    addedExist = True
                                    existSentence += temp
                                    addedExistVars.append(possName)

            if addedVerbsNum > 1:
                secedentString = "(and " + secedentString + ")"
            if existSentence != "":
                secedentString = existSentence + ") " + secedentString + ")"
            
            return declareString, antecedentString + " " + secedentString

        if type_AB1 == entailmentType:
            res = ""
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            res = declareString + "(=> " + realityString
            return self.bracketCheck(res) + "\n"
        
        elif type_AB2 == entailmentType:
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            return self.bracketCheck(declareString + "(= " + realityString) + "\n"

        elif type_ANT_ABC1 == entailmentType:
            res = ""
            declareString, realityString = addRealityByAntAndSec(antecedent, secedent, verbs)
            res = self.bracketCheck(declareString + "(=> " + realityString) + "\n"
            #revision of the all verbs
            newVerbs = {}
            for verb in antecedent:
                newVerbs[verb[0]] = verb[1]
            for verb in secedent:
                addedVerbsIndex = []
                tempVerbs = newVerbs
                tempVerbs[verb[0]] = verb[1]
                declareString, realityString = addRealityByAntAndSec([verb], antecedent, tempVerbs)
                res += self.bracketCheck(declareString + "(=> " + realityString) + "\n"
            return res
        
        elif type_ANT_ABC2 == entailmentType:
            res = ""
            #neglect the answer antecedent to get description secedent
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
                res += self.bracketCheck(declareString + "(=> " + realityString) + "\n"
            return res

        elif type_SEC_ABC3 == entailmentType:
            res = ""
            newVerbs = {}
            for verb in antecedent:
                newVerbs[verb[0]] = verb[1]
            for verb in secedent:
                addedVerbsIndex = []
                tempVerbs = newVerbs
                tempVerbs[verb[0]] = verb[1]
                declareString, realityString = addRealityByAntAndSec(antecedent, [verb], tempVerbs)
                res += self.bracketCheck(declareString + "(=> " + realityString) + "\n"
            return res

    def addExistVarDeclaration(self, token, addedExist, pronoun_name_Map):
        headString = ""
        if "somebody" == token and pronoun_name_Map.has_key("somebody"):
            if addedExist:
                headString += " (" + pronoun_name_Map["somebody"] + " person )"
            else:
                headString = "(exists ((" + pronoun_name_Map["somebody"] + " person)"
                addedExist = True
        
        if "sb" == token and pronoun_name_Map.has_key("sb"):
            if addedExist:
                headString += " (" + pronoun_name_Map["sb"] + " person)"
            else:
                headString = "(exists ((" + pronoun_name_Map["sb"] + " person)"
                addedExist = True
        
        if "something" == token and pronoun_name_Map.has_key("something"):
            if addedExist:
                headString += " (" + pronoun_name_Map["something"] + " thing)"
            else:
                headString = "(exists ((" + pronoun_name_Map["something"] + " thing)"
                addedExist = True
        
        if "sth" == token and pronoun_name_Map.has_key("sth"):
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
        nounAsVerbSentence = ""
        for index, info in theVerb.iteritems():
            if index in addedVerbsIndex:
                continue
            nouns = info[self.VERB_RELATION_NOUN_TAG]
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            if verbName not in self.addedVerbs.keys():
                verbName = info[self.VERB_ORIGIN_NAME_TAG]
                if verbName not in self.addedVerbs.keys():
                    self.errorTypes.append({"type" : ErrorTypes.PREDICATE_NAME_ERROR, "val" : verbName})
                    continue

            headString += "(" + verbSymbol + verbName
            possessionStrs = []
            numOfNounInVerb = self.addedVerbs[verbName]
            num = 0
            for noun in nouns:
                num += 1
                if num > numOfNounInVerb:
                    break
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                nounName = tokens[nounIndex] 
                nounVar = noun[self.VERB_NOUN_SORT_TAG]
                
                if nounVar:
                    #if it is a variable, find its compound noun
                    nounChild = children[nounIndex]
                    if nounChild.find("compound") != -1:
                        compoundIndex = self.findIndexBySymbol(nounChild, "compound")
                        compoundNounName = tokens[compoundIndex]
                        nounName = compoundNounName + "_"+ nounName
                else:
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

                if nounVar:
                    #when the words, "he", "it" and so on, is used as variable
                    if pronoun_name_Map.has_key(nounName):
                        headString += " " + pronoun_name_Map[nounName]
                    #when the words, "he", "it" and so on, is used as constant
                    elif nounName in self.addedNouns.keys():
                        headString += " " + nounSymbol + nounName
                    else:
                        print "[ERROR]: incorrect variable name:", nounName
                        errorType = ErrorTypes.VAR_NAME_ERROR
                        self.errorTypes.append({"type" : errorType, "val" : nounName})

                else:
                    #if noun exists in self.nounAsVerbs list a verb
                    #then this noun is marked as a classification verb, such as Fish is an anmial
                    #then transform verb noun into (=> (noun x) (verb x))
                    if nounName in self.nounAsVerbs:
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

        
            #add possession reality
            if possessionStrs != []:
                headString = "(and " + headString
                for posStr in possessionStrs:
                    headString += " " + posStr + " "
                headString += ")"
            #add noun as verb sentence reality
            if nounAsVerbSentence != "":
                    headString = "(=> " + nounAsVerbSentence + " " + headString + ")"

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
            if (subjName == "somebody" or subjName == "his") and pronoun_name_Map.has_key(subjName):
                res += "(" + verbSymbol + self.Possess_Person_Thing + " " + pronoun_name_Map[subjName] \
                + " " + nounSymbol + objName + ")"
            elif (subjName == "something" or subjName == "its") and pronoun_name_Map.has_key(subjName):
                res += "(" + verbSymbol + self.Possess_Thing_Thing + " " + pronoun_name_Map[subjName] \
                + " " + nounSymbol + objName + ")"
            else:
                subjChild = children[subjIndex]
                i = subjChild.find("compound")
                if i != -1:
                    compoundIndex = self.findIndexBySymbol(subjChild, "compound")
                    compoundNoun = tokens[compoundIndex]
                    if compoundNoun == "person" and pronoun_name_Map.has_key(subjName):
                        res += "(" + verbSymbol + self.Possess_Person_Thing + " " + pronoun_name_Map[subjName] + " " \
                            + nounSymbol + objName + ")"
                    elif compoundNoun == "thing" and pronoun_name_Map.has_key(subjName):
                        res += "(" + verbSymbol + self.Possess_Thing_Thing + " " + pronoun_name_Map[subjName] + " " \
                            + nounSymbol + objName + ")"   
                    else:
                        self.errorTypes.append({"type" : ErrorTypes.PREDICATE_PARAMETER_ERROR, "val" : "posses"})
                        return ""
                #subjname is a constant
                else:
                    if subjName + "_p" in self.addedNouns.keys():
                        res += "(" + verbSymbol + self.Possess_Person_Thing + " " + nounSymbol + subjName + "_p " \
                        + nounSymbol + objName + ") "
         
                    if subjName + "_t" in self.addedNouns.keys():
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
                return self.addReality_NoEntailment(library, verbs, outputStr)
        else:
            return self.addReality_Entailment(library, verbs, sepIndex, outputStr)

    def addRules_NegativeFormEntailment(self, library, verbs, outputStr):
        addedVerbs = []
        res = ""
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        tokens = library[self.LEM_TOKEN_TAG]
        completeNouns = self.findCompleteNouns(library)
        headString = "(assert "
        for index, info in verbs.iteritems():
            combinedVerbName = info[self.VERB_COMBINE_NAME_TAG]
            if combinedVerbName not in addedVerbs:
                addedVerbs.append(combinedVerbName)
                posVerbName = ""
                negVerbName = ""
                if "not" not in combinedVerbName:
                    negVerbName = "not_" + combinedVerbName
                    posVerbName = combinedVerbName
                else:
                    verbNames = combinedVerbName.split("_")
                    for name in verbNames:
                        if name != "not":
                            posVerbName += name + "_"
                    posVerbName = posVerbName[:-1]
                    negVerbName = combinedVerbName

                number = 1
                negSentence = "(" + verbSymbol + negVerbName + " "
                posSentence = "(" + verbSymbol + posVerbName + " "
                nounSentence = ""
                nounDeclareString = ""
                for noun in info[self.VERB_RELATION_NOUN_TAG]:
                    if noun[self.VERB_NOUN_VAR_TAG]:
                        pronoun = chr(ord('a') + number)
                        nounSentence += pronoun + " "
                        nounDeclareString += "(" + pronoun + " " + noun[self.VERB_NOUN_SORT_TAG] + ") "
                    else:
                        nounSentence += nounSymbol + self.getCompleteNounNameByIndex(noun[self.VERB_NOUN_INDEX_TAG], completeNouns, tokens, True) + " "
                    number += 1
                if nounDeclareString != "":
                    nounDeclareString = "(forall (" + nounDeclareString + ") "
                temp = headString + nounDeclareString + "(= " + posSentence + nounSentence + ") "
                temp += "(not " + negSentence + nounSentence
                res += self.bracketCheck(temp) + "\n"
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
        nounList = self.getCandidateAnswerNounForQuestion(nounSortMap)

        verbs = self.findVerbsAndItsRelatedNouns(question)
        allQuestionVerbSentences = []
        for index, info in verbs.iteritems():
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            nouns = info[self.VERB_RELATION_NOUN_TAG]
            if verbName not in self.addedVerbs.keys():
                verbName = info[self.VERB_ORIGIN_NAME_TAG]
                length = len(nouns)
                number = length
                for _ in range(length):
                    lessParaVerbName = verbName + "_" + str(number)
                    if lessParaVerbName in self.addedVerbs.keys():
                        verbName = lessParaVerbName
                        break
                    number -= 1
                
                if verbName not in self.addedVerbs.keys():
                    continue
            
            verbSentence = "(" + verbSymbol + verbName + " "
            addingNouns = []
            #determine if the noun is an variable
            numOfNounInVerb = self.addedVerbs[verbName]
            num = 0
            for noun in nouns:
                num += 1
                if num > numOfNounInVerb:
                    break
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
                nouns = info[self.VERB_RELATION_NOUN_TAG]
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
                numOfNounInVerb = self.addedVerbs[verbName]
                num = 0
                for noun in nouns:
                    num += 1
                    if num > numOfNounInVerb:
                        break
                    nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                    nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, False)
                    #align description noun name to the noun name in kb
                    if verbName in self.possessionVerbs:
                        nounName = self.getCompleteNounNameByIndex(nounIndex, completeNouns, descriptionTokens, True)
                        possessionStrs.append(self.addPossessionReality(self.description, nounIndex, nounSortMap))
                    #if nounName has added as possesion name, 
                    #then transform original name into possesion name
                    nounVar = noun[self.VERB_NOUN_SORT_TAG]
                    if self.addedNouns.has_key(nounName):
                        if self.addedNouns[nounName] == "person":
                            if self.addedNouns.has_key(nounName + "_p"):
                                nounName += "_p"
                        elif self.addedNouns[nounName] == "thing":
                            if self.addedNouns.has_key(nounName + "_t"):
                                nounName += "_t"
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

    def getCandidateAnswerNounForQuestion(self, nounSortMap):
        res = set()
        tokens = self.question[self.LEM_TOKEN_TAG]
        if "who" in tokens or "whom" in tokens or "whose" in tokens or "which" in tokens:
            if nounSortMap.has_key("person"):
                for noun in nounSortMap["person"]:
                    if noun in self.pronounList:
                        continue
                    #remove suffix to discard nouns like he_p, he_t and so on
                    if len(noun) >= 3 and ("_p" == noun[-2:] or "_t" == noun[-2:]):
                        if noun[:-2] in self.pronounList:
                            continue
                    if self.hasCandidateAnswerSymbol:
                        originalNounNames = noun.split('_')
                        for name in originalNounNames:
                            if name in self.candidateAnswers:
                                res.add(noun)
                    else:
                        res.add(noun)
        #thing answer
        if "what" in tokens or "which" in tokens:
            if nounSortMap.has_key("thing"):
                for noun in nounSortMap["thing"]:
                    if noun in self.pronounList:
                        continue
                    #remove suffix to discard nouns like it_p, it_t and so on
                    if len(noun) >= 3 and ("_p" == noun[-2:] or "_t" == noun[-2:]):
                        if noun[:-2] in self.pronounList:
                            continue
                    if self.hasCandidateAnswerSymbol:
                        originalNounNames = noun.split('_')
                        for name in originalNounNames:
                            if name in self.candidateAnswers:
                                res.add(noun)
                    else:
                        res.add(noun)
        return list(res)

    def reasoning(self, nounSortMap, outputStr):
        question = self.question
        tokens = question[self.LEM_TOKEN_TAG]
        tags = question[self.POS_TAG]
        children = question[self.CHILDREN_TAG]
        headString = "(assert (not "
        verbSymbol = self.VERB_SYMBOL
        nounSymbol = self.NOUN_SYMBOL
        nounList = self.getCandidateAnswerNounForQuestion(nounSortMap)         

        #deal with possesion question
        possessionStr = ""
        possessionSentences = []
        if "whose" in tokens:
            i = 0
            completeNouns = self.findCompleteNouns(question)
            solvedRight = True
            for child in children:
                if child.find("poss") != -1:
                    nounName = self.getCompleteNounNameByIndex(i, completeNouns, tokens, False)
                    if nounSortMap.has_key("thing") and nounName in nounSortMap["thing"]:
                        possessionStr = "(" + verbSymbol + self.Possess_Thing_Thing \
                                        + " WP " + nounSymbol + nounName
                    elif nounSortMap.has_key("person") and nounName in nounSortMap["person"]:
                        possessionStr = "(" + verbSymbol + self.Possess_Person_Thing \
                                        + " WP " + nounSymbol + nounName
                    else:
                        nounName = tokens[i]
                        if nounSortMap.has_key("thing") and nounName in nounSortMap["thing"]:
                            possessionStr = "(" + verbSymbol + self.Possess_Thing_Thing \
                                            + " WP " + nounSymbol + nounName
                        elif nounSortMap.has_key("person") and nounName in nounSortMap["person"]:
                            possessionStr = "(" + verbSymbol + self.Possess_Person_Thing \
                                            + " WP " + nounSymbol + nounName
                        else:
                            self.errorTypes.append({"type" : ErrorTypes.ENTITY_NAME_ERROR, "val" : nounName})
                            solvedRight = False
                            break
                    break
                i += 1

            #replace "WP" with candidate noun words
            if possessionStr != "" and solvedRight:
                index = possessionStr.find("WP")
                for noun in nounList:
                    if noun not in self.pronounList:
                        possessionSentences.append(possessionStr[:index] + nounSymbol \
                            + noun + possessionStr[index + len("WP"):])

        length = len(nounList)
        i = 0
        verbs = self.findVerbsAndItsRelatedNouns(question)
        completeNouns = self.findCompleteNouns(question)
        answer = ""
        z3Content = ""
        #get all the possible reality sentences for question
        verbSentencesList = []
        for index, info in verbs.iteritems():
            verbName = info[self.VERB_COMBINE_NAME_TAG]
            nouns = info[self.VERB_RELATION_NOUN_TAG]
            length = len(nouns)
            #if verbName and verb's related nouns not match, then transform verbName
            if verbName not in self.addedVerbs.keys() or self.addedVerbs[verbName] != length:
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
            numOfNounInVerb = self.addedVerbs[verbName]
            num = 0
            for noun in nouns:
                num += 1
                if num > numOfNounInVerb:
                    break
                nounIndex = noun[self.VERB_NOUN_INDEX_TAG]
                tag = tags[nounIndex]
                if tag in self.questionAnswerTags:
                    addingNouns.append(tag)
                else:
                    addingNouns.append(self.getCompleteNounNameByIndex(nounIndex, completeNouns, tokens, False))
            
            sentences = []
            self.findAllAnswerSentence(addingNouns, nounList, sentences, "")
            verbSentencesList.append([verbName, sentences])
            i += 1
                
        i = 1

        answerSymbol = "unsat"
        reverseSymbol = False
        for reverseWord in self.reverseKeywords:
            if reverseSymbol:
                break
            num = 0
            for token in self.description[self.LEM_TOKEN_TAG]:
                if token == reverseWord:
                    #if there exists a comma before reverseKeywords 
                    #or reverseKeywords exists at the begining
                    if num == 0 or \
                        num > 1 and self.description[self.LEM_TOKEN_TAG][num - 1] == ',':
                        answerSymbol = "sat"
                        reverseSymbol = True
                    break
                num += 1

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
                if str(var) == answerSymbol:
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
                
                #delete error infos 
                var = var.split('\n')
                for string in var:
                    if len(string) < 10:
                        var = string
                        break

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

        hasGottenAnswer = True 
        if answer == "":
            hasGottenAnswer = False 
            print "Guessing :"
            length = len(self.givenAnswerTokens)
            guessingNum = random.randint(0, length - 1)
            answer = self.givenAnswerTokens[guessingNum]

        print "Answer :", answer
        return answer, z3Content, hasGottenAnswer

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
                nouns = info[self.VERB_RELATION_NOUN_TAG]
                combinedVerbNameToIndexMap[info[self.VERB_COMBINE_NAME_TAG]] = index
                originalVerbNameToIndexMap[info[self.VERB_ORIGIN_NAME_TAG]] = index
                for noun in nouns:
                    if not noun[self.VERB_NOUN_VAR_TAG]:
                        sort = noun[self.VERB_NOUN_SORT_TAG]
                        index = noun[self.VERB_NOUN_INDEX_TAG]
                        nounName1 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, False)
                        nounName2 = self.getCompleteNounNameByIndex(index, completeNouns, tokens, True)
                        def addNounIntoMap(sort, name):
                            if name not in self.addedNouns.keys():
                                if nounSortMap.has_key(sort):
                                    nounSortMap[sort].append(name)
                                else:
                                    nounSortMap[sort] = [name]
                                self.addedNouns[name] = sort
                        
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
                    nouns = info[self.VERB_RELATION_NOUN_TAG]
                    kbinfo = kbVerbs[kbindex]
                    kbNounsInfo = kbinfo[self.VERB_RELATION_NOUN_TAG]
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
                            if name not in self.addedNouns.keys():
                                if nounSortMap.has_key(sort):
                                    nounSortMap[sort].append(name)
                                else:
                                    nounSortMap[sort] = [name]
                                self.addedNouns[name] = sort

                        #just add the complete form of noun into self.addedNouns
                        addNounIntoMap(sort, nounName1)
                       
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
        #res += self.addRules_OnlyOneAnswer(nounSortMap)
        res += self.addDescription(self.description, nounSortMap)
        if len(self.context) >= 3:
            print "Description", self.context[0]
            print "Knowledge",
            for kb in self.context[1:-1]:
                print kb,
            print ""
            print "Queseion", self.context[-1]
        answer, z3Content, symbol = self.reasoning(nounSortMap, res)
        if symbol:
            self.provedAnswers.append(answer)
        else:
            res += self.addRules_OnlyOneAnswer(nounSortMap)
            answer, z3Content, symbol = self.reasoning(nounSortMap, res)
            self.provedAnswers.append(answer)
        return answer, z3Content

    def writeIntoFile(self, fileName):
        with open(fileName, 'w') as f:
            f.write(self.outputStr)

    def saveAnswerIntoFile(self):
        with open(self.inputFilePath_Win + self.answerFileName, "w") as f:
            for i in range(len(self.provedAnswers)):
                f.write(str(i + 1) + " : " + self.provedAnswers[i] + "\n")

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

def main():
    t = Translater(True)
    t.loadFromFile("outputTemp")
    t.saveAnswerIntoFile()
    #t.parsingSample()

if __name__ == '__main__':
    main()
