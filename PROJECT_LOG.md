# Project Log: Call Volume Agent

Purpose: learn how an AI agent works by building a small one. Each step is recorded here as it is done. The README is written from this log. Edit any step and note the change in the Changelog.

## Step 1: Scope (done)

- Goal: the agent reads 4 weeks of 15-minute call data, says in plain language which hours of the day get the most calls (with the numbers), and creates a chart of call volume by hour.
- Aggregation: average across all days, one chart showing a typical day (option A). A by-day-of-week view can be added later as a second tool.
- First platform: AWS Connect. Platform column names will be mapped to our standard names later, so adding other platforms does not change the agent.
- Not in scope for now: forecast, staffing, service level diagnosis, other platforms, compliance module. These are later additions on the same design.
- Why this size: it still covers the core of an agent (pick a tool, run it, read the result, create a chart) and can be finished quickly.

## Step 2: Sample data (done)

- File: data/sample_calls_4wk.csv, made by scripts/make_sample_data.py (fixed random seed, so it can be recreated exactly).
- Columns: interval_start, queue, calls_offered. The queue column stays even with one queue so more queues can be added without changes.
- Size: 1,088 rows, 24 open days from 2026-10-12 to 2026-11-07, 19,515 calls in total.
- Hours open: Mon-Fri 7am-7pm, Sat 8am-4pm, closed Sunday.
- Planted pattern: morning peak around 10-11am, lunch dip, smaller afternoon bump around 2-3pm, Mondays busier, Fridays lighter, Saturdays about half a weekday.
- Answer key (total calls by hour, calculated separately from the agent): 10am 2,918; 11am 2,859; 2pm 2,290; 3pm 2,052; 9am 2,008. The agent should name 10am and 11am as the busiest hours.
- To change: edit the profile and day factors at the top of the script and run it again.

## Setup (done)

- What: Python 3.12 on a Windows PC, libraries anthropic, pandas and matplotlib, a Claude Console account, an API key stored in the ANTHROPIC_API_KEY environment variable, and a small credit balance.
- Why: the agent's reasoning comes from Claude through the API. The key tells the API who is calling and who to bill. It lives in an environment variable so it never appears in code or on GitHub. A Claude chat subscription does not cover API use, so API use is billed separately from the Console credits.
- Check: scripts/test_api.py sends one message to Claude. It confirmed the key, credits and install work.
- Lesson: a reply from Claude is a list of blocks (thinking, text, later tool requests), not one string. The first version of the test script assumed the first block was text and failed. The fix was to read only the blocks of type text.

## Step 3: Calculation tool (done)

- What: tools.py, function hourly_call_volume. It reads the 15-minute file, checks the three expected columns, adds intervals up to hours for each day, then averages each hour across days.
- Why: Claude is unreliable at arithmetic on 1,000 rows, so code does the math and Claude decides when to use it and explains the result. This split is the main design idea of an agent.
- Design choice: each hour is divided by the number of days it was open, not by all days. Saturdays open fewer hours, so 7am and 4pm to 6pm exist on 20 days and the others on 24. Dividing by all days would understate those hours.
- Check: totals match the answer key (10am 2,918; 11am 2,859; 2pm 2,290; 3pm 2,052; 9am 2,008). Confirmed on the PC as well.
- To change: edit REQUIRED_COLUMNS or the grouping in tools.py. A platform column mapping layer would go in front of load_intervals.

## Step 4: Instructions (done)

- What: the SYSTEM text at the top of agent.py. It names the reader (a contact center manager), explains the columns, and sets the rules: take numbers from the tools only, plain language, busiest hours first with the average per typical day, hours written as 10am, mention hours with fewer open days, under 120 words, create the chart, do not guess causes.
- Why: this is where domain knowledge goes. The same model gives a generic or a useful answer depending on these words. The no-guessing rule stops invented explanations the data cannot support.
- To change: edit the text. This is the part changed most often.

## Step 5: Agent loop (done)

