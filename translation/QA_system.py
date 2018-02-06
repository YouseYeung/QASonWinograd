#coding=utf-8

import os
import time
import platform
import Tkinter as tk
from Tkinter import *
import tkMessageBox
import tkFileDialog
from Translater import Translater

colors = '''#FFB6C1 LightPink 浅粉红
#FFC0CB Pink 粉红
#DC143C Crimson 深红/猩红
#FFF0F5 LavenderBlush 淡紫红
#DB7093 PaleVioletRed 弱紫罗兰红
#FF69B4 HotPink 热情的粉红
#FF1493 DeepPink 深粉红
#C71585 MediumVioletRed 中紫罗兰红
#DA70D6 Orchid 暗紫色/兰花紫
#D8BFD8 Thistle 蓟色
#DDA0DD Plum 洋李色/李子紫
#EE82EE Violet 紫罗兰
#FF00FF Magenta 洋红/玫瑰红
#FF00FF Fuchsia 紫红/灯笼海棠
#8B008B DarkMagenta 深洋红
#800080 Purple 紫色
#BA55D3 MediumOrchid 中兰花紫
#9400D3 DarkViolet 暗紫罗兰
#9932CC DarkOrchid 暗兰花紫
#4B0082 Indigo 靛青/紫兰色
#8A2BE2 BlueViolet 蓝紫罗兰
#9370DB MediumPurple 中紫色
#7B68EE MediumSlateBlue 中暗蓝色/中板岩蓝
#6A5ACD SlateBlue 石蓝色/板岩蓝
#483D8B DarkSlateBlue 暗灰蓝色/暗板岩蓝
#E6E6FA Lavender 淡紫色/熏衣草淡紫
#F8F8FF GhostWhite 幽灵白
#0000FF Blue 纯蓝
#0000CD MediumBlue 中蓝色
#191970 MidnightBlue 午夜蓝
#00008B DarkBlue 暗蓝色
#000080 Navy 海军蓝
#4169E1 RoyalBlue 皇家蓝/宝蓝
#6495ED CornflowerBlue 矢车菊蓝
#B0C4DE LightSteelBlue 亮钢蓝
#778899 LightSlateGray 亮蓝灰/亮石板灰
#708090 SlateGray 灰石色/石板灰
#1E90FF DodgerBlue 闪兰色/道奇蓝
#F0F8FF AliceBlue 爱丽丝蓝
#4682B4 SteelBlue 钢蓝/铁青
#87CEFA LightSkyBlue 亮天蓝色
#87CEEB SkyBlue 天蓝色
#00BFFF DeepSkyBlue 深天蓝
#ADD8E6 LightBlue 亮蓝
#B0E0E6 PowderBlue 粉蓝色/火药青
#5F9EA0 CadetBlue 军兰色/军服蓝
#F0FFFF Azure 蔚蓝色
#E0FFFF LightCyan 淡青色
#AFEEEE PaleTurquoise 弱绿宝石
#00FFFF Cyan 青色
#00FFFF Aqua 浅绿色/水色
#00CED1 DarkTurquoise 暗绿宝石
#2F4F4F DarkSlateGray 暗瓦灰色/暗石板灰
#008B8B DarkCyan 暗青色
#008080 Teal 水鸭色
#48D1CC MediumTurquoise 中绿宝石
#20B2AA LightSeaGreen 浅海洋绿
#40E0D0 Turquoise 绿宝石
#7FFFD4 Aquamarine 宝石碧绿
#66CDAA MediumAquamarine 中宝石碧绿
#00FA9A MediumSpringGreen 中春绿色
#F5FFFA MintCream 薄荷奶油
#00FF7F SpringGreen 春绿色
#3CB371 MediumSeaGreen 中海洋绿
#2E8B57 SeaGreen 海洋绿
#F0FFF0 Honeydew 蜜色/蜜瓜色
#90EE90 LightGreen 淡绿色
#98FB98 PaleGreen 弱绿色
#8FBC8F DarkSeaGreen 暗海洋绿
#32CD32 LimeGreen 闪光深绿
#00FF00 Lime 闪光绿
#228B22 ForestGreen 森林绿
#008000 Green 纯绿
#006400 DarkGreen 暗绿色
#7FFF00 Chartreuse 黄绿色/查特酒绿
#7CFC00 LawnGreen 草绿色/草坪绿
#ADFF2F GreenYellow 绿黄色
#556B2F DarkOliveGreen 暗橄榄绿
#9ACD32 YellowGreen 黄绿色
#6B8E23 OliveDrab 橄榄褐色
#F5F5DC Beige 米色/灰棕色
#FAFAD2 LightGoldenrodYellow 亮菊黄
#FFFFF0 Ivory 象牙色
#FFFFE0 LightYellow 浅黄色
#FFFF00 Yellow 纯黄
#808000 Olive 橄榄
#BDB76B DarkKhaki 暗黄褐色/深卡叽布
#FFFACD LemonChiffon 柠檬绸
#EEE8AA PaleGoldenrod 灰菊黄/苍麒麟色
#F0E68C Khaki 黄褐色/卡叽布
#FFD700 Gold 金色
#FFF8DC Cornsilk 玉米丝色
#DAA520 Goldenrod 金菊黄
#B8860B DarkGoldenrod 暗金菊黄
#FFFAF0 FloralWhite 花的白色
#FDF5E6 OldLace 老花色/旧蕾丝
#F5DEB3 Wheat 浅黄色/小麦色
#FFE4B5 Moccasin 鹿皮色/鹿皮靴
#FFA500 Orange 橙色
#FFEFD5 PapayaWhip 番木色/番木瓜
#FFEBCD BlanchedAlmond 白杏色
#FFDEAD NavajoWhite 纳瓦白/土著白
#FAEBD7 AntiqueWhite 古董白
#D2B48C Tan 茶色
#DEB887 BurlyWood 硬木色
#FFE4C4 Bisque 陶坯黄
#FF8C00 DarkOrange 深橙色
#FAF0E6 Linen 亚麻布
#CD853F Peru 秘鲁色
#FFDAB9 PeachPuff 桃肉色
#F4A460 SandyBrown 沙棕色
#D2691E Chocolate 巧克力色
#8B4513 SaddleBrown 重褐色/马鞍棕色
#FFF5EE Seashell 海贝壳
#A0522D Sienna 黄土赭色
#FFA07A LightSalmon 浅鲑鱼肉色
#FF7F50 Coral 珊瑚
#FF4500 OrangeRed 橙红色
#E9967A DarkSalmon 深鲜肉/鲑鱼色
#FF6347 Tomato 番茄红
#FFE4E1 MistyRose 浅玫瑰色/薄雾玫瑰
#FA8072 Salmon 鲜肉/鲑鱼色
#FFFAFA Snow 雪白色
#F08080 LightCoral 淡珊瑚色
#BC8F8F RosyBrown 玫瑰棕色
#CD5C5C IndianRed 印度红
#FF0000 Red 纯红
#A52A2A Brown 棕色
#B22222 FireBrick 火砖色/耐火砖
#8B0000 DarkRed 深红色
#800000 Maroon 栗色
#FFFFFF White 纯白
#F5F5F5 WhiteSmoke 白烟
#DCDCDC Gainsboro 淡灰色
#D3D3D3 LightGrey 浅灰色
#C0C0C0 Silver 银灰色
#A9A9A9 DarkGray 深灰色
#808080 Gray 灰色
#696969 DimGray 暗淡灰
#000000 Black 纯黑'''

