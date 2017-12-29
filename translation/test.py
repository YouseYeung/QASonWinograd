import requests
import os

url = 'http://youse-thinkstation-e31:8400/sempre?q='
print url

fileName = "wsc"
outputFileName = "output"
ofp = open(outputFileName,'w')
with open(fileName, 'r') as f:
    startSymbol = "<pre>"
    endSymbol = "</pre>"
    while True:
        i = 0
        end = False
        while i < 2:
            oneLineContent = f.readline()
            if oneLineContent == '\n':
                continue
            if not oneLineContent:
                end = True
                break
            content = requests.get(url + oneLineContent).content
            startPos = content.find(startSymbol)
            endPos = content.find(endSymbol)
            ofp.write(content[startPos + 5:endPos])
            i += 1
        if end:
            break
        
        
ofp.close()
    
	