- What: run_agent in agent.py. It sends the question and the tool descriptions to Claude. If Claude asks for a tool, our code runs it and sends the result back. This repeats until Claude writes a final answer. A limit of 6 rounds stops runaway loops, and a tool error is reported back to Claude instead of crashing.
- Why: this loop is what makes it an agent and not a chat. Claude never runs code itself. It asks, and our code does the work. Claude sees only the tool descriptions in TOOLS, never the code, so a clear description decides whether it picks the right tool.
- Check: the loop was tested with a stand-in for Claude (two calls, result passed back, error path handled), then on the PC with the real API. The answer named 10am and 11am as the busiest with averages matching the tool table.
- To change: add a tool by adding an entry to TOOLS and a branch in run_tool.

## Step 6: Chart tool (done)

- What: make_hourly_chart in tools.py, registered as a second tool. It draws average calls per hour on a typical day and saves it in the output folder as hourly_call_volume_<date>_<time>.png, a new file for every chart. The instructions tell Claude to create it after naming the busiest hours.
- Why: it shows the agent choosing between two tools and gives a visible result for the showcase.
- Chart choices: one color, no legend (one series, the title names it), thin gridlines, number labels only on the three busiest hours, hours written as 7am, 2pm.
- To change: edit make_hourly_chart. The label_top setting controls how many bars carry a number.
- Lesson from the first real run: Claude made both tool calls, but its wording varied between runs. It skipped the chart file name that the instructions asked for, and the list of busiest hours changed length. Instructions are followed most of the time, not every time. Fix: anything that must always appear is added by code, not left to Claude. run_agent now appends the chart's full path to the answer whenever the chart tool ran, and the instructions tell Claude not to write it. Rule of thumb: guarantees go in code, style goes in the instructions.

## Step 7: Test against the answer key (done)

- What: ran the agent on the real API from the PC with three kinds of question and checked each answer.
- Why: an agent's output has to be checked, not trusted. This is the habit that separates a demo from something reliable.
- Test 1, normal question ("Which hours of the day get the most calls?"), run several times: every number matched the answer key (10am 121.6, 11am 119.1, 2pm 95.4, 3pm 85.5, 9am 83.7). The open-days note appeared. The wording and the length of the list changed from run to run.
- Test 2, a question the data cannot answer ("Why do calls peak at 10am?"): passed. Claude said the data only has call counts and gave no cause. It ended by suggesting extra data to compare (campaigns, mailings, staffing changes), which is advice and not a claim. If example causes are unwanted, one line in the instructions can stop it.
- Test 3, a queue that does not exist ("Billing"): passed in the run I saw in full. Every error showed as a [tool error] line, Claude tried "billing" and "Billing Queue", made no numbers or chart, and asked for the exact name. In an earlier run it dropped the queue and used all queues instead, and I did not see how that answer ended, so that run is unverified.
- Chart file error: after the file name change, five chart runs in a row saved without error. Before the change, 2 of 3 failed. Treated as fixed so far, still being watched. Fallback if it returns: retry in code with a short pause.
- Ideas that came out of testing (not built): a list_queues tool so Claude can check queue names instead of guessing; an instruction line to avoid naming example causes; making the chart tool skip when the data tool already failed.

## Step 8: README and publish (planned)

- Write the README from this log and put the project on GitHub. Keep the API key and the output folder out of the repo.

## Changelog

- 2026-11-09: log started, Steps 1 and 2 recorded.
- 2026-11-10: added Setup and Steps 3 to 6 with what and why for each, and planned Steps 7 and 8.
- 2026-11-10: the chart file path is now added to the answer by code (agent.py), and the instructions no longer ask Claude to write it.
- 2026-11-10: a real run showed the chart tool failing once and succeeding on a retry. Claude reported the retry honestly, but the error text was only passed to Claude and never shown to the developer, so the cause is unknown. agent.py now prints every tool error as "[tool error] ..." in the terminal. Lesson: make failures visible to the developer, not only to the model.
- 2026-11-10: the error was [Errno 22] Invalid argument when saving output/hourly_call_volume.png on Windows. It happened on the first chart call in two agent runs, the retry worked, and running tools.py alone never failed. The cause is not confirmed (a briefly locked file is a guess). Chosen fix: every chart is saved with the date and time in its file name, so an existing file can never block a new one. Trade-off: more files in the output folder. Fallback if failures continue: retry in code with a short pause.
- 2026-11-10: Step 7 done. Three kinds of test run on the PC, results recorded in Step 7. Five chart runs in a row after the file name change saved without error.
