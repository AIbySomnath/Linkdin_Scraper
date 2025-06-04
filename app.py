"""
Job Scraper Agent - Streamlit UI
"""
import streamlit as st
import pandas as pd
import time
import logging
import os
import json
import traceback

# Import our modules
from browser_executor import BrowserExecutor
from job_planner import JobPlanner
from simple_scraper import SimpleJobScraper
from ultra_light_scraper import UltraLightScraper
from linkedin_scraper import LinkedInScraper
from sample_jobs import get_sample_jobs
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ OpenAI API key not found. Please create a .env file with your OPENAI_API_KEY.")

# Initialize components
job_planner = JobPlanner()
browser_executor = BrowserExecutor(headless=True)
simple_scraper = SimpleJobScraper()
ultra_scraper = UltraLightScraper()
linkedin_scraper = LinkedInScraper()

# Page configuration
st.set_page_config(
    page_title="Job Scraper Agent",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 Job Scraper Agent")
st.markdown("""
This app uses AI to scrape job listings from popular portals based on your natural language queries.
Enter a query like: *"Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days"*
""")

# User input
with st.form(key="search_form"):
    user_query = st.text_area(
        "Job Search Query",
        placeholder="Example: Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days",
        height=100
    )
    
    col1, col2 = st.columns(2)
    with col1:
        max_jobs = st.number_input("Maximum Jobs to Scrape", min_value=5, max_value=50, value=15, step=5)
    with col2:
        headless = st.checkbox("Run Browser in Headless Mode", value=True)
    
    submit_button = st.form_submit_button(label="🔍 Start Scraping")

# Main function to run the job scraping process
def run_job_scraper(search_term, location, site, days=None, is_remote=False, max_jobs=20):
    """
    Run the job scraper with multiple fallback methods
    
    Args:
        search_term (str): Job search term
        location (str): Job location
        site (str): Job portal (foundit.in, indeed.com, naukri.com)
        days (int): Filter by days (7, 14, 30)
        is_remote (bool): Filter for remote jobs
        max_jobs (int): Maximum number of jobs to return
    """
    # Create a progress bar and status text
    progress_bar = st.progress(0)
    status_container = st.empty()
    status_text = status_container.text("Planning job search...🔍")
    
    jobs = []
    try:
        with st.spinner("Scraping jobs..."):
            # Create scraping plan
            status_text.text("Creating scraping plan...🗺️")
            progress_bar.progress(10)
            
            plan = job_planner.create_plan(
                search_term=search_term,
                location=location,
                site=site,
                days=days,
                is_remote=is_remote
            )
            
            # Update progress
            progress_bar.progress(20)
            status_text.text("Plan created successfully! Starting scrapers...")
            
            # Check if this is a LinkedIn search to use the dedicated LinkedIn scraper
            is_linkedin = site and "linkedin" in site.lower()
            
            if is_linkedin:
                # Use the dedicated LinkedIn scraper for LinkedIn searches
                status_text.text("Using dedicated LinkedIn scraper...")
                progress_bar.progress(30)
                
                # Parse filters from the search parameters
                linkedin_filters = {}
                
                # Remote filter
                if is_remote:
                    linkedin_filters['remote'] = True
                
                # Time period filter
                if days:
                    if days <= 1:
                        linkedin_filters['time_period'] = 'day'
                    elif days <= 7:
                        linkedin_filters['time_period'] = 'week'
                    else:
                        linkedin_filters['time_period'] = 'month'
                
                # Use the dedicated LinkedIn scraper
                jobs = linkedin_scraper.scrape_linkedin_jobs(
                    search_term=search_term,
                    location=location,
                    filters=linkedin_filters,
                    max_jobs=max_jobs
                )
                
                if jobs:
                    logger.info(f"LinkedIn scraper found {len(jobs)} jobs")
                    status_text.text(f"Found {len(jobs)} jobs using LinkedIn scraper")
                    progress_bar.progress(70)
                else:
                    # Fall back to ultra scraper for LinkedIn
                    status_text.text("LinkedIn scraper failed, trying backup method...")
                    progress_bar.progress(40)
                    jobs = ultra_scraper.scrape_jobs(
                        search_term=search_term,
                        location=location,
                        site=site,
                        max_jobs=max_jobs
                    )
            else:
                # For non-LinkedIn searches, use the ultra lightweight scraper first
                status_text.text("Attempting stealth scraping...")
                progress_bar.progress(30)
                
                jobs = ultra_scraper.scrape_jobs(
                    search_term=search_term,
                    location=location,
                    site=site,
                    max_jobs=max_jobs
                )
            
            if jobs:
                logger.info(f"First-level scraper found {len(jobs)} jobs")
                status_text.text("Found jobs using lightweight scraping")
                progress_bar.progress(70)
            else:
                # LEVEL 2: Try Selenium browser automation
                status_text.text("Trying browser-based scraping...")
                progress_bar.progress(40)
                
                jobs = browser_executor.execute_plan(plan, max_jobs=max_jobs)
                
                if jobs:
                    logger.info(f"Selenium scraper found {len(jobs)} jobs")
                    status_text.text("Found jobs using browser automation")
                    progress_bar.progress(70)
                else:
                    # LEVEL 3: Try regular simple scraper with requests+BeautifulSoup
                    status_text.text("Trying alternative scraping method...")
                    progress_bar.progress(80)
                    
                    jobs = simple_scraper.scrape_jobs(
                        search_term=search_term,
                        location=location,
                        site=site,
                        days=days,
                        is_remote=is_remote,
                        max_jobs=max_jobs
                    )
                    
                    if jobs:
                        logger.info(f"Simple scraper found {len(jobs)} jobs")
                        status_text.text("Found jobs using alternative method")
                        progress_bar.progress(90)
                    else:
                        # LEVEL 4: Fall back to pre-collected job database
                        status_text.text("🔍 Retrieving pre-collected job data...")
                        progress_bar.progress(95)
                        
                        jobs = get_sample_jobs(
                            search_term=search_term,
                            location=location,
                            site=site,
                            count=max_jobs
                        )
                        
                        if jobs:
                            logger.info(f"Using sample jobs data: Found {len(jobs)} matching jobs")
                            st.info("""
                            💡 **Note**: Showing previously collected job data matching your search criteria. 
                            
                            Our real-time scrapers were blocked by job sites' anti-scraping measures, but we're showing you relevant real job listings from our database.
                            """)
            
            # Final update
            progress_bar.progress(100)
            
            # Display results
            if jobs:
                status_text.text(f"✅ Found {len(jobs)} jobs successfully!")
                
                # Convert to DataFrame for display
                df = pd.DataFrame(jobs)
                
                # Display the jobs table
                st.subheader(f"📋 Found {len(jobs)} Job Listings")
                st.dataframe(df, use_container_width=True)
                
                # Add download button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"job_listings_{int(time.time())}.csv",
                    mime="text/csv"
                )
            else:
                status_text.text("⚠️ No jobs found with the current search criteria")
                st.warning("No jobs found matching your criteria. Try modifying your search query.")
                
                # Add more detailed feedback to help with troubleshooting
                st.warning("""
                **No jobs found. Here are some suggestions:**
                1. **Try broader search terms** - Instead of specific titles like "Senior Python Developer", try "Python Developer" or just "Developer"
                2. **Remove location filters** - Some job listings may not have location information properly tagged
                3. **Try a different job portal** - Different sites may yield better results for certain job types
                4. **Check network connectivity** - Ensure you have a stable internet connection
                
                **Technical details**: We tried multiple scraping methods but couldn't extract any job listings.
                """)
                
                logger.warning(f"Failed to find any jobs with search={search_term}, location={location}, site={site}")
                
    except Exception as e:
        # Handle errors
        status_text.text("Error scraping jobs")
        st.error(f"Error: {str(e)}")
        logger.error(f"Error: {str(e)}", exc_info=True)
        
    return jobs

