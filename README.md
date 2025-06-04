# Job Scraper Agent

An intelligent browser-based agent that scrapes job listings from portals like Foundit.in or Indeed based on natural language queries.

## Features

- Parse natural language job search queries using GPT
- Automate browser-based job search using Playwright
- Extract structured job data from multiple job portals
- Export results to CSV or view directly in Streamlit UI

## Setup and Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```
4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

1. Run the Streamlit app:
   ```
   streamlit run app.py
   ```
2. Enter your job search query in natural language
3. View the structured results and export to CSV if desired

## Examples

- "Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days"
- "Get me software engineer jobs in Bangalore from Indeed with salary above 10LPA"
