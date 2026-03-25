To achieve maximum performance in C, the parser should use **Memory Mapping (`mmap`)** and **String Views** (pointers + lengths) instead of duplicating memory with `malloc` and `strcpy`. 

---

### 1. Data Structures (C Implementation)

Use a tagged union to store the entry types efficiently. 

```c
typedef enum {
    ENTRY_NOUN,
    ENTRY_VERB,
    ENTRY_ADJ,
    ENTRY_PHRASE
} EntryType;

typedef enum {
    GENDER_MASC,  // der
    GENDER_FEM,   // die
    GENDER_NEUT,  // das
    GENDER_NONE   // (-)
} NounGender;

// String View for zero-copy parsing
typedef struct {
    const char* str;
    size_t len;
} StringView;

typedef struct {
    StringView lemma;
    StringView plural_marker; // "-en", "(sg.)", etc.
    NounGender gender;
} NounData;

typedef struct {
    StringView infinitive;
    StringView present_exception; // Can be empty
    StringView praeteritum;       // Can be empty
    StringView participle_aux;    // Can be empty
} VerbData;

typedef struct {
    StringView lemma;
    StringView comparative;       // Can be empty
    StringView superlative;       // Can be empty
    bool is_indeclinable;
} AdjData;

typedef struct {
    StringView text;
} PhraseData;

typedef struct {
    EntryType type;
    union {
        NounData noun;
        VerbData verb;
        AdjData adj;
        PhraseData phrase;
    } data;
    
    StringView translations; // The whole second line; items may optionally use gloss{cue1, cue2}
    StringView grammar;      // Optional 3rd line: [government; pattern]
    StringView examples;     // 4th+ lines, or 3rd+ if no grammar line
} DictEntry;
```

---

### 2. Parser Instructions (Fast One-Pass)

#### A. I/O and State Machine
1.  **Read Strategy**: Load the entire file into memory using `mmap()`. Iterate through the file with a pointer `const char* p`.
2.  **State Machine**: Maintain a state variable: `STATE_LEMMA` -> `STATE_TRANSLATION` -> `STATE_GRAMMAR_OR_EXAMPLE_OR_EMPTY`.
3.  **Line Iteration**: Create a helper function `StringView next_line(const char** p)` that reads until `\n`, advances `p`, and strips carriage returns (`\r`).

#### B. Parsing the Lemma Line (Line 1)
Identify the entry type by checking the first few characters.

*   **Nouns** (`der `, `die `, `das `, `(-) `):
    *   Identify gender based on the prefix. Advance the string pointer past the prefix.
    *   To separate the noun from the plural marker, find the **last space** in the line using a reverse search (`memrchr` or a custom loop backwards from the end of the line). 
    *   Everything before the last space is the noun (handles nouns with spaces like `(-) Rotes Kreuz`).
    *   Everything after the last space is the plural marker.
*   **Verbs** (`v `):
    *   Advance past `v `.
    *   Split the line by the delimiter ` / `. 
    *   **Field 1 (Infinitive/Present)**: Search for `-`. If found, the left part is the infinitive, the right part is `present_exception`. If not found, assign the whole block to `infinitive`.
    *   **Field 2 (Präteritum)**: Assign to `praeteritum`. If it is exactly `-`, you can flag it as regular/empty.
    *   **Field 3 (Participle)**: Assign to `participle_aux`.
*   **Adjectives/Adverbs** (`a `):
    *   Advance past `a `.
    *   Find the first space. Left is the lemma. 
    *   If no space follows, it's a standard adjective.
    *   If space follows, check if the remaining string is `(indecl.)`. If so, set `is_indeclinable = true`.
    *   Otherwise, find the *next* space. The token between the first and second space is the `comparative`. Everything after the second space is the `superlative` (which gracefully handles the space in `am höchsten`).
*   **Phrases** (Fallback):
    *   If none of the above prefixes match, treat the entire line as a Phrase.

