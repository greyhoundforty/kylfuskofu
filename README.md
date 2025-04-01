# kylfusköfu (Icelandic for "club scraper")

## Overview

This application collects random websites from multiple sources (indieblog.page, hackernews, 512kb.club), stores them in a SQLite database, and syncs the database with IBM Cloud Object Storage. It also sends notifications to a Discord webhook with clickable links to the discovered sites.

![kylfusköfu in action](https://images.gh40-dev.systems/Capto_Capture-2025-03-19_12-43-20_PM.png)

### But why?

Fair question. I am building this little tool for a few reasons:

- I learn best when I have a problem to solve and I am trying to learn more python in 2025. Two birds, one stone.
- I love the concept of sites like https://512kb.club/ and https://indieblog.page, but visiting the site and clicking the `Random Site` button 20-30 times a day is annoying.
- While not all sites are going to be up my alley or even in my native language, I want a way to discover more people and information outside of the traditional social media sites.
- I want more data coming into my RSS reader and I am looking for ways to aggregate content and provide myself with more tailored feeds.

### Current Status

- [x] It scrapes!
- [x] It runs on a schedule
- [x] It sends a webhook

### Future Plans

- [ ] Add Code Engine deployment instructions
- [ ] Add more sources
- [ ] Build RSS feed from daily links (possibly hosted on GH)

## Testing Locally

### Prerequisites

- Python 3.12+
- Discord webhook URL (for notifications)

### Setup

1. Clone the repository

```bash
git clone https://github.com/greyhoundforty/kylfuskofu
cd kylfuskofu
```

2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

4. Ensure environment variables are set:

```bash
export DISCORD_WEBHOOK_URL=<your-discord-webhook-url>
```

5. Run the application using a local sqlitedb file

```bash
python app.py --local
```

## Run with remote DB file

To persist data across runs, you can use a remote SQLite database file. This is useful for running the application in a containerized environment. In this case we will use IBM Cloud Object Storage (COS) to store the SQLite database file.

### Prerequisites

- IBM Cloud Object Storage instance

You will need to create a bucket in IBM Cloud Object Storage and set the following environment variables before running the application:

```bash
export COS_ENDPOINT=<your-cos-endpoint>
export COS_API_KEY=<your-cos-api-key>
export COS_INSTANCE_CRN=<your-cos-instance-crn>
export COS_BUCKET_NAME=<your-bucket-name>
```

### Run the application

```bash
python app.py
```
