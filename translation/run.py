import requests
import os

keywords = [" but ", " because ", " then ", " although "]
keywords2 = [ " and ", " or "]
pronoun = ["he", "He", "she", "She", "it", "It", "they", "They", ]

class questionParsing(object):
    def __init__(self):
        self.url = 'http://youse-thinkstation-e31:8400/sempre?q='
        self.inputFileName = ""
        self.outputFileName = ""

    def setInputFileName(self, fileName):
        if os.path.isfile(fileName):
            self.inputFileName = fileName

    def getInputFileName(self):
        return self.inputFileName

    def setOutputFileName(self, fileName):
        self.outputFileName = fileName
    
    def getOutputFileName(self):
        return self.outputFileName

    def parsing(self):
        with open(self.outputFileName, 'w') as ofp:
            with open(self.inputFileName,'r') as ifp:
                startSymbol = "<pre>"
                endSymbol = "</pre>"
                url = self.url
                while True:
                    i = 0
                    end = False
                    while i < 3:
                        oneLineContent= ifp.readline()
                        contentList = [oneLineContent]
                        if oneLineContent == "":
                            end = True
                            break
                        index = oneLineContent.find('?')
                        if index != -1:
                            oneLineContent = oneLineContent[:index] + oneLineContent[index + 1:]
                        if oneLineContent == '\n':
                            ofp.write('\n')
                            i += 1
                            break
                        if i == 1:
                            contentList = oneLineContent.split('. ')
                        for content in contentList:
                            content = content.strip()
                            for word in keywords:
                                indexList = []
                                index = content.find(word)
                                #keyword is not in the front of the sentence
                                if index != -1 and index != 0:
                                    changed = True
                                    if index - 1 > 0:
                                        if content[index - 1] == ',':
                                            changed = False
                                    if index - 2 > 0:
                                        if content[index - 2] == ',':
                                            changed = False
                                    if changed:
                                        content = content[:index] + '.' + content[index:]
                            for word in keywords2:
                                indexList = []
                                index = content.find(word)
                                #keyword is not in the front of the sentence
                                if index != -1 and index != 0:
                                    changed = True
                                    if index - 1 > 0:
                                        if content[index - 1] == ',':
                                            changed = False
                                    if index - 2 > 0:
                                        if content[index - 2] == ',':
                                            changed = False
                                    if changed:
                                        content = content[:index] + ',' + content[index:]
                            content.strip()
                            if content != "":
                                if content[-1] == '.':
                                    content = content[:-1].strip()
                            content = requests.get(url + content).content
                            startPos = content.find(startSymbol)
                            endPos = content.find(endSymbol)
                            ofp.write(content[startPos + 5:endPos])
                        i += 1
                    if end:
                        break

t = questionParsing()
t.setInputFileName("input/formatWSC")
t.setOutputFileName("output/AllQuestionsParsing")
t.parsing()
