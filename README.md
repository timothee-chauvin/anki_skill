# anki skill

LLMs have gotten good enough to create valuable anki cards. Two ingredients that help a lot with that, and that this skill implements:

* showing the LLM a sample of your own collection
* telling the LLMs to search for related cards and concepts before adding anything

## Do I need ankiconnect?

No, I try to avoid third-party dependencies that look like servers when possible, and it turns out not much code is needed (see [anki_add.py](/anki_add.py)).

## List of things you need to change before use

1. replace my card subset in the skill with yours; change other instructions as needed
1. change the hardcoded constants at the top of [anki_add.py](/anki_add.py)
1. move SKILL.md to an appropriate location

You're on your own in any case, but particularly so if you're not on Linux.

