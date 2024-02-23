# Dictionary Bot
---

This is a bot that creates a post for Bluesky containing information related to Merriam Webster's word of the day.

## Install Dependencies
---

Install [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) and use the `environment.yml` file to install dependencies:
```
conda env create -f environment.yml

conda activate word

conda env export > environment.yml
```

## How it works
---
This bot uses the `requests` library to first get the word of the day from Merriam Webster's website and then uses Merriam Webster's [Collegiate API](https://dictionaryapi.com/products/api-collegiate-dictionary) to get the full data related to the word including the definition, pronunciations, examples, etymologies, and more.

Then the API response is parsed to get only certain information that is then used in a post:
* Word
* Part of speech
* Pronunciation
* Definition

Then we use the [Bluesky API](https://www.docs.bsky.app/docs/get-started) to login to the bot's account and make a post. Just prior to logging in we format the post text. After logging in a post is submitted.

## Deployment

This bot is deployed through AWS using Lambda and Eventbridge. The lambda function executes the main bot code to create a post to Bluesky and an eventbridge rule is set up to trigger the lambda function once a day.

TODO:
- [ ] create tests
- [x] update deployment section of readme