from pymystem3 import Mystem
from pathlib import Path


def main():
    mystem = Mystem()
    text_path = Path(__file__).parent / 'lab_6_pipeline' / '1_raw.txt'
    with text_path.open(encoding='utf-8') as f:
        content = f.read()
    print(content)


analyzed_content = Mystem.analyze(content)
print(analyzed_content)
noun_count = 0
for i in analyzed_content:
    if 'analysis' in i:
        a = i['analysis'][0]['gr']
        if a[0] == 'S':
            noun_count += 1
print(noun_count)

if __name__ == '__main__':
    main()
