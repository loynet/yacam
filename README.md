# YACAM

A bot designed to detect and handle (dumb) spam on [jschan](https://gitgud.io/fatchan/jschan) imageboards.

Due to its nature, both false positives and false negatives are possible. If a user posts like a spammer (e.g., writes
`l*i*k*e t*h*i*s` while sharing URLs), they will be considered one. Read the ["How it works" section](#how-it-works)
to understand these and other limitations.

Note that the current implementation should not be considered "production ready". Although it works and has been running
for a few months at the time of writing, it was initially implemented as a proof of concept.

## How it works

In short, the bot listens for new posts or threads through the global management socket. Posts and threads are handled
similarly, and the terms are used interchangeably.

New posts are evaluated through a set of rules designed to reduce false positives. Posts without files, without a
message, with a capcode, with a geo-flag from a whitelisted country, and without URLs are ignored.

If the post is not considered safe at this point, the message (excluding URLs) is evaluated. Currently, two modes of "spam detection" are supported: threshold and entries.

### Threshold mode

In threshold mode, the bot detects spam messages by comparing the ratio between _tokens_ and message size against a
_threshold_.
A token is a character typically used by spammers to obfuscate a message (e.g., * or #).
If the ratio exceeds the threshold, the post is flagged as spam.

### Entries mode

In entries mode, the bot counts the number of consecutive entries. An entry is defined as a word character (as defined
by Python regular expressions) followed by a token (e.g., a*).

For example, with *#$ tokens, the message a\*a#b$ would have three consecutive entries.

If the count surpasses a configurable amount, the post is considered spam.

Finally, if a post is considered spam, the configured moderation action is performed, and the post is saved as a JSON
file (currently experimental and not thoroughly tested).

The moderation action is performed by the account configured in the `.env` file, and the username is hidden by default.
The following moderation actions are supported: ban and delete. The ban action also deletes the post.

## Before you run

For reasons explained in the "How it works" section, you will need to provide the bot with credentials for an account
with global staff permissions without 2FA enabled (not supported). Ideally, the account should be a global moderator
since no other type of account has been tested.

1. (Optional) Create and activate a new virtual environment by running `python -m venv path/to/venv`
   and `source path/to/venv/bin/activate` respectively.
2. Use `pip install -r requirements.txt` to install the dependencies.
3. Copy, update, and rename `.env.example` to `.env`.
4. Copy, tweak, and rename `example.ini` to `config.ini`.

## Running

1. (Optional) Activate the virtual environment with `source path/to/venv/bin/activate`.
2. Run `python yacam/yacam.py` to start the bot.
