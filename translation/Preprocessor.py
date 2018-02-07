import requests
import os
import socket

keywords = [" but ", " because ", " then ", " although "]
keywords2 = [ " and ", " or "]
pronoun = ["he", "He", "she", "She", "it", "It", "they", "They", "I"]


class Preprocessor(object):
    def __init__(self):
        hostname = socket.gethostname()
        self.url = 'http://' + hostname + ':8400/sempre?q='
        self.inputFileName = ""
        self.outputFileName = ""
        self.outputFilePath = "output/"
        self.inputFilePath = "input/"

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
        url = self.url
        outputFile = self.inputFilePath + self.outputFileName
        inputFile = self.inputFilePath + self.inputFileName
        with open(outputFile, 'w') as ofp:
            with open(inputFile,'r') as ifp:
                startSymbol = "<pre>"
                endSymbol = "</pre>"
                while True:
                    i = 0
                    end = False
                    while i < 3:
                        oneLineContent= ifp.readline()
                        oneLineContent = oneLineContent.strip()
                        if oneLineContent == "":
                            end = True
                            break
                        contentList = [oneLineContent]
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
                            print content
                            startPos = content.find(startSymbol)
                            endPos = content.find(endSymbol)
                            ofp.write(content[startPos + 7:endPos])
                            if i != 2:
                                ofp.write('\n')
                        i += 1
                    if end:
                        break
