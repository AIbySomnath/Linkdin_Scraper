"""
Test script for Job Scraper components
"""
import json
import time
from job_planner import JobPlanner
from browser_executor import BrowserExecutor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_test_scrape(query="Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days", max_jobs=5):
    """
    Run a test scrape with the given query
    
    Args:
        query (str): Natural language job search query
        max_jobs (int): Maximum number of jobs to scrape
    """
    # Initialize components
    planner = JobPlanner()
    executor = BrowserExecutor(headless=False)  # Set to False to see the browser in action
    
    # Create a plan
    logger.info(f"Creating plan for query: {query}")
    plan = planner.create_plan(query)
    
    # Add site-specific details to the plan
    plan['site_details'] = planner.get_site_details(plan['site'])
    
    # Print the plan
    logger.info("Generated scraping plan:")
    print(json.dumps(plan, indent=2))
    
    # Execute the plan
    logger.info("Executing scraping plan...")
    jobs = executor.execute_plan(plan, max_jobs=max_jobs)
    
    # Print the results
    logger.info(f"Scraped {len(jobs)} jobs:")
    for i, job in enumerate(jobs):
        print(f"\nJob {i+1}:")
        for key, value in job.items():
            print(f"{key}: {value}")
    
    return jobs

# Run the test
if __name__ == "__main__":
    test_query = "Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days"
    logger.info("Starting Job Scraper test")
    
    # Run the test
    run_test_scrape(test_query, max_jobs=5)
    
    logger.info("Test complete")
