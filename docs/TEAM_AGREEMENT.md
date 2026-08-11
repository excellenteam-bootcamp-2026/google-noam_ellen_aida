# Step A Team Agreement

This file defines the technical decisions the team must follow while developing Step A. Any change to these rules must be agreed upon by all three team members before implementation.

## 1. Scope

Step A includes:

1. Recursively loading the supplied English text files.
2. Treating every line as a complete sentence.
3. Preparing and storing searchable data during an offline initialization stage.
4. Accepting user input during an online serving stage.
5. Finding exact substring matches anywhere in a sentence.
6. Finding matches that require at most one character substitution, insertion, or deletion.
7. Calculating the score defined in the assignment.
8. Returning the five highest-scoring completions.
9. Supporting continued input and `#` reset behavior.

Step A does not include C++, Protobuf, Gemini, or the optimization work from later stages.

## 2. Development Environment

- Python 3.11 or newer.
- `pytest` for automated tests.
- UTF-8 source files and input files.
- Type hints on all public functions.
- Git feature branches and pull requests.
- No external dependency may be added without team agreement.
- No module may perform unrelated responsibilities.

## 3. Project Structure

```text
src/
└── autocomplete/
    ├── __init__.py
    ├── models.py
    ├── normalization.py
    ├── loader.py
    ├── index.py
    ├── matcher.py
    ├── scoring.py
    ├── service.py
    └── cli.py

tests/
├── test_normalization.py
├── test_loader.py
├── test_index.py
├── test_matcher.py
├── test_scoring.py
├── test_service.py
└── test_cli.py
```

## 4. Required Public Interface

The final autocomplete interface must be:

```python
def get_best_k_completions(
    prefix: str,
) -> list[AutoCompleteData]:
    ...
```

Rules:

- The function returns no more than five results.
- It returns an empty list for an empty normalized query.
- It returns an empty list when no matches exist.
- It must not print anything.
- The autocomplete service must be initialized before it is called.
- The `AutoCompleteData` definition must remain exactly as agreed in `models.py`.

## 5. Component Interfaces

### Normalization

```python
def normalize(text: str) -> str:
    ...
```

### Sentence loading

```python
from pathlib import Path


def load_sentences(root_path: Path) -> list[SentenceRecord]:
    ...
```

### Index management

```python
from pathlib import Path


def build_index(
    records: list[SentenceRecord],
) -> object:
    ...


def save_index(
    index: object,
    output_path: Path,
) -> None:
    ...


def load_index(
    index_path: Path,
) -> object:
    ...
```

The data/index developer may replace `object` with a concrete shared index type. That change must be merged into `main` before another component depends on it.

### Matching

```python
def find_best_match_score(
    normalized_prefix: str,
    normalized_sentence: str,
) -> int | None:
    ...
```

This function returns the best valid score for that sentence, or `None` if the sentence does not match.

### Service initialization

```python
from pathlib import Path


def initialize(index_path: Path) -> None:
    ...
```

### CLI

```python
def run_cli() -> None:
    ...
```

## 6. Source-File Rules

The loader must:

1. Search the supplied root directory recursively.
2. Read every `.txt` file.
3. Open each file using UTF-8.
4. Treat every non-empty line as one complete sentence.
5. Remove only the line-ending characters from the original sentence.
6. Preserve the original capitalization, punctuation, and spacing.
7. Store the path relative to the supplied data root.
8. Store the sentence's zero-based line number.

The team will use zero-based line numbers consistently. The stored line number becomes the `offset` in the returned autocomplete result.

## 7. Normalization Rules

The same `normalize()` function must process stored sentences and user queries.

Normalization must:

1. Convert letters to lowercase.
2. Remove punctuation.
3. Replace every consecutive sequence of whitespace with one ordinary space.
4. Remove whitespace from the beginning and end.
5. Preserve letters, digits, and normalized spaces.

The original sentence must never be overwritten by its normalized form. Normalized text is used only for searching and scoring. Results must contain the original sentence.

## 8. Matching Rules

A normalized query matches a normalized sentence when it appears anywhere in the sentence as:

- An exact substring.
- A substring requiring exactly one character substitution.
- A substring requiring exactly one character insertion.
- A substring requiring exactly one character deletion.

Rules:

- A match requiring two or more corrections must be rejected.
- Every possible starting position in the sentence must be considered.
- If a sentence has multiple possible matches, keep its highest score.
- The matcher must not load files.
- The matcher must not print output.
- The matcher must not sort the final result list.
- The matcher must not construct the public result object.

