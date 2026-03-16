The dictionary format.

### 1. The Word Types & Examples

When we want to clarify vague translation, we can use more than one word (just divide them by `, `). For all the word classes we spoke, write me more corner cases. This also works for the german words, if multiple variants are allowed.
A word entry consists of 2 lines; entries are separated by an empty line; if there is a third(4th, 5th, etc.) line of an entry is not empty — it contains a sentence, which is a usage example.

#### A. Nouns (Articles: `der`, `die`, `das` or `(-)`)
Identified by the definite article at the start of the line. The plural marker follows the noun. It may be a suffix such as `-en`, an umlaut+suffix such as `"-e`, or `(sg.)` / `(pl.)`.

For **Singularetantum** german nouns we will use ` (sg.)` instead of plural suffix.
For **Pluraletantum** german nouns we will use ` (pl.)` instead of plural suffix.

**1. Homonyms with different plurals:** Some words have exactly the same singular form but completely different plurals depending on the meaning.
```text
das Wort "-er
isolated words, vocabulary words;

das Wort -e
connected words, statement, speech;
```

**2. Nouns with no article (Proper Nouns / Names):** How to handle a noun that doesn't take `der`, `die`, or `das`? You can use `(-) ` as a dummy article so the parser still knows it's a noun.
```text
(-) Deutschland (sg.)
Germany;
```

**3. Gender switchers:** Words that change meaning completely based on the article.
```text
der Schild -e
shield, buckler;

das Schild -er
sign, signboard, label;
```

*   **Standard Example:**
    ```text
    die Arbeit -en
    work; labor;
    ```
