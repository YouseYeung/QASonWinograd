li = []
content = ""
with open('tttt', 'r') as f:
    while 1:
        val = f.readline()
        if not val:
            break
        if val == '\n':
            length = len(li)
            if length == 4:
                content += li[0] + li[3] + li[2] + '\n' + li[1] + li[3] + li[2] + '\n'
            elif length == 5:
                content += li[0] + li[4] + li[2] + '\n' + li[1] + li[4] + li[3] + '\n'
            else:
                for val in li:
                    content += val
                content += '\n'
            li = []
            
        else:
            li.append(val)

    wf = open('wsc2', 'w')
    wf.write(content)
    wf.close()

