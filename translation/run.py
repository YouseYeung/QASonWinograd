import requests
import os

url = 'http://youse-thinkstation-e31:8400/sempre?q='
print url

fileName = "formatWSC"
outputFileName = "output2"
ofp = open(outputFileName,'w')
with open(fileName, 'r') as f:
    startSymbol = "<pre>"
    endSymbol = "</pre>"
    while True:
        i = 0
        end = False
        while i < 1:
            oneLineContent = f.readline()
            if not oneLineContent:
                end = True
                break
            index = oneLineContent.find('?')
            if index != -1:
                oneLineContent = oneLineContent[:index] + oneLineContent[index + 1:]
            if oneLineContent == '\n':
                ofp.write('\n')
                continue
            content = requests.get(url + oneLineContent).content
            startPos = content.find(startSymbol)
            endPos = content.find(endSymbol)
            ofp.write(content[startPos + 5:endPos])
            i += 1
        if end:
            break
        
        
ofp.close()
    
	