*   **Corner Cases:**
    Umlaut plurals (use `"`), no plural (use `(sg.)` and plural-only nouns (use `(pl.)`).
    ```text
    der Grund "-e
    reason; ground;
    
    das Leben (sg.)
    life;
    
    die Leute (pl.)
    people;
    ```

#### B. Verbs (Prefix: `v `)
Identified by the `v ` prefix. Form delimiter is ` / `.
After the infinitive, `-` introduces one or more explicitly stored present-tense exception forms, normally the 3rd person singular Präsens (er/sie/es). For separable or reflexive verbs, the full surface form is stored.
Verbs may have 1 to 3 fields, with omitted fields meaning “regular/default”, or `v infinitive-exception / Präteritum / auxiliary + participle`. The third field should not contain the participle if the form is regular.
`-` may be used in the Präteritum field when the past stem is regular and does not need to be stored explicitly. If participle is regular, field 3 may contain only auxiliary.

**1. Modal Verbs:** Modals are highly irregular because their `ich` and `er/sie/es` forms in the present tense don't have typical endings. Those go as hardcoded.

The **core German modal verbs** are:

1. **dürfen** — to be allowed to, may
2. **können** — can, to be able to
3. **mögen** — to like; in some contexts, to want
4. **müssen** — must, to have to
5. **sollen** — should, to be supposed to
6. **wollen** — to want to
7. **möchten** — would like
   This is usually treated as a **Konjunktiv II** form of **mögen**, not as a separate infinitive verb, but learners often study it almost like a modal verb because it is so common.

**brauchen**, **lassen**, and sometimes **werden** can behave similarly to modal verbs in certain constructions.


**2. Separable verbs with irregular roots:** The parser splits by space, so it handles the separated prefixes in the present and past perfectly.
```text
v abnehmen-nimmt ab / nahm ab / hat abgenommen
to lose weight, to decrease, to take off;
```

**3. Verbs that are both regular AND irregular (Transitive vs. Intransitive):** Some verbs change their rules based on if you are doing the action *to* something, or if the action is just *happening*.
```text
v hängen / hängte / hat gehängt
to hang something up, to suspend (action);

v hängen-hängt / hing / hat gehangen
to hang, to be suspended;
```

*   **Standard Examples:**
    ```text
    v machen
    make; do;
    
    v essen-isst / aß / hat gegessen
    eat;
    ```

*   **Corner Cases:** 
    Regular verbs that take *sein*, partially irregular verbs, and separable/reflexive verbs (where the space count changes).
    ```text
    v reisen / - / ist
    travel;
    
    v backen-backt,bäckt / backte,buk / hat gebacken
    bake;

    v aufstehen-steht auf / stand auf / ist aufgestanden
    get up; stand up;
    
    v sich waschen-wäscht sich / wusch sich / hat sich gewaschen
    wash oneself;
    ```

#### C. Adjectives & Adverbs (Prefix: `a `)
Identified by the `a ` prefix. `a` covers adjectives and adjective-like adverbs, which are stored under the same lemma line because German usually does not distinguish them in base form. Irregular comparative and superlative forms follow the base word, if it is irregular, separated by spaces:
```text
a lemma
a lemma (indecl.)
a lemma comparative superlative
```

**1. Irregular stem changes in Comparative:**
```text
a nah näher am nächsten
near, close;

a hoch höher am höchsten
high, tall;
```

**2. Absolute / Indeclinable Adjectives:** Adjectives that never take endings (like certain colors or city adjectives). Note them in the translation or add an `(indecl.)` marker if you want your app to disable ending-exercises for them.
```text
a lila (indecl.)
purple, lilac;
```

**3. Adjectives that are also used as Nouns (Nominalized Adjectives):** You handle these simply by categorizing them as Nouns with the appropriate article.
```text
der Bekannte -n
male acquaintance, friend;

die Bekannte -n
female acquaintance, friend;
```

*   **Standard Example:**
    ```text
    a schnell
    fast; quick;
    ```
*   **Corner Cases:**
    Irregular adjectives, and adjectives with no comparatives (like *dead* or *pregnant*).
    ```text
    a gut besser am besten
    good;
    
    a hoch höher am höchsten
    high;
    
    a schwanger
    pregnant;
    ```

#### D. Phrases, Idioms & Fixed Expressions (No prefix)

Identified by the **lack of any prefix**. This class is used for everything that is **not** stored as a noun, verb, or adjective/adverb entry, including:

* full sentences
* idioms
* colloquial expressions
* proverbs
* multi-word conjunctions
* fixed prepositional expressions
* fused forms
* other expressions

**1. Phrases with placeholders:**
When learners need to know where to insert a person or thing, use standard abbreviations like `j-m` (jemandem, dative), `j-n` (jemanden, accusative), or `etw.` (etwas).

```text
j-m die Daumen drücken
to cross one's fingers for someone, to wish someone luck;

j-m auf die Nerven gehen
to get on someone's nerves, to annoy someone;
```

**2. Proverbs / Full Sentences:**

```text
Übung macht den Meister
practice makes perfect;

Das ist mir Wurst
I don't care, it doesn't matter to me;
```

**3. Multi-word conjunctions and fixed connectors:**

```text
entweder ... oder
either ... or;

sowohl ... als auch
both ... and, as well as;
```

**4. Prepositions with case government:**
If needed, include case information directly in the lemma.

```text
mit + Dat.
with;

in + Akk./Dat.
in, into, inside;
```

**5. Fused forms and contracted forms:**
The full underlying form may be shown in parentheses.

```text
zum (zu dem)
to the;

ins (in das)
into the, in the;
```

**6. Fixed expressions and adverbial phrases:**

```text
auf jeden Fall
definitely; in any case;

nach wie vor
still, as before, as ever;
```

* **Standard Example:**

  ```text
  Wie geht es dir?
  how are you?;
  ```

* **Corner Cases:**
  Phrases containing internal punctuation, placeholders, ellipsis, or multiple words that behave as a single unit.

  ```text
  Hals- und Beinbruch!
  break a leg!; good luck!;

  je ... desto ...
  the ... the ...;
  ```

---

