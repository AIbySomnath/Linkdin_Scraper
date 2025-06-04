"""
LinkedIn Job Scraper - Dedicated Streamlit UI for LinkedIn job scraping
"""
import streamlit as st
import pandas as pd
import time
import logging
import os
import json
from datetime import datetime
from linkedin_scraper import LinkedInScraper
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize components
linkedin_scraper = LinkedInScraper()

# Page configuration
st.set_page_config(
    page_title="LinkedIn Job Scraper",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 LinkedIn Job Scraper")
st.markdown("""
This app specializes in scraping job listings from LinkedIn based on your search criteria.
Enter your search parameters below to find LinkedIn job listings matching your requirements.
""")

# Create tabs for different search methods
tab1, tab2 = st.tabs(["Basic Search", "Advanced Search"])

with tab1:
    # Basic search form
    with st.form(key="basic_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input(
                "Job Title/Keywords",
                placeholder="e.g., Software Engineer, Data Scientist"
            )
            
        with col2:
            location = st.text_input(
                "Location",
                placeholder="e.g., New York, Remote"
            )
        
        max_jobs = st.slider("Maximum Jobs to Scrape", min_value=5, max_value=50, value=20, step=5)
        
        basic_submit = st.form_submit_button(label="🔍 Search LinkedIn Jobs")

with tab2:
    # Advanced search form
    with st.form(key="advanced_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            adv_search_term = st.text_input(
                "Job Title/Keywords",
                placeholder="e.g., Software Engineer, Data Scientist"
            )
            
            adv_location = st.text_input(
                "Location",
                placeholder="e.g., New York, Remote"
            )
            
            remote_filter = st.checkbox("Remote Jobs Only")
        
        with col2:
            time_period = st.radio(
                "Time Period",
                options=["Past 24 hours", "Past Week", "Past Month", "Any Time"],
                index=1
            )
            
            experience_level = st.selectbox(
                "Experience Level",
                options=["Any", "Internship", "Entry level", "Associate", "Senior", "Director"],
                index=0
            )
            
            job_type = st.selectbox(
                "Job Type",
                options=["Any", "Full-time", "Part-time", "Contract", "Temporary", "Volunteer"],
                index=0
            )
        
        adv_max_jobs = st.slider("Maximum Jobs to Scrape", min_value=5, max_value=50, value=20, step=5)
        
        advanced_submit = st.form_submit_button(label="🔍 Advanced LinkedIn Search")

# Main function to run the LinkedIn job scraping process
def run_linkedin_scraper(search_term, location, filters=None, max_jobs=20):
    """
    Run the LinkedIn scraper with the specified parameters
    
    Args:
        search_term (str): Job search term
        location (str): Job location
        filters (dict): Dictionary of filters to apply
        max_jobs (int): Maximum number of jobs to return
    """
    if not search_term:
        st.warning("Please enter a job title or keywords to search for.")
        return
    
    # Create a progress bar and status text
    progress_bar = st.progress(0)
    status_container = st.empty()
    status_text = status_container.text("Preparing LinkedIn search...")
    
    try:
        # Update progress
        progress_bar.progress(20)
        status_text.text(f"Searching LinkedIn for '{search_term}' in '{location}'...")
        
        # Set default filters if none provided
        if filters is None:
            filters = {}
        
        # Start scraping
        start_time = time.time()
        progress_bar.progress(40)
        
        jobs = linkedin_scraper.scrape_linkedin_jobs(
            search_term=search_term,
            location=location,
            filters=filters,
            max_jobs=max_jobs
        )
        
        # Update progress
        progress_bar.progress(70)
        status_text.text(f"Processing {len(jobs)} LinkedIn jobs...")
        
        # Process results
        if jobs:
            # Create DataFrame
            df = pd.DataFrame(jobs)
            
            # Add enhanced details if needed
            if 'url' in df.columns:
                # Sample detailed scraping for the first job only
                with st.expander("Sample Enhanced Job Details", expanded=False):
                    try:
                        first_job_url = df.iloc[0]['url']
                        if first_job_url:
                            status_text.text("Fetching detailed information for sample job...")
                            job_details = linkedin_scraper.scrape_job_details(first_job_url)
                            
                            if job_details:
                                st.subheader(job_details.get('title', 'Job Details'))
                                st.write(f"**Company:** {job_details.get('company', 'N/A')}")
                                st.write(f"**Location:** {job_details.get('location', 'N/A')}")
                                st.write(f"**Date Posted:** {job_details.get('date_posted', 'N/A')}")
                                
                                if 'employment_type' in job_details:
                                    st.write(f"**Employment Type:** {job_details.get('employment_type', 'N/A')}")
                                
                                if 'salary_range' in job_details:
                                    st.write(f"**Salary Range:** {job_details.get('salary_range', 'N/A')}")
                                
                                if 'description' in job_details:
                                    st.markdown("### Job Description")
                                    st.markdown(job_details.get('description', 'No description available.'))
                    except Exception as e:
                        st.warning(f"Could not fetch detailed job information: {str(e)}")
            
            # Show results
            progress_bar.progress(100)
            elapsed_time = time.time() - start_time
            status_text.text(f"✅ Found {len(jobs)} LinkedIn jobs in {elapsed_time:.2f} seconds!")
            
            # Results expander
            with st.expander("LinkedIn Job Results", expanded=True):
                # Show the results
                st.dataframe(df, use_container_width=True)
                
                # Add download button
                csv = df.to_csv(index=False).encode('utf-8')
                date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"linkedin_jobs_{date_str}.csv",
                    mime="text/csv"
                )
                
                # Visualizations
                if len(jobs) > 1:
                    st.subheader("Job Insights")
                    
                    # Company distribution
                    if 'company' in df.columns:
                        st.write("#### Top Companies")
                        company_counts = df['company'].value_counts().head(10)
                        st.bar_chart(company_counts)
                    
                    # Location distribution
                    if 'location' in df.columns:
                        st.write("#### Top Locations")
                        location_counts = df['location'].value_counts().head(10)
                        st.bar_chart(location_counts)
                    
                    # Recent vs older postings
                    if 'date_posted' in df.columns:
                        st.write("#### Job Freshness")
                        date_counts = df['date_posted'].value_counts().head(10)
                        st.bar_chart(date_counts)
        else:
            status_text.text("⚠️ No LinkedIn jobs found with the current search criteria")
            st.warning("""
            No jobs found matching your criteria. Try modifying your search:
            
            1. Use more general job titles (e.g., "Developer" instead of "Senior Python Developer")
            2. Try different locations or remove location filters
            3. Expand the time period filter
            4. LinkedIn might be limiting scraping - try again later
            """)
            
    except Exception as e:
        # Handle errors
        status_text.text("❌ Error scraping LinkedIn jobs")
        st.error(f"Error: {str(e)}")
        logger.error(f"LinkedIn scraping error: {str(e)}", exc_info=True)

