# Agent Board template

A shared task board for a founder and a team of AI agents (two or more), kept in plain files.

## The idea

Most founders end up with several AI tools and no single view of what each is doing. This board fixes that with a few rules:

- One task list that every agent reads and writes through a locking script, so agents never overwrite each other.
- A Desk, a single page where you write requests in plain English, answer questions and tick off finished work.
- A clear split of labour. In the starter setup one agent does the thinking and writing and another does the finding, checking and filing. Add a third or fourth agent with its own lane if you have one.
- You only act when a task lands in "Waiting on you" or "Ready to sign off". Everything else keeps moving without you.
- Outward steps (sending, publishing, spending, deleting) always wait for your yes.
- Real-world jobs only you can do show up as errands, and small choices the agents made for you are listed so you can overturn them.

## What is in the box

- `agentboard.py`: the locking script. Standard Python 3 on macOS or Linux, no dependencies.
- `RULES.md`: the working agreement to give both agents. Edit it to suit your business.
- `tasks.example.js`: two sample tasks showing the shape of the data. Copy it to `tasks.js` to start.

## Getting started

1. Copy `tasks.example.js` to `tasks.js` and delete the sample tasks, or keep them to see how it works.
2. Rename `agent-a` and `agent-b` in the script and in `RULES.md` to match your own tools. Have three or more? Add them to the `AGENTS` line near the top of the script and give each a lane in `RULES.md`.
3. Point each agent at `RULES.md` and tell it to run `python3 agentboard.py intake` at the start of every run.
4. Run `python3 agentboard.py desk` once to create `DESK.md`. Write a request under "Write to us", run `intake`, and watch it appear on the board.

Run `python3 agentboard.py -h` for every command.

## Make it yours

Change the areas, the statuses and the limits in `RULES.md`. Add a phone view or a dashboard on top if you want one: the task file is plain JSON, so anything can read it.

## From Global Playground

Global Playground is a curated community for founders and entrepreneurs. Members get the full playbook library and a programme of events. Find out more at globalplayground.app.