#### C. Parsing Translations, Grammar & Examples (Lines 2+)
*   **Translations**: Read the next line. Trim the trailing `;` if it exists (as shown in your examples). Store as a single `StringView`.
    *   Each semicolon-separated translation item may optionally end with a reverse-recall cue block: `gloss{cue1, cue2}`.
    *   Treat the text before `{` as the display gloss. Treat the comma-separated items inside `{}` as prompt-only aliases for reverse recall, not as extra forward translations.
    *   Require the cue block to attach directly to the gloss with no intervening space. Reserve literal `{` and `}` for this syntax only.
    *   If you do not need reverse-recall prompts at parse time, storing the raw translation line unchanged is sufficient.
*   **Optional Grammar Line**: Peek at the next non-consumed line.
    *   If it starts with `[` and ends with `]`, store it as `grammar` and consume it.
    *   At most one grammar line is allowed per entry, and it must come immediately after the translation line.
*   **Examples**: Continue reading lines after the translation line or optional grammar line.
    *   If the line is **not empty**, append it to the `examples` buffer. (In a string-view approach, just mark the start of the first example, and extend the length until an empty line is hit).
    *   If the line **is empty** (`len == 0`), the entry is complete. Emit the `DictEntry` to your output array/callback, reset the state to `STATE_LEMMA`, and continue.

---

### 3. Writer Instructions

The writer simply reverses the process. Because C lacks built-in string formatting safety, use `fprintf` or a buffered `fwrite` system (like `fputc`/`fputs`) for speed.

**1. Outputting the Lemma Line**:
*   **Nouns**: `fprintf(out, "%s %.*s %.*s\n", gender_str, noun.len, noun.str, plural.len, plural.str);`
*   **Verbs**: 
    *   Print `v %.*s`, infinitive.
    *   If `present_exception` exists, print `-%.*s`.
    *   If `praeteritum` or `participle` exists, print ` / %.*s` for each. Maintain empty fields if skipping to field 3 (e.g., `v inf / - / ist`).
*   **Adjectives**: 
    *   Print `a %.*s`. 
    *   If `is_indeclinable`, append ` (indecl.)`.
    *   If `comparative` exists, append ` %.*s %.*s`.
*   **Phrases**: Print as-is `%.*s\n`.

**2. Outputting Translations, Grammar & Examples**:
*   Print the translations. Append `;` if it was stripped during parsing. Print `\n`.
*   If `grammar` length > 0, print the grammar line followed by `\n`.
*   If `examples` length > 0, print the examples block followed by `\n`.
*   **Crucial Rule**: Print exactly one empty `\n` to close the entry and act as the delimiter for the next block.

---

### 4. Corner Cases to Handle in C

1.  **Consecutive Empty Lines**: The file might have multiple blank lines between entries or at the end of the file. 
    *   *Parser mitigation*: If in `STATE_LEMMA` and an empty line is read, simply `continue` without throwing an error.
2.  **Missing Translation Line**: A malformed entry might have a lemma and immediately an empty line. 
    *   *Parser mitigation*: If an empty line is encountered while in `STATE_TRANSLATION`, emit a warning/error with the current file line number.
3.  **Malformed Grammar Lines**: A bracketed grammar line anywhere other than the single optional slot after the translation line should be treated as invalid format, not as an example line.
    *   *Parser mitigation*: If a second bracketed line appears before the entry-closing empty line, emit a warning/error with the current file line number.
4.  **Malformed Translation Cue Blocks**: If a translation item contains `{` or `}`, require the form `gloss{cue1, cue2}` with the cue block at the end of the item.
    *   *Parser mitigation*: Reject empty cue lists, unmatched braces, or brace blocks that appear in the middle of the gloss.
5.  **Whitespace Management**: Ensure your `StringView` extraction uses a `trim()` function to strip leading/trailing spaces (e.g., spaces around the ` / ` verb delimiters), so `aß` doesn't get captured as `" aß "`.
6.  **UTF-8 Encoding**: C string functions (`strchr`, `memchr`) are byte-oriented. Because standard German characters (Umlaute `ä, ö, ü, ß`) and prefixes (`der`, `die`, `a`, `v`) use ASCII spaces, brackets, braces, hyphens, and slashes, byte-oriented searching for ` ` (0x20), `[` (0x5B), `]` (0x5D), `{` (0x7B), `}` (0x7D), `-` (0x2D), and `/` (0x2F) is **100% safe in UTF-8**. You do not need a heavy wide-character (wchar_t) library for the structural parsing.