## 9. Scoring Rules

The base score is:

```text
2 × the number of matching normalized characters
```

Normalized spaces count as matching characters. Punctuation does not count because it is removed during normalization.

### Substitution penalties

| Zero-based correction position | Penalty |
|---:|---:|
| 0 | 5 |
| 1 | 4 |
| 2 | 3 |
| 3 | 2 |
| 4 or later | 1 |

### Insertion or deletion penalties

| Zero-based correction position | Penalty |
|---:|---:|
| 0 | 10 |
| 1 | 8 |
| 2 | 6 |
| 3 | 4 |
| 4 or later | 2 |

The final score is:

```text
base score - correction penalty
```

An exact match has no correction penalty. Correction positions are measured in the normalized comparison.

## 10. Result Construction

For every matching sentence, the service must return:

- The complete original sentence.
- The relative path of the source file.
- The zero-based source line number as the offset.
- The best calculated score for that sentence.

Occurrences on different source lines or in different files are separate results, even if their sentence text is identical.

## 11. Result Ordering

The service must sort results by:

1. Higher score first.
2. Completed sentence in case-insensitive alphabetical order.
3. Source path in alphabetical order.
4. Lower offset first.

The last two rules guarantee deterministic output when both the score and sentence are identical. After sorting, return only the first five results.

## 12. Interactive Behavior

The CLI must:

1. Load the prepared data before accepting input.
2. Maintain the complete text entered for the current query.
3. Search when the user presses Enter.
4. Display no more than five results.
5. Allow the user to continue typing after displaying results.
6. Append additional input to the current query.
7. Reset the current query when the user enters `#`.
8. Continue running after a reset.

Only `cli.py` may read from standard input or print user-facing output.

## 13. Error Handling

The program must provide clear errors for:

- A missing data directory.
- A missing prepared index.
- A source file that cannot be read.
- Searching before initialization.

Library modules must raise appropriate exceptions instead of terminating the program. The CLI is responsible for converting exceptions into readable messages.

## 14. Work Division

### Developer 1: Data and indexing

Owns:

- `normalization.py`
- `loader.py`
- `index.py`
- Their corresponding tests

Responsible for:

- Recursive file loading
- Text normalization
- Source metadata
- Offline index construction
- Saving and loading the index

### Developer 2: Matching and scoring

Owns:

- `matcher.py`
- `scoring.py`
- Their corresponding tests

Responsible for:

- Exact substring matching
- One-substitution matching
- One-insertion matching
- One-deletion matching
- Rejecting matches requiring multiple corrections
- Score calculation
- Selecting the best match within a sentence

### Developer 3: Integration and CLI

Owns:

- `service.py`
- `cli.py`
- Their corresponding tests

Responsible for:

- Service initialization
- Connecting the index and matcher
- Constructing autocomplete results
- Sorting and selecting the best five results
- Interactive input behavior
- End-to-end tests

## 15. Shared Responsibilities

Every team member must:

- Follow the shared interfaces in this document.
- Review the normalization and scoring behavior.
- Understand all code included in the final submission.
- Review at least one teammate's pull request.
- Run the entire test suite before merging.
- Help resolve integration failures.

No team member may silently change a shared model or function signature. A shared-interface change must be discussed and merged into `main` before dependent work continues.

## 16. Git Workflow

Before creating a branch:

```bash
git switch main
git pull origin main
```

Branches:

```text
feature/data-index
feature/matching-scoring
feature/integration-cli
```

Before opening a pull request:

```bash
git switch main
git pull origin main
git switch feature/your-branch-name
git merge main
python -m pytest
```

Push the feature branch:

```bash
git push -u origin feature/your-branch-name
```

Every pull request must have:

- A concise description.
- Passing tests.
- Review from at least one teammate.
- No unrelated files.
- No IDE settings, virtual environments, caches, prepared indexes, or raw datasets.

Do not force-push to `main`.

## 17. Definition of Done

Step A is complete only when:

- All `.txt` files are loaded recursively.
- Each sentence retains its original text and source information.
- Exact substring matching works anywhere in a sentence.
- All three allowed single-character corrections work.
- Matches requiring multiple corrections are rejected.
- Scoring follows the assignment's tables.
- Results are ordered correctly.
- No more than five results are returned.
- Continued input and `#` reset behavior work.
- Offline preparation is separated from online searching.
- All automated tests pass.
- Every team member understands the final implementation.
