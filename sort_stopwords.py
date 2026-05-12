with open("custom_stopwords.txt","r") as f:
    words = f.readlines()

words.sort()

with open("custom_stopwords.txt","w") as outf:
    _ = outf.writelines(words)