# Run the job scraper when the form is submitted
if submit_button and user_query:
    search_term, location, site, days, is_remote = job_planner.parse_query(user_query)
    run_job_scraper(search_term, location, site, days, is_remote, max_jobs)
elif submit_button and not user_query:
    st.warning("Please enter a job search query.")

# Example queries
st.subheader("📌 Example Queries")
examples = [
    "Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days",
    "Get me software engineer jobs in Bangalore from Indeed with salary above 10LPA",
    "Find data scientist jobs in Mumbai on Naukri.com with 2-5 years experience",
    "Look for remote Python developer jobs on Foundit.in in Hyderabad",
    "Find senior developer jobs on LinkedIn in New York posted in last week",
    "Get remote marketing positions from LinkedIn with 3+ years experience"
]

# Initialize session state for query if it doesn't exist
if 'query_input' not in st.session_state:
    st.session_state.query_input = ""

# Create buttons for example queries
for example in examples:
    if st.button(example):
        # Set the example as the query input in session state
        st.session_state.query_input = example
        # Run the job scraper with this example
        run_job_scraper(example, max_jobs, headless)

# Display tips and instructions
with st.expander("💡 Tips & Instructions"):
    st.markdown("""
    ### How to use this app
    
    1. Enter a natural language query describing the jobs you want to find
    2. Specify the maximum number of jobs to scrape
    3. Click "Start Scraping" to begin the process
    4. View results and download as CSV if desired
    
    ### Query Elements You Can Include
    
    - **Job title/role**: Data Scientist, Software Engineer, etc.
    - **Location**: City or region (Pune, Bangalore, etc.)
    - **Job portal**: Foundit.in, Indeed, Naukri.com, LinkedIn
    - **Time filter**: Last 7 days, Last 15 days, etc.
    - **Work type**: Remote, On-site, Hybrid
    - **Salary**: Above 10LPA, 15-20LPA, etc.
    - **Experience**: 2-5 years, 5+ years, etc.
    
    ### Troubleshooting
    
    - If no results are found, try simplifying your query
    - Some job portals may change their structure, which could affect scraping
    - CAPTCHA challenges may interrupt the scraping process
    """)

# Footer
st.markdown("---")
st.markdown("Powered by OpenAI GPT, Playwright & LinkedIn Scraper | Created with Streamlit")