class MainWindow(object):
    def __init__(self):
        window = tk.Tk()
        self.questionWords = ["Whose", "whose", "What", "what", "Who", "who", \
                            "Whom", "whom", "Why", "why", "Where", "where"]
        self.pronounWords = ["He", "he", "It", "it", "We", "we", "I", "She", "she", "They", "they", \
                            "him", "me", "them",\
                            "His", "his", "Its", "its", "My", "my", "Her", "her", "Their", "their"]
        self.window = window
        self.descriptionVar = StringVar()
        self.knowledgeVar = StringVar()
        self.questionVar = StringVar()
        self.descriptionVar.set("Please input description sentence")
        self.knowledgeVar.set("Please input knowledge sentence")
        self.questionVar.set("Please input question sentence")
        window.title("QA SYSTEM Version 1.0")
        width = 960
        height = 640
        entryWidth = 120
        rowNum = 2
        rowWidth = 1
        window.geometry(str(width) + "x" + str(height))
        window.maxsize(width, height)
        window.minsize(width, height)

        frame = tk.Frame(window, width = width, height = height)
        frame.grid(row = 0, column = 0)
        menuBar = tk.Menu(window)
        loadBar = tk.Menu(menuBar, tearoff = 0)
        loadBar.add_command(label = "LoadQuestion", command = self.loadFile)
        loadBar.add_command(label = "LoadSample", command = self.loadSample)
        menuBar.add_cascade(label = "Load", menu = loadBar)
        menuBar.add_command(label = "GetAnswer", command = self.checkInput)
        menuBar.add_command(label = "Save", command = self.saveInfo)
        menuBar.add_command(label = "Help", command = self.showHelpWindow)
        menuBar.add_command(label = "Exit", command = self.window.quit)
        window.config(menu = menuBar)
        
        labelColor = "Gray"
        labelWidth = 15
        Label(frame, text = "Description", bg = labelColor, width = labelWidth).grid(row = rowNum)
        descriptionEntry = tk.Entry(frame, width = entryWidth, text = self.descriptionVar)
        descriptionEntry.grid(row = rowNum, column = 1)
        rowNum += rowWidth

        Label(frame, text = "Knowledge", bg = labelColor, width = labelWidth).grid(row = rowNum)
        knowledgeEntry = tk.Entry(frame, width = entryWidth, text = self.knowledgeVar)
        knowledgeEntry.grid(row = rowNum, column = 1)
        rowNum += rowWidth
        
        Label(frame, text = "Queseion", bg = labelColor, width = labelWidth).grid(row = rowNum)
        questionEntry = tk.Entry(frame, width = entryWidth, text = self.questionVar)
        questionEntry.grid(row = rowNum, column = 1)
        rowNum += rowWidth
        
        Label(frame, text = "Answer", bg = labelColor, width = labelWidth).grid(row = rowNum)
        answerText = tk.Text(frame, height = 1, width = entryWidth)
        answerText.grid(row = rowNum, column = 1)
        rowNum += rowWidth
        
        Label(frame, text = "Used Time(s)", bg = labelColor, width = labelWidth).grid(row = rowNum)
        timeText = tk.Text(frame, height = 1, width = entryWidth)
        timeText.grid(row = rowNum, column = 1)
        rowNum += rowWidth
        '''
        loadBtn = tk.Button(frame, text = "Load Question", command = self.loadFile)
        loadBtn.grid(row = rowNum, column = 0)

        showBtn = tk.Button(frame, text = "Get Answer", command = self.parsing)
        showBtn.grid(row = rowNum, column = 1)
        
        helpBtn = tk.Button(frame, text = "Help Info", command = self.showHelpWindow)
        helpBtn.grid(row = rowNum, column = 2)
        rowNum += rowWidth
        '''
        canvas = tk.Canvas(frame, width = width, height = height)
        canvas.create_line(0, rowNum, width, rowNum)

        infoBoxHeight = 10
        Label(frame, text = "Z3 Reasoning", bg = labelColor, width = labelWidth).grid(row = rowNum)
        z3ContentText = tk.Text(frame, height = 3 * infoBoxHeight, width = entryWidth)
        z3ContentText.grid(row = rowNum, column = 1)
        rowNum += entryWidth
        
        Label(frame, text = "Error Info", bg = labelColor, width = labelWidth).grid(row = rowNum)
        errorInfoBox = tk.Text(frame, height = infoBoxHeight, width = entryWidth)
        errorInfoBox.grid(row = rowNum, column = 1)

        self.descriptionEntry = descriptionEntry
        self.knowledgeEntry = knowledgeEntry
        self.questionEntry = questionEntry
        self.answerText = answerText
        self.timeText = timeText
        '''
        self.loadBtn = loadBtn
        self.showBtn = showBtn
        self.helpBtn = helpBtn
        '''
        self.z3ContentText = z3ContentText
        self.errorInfoBox = errorInfoBox
        self.sampleFileName = "sample"
        self.inputFilePath_Win = "input/"
        self.inputFilePath_Linux = "input/"
        self.outputFilePath_Win = "output/"
        self.outputFilePath_Linux = "output/"
        self.translater = Translater()

    def run(self):
        self.window.mainloop()

    def showHelpWindow(self):
        info = "QA SYSTEM Version 1.0, designed by Yoz." \
                + '\n' + "This system is used to find answer for problems that need reasoning." \
                + '\n' + "User can input problems sentence by keyboard or by loading specific file.\n" \
                + '\n' + "[Description]\t box is used to show and get Description." \
                + '\n' + "[Knowledge]\t box is used to show and get knowledge." \
                + '\n' + "[Question]\t box is used to show and get question." \
                + '\n' + "[Load Question]\t button is used to load sentences from a file." \
                + '\n' + "[Get Answer]\t button is used to get answer.\n" \
                + '\n' + "[Save]\t button is used to save question, answer and z3 code." \
                + '\n' + "[Exit]\t button is used to close this software." \
                + '\n' + "@copyright youseyeung@foxmail.com"

        tkMessageBox.showinfo(title="Help Info", message = info)

    def loadSample(self):
        systemType = platform.system()
        fileName = self.sampleFileName
        if "Win" in systemType:
            fileName = self.inputFilePath_Win + fileName
        else:
            fileName = self.outputFilePath_Linux + fileName
        if not os.path.isfile(fileName):
            tkMessageBox.showinfo(title = "Error", message = "File doesn't exist: " + fileName)
            return
        with open(fileName, "r") as f:
            i = 0
            while True:
                content = f.readline()
                content = content.strip()
                if not content:
                    break
                if i == 0:
                    self.descriptionVar.set(content)
                elif i == 1:
                    self.knowledgeVar.set(content)
                elif i == 2:
                    self.questionVar.set(content)
                i += 1
            if i != 3:
                tkMessageBox.showinfo(title = "Error", message = "File Content Wrong.")
                return
            print "Description:", self.descriptionVar.get()
            print "Knowledge:", self.knowledgeVar.get()
            print "Question:", self.questionVar.get()

    def loadFile(self):
        fileName = tkFileDialog.askopenfilename()
        if not os.path.isfile(fileName):
            tkMessageBox.showinfo(title = "Error", message = "File doesn't exist: " + fileName)
            return
        print "Open File:", fileName
        with open(fileName, "r") as f:
            i = 0
            while True:
                content = f.readline()
                content = content.strip()
                if not content:
                    break
                if i == 0:
                    self.descriptionVar.set(content)
                elif i == 1:
                    self.knowledgeVar.set(content)
                elif i == 2:
                    self.questionVar.set(content)
                i += 1
            if i != 3:
                tkMessageBox.showinfo(title = "Error", message = "File Content Wrong.")
                return
            print "Description:", self.descriptionVar.get()
            print "Knowledge:", self.knowledgeVar.get()
            print "Question:", self.questionVar.get()

    def checkInput(self):
        dStr = self.descriptionEntry.get()
        kStr = self.knowledgeEntry.get()
        qStr = self.questionEntry.get()
        if qStr != "":
            qTokens = qStr.split(' ')
            if qTokens != []:
                correct = False
                for token in qTokens:
                    if token in self.questionWords:
                        correct = True
                        break
                if not correct:
                    tkMessageBox.showinfo(title="Error", message = "[Error]: Question Format Wrong!")
                    return
            else:
                tkMessageBox.showinfo(title="Error", message = "[Error]: Question Format Wrong!")
                return
                
        if kStr != "":
            kTokens = kStr.split(' ')
            if kTokens != []:
                correct = False
                numOfKeyword_if = 0
                numOfKeyword_then = 0
                for token in qTokens:
                    if token == "if":
                        if numOfKeyword_if != 0:
                            tkMessageBox.showinfo(title="Error", message = "[Error]: Knowledge Format Wrong!")
                            return
                        numOfKeyword_if += 1
                    elif token == "then":
                        if numOfKeyword_if > 0:
                            numOfKeyword_if -= 1
            else:
                tkMessageBox.showinfo(title="Error", message = "[Error]: Knowledge Format Wrong!")
                
        if dStr != "":
            dTokens = dStr.split(' ')
            if dTokens != []:
                correct = False
                for token in dTokens:
                    if token in self.pronounWords:
                        correct = True
                        break
                if not correct:
                    tkMessageBox.showinfo(title="Error", message = "[Error]: Description Format Wrong!")
                    return
            else:
                tkMessageBox.showinfo(title="Error", message = "[Error]: Description Format Wrong!")
                return
        self.parsing()

    def parsing(self):
        startTime = time.clock()
        dStr = self.descriptionEntry.get()
        kStr = self.knowledgeEntry.get()
        qStr = self.questionEntry.get()
        if dStr == "" or kStr == "" or qStr == "":
            msg = "[ERROR]:\t Wrong format for this question.\n"
            if dStr == "":
                msg += "[Description]\t sentence doesn't exist.\n"
            if kStr == "":
                msg += "[Knowledge]\t sentence doesn't exist.\n"
            if qStr == "":
                msg += "[Question]\t sentence doesn't exist.\n"

            tkMessageBox.showinfo(title = "File Error", message = msg)
        inputFileName = "inputTemp"
        with open(inputFileName, "w") as f:
            if dStr[-1] != '\n':
                dStr += '\n'
            if kStr[-1] != '\n':
                kStr += '\n'
            if qStr[-1] != '\n':
                qStr += '\n'
            f.write(dStr)
            f.write(kStr)
            f.write(qStr)

        processedFileName = self.translater.preprocessFile(inputFileName)
        if processedFileName == "":
            tkMessageBox.showinfo(title = "File Error", message = "File doesn't exist.")
            return
        #this line need modifying
        answer, z3Content = self.translater.loadFromFile(processedFileName)
        errorInfo = self.translater.getErrorInfo()
        self.answerText.delete(1.0, tk.END)
        self.answerText.insert("insert", answer)
        self.z3ContentText.delete(1.0, tk.END)
        if z3Content == "":
            z3Content = "Fail to reason. Just Guess."
        self.z3ContentText.insert("insert", z3Content)
        
        if errorInfo != "":
            self.errorInfoBox.delete(1.0, tk.END)
            self.errorInfoBox.insert("insert", errorInfo)
        
        elapsed = time.clock() - startTime
        self.timeText.delete(1.0, tk.END)
        self.timeText.insert("insert", round(elapsed, 2))

    def saveInfo(self):
        fileName = tkFileDialog.asksaveasfilename()
        with open(fileName, "w") as f:
            f.write("Description:\t" + self.descriptionEntry.get() + "\n")
            f.write("Knowledge:\t" + self.knowledgeEntry.get() + "\n")
            f.write("Question:\t" + self.questionEntry.get() + "\n")
            f.write("Answer:\t" + self.answerText.get("1.0", tk.END) + "\n")
            f.write("Z3 Code:\n" + self.z3ContentText.get("1.0", tk.END) + "\n")

def main():
    m = MainWindow()
    m.run()

if __name__ == '__main__':
    main()