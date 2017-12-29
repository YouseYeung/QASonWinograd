import os

readFileName = "newWSC2"
writeFileName = "newWSC3"


with open(readFileName, 'r') as rf:
    with open(writeFileName, 'w') as wf:
        while True:
            content = rf.readline()
            if not content:
                break
            if content == '\n':
                wf.write('\n')
                continue
            start = content.find('[')
            mid = content.find('/')
            end = content.find(']')
            if start != -1:
                wf.write(content[:start] + content[start + 1:mid] + content[end + 1:])
                wf.write(content[:start] + content[mid + 1:end] + content[end + 1:])
            else:
                wf.write(content)
            continue
            if number <= 4 and number != -1:
                content = content[number + 1:]
                answerNumber = content.find('?')
                if answerNumber != -1:
                    index = content[::-1].find('.')
                    content = content[:len(content) - index] + '\n' + content[len(content) - index + 1:]
            number = content.find('(KB:')
            if number != -1:
                content = content[number + 4:]
            number = content.find('Answers:')
            if number != -1:
                wf.write('\n')
                continue
            number = content.find('Comment:')
            if number != -1:
                wf.write('\n')
                continue
            if len(content) > 1 and content[-2] == ')':
                content = content[:-2]

            wf.write(content.strip() + '\n')
