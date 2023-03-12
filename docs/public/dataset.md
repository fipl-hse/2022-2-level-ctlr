## Dataset requirements

1. Structure:
```
+-- 2022-2-level-ctlr
    +-- tmp
        +-- articles
        +-- raw_dataset.zip
            +-- articles
                +-- 1_raw.txt <- the paper with the ID as the name
                +-- 1_cleaned.txt <- lowercased text with no punctuation
                +-- 1_morphological_conllu.conllu <- UD text format with morphological tags 
                +-- 1_meta.json <- the paper meta-information
                    {
                        "id": "1",
                        "title": "Власти продлили «дачную амнистию». Разбираемся в нововведениях с NN.RU",
                        "date": "2021-01-26 07:30:00",
                        "url": "https://www.nn.ru/text/realty/2021/01/26/69724161/",
                        "topics": ["недвижимость"], <- Optional. 4 module -> skip-topics=True
                        "author": "Егор Герасимов" <- Optional. .skips -> skip-author=True
                    }
                +-- 2_raw.txt
                +-- 2_cleaned.txt
                +-- 2_morphological_conllu.conllu
                +-- 2_meta.json
                +-- ...
                +-- 100_raw.txt
                +-- 100_cleaned.txt
                +-- 100_morphological_conllu.conllu
                +-- 100_meta.json
```
1. Volume: not less than 100 texts
1. Tagged: each token has inplace tag with morphological information: 
   1. Full description of working with UD format can be found [here](ud_format.md).
1. Recoverability of information (meta-information):
   1. Article id
   1. Article title
   1. Article date
   1. Article URL 
   1. Article topics
   1. Article author