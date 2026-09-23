# Generated-Corpus Techniques

Cases enumerated by a generator rather than typed by hand, offloaded from the SKILL.md Writing Good Tests section. Reach for these where the behavior under test emerges from a whole table, or where the change is mechanical and the existing suite is the wrong instrument.

## A hand-picked corpus for emergent-precedence behavior

**Symptom:** the behavior emerges from a whole table (phrase lists, route priorities, rule sets), but the cases are typed by hand, so they test the author's model of the table rather than the table. Every case the author did not think of is a precedence interaction nobody has seen.

**Fix:** build the corpus as the cross-product of the axes the table enumerates, drive it through the real matcher against both the old and the new table, and diff the outcomes. Grouping the analysis on the hand-picked axis re-imposes the same blind spot the corpus was built to remove. Sample a real corpus wherever one exists, and keep the generated diff as the review artifact rather than a prose summary of it.

## Proving a mechanical refactor behavior-preserving with a generated transcript

**Symptom:** a mechanical refactor is declared safe because the suite is green. The suite covers what someone thought to test, and a mechanical refactor can move anything else, including the surfaces nobody wrote a case for.

**Fix:** enumerate the public surface by reflection, call each entry with a per-type pool of edge values varying one parameter at a time, and print one deterministic line per call: return value, warning, exception. Run that against both revisions and diff the transcripts. Rebuild fixtures before every call, so a mutated fixture does not read as a behavior change. Require every surviving difference to map to an intended change, and treat an unexplained difference as the finding rather than as transcript noise.
