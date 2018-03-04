string = "Tokens: [what, was, made, of, styrofoam]\n\
    Lemmatized tokens: [what, be, make, of, styrofoam]\n\
    POS tags: [WP, VBD-AUX, VBN, IN, NN]\n\
    NER tags: [O, O, O, O, O]\n\
    NER values: [null, null, null, null, null]\n\
    Dependency children: [[], [], [nsubjpass->0, auxpass->1, nmod:of->4], [], [case->3]]\n\
  }\n"

i = 0
lastContent = "."
answer = ""
num = 1
with open("output\AllQuestionsParsing", "r") as f1:
    with open("input\\answers", 'r') as f2:
        with open("input\\outputTemp", 'w') as f3:
            while True and i < 1:
                content = f1.readline()
                if not content:
                    break
                if content.strip() == "":
                    if lastContent == "":
                        if num == 1:
                            answer = f2.readline()
                        f3.write("Example:" + answer + string + "\n")
                        num = (num + 1) % 2
                        i += 1
                lastContent = content.strip()
                f3.write(content)