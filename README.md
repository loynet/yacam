# YACAM

A bot that tries to detect (dumb) spam on [jschan](https://gitgud.io/fatchan/jschan) imageboards and does something about it.

Consider that, because of how it works, both false positives and false negatives are a possibility.
If a user posts like a spammer (for instance, writes likes `l*i*k*e t*h*i*s` while sharing URLs, etc.), will be
considered one.
Read the [How it works](#how-it-works) section to understand this, and other, limitations.

Also note that the current implementation should not be seen as "production ready", although it works,
and it has been running for a couple of months at the time of writing, it was initially implemented as proof of
concept.

## How it works

In a nutshell, the bot listens to new posts or threads through the global management socket.
Posts and threads are handled in the same way, we will use those terms interchangeably.

New posts are evaluated through a set of rules that aim to reduce the number of false positives.
Posts _without files_, _without a message_, _with a capcode_, _with a geo-flag_ and _from a country in the whitelist_,
and _without URLs_ are ignored.

If the post is not considered safe at this point, the message (without URLs) is evaluated.
Currently, two modes of "spam detection" are supported: _threshold_ or _entries_.

#### Threshold mode

In threshold mode, the bot tries to detect spam messages by comparing the ratio between _tokens_ and message size with a
_threshold_.

In this context, a _token_ is a character that is usually used by spammers to obfuscate a message (for instance, `*`
or `#`).

If the ratio is greater than the threshold, the post is flagged as spam.

--- 

#### Entries mode

In "entries" mode, the bot counts the number of consecutive entries. We define an entry as a word character (as defined
by
python regular expressions) followed by a _token_, (e.g. `a*`).

For instance, with `*#$` tokens, the message `a*a#b$` would have three consecutive entries.

If the count surpasses a configurable amount, the post is considered spam.

---

Finally, if a post is considered spam, the configured moderation action is performed and the post is saved as a
json with all the URLs redacted (currently experimental and not properly tested).

As expected, the moderation action is performed by the account configured in the `.env` file and the username is hidden
by default.
We support the following self-explanatory moderation actions: _ban_ and _delete_.
The ban also deletes the post.

## Before you run

For reasons explained in the [How it works](#how-it-works) section,
you will need to provide the bot with credentials for an account with global staff permissions without 2FA enabled (not
supported).
Ideally, the account must be a global moderator since, as far as I know, no other type of account was tested.

1. (Optional) Create and activate a new [virtual environment](https://docs.python.org/3/library/venv.html) by
   running `python -m venv path/to/venv` and `source path/to/venv/bin/activate` respectively
2. Use `pip install -r requirements.txt` to install the dependencies
3. Copy, update, and rename `.env.example` to `.env`
4. Copy, tweak, and rename `example.ini` to `config.ini`

## Running

1. (Optional) Activate the virtual environment with `source path/to/venv/bin/activate`
2. Run `python yacam/yacam.py` to start the bot

