# Machine-Parsed Text

Applies when a model reads the output with no back-channel: tool and function descriptions, system prompts, skill and agent instructions, error strings, inter-agent messages. A person resolves an ambiguous sentence by asking. A model resolves it by guessing.

- **One directive per sentence.** A compound instruction gets partially executed: the model does the first clause and the last, and drops the middle. Split "Open the file and read line 3, then check it matches" into three sentences.
- **Simple tenses in directives.** "The job finished", not "the job has completed". A compound tense adds a second parse (finished when? still true now?) that carries no instruction.
- **Cap noun stacks at three.** "the agent task queue priority handler" has four readings. Break it with a preposition: "the handler that sets task-queue priority".
- **Modal words carry the requirement.** Reserve `must` and `never` for requirements, `should` and `may` for genuine latitude. "The agent should verify first" reads as optional; if it is not optional, write "verify first".
- **Keep every referent explicit.** Name the subject instead of "this", "it", or "the above" whenever more than one antecedent is in scope.
- **Do not compress into ambiguity.** Dropping a subject, verb, or article to save tokens yields a shorter sentence with more readings, not fewer: "Files not backed up will be lost" hides which files. This bounds any length-reduction rule: cut whole sentences that change no behavior, never words that carry a referent.

## Verify

- No sentence carries two directives.
- No `should` or `may` sits on a requirement.
- Every "this", "it", or "the above" has exactly one antecedent in scope.
