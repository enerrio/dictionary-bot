# Dictionary Bot

A Bluesky bot that posts information about Merriam-Webster's word of the day. It was originally deployed through AWS Lambda and EventBridge, and now runs locally on macOS with `launchd`, the same way the [stock bots](https://github.com/enerrio/stock-bots) do.

## How it works

Merriam-Webster's word of the day page blocks non-browser clients (it returns a 403 from a plain HTTP client), so the bot reads the word from the [word of the day RSS feed](https://www.merriam-webster.com/wotd/feed/rss2) instead — the most recent item in the feed is today's word.

That word is then looked up through Merriam-Webster's [Collegiate API](https://dictionaryapi.com/products/api-collegiate-dictionary), which returns the full entry including definitions, pronunciations, examples, and etymologies. The response is parsed down to the fields used in the post:

* Word
* Part of speech
* Pronunciation (only the pronunciation that has an audio file)
* Definition

Finally the [Bluesky API](https://www.docs.bsky.app/docs/get-started) is used to log in to the bot's account and post. A post looks like this:

```
🌟 Word of the day: pedagogical
📚 Part of Speech: adjective
🔊 Pronunciation: ˌpe-də-ˈgä-ji-kəl
📖 Definition: of, relating to, or befitting a teacher or education
```

## Project Structure

* `Makefile`: Targets to lint code, format code, run unit tests, and run the bot. Run with `make lint`, `make format`, `make test`, and `make run`
* `bot/`
  * `client.py`: Bluesky client creation, login, and posting
  * `fetch_data.py`: Reads the RSS feed and the Merriam-Webster API, and parses both
  * `message.py`: Builds the post text
  * `post.py`: Main bot logic
  * `schedule.py`: Tracks whether the bot has already posted today
* `config/settings.py`: Credentials, URLs, and other settings
* `scripts/`
  * `run_bot.py`: Runs the bot with an execution timeout
  * `run_scheduled_bot.sh`: Wrapper used by `launchd` that handles logging and log rotation
* `launchd/`: The `launchd` job definition
* `tests/`: Unit tests

## Development

This project uses [uv](https://docs.astral.sh/uv/) for Python package management. To set up the environment:

```bash
uv sync
```

Then run the bot manually:

```bash
make run
```

With `DEBUG=true` the bot fetches and prints the post but does not log in or post to Bluesky.

## Secrets

The following environment variables are read from a `.env` file at the repo root:

* `API_KEY`: Merriam-Webster Collegiate API key
* `BLUESKY_USERNAME`: Bot's Bluesky handle
* `BLUESKY_PASSWORD`: Bluesky app password
* `DEBUG`: Set to `true` to print the post without publishing it

## Local Scheduling With launchd

The wrapper script in [`scripts/run_scheduled_bot.sh`](https://github.com/enerrio/dictionary-bot/blob/main/scripts/run_scheduled_bot.sh) is used together with the plist file in `launchd/`. The wrapper keeps the working directory anchored at the repo root, runs the Python entrypoint with the repo-local virtualenv at `.venv/bin/python`, enforces a 60-second timeout, and prunes bot log files older than 7 days.

The job runs once a day at 9:00 AM local time. Because `launchd` replays a missed calendar job when the machine wakes from sleep, the bot records the date of each successful post in `state/last_posted_date` and exits without posting if it has already posted for the current day.

To install the job for the current macOS user:

```bash
mkdir -p ~/Library/LaunchAgents
cp launchd/com.enerrio.dictionary-bot.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.enerrio.dictionary-bot.plist
```

To inspect or restart it:

```bash
launchctl print gui/$(id -u)/com.enerrio.dictionary-bot
launchctl kickstart -k gui/$(id -u)/com.enerrio.dictionary-bot
```

To remove it:

```bash
launchctl bootout gui/$(id -u)/com.enerrio.dictionary-bot
```

Log files are written to the `logs/` directory as daily files named like `dictionary-2026-08-10.log`. The wrapper deletes bot log files older than 7 days each time the job runs. If you move the repo to a different path, update the absolute paths inside the plist file before loading it.

## Previous AWS Deployment

The bot used to run as a Lambda function on Python 3.11 / arm64, triggered by an EventBridge rule once a day at 9am PT. Dependencies were installed with `--platform manylinux2014_aarch64` into a `package/` directory, zipped together with the Python sources, and uploaded to the Lambda function. That path has been replaced by the `launchd` setup above, so the EventBridge rule should be disabled to avoid double posting.
