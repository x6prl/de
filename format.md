The dictionary format.

### 1. Entry Layout

The current 2-line core stays unchanged:

1. lemma line
2. translation line

Entries are separated by an empty line.

One optional grammar line may appear directly after the translation line. If present, it is always the third line, appears at most once per entry, and always uses square brackets. Any later non-empty lines are usage examples.

```text
v helfen-hilft / half / hat geholfen
help;
[j-m]
Ich helfe dir gern.
```

The grammar line is a government line, not a free-form notes line. Its purpose is limited to learner-relevant argument structure and government. Separate grammar elements with `; `.

The translation line may optionally attach reverse-recall prompt cues directly to an individual translation item with `{}`:

```text
translation{cue1, cue2}; other translation;
```

Use this only for prompt-only English forms that should map back to the German base lemma in reverse recall. These cues are not additional forward translations. Keep them compact and attach them to the closest base gloss. Do not insert a space before `{`. Literal `{` or `}` in translation text are not supported.

```text
v gehen-geht / ging / ist gegangen
go{goes, went, gone};

a gut besser am besten
good{better, best};

v helfen-hilft / half / hat geholfen
help{helps};
[j-m]
```

Recommended grammar elements:

* argument placeholders: `j-n`, `j-m`, `j-s`, `etw.`
* case markers: `Akk.`, `Dat.`, `Gen.`
* preposition + case: `an+Akk`, `mit+Dat`, `für+Akk`, `auf+Akk`
* reflexive case markers: `sich+Akk`, `sich+Dat`
* impersonal marker: `es`

Prefer compact government notation over full syntactic templates. For example, prefer `[bei+Dat; für+Akk]` over `[bei+j-m; für+Akk]` unless the parser explicitly needs placeholders inside prepositional complements.

Do not turn the grammar line into a general annotation field. Keep rare constructions, stylistic notes, and usage nuances in the example lines.

### 2. The Word Types & Examples

#### A. Nouns (Articles: `der`, `die`, `das` or `(-)`)
Identified by the definite article at the start of the line. The plural marker follows the noun. It may be a suffix such as `-en`, a zero-ending plural marker such as `-`, an umlaut-only marker such as `"-`, an umlaut+suffix such as `"-e`, or `(sg.)` / `(pl.)`.

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
    Zero-ending plurals (use `-`), umlaut-only plurals (use `"-`), umlaut plurals (use `"`), no plural (use `(sg.)`), and plural-only nouns (use `(pl.)`).
    ```text
    das Zeichen -
    sign; symbol;

    der Laden "-
    shop; store;

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

Reflexive verbs that are real learner units are stored as separate lemmas. Do not merge reflexive and non-reflexive uses into one entry just because they share a stem.

Use the optional grammar line for government-only notation. For verbs, prefer argument placeholders and governed prepositions. Do not add `tr.` / `intr.` to the core format unless you explicitly need them as extra metadata.

**1. Government lines and reflexive lemmas:**

```text
v helfen-hilft / half / hat geholfen
help;
[j-m]

v bitten / bat / hat gebeten
ask; request;
[j-n; um+Akk]

v erinnern / - / hat erinnert
remind;

v sich erinnern / - / hat erinnert
remember;
[an+Akk]
```

Use `sich+Akk` and `sich+Dat` if the reflexive case itself is part of the government pattern. Do not use free-form labels such as `refl Akk` or `refl Dat`.

**2. Modal Verbs:** Modals are highly irregular because their `ich` and `er/sie/es` forms in the present tense don't have typical endings. Those go as hardcoded.

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


**3. Separable verbs with irregular roots:** The parser splits by space, so it handles the separated prefixes in the present and past perfectly.
```text
v abnehmen-nimmt ab / nahm ab / hat abgenommen
to lose weight, to decrease, to take off;
```

**4. Separate entries for learner-relevant pattern changes:** Create separate entries whenever the learner must memorize a distinct form separately because of a change in meaning, reflexive vs. non-reflexive form, auxiliary, government, or transitivity pattern.
```text
v fahren-fährt / fuhr / ist gefahren
go, travel;

v fahren-fährt / fuhr / hat gefahren
drive;
[etw.]

v hängen / hängte / hat gehängt
to hang something up, to suspend (action);
[etw.]

v hängen-hängt / hing / hat gehangen
to hang, to be suspended;
```

*   **Standard Examples:**
    ```text
    v machen
    make; do;
    
    v essen-isst / aß / hat gegessen
    eat{eats, ate, eaten};
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
    [sich+Akk]
    ```

#### C. Adjectives & Adverbs (Prefix: `a `)
Identified by the `a ` prefix. `a` covers adjectives and adjective-like adverbs, which are stored under the same lemma line because German usually does not distinguish them in base form. Irregular comparative and superlative forms follow the base word, if it is irregular, separated by spaces:
```text
a lemma
a lemma (indecl.)
a lemma comparative superlative
```

When an adjective has learner-relevant government, use the optional grammar line. For adjectives, prefer bare case markers or `preposition+case`.

**1. Irregular stem changes in Comparative:**
```text
a nah näher am nächsten
near, close;

a hoch höher am höchsten
high, tall;
```

**2. Adjectives with government:**
```text
a stolz
proud;
[auf+Akk]
```

**3. Absolute / Indeclinable Adjectives:** Adjectives that never take endings (like certain colors or city adjectives). Note them in the translation or add an `(indecl.)` marker if you want your app to disable ending-exercises for them.
```text
a lila (indecl.)
purple, lilac;
```

**4. Adjectives that are also used as Nouns (Nominalized Adjectives):** You handle these simply by categorizing them as Nouns with the appropriate article.
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
    good{better, best};
    
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

Phrases usually do not take a grammar line. Add one only when there is a strong reason that cannot be expressed cleanly in the lemma itself.

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
