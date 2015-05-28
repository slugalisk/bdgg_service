import random

#pseudorandom name generator
grammar = { '{lexpat}' : [  '{c}{v}{lexpat}',
                            '{v}{c}{lexpat}',
                            '{word}',
                            ''
                            ],
            '{c}' : 'bcdfghjklmnpqrstvwxyz',
            '{v}' : 'aeiouy',
            '{word}' : [    '{c}{v}{c}{lexpat}',
                            '{v}{c}{v}{lexpat}',
                            ]
            }
grammarindex = sorted(grammar.keys())

weights = { '{lexpat}' : [0.25,0.25,0.15,1],
            '{c}' : [0.0477, 0.0477,0.0477,0.0477,0.0476,
                    0.0476,0.0476,0.0476,0.0476,0.0476,
                    0.0476,0.0476,0.0476,0.0476,0.0476,
                    0.0476,0.0476,0.0476,0.0476,0.0476,
                    0.0476
                    ],
            '{v}' : [   0.1667,0.1667,0.1667,0.1666,0.1667,
                        0.1666
                    ],
            '{word}' : [0.5,0.5]
            }

def getToken(token):
    num = random.random()
    acc = 0.0
    i = 0

    while num > acc:
        acc += weights[token][i]
        i += 1

    i -= 1
    return grammar[token][i]


def generate(rseed):
    random.seed(rseed)
    word = ''

    while len(word) < 4:
        word += '{word}'
        flag = 1
        while flag:
            flag = 0
            for key in grammarindex:
                index = word.find(key)

                while index != -1:
                    word = word.replace(key, getToken(key), 1)
                    index = word.find(key)
                    flag = 1
    return word[:10]
