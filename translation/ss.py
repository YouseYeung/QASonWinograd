import os
with open("formatWSC", "r") as ifp:
    with open("newWSC", "w") as ofp:
        num = 0
        begin = True
        while True:
            line = ifp.readline()
            if begin:
                ofp.write(str(int(num / 2) + 1)) + ".")
            if line.strip() == "":
                begin = True
            else:
                begin = False
            ofp.write(line)
            num += 1
