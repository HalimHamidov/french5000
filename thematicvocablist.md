## Additional extraction task: Thematic Vocabulary Lists

The book also contains a section titled "Thematic vocabulary lists".

You must extract these thematic lists and store them in a separate dataset.

Do NOT mix them with the frequency-ranked dictionary entries.

Instead, create a separate JSON file named:

french_thematic_vocabulary.json


## Thematic categories to extract

The book includes the following thematic sections:

1 Animals
2 Body
3 Food
4 Clothing
5 Transportation
6 Family
7 Materials
8 Time
9 Sports
10 Natural features and plants
11 Weather
12 Professions
13 Creating nouns – 1
14 Relationships
15 Nouns – differences across registers
16 Colors
17 Opposites
18 Nationalities
19 Creating nouns – 2
20 Emotions
21 Adjectives – differences across registers
22 Verbs of movement
23 Verbs of communication
24 Use of the pronoun “se”
25 Verbs – differences across registers
26 Adverbs – differences across registers
27 Word length


## Goal

Extract all words that appear in these thematic lists and organize them by category.


## Output structure

Create a JSON object where each category contains its vocabulary items.

Example format:

{
  "animals": {
    "id": 1,
    "title": "Animals",
    "words": [
      {
        "word": "chien",
        french ipa
        "translation_en": "dog",
        "translation_ru": "собака"
      },
      {
        "word": "chat",
         french ipa
        "translation_en": "cat",
        "translation_ru": "кот"
      }
    ]
  },

  "food": {
    "id": 3,
    "title": "Food",
    "words": [
      {
        "word": "pain",
         french ipa
        "translation_en": "bread",
        "translation_ru": "хлеб"
      }
    ]
  }
}


## Extraction rules

- Extract vocabulary exactly from the thematic lists.
- Preserve the category numbering (1–27).
- Preserve the category titles exactly as written.
- Normalize the category keys into lowercase snake_case.

Example:

Animals → animals  
Natural features and plants → natural_features_and_plants


## Word fields

Each word object should contain:

{
  "word": "chien",
   french ipa
  "translation_en": "dog",
  "translation_ru": "собака",
  "pos": null,
  "notes": null
}

If the thematic list includes additional information, extract it when possible.


## Cross-linking requirement

If a word from a thematic list also exists in the frequency dictionary dataset:

- add a field called:

"rank_reference"

Example:

{
  "word": "chien",
   french ipa
  "translation_en": "dog",
  "translation_ru": "собака",
  "rank_reference": 345
}

This allows linking the thematic vocabulary with the main frequency dataset.


## Output validation

Ensure that:

- every category contains its word list
- categories remain in numeric order
- duplicate words inside a category are removed
- JSON encoding is UTF-8
- the file is valid JSON


## Deliverable

Create the file:

french_thematic_vocabulary.json


## Optional chunking

If this file becomes too large, apply the same chunking rule used for the frequency dataset:

french_thematic_vocabulary_001.json  
french_thematic_vocabulary_002.json  

and generate an index file:

french_thematic_vocabulary_index.json