# Handle form submissions
if basic_submit:
    run_linkedin_scraper(search_term, location, None, max_jobs)

if advanced_submit:
    # Map the form selections to the filter parameters
    filters = {}
    
    # Remote filter
    if remote_filter:
        filters['remote'] = True
    
    # Time period filter
    if time_period == "Past 24 hours":
        filters['time_period'] = 'day'
    elif time_period == "Past Week":
        filters['time_period'] = 'week'
    elif time_period == "Past Month":
        filters['time_period'] = 'month'
    
    # Experience level filter
    if experience_level != "Any":
        filters['experience'] = experience_level.lower().replace(' ', '_')
    
    # Job type filter
    if job_type != "Any":
        filters['job_type'] = job_type.lower().replace('-', '_')
    
    run_linkedin_scraper(adv_search_term, adv_location, filters, adv_max_jobs)

# Example queries
st.subheader("📌 Example LinkedIn Searches")
examples = {
    "Software Engineers in New York": {
        "search": "Software Engineer",
        "location": "New York"
    },
    "Remote Data Scientists": {
        "search": "Data Scientist",
        "location": "Remote",
        "filters": {"remote": True}
    },
    "Marketing Managers posted this week": {
        "search": "Marketing Manager",
        "location": "",
        "filters": {"time_period": "week"}
    },
    "Senior Product Managers in San Francisco": {
        "search": "Product Manager",
        "location": "San Francisco",
        "filters": {"experience": "senior"}
    }
}

# Create example buttons in columns
example_cols = st.columns(4)
for i, (example_name, example_params) in enumerate(examples.items()):
    with example_cols[i % 4]:
        if st.button(example_name):
            with st.spinner(f"Running example search: {example_name}"):
                run_linkedin_scraper(
                    example_params["search"],
                    example_params["location"],
                    example_params.get("filters", None),
                    20
                )

# Tips and information
with st.expander("💡 LinkedIn Scraping Tips"):
    st.markdown("""
    ### Tips for Effective LinkedIn Job Scraping
    
    1. **Be specific with job titles** - Use industry-standard job titles for better results
    2. **Location matters** - For remote jobs, you can use "Remote" as the location or check the Remote filter
    3. **Time filters** - Newer job postings are more likely to be active and accepting applications
    4. **Combine filters wisely** - Using too many filters may lead to fewer results
    
    ### About Rate Limiting
    
    LinkedIn may rate-limit excessive scraping. If you encounter issues:
    
    - Wait a few minutes before trying again
    - Use more specific searches to reduce the number of results
    - Use the advanced filters to narrow down results
    - Consider using a VPN if you're making many requests
    
    ### Exporting Data
    
    All search results can be downloaded as CSV files using the Download button below each search result.
    """)

# Footer
st.markdown("---")
st.markdown("Powered by LinkedIn Scraper | Created with Streamlit")

# Execute only if running as the main app
if __name__ == "__main__":
    print("LinkedIn Job Scraper is running!")
