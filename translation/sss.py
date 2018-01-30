import os

with open("formatWSC", "r") as f:
    with open("newWSC", "w") as f1:
        num = 0
        hasN = True
        while True:
            line = f.readline()
            if hasN:
                line = str(int(num / 2) + 1) + "." + line
                hasN = False
            if line == "\n":
                num += 1
                hasN = True
            f1.write(line)
            if not line:
                break