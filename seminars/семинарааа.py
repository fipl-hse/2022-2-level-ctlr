# import pymystem3
#
# copypasta = ''
# punct = '''!"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~'''
# text = ''
# for char in copypasta.lower():
#     if char not in punct:
#         text += char
#
# print(text)
#
# analysed = pymystem3.Mystem().analyze(text)
# counter = 0
#
# for i in analysed:
#     if 'analysis' in i and i['analysis'] and 'gr' in i['analysis'][0] and i['analysis'][0]['gr'][:2] == 'S,':
#         counter += 1
#         print(i['analysis'][0])
# print(counter)
