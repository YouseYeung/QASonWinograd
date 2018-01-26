import requests
import os

url = 'http://youse-thinkstation-e31:8400/sempre?q='
print url

fileName = "formatWSC"
outputFileName = "output"
ofp = open(outputFileName,'w')

keywords = [" but ", " because ", " then ", " although "]
keywords2 = [ " and ", " or "]

pronoun = ["he", "He", "she", "She", "it", "It", "they", "They", ]

def removingPronouns(s):
    return ""

with open(fileName, 'r') as f:
    startSymbol = "<pre>"
    endSymbol = "</pre>"
    while True:
        i = 0
        end = False
        while i < 3:
            oneLineContent= f.readline()
            contentList = [oneLineContent]
            if oneLineContent == "":
                end = True
                break
            index = oneLineContent.find('?')
            if index != -1:
                oneLineContent = oneLineContent[:index] + oneLineContent[index + 1:]
            if oneLineContent == '\n':
                ofp.write('\n')
                continue
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
        
        
ofp.close()
    
	





