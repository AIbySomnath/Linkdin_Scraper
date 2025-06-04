"""
Browser Executor - Executes job scraping plans using Playwright for browser automation
and OpenAI GPT for enhanced job data extraction and analysis
"""
import time
import logging
import json
import traceback
import asyncio
import os
import re
from playwright.async_api import async_playwright
import nest_asyncio
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from job_extractor import JobExtractor

# Apply nest_asyncio to allow running asyncio in Jupyter/IPython environments
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)

class BrowserExecutor:
    """
    Executes job scraping tasks using Playwright for browser automation
    and OpenAI GPT for enhanced job data extraction and analysis
    """
    
    def __init__(self, headless=True):
        """
        Initialize the browser executor
        
        Args:
            headless (bool): Whether to run the browser in headless mode
        """
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.timeout = 30000  # 30 seconds timeout
        self.extractor = JobExtractor()  # Use the JobExtractor for parsing job data
        
    async def _setup_browser(self):
        """Set up the browser using Playwright"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        
        # Create a context with specific viewport and user agent
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            ignore_https_errors=True
        )
        
        # Enable JavaScript and cookies
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
        # Create a new page
        self.page = await self.context.new_page()
        return self.page
    
    async def _close_browser(self):
        """Close the browser and clean up resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    def execute_plan(self, plan, max_jobs=20):
        """Execute the job scraping plan
        
        Args:
            plan (dict): The job scraping plan
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        try:
            # Create and run an asyncio event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._execute_plan_async(plan, max_jobs))
        except Exception as e:
            logger.error(f"Error executing plan: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def _execute_plan_async(self, plan, max_jobs=20):
        """Execute the job scraping plan asynchronously
        
        Args:
            plan (dict): The job scraping plan
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        try:
            # Set up the browser
            await self._setup_browser()
            
            # Get the search URL
            search_url = self._build_search_url(plan)
            logger.info(f"Navigating to: {search_url}")
            
            # Navigate to the search URL
            await self.page.goto(search_url, wait_until='networkidle', timeout=self.timeout)
            logger.info(f"Page loaded: {await self.page.title()}")
            
            # Wait for job cards to load
            selectors = self._get_selectors_for_site(plan.get('site', ''))
            job_card_selector = selectors.get('job_card')
            
            try:
                await self.page.wait_for_selector(job_card_selector, timeout=self.timeout)
                logger.info(f"Found job cards with selector: {job_card_selector}")
            except Exception as e:
                logger.warning(f"Timeout waiting for job cards: {str(e)}")
            
            # Extract jobs from the page
            jobs = await self._extract_jobs_from_page(plan, max_jobs)
            logger.info(f"Extracted {len(jobs)} jobs from the page")
            
            # Use OpenAI GPT to enhance job descriptions and extract skills
            if jobs:
                jobs = await self._enhance_jobs_with_gpt(jobs)
            
            # Close the browser
            await self._close_browser()
            
        except Exception as e:
            logger.error(f"Error during browser execution: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Always try to close the browser
            try:
                await self._close_browser()
            except:
                pass
        
        return jobs
    
    def _build_search_url(self, plan):
        """Build a search URL from the plan
        
        Args:
            plan (dict): The job scraping plan
            
        Returns:
            str: The search URL
        """
        # Check if plan exists
        if not plan or not isinstance(plan, dict):
            logger.error("No valid plan provided for URL building")
            return "https://www.foundit.in"

        # Extract and convert parameters to strings
        site = str(plan.get('site', '')).lower() if plan.get('site') is not None else ''
        search_term = str(plan.get('search', '')) if plan.get('search') is not None else ''
        location = str(plan.get('location', '')) if plan.get('location') is not None else ''
        
        # Build URL based on site
        if not site or 'foundit.in' in site:
            return f"https://www.foundit.in/srp/results?searchType=personalizedSearch&keyword={search_term}&location={location}"
        elif 'indeed.com' in site:
            return f"https://www.indeed.com/jobs?q={search_term}&l={location}"
        elif 'naukri.com' in site:
            return f"https://www.naukri.com/{search_term}-jobs-in-{location}"
        elif 'linkedin.com' in site or 'linkedin' in site:
            # Format search term and location for LinkedIn
            search_term_formatted = search_term.replace(' ', '%20')
            location_formatted = location.replace(' ', '%20') if location else ''
            # LinkedIn job search URL with parameters
            return f"https://www.linkedin.com/jobs/search/?keywords={search_term_formatted}&location={location_formatted}&f_TPR=r86400"
        else:
            # Default to Foundit.in
            return f"https://www.foundit.in/srp/results?searchType=personalizedSearch&keyword={search_term}&location={location}"
    
    def _get_selectors_for_site(self, site):
        """Get CSS selectors for the site
        
        Args:
            site (str): The job portal site
            
        Returns:
            dict: Dictionary of CSS selectors
        """
        site = site.lower() if isinstance(site, str) else ''
        
        if 'foundit.in' in site:
            return {
                'job_card': '.card-apply-content, .job-tittle, .card',
                'title': '.job-title, h3, .title',
                'company': '.company-name, .subtitle-link, .company',
                'location': '.location-link, .location, .loc',
                'date': '.posted-update, .date',
                'description': '.job-desc, .job-description',
                'next_page': '.srpPagination li:last-child a'
            }
        elif 'indeed.com' in site:
            return {
                'job_card': '.job_seen_beacon, .tapItem, .job-container',
                'title': '.jobTitle, .jcs-JobTitle, h2 a',
                'company': '.companyName, .company-name, .companyInfo a',
                'location': '.companyLocation, .location, .job-location',
                'date': '.date, .new-job-age, .postDate',
                'description': '.job-snippet, .summary',
                'next_page': 'a[data-testid="pagination-page-next"]'
            }
        elif 'naukri.com' in site:
            return {
                'job_card': '.jobTuple, .job-card, article.jobTupleCard',
                'title': '.title, .jobTitle, a.title',
                'company': '.company, .companyInfo, .subTitle, .companyName',
                'location': '.location, .loc, .jobLocation, .locWdth',
                'date': '.freshness, .date, .posted-date',
                'description': '.job-description, .job-desc',
                'next_page': '.pagination a.fright'
            }
        else:
            # Default to Foundit.in
            return {
                'job_card': '.card-apply-content, .job-tittle, .card',
                'title': '.job-title, h3, .title',
                'company': '.company-name, .subtitle-link, .company',
                'location': '.location-link, .location, .loc',
                'date': '.posted-update, .date',
                'description': '.job-desc, .job-description',
                'next_page': '.srpPagination li:last-child a'
            }
    
    async def _extract_jobs_from_page(self, plan, max_jobs=20):
        """Extract jobs from the page using JobExtractor
        
        Args:
            plan (dict): The job scraping plan
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        site = plan.get('site', '')
        logger.info(f"Extracting jobs from page for site: {site}")
        
        try:
            # Use the JobExtractor to extract jobs from the page
            jobs = await self.extractor.extract_jobs_from_page(self.page, site, max_jobs)
            logger.info(f"Extracted {len(jobs)} jobs from page using JobExtractor")
            
            # Apply any filters from the plan
            jobs = self._apply_filters_to_jobs(jobs, plan)
            logger.info(f"After filtering: {len(jobs)} jobs remain")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error extracting jobs from page: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try HTML extraction as fallback
            try:
                logger.info("Trying HTML fallback extraction...")
                html_content = await self.page.content()
                jobs = self.extractor.extract_jobs_from_html(html_content, site, max_jobs)
                
                # Apply any filters
                jobs = self._apply_filters_to_jobs(jobs, plan)
                
                return jobs
                
            except Exception as html_err:
                logger.error(f"HTML fallback also failed: {str(html_err)}")
                return []
    
    def _apply_filters_to_jobs(self, jobs, plan):
        """Apply filters from the plan to the job results
        
        Args:
            jobs (list): List of job dictionaries
            plan (dict): The job scraping plan with filters
            
        Returns:
            list: Filtered list of jobs
        """
        if not jobs or not plan:
            return jobs
            
        filtered_jobs = jobs.copy()
        filters = plan.get('filters', [])
        
        if not filters:
            return filtered_jobs
            
        logger.info(f"Applying filters: {filters}")
        
        # Process filters one by one
        for filter_item in filters:
            if not filter_item:
                continue
                
            filter_lower = filter_item.lower()
            
            # Filter by remote jobs
            if any(term in filter_lower for term in ['remote', 'work from home', 'wfh']):
                filtered_jobs = [job for job in filtered_jobs if self._is_remote_job(job)]
                
            # Filter by recency
            if 'last 24 hours' in filter_lower or 'today' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._is_recent_job(job, hours=24)]
            elif 'last 3 days' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._is_recent_job(job, hours=72)]
            elif 'last 7 days' in filter_lower or 'week' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._is_recent_job(job, hours=168)]
            elif 'last 30 days' in filter_lower or 'month' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._is_recent_job(job, hours=720)]
                
            # Filter by experience level
            if 'entry' in filter_lower or 'junior' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._matches_experience(job, 'entry')]
            elif 'mid' in filter_lower or 'intermediate' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._matches_experience(job, 'mid')]
            elif 'senior' in filter_lower or 'experienced' in filter_lower:
                filtered_jobs = [job for job in filtered_jobs if self._matches_experience(job, 'senior')]
                
            # Filter by salary (if specified with a number)
            salary_match = re.search(r'(salary|compensation)\s*(>|above|over|more than)\s*(\d+)\s*(k|l|lpa|lakh|cr|crore)', filter_lower)
            if salary_match:
                amount = int(salary_match.group(3))
                unit = salary_match.group(4).lower()
                # Convert to a standard unit (lakhs)
                if unit in ['k', 'thousand']:
                    amount = amount / 100  # Convert thousands to lakhs
                elif unit in ['cr', 'crore']:
                    amount = amount * 100  # Convert crores to lakhs
                
                filtered_jobs = [job for job in filtered_jobs if self._meets_salary_requirement(job, amount)]
        
        logger.info(f"After filtering, {len(filtered_jobs)} jobs remain")
        return filtered_jobs
    
    def _is_remote_job(self, job):
        """Check if a job is remote
        
        Args:
            job (dict): Job dictionary
            
        Returns:
            bool: True if job is remote
        """
        remote_terms = ['remote', 'work from home', 'wfh', 'virtual', 'telecommute', 'anywhere']
        
        # Check various fields for remote indicators
        for field in ['title', 'description', 'location']:
            if field in job and job[field]:
                text = job[field].lower()
                if any(term in text for term in remote_terms):
                    return True
        
        return False
    
    def _is_recent_job(self, job, hours=168):  # Default to 7 days (168 hours)
        """Check if a job was posted within the specified time period
        
        Args:
            job (dict): Job dictionary
            hours (int): Number of hours to consider as recent
            
        Returns:
            bool: True if job was posted within the specified time period
        """
        date_field = next((f for f in ['date_posted', 'posted_date', 'date'] if f in job), None)
        
        if not date_field or not job[date_field]:
            return True  # If no date information, assume it's recent
            
        date_text = job[date_field].lower()
        
        # Simple text-based checks (common patterns in job listings)
        if 'just now' in date_text or 'today' in date_text:
            return True
        if 'yesterday' in date_text and hours >= 24:
            return True
        if 'this week' in date_text and hours >= 168:
            return True
        if 'this month' in date_text and hours >= 720:
            return True
            
        # Check for '5 days ago', '2 hours ago', etc.
        time_match = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', date_text)
        if time_match:
            value = int(time_match.group(1))
            unit = time_match.group(2)
            
            if unit == 'hour' and value <= hours:
                return True
            if unit == 'day' and value * 24 <= hours:
                return True
            if unit == 'week' and value * 168 <= hours:
                return True
            if unit == 'month' and value * 720 <= hours:
                return True
                
            return False
            
        # Default to including the job if we can't determine recency
        return True
    
    def _matches_experience(self, job, level):
        """Check if a job matches the specified experience level
        
        Args:
            job (dict): Job dictionary
            level (str): Experience level to check for ('entry', 'mid', 'senior')
            
        Returns:
            bool: True if job matches the experience level
        """
        # First check if the job has an explicit experience_level field (from GPT enhancement)
        if 'experience_level' in job and job['experience_level']:
            exp_level = job['experience_level'].lower()
            
            if level == 'entry' and any(term in exp_level for term in ['entry', 'junior', 'fresher', 'trainee', '0-1', '0-2']):
                return True
            if level == 'mid' and any(term in exp_level for term in ['mid', 'intermediate', 'associate', '2-5', '3-5']):
                return True
            if level == 'senior' and any(term in exp_level for term in ['senior', 'lead', 'manager', 'principal', '5+', '7+']):
                return True
                
        # Check other fields for experience level indicators
        for field in ['title', 'description', 'experience']:
            if field in job and job[field]:
                text = job[field].lower()
                
                if level == 'entry' and any(term in text for term in ['entry', 'junior', 'fresher', 'trainee', 'graduate', '0-1', '0-2']):
                    return True
                if level == 'mid' and any(term in text for term in ['mid', 'intermediate', 'associate', '2-5', '3-5']):
                    return True
                if level == 'senior' and any(term in text for term in ['senior', 'lead', 'manager', 'principal', 'head', '5+', '7+']):
                    return True
                    
        # If no experience level indicators are found, default to including the job
        return True
    
    def _meets_salary_requirement(self, job, min_lakhs):
        """Check if a job meets the minimum salary requirement
        
        Args:
            job (dict): Job dictionary
            min_lakhs (float): Minimum salary in lakhs per annum
            
        Returns:
            bool: True if job meets or exceeds the salary requirement
        """
        # Check if the job has a salary field (either original or from GPT enhancement)
        salary_field = next((f for f in ['salary', 'salary_range'] if f in job), None)
        
        if not salary_field or not job[salary_field]:
            return True  # If no salary information, assume it meets the requirement
            
        salary_text = job[salary_field].lower()
        
        # Try to extract salary information using regex
        # Look for patterns like "10-15 LPA", "₹10L - ₹15L", "10 Lakhs", etc.
        salary_match = re.search(r'(\d+(?:\.\d+)?)\s*-?\s*(\d+(?:\.\d+)?)?\s*(lpa|l|lakh|lakhs|k|cr|crore)', salary_text)
        
        if salary_match:
            min_value = float(salary_match.group(1))
            unit = salary_match.group(3).lower()
            
            # Convert to lakhs for comparison
            if unit in ['k', 'thousand']:
                min_value = min_value / 100  # Convert thousands to lakhs
            elif unit in ['cr', 'crore']:
                min_value = min_value * 100  # Convert crores to lakhs
                
            return min_value >= min_lakhs
            
        # Default to including the job if we can't determine salary
        return True

    def _extract_jobs_from_html(self, html_content, plan, max_jobs=20):
        """Extract jobs from raw HTML content using JobExtractor
        
        Args:
            html_content (str): HTML content of the page
            plan (dict): The job scraping plan
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        site = plan.get('site', '')
        
        # Use JobExtractor to extract jobs from HTML
        jobs = self.extractor.extract_jobs_from_html(html_content, site, max_jobs)
        
        # Apply any filters
        jobs = self._apply_filters_to_jobs(jobs, plan)
        
        return jobs
    
    async def _enhance_jobs_with_gpt(self, jobs):
        """Use JobExtractor to enhance job descriptions with GPT
        
        Args:
            jobs (list): List of job dictionaries
            
        Returns:
            list: Enhanced list of job dictionaries
        """
        try:
            # Use the JobExtractor's GPT enhancement method
            enhanced_jobs = await self.extractor.enhance_jobs_with_gpt(jobs)
            logger.info(f"Enhanced {len(enhanced_jobs)} jobs with GPT")
            return enhanced_jobs
        except Exception as e:
            logger.error(f"Error enhancing jobs with GPT: {str(e)}")
            logger.error(traceback.format_exc())
            # Return the original jobs if enhancement fails
            return jobs
        """
        Initialize the browser executor
        
        Args:
            headless (bool): Whether to run the browser in headless mode
        """
        self.headless = headless
        self.extractor = JobExtractor()
        
    def execute_plan(self, plan, max_jobs=20):
        """
        Execute a job scraping plan
        
        Args:
            plan (dict): The scraping plan created by JobPlanner
            max_jobs (int): Maximum number of jobs to scrape
            
        Returns:
            list: List of scraped job data
        """
        site_details = plan.get('site_details', {})
        if not site_details:
            logger.error("No site details found in plan")
            return []
            
        jobs = []
        driver = None
        
        try:
            # User agents list for randomization
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
            ]
            
            # Choose a random user agent
            random_user_agent = random.choice(user_agents)
            logger.info(f"Using user agent: {random_user_agent}")
            
            # Use undetected_chromedriver if available, else use standard Selenium
            if USING_UNDETECTED:
                logger.info("Using undetected_chromedriver for stealth operation")
                options = uc.ChromeOptions()
                
                # Configure options
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument(f'--user-agent={random_user_agent}')
                options.add_argument('--window-size=1920,1080')  # Use larger window for better visibility
                
                # Add experimental options to avoid detection
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # Create a data directory to maintain cookies and session
                data_dir = Path.home() / ".jobscraper_data"
                data_dir.mkdir(exist_ok=True)
                options.add_argument(f'--user-data-dir={str(data_dir)}')
                
                # Initialize the undetected Chrome WebDriver
                driver = uc.Chrome(options=options)
            else:
                logger.info("Using standard Selenium WebDriver")
                options = webdriver.ChromeOptions()
                
                # Configure options
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument(f'--user-agent={random_user_agent}')
                options.add_argument('--window-size=1920,1080')  # Use larger window
                
                # Add experimental options to avoid detection
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Initialize the Chrome WebDriver
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            
            # Set page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to job site and search
            search_url = self._build_search_url(plan, site_details)
            logger.info(f"Navigating to: {search_url}")
            driver.get(search_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Apply filters
            self._apply_filters(driver, plan, site_details)
            
            # Extract jobs from first page
            page_jobs = self._extract_jobs_from_page(driver, plan, site_details)
            jobs.extend(page_jobs)
            
            # Handle pagination if needed to get up to max_jobs
            page_num = 1
            while len(jobs) < max_jobs:
                # Check if there's a next page button
                next_button_selectors = [
                    "//a[text()='Next']", 
                    "//a[@aria-label='Next']", 
                    ".nextPage", 
                    ".pagination a:last-child"
                ]
                
                next_button = None
                for selector in next_button_selectors:
                    try:
                        if selector.startswith("//"):  # XPath
                            next_button = driver.find_element(By.XPATH, selector)
                        else:  # CSS
                            next_button = driver.find_element(By.CSS_SELECTOR, selector)
                        if next_button:
                            break
                    except NoSuchElementException:
                        continue
                
                if not next_button:
                    logger.info("No more pages available")
                    break
                    
                # Click next page
                logger.info(f"Moving to page {page_num + 1}")
                next_button.click()
                time.sleep(3)  # Wait for page to load
                
                # Extract jobs from this page
                page_jobs = self._extract_jobs_from_page(driver, plan, site_details)
                jobs.extend(page_jobs)
                page_num += 1
                
                # Safety check - limit to 5 pages maximum
                if page_num >= 5:
                    break
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            
        finally:
            # Close browser
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
        # Limit to max_jobs
        return jobs[:max_jobs]
    
    def _build_search_url(self, plan, site_details):
        """
        Build the search URL based on the plan and site details
        
        Args:
            plan (dict): The scraping plan
            site_details (dict): Site-specific details
            
        Returns:
            str: The search URL
        """
        site = plan['site']
        search_term = plan['search']
        location = plan['location']
        
        base_url = site_details.get('search_url', site)
        search_param = site_details.get('search_param', 'q')
        location_param = site_details.get('location_param', 'l')
        
        # Handle different site URL formats
        if "foundit.in" in site.lower():
            search_url = f"{base_url}?{search_param}={search_term.replace(' ', '%20')}&{location_param}={location.replace(' ', '%20')}"
        elif "indeed.com" in site.lower():
            search_url = f"{base_url}?{search_param}={search_term.replace(' ', '+')}&{location_param}={location.replace(' ', '+')}"
        elif "naukri.com" in site.lower():
            search_url = f"{base_url}?{search_param}={search_term.replace(' ', '-')}&{location_param}={location.replace(' ', '-')}"
        else:
            # Generic format
            search_url = f"{base_url}?{search_param}={search_term.replace(' ', '+')}&{location_param}={location.replace(' ', '+')}"
            
        return search_url
    
    def _apply_filters(self, driver, plan, site_details):
        """
        Apply filters specified in the plan
        
        Args:
            driver: Selenium WebDriver object
            plan (dict): The scraping plan
            site_details (dict): Site-specific details
        """
        filters = plan.get('filters', [])
        site_filters = site_details.get('filters', {})
        
        for filter_name in filters:
            selector = site_filters.get(filter_name)
            if selector:
                try:
                    logger.info(f"Applying filter: {filter_name} with selector {selector}")
                    
                    # Wait for the filter element to be clickable
                    wait = WebDriverWait(driver, 10)
                    if selector.startswith('//'):
                        filter_element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        filter_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    # Click the filter
                    filter_element.click()
                    
                    # Wait for results to update
                    time.sleep(2)
                except TimeoutException:
                    logger.warning(f"Filter not found or not clickable: {filter_name}")
                except Exception as e:
                    logger.warning(f"Error applying filter {filter_name}: {str(e)}")
    
    def _extract_jobs_from_page(self, driver, plan, site_details):
        """
        Extract jobs from the current page
        
        Args:
            driver: Selenium WebDriver object
            plan (dict): The scraping plan
            site_details (dict): Site-specific details
            
        Returns:
            list: List of job data extracted from the page
        """
        # Get the selectors for this site
        selectors = site_details.get('selectors', {})
        if not selectors:
            logger.error("No selectors found for this site")
            return []
            
        jobs = []
        
        # Wait for page to fully load with increased timeout
        logger.info("Waiting for page to fully load...")
        try:
            # Allow more time for the page to fully render
            time.sleep(5)
            
            # Scroll down slowly to load lazy-loaded content
            logger.info("Scrolling page to trigger lazy loading...")
            total_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(1, 10):
                driver.execute_script(f"window.scrollTo(0, {i * total_height / 10});")
                time.sleep(0.5)
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Save page source for debugging
            page_title = driver.title
            page_url = driver.current_url
            logger.info(f"Current page: '{page_title}' at URL: {page_url}")
            
            # Try the job card selector from the site details first
            card_selector = selectors.get('job_card')
            job_cards = []
            
            if card_selector:
                logger.info(f"Using provided job card selector: {card_selector}")
                try:
                    job_cards = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, card_selector))
                    )
                    logger.info(f"Found {len(job_cards)} job cards with provided selector")
                except TimeoutException:
                    logger.warning(f"Timeout waiting for job cards with selector: {card_selector}")
                    job_cards = []
            
            # If no cards found with the primary selector, try alternative selectors
            if not job_cards:
                # Multi-level approach to find job cards
                logger.info("Primary selector failed. Trying alternative selectors...")
                
                # Level 1: Common job card selectors across sites
                alternative_selectors = [
                    # Common job card selectors across different sites
                    '.job_seen_beacon', '.job-card', '.card', '[data-job-id]', '.jobTuple', '.jobTupleHeader',
                    '.job-container', 'div[class*="job-"]', 'article.jobTuple', '.srp-jobtuple',
                    # Broader selectors that might catch job listings
                    'div.result', 'div[data-tn-component="organicJob"]', 'div[class*="result"]', 
                    # Even broader fallbacks
                    'div[class*="card"]', 'article', 'div.list-group-item'
                ]
                
                # Try each alternative selector
                for selector in alternative_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            job_cards = elements
                            logger.info(f"Found {len(job_cards)} job cards with selector: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {str(e)}")
                        continue
            
            # Level 2: If still no cards found, try a more aggressive approach
            if not job_cards:
                logger.info("Trying more aggressive approach to find job cards...")
                try:
                    # Look for elements that look like job listings based on content
                    all_divs = driver.find_elements(By.CSS_SELECTOR, 'div, article, li')
                    potential_cards = []
                    
                    for div in all_divs:
                        try:
                            div_text = div.text.lower()
                            # Check if this element has job-related content
                            if (('job' in div_text or 'position' in div_text or 'hiring' in div_text) and 
                                ('apply' in div_text or 'company' in div_text or 'location' in div_text)):
                                if len(div_text) > 50 and len(div_text) < 1000:  # Reasonable size for a job card
                                    potential_cards.append(div)
                        except Exception:
                            continue
                    
                    if potential_cards:
                        job_cards = potential_cards
                        logger.info(f"Found {len(job_cards)} potential job cards using content analysis")
                except Exception as e:
                    logger.error(f"Error finding job cards by content: {str(e)}")
            
            # Level 3: Ultimate fallback - extract structured data from page
            if not job_cards:
                logger.info("Trying to extract structured job data from page...")
                try:
                    # Look for schema.org job posting markup
                    script_elements = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
                    for script in script_elements:
                        try:
                            json_data = json.loads(script.get_attribute('innerHTML'))
                            if '@type' in json_data and json_data['@type'] == 'JobPosting':
                                # We found structured job data
                                job_data = {
                                    'title': json_data.get('title', ''),
                                    'company': json_data.get('hiringOrganization', {}).get('name', ''),
                                    'location': json_data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                                    'date': json_data.get('datePosted', ''),
                                    'link': json_data.get('url', '')
                                }
                                jobs.append(job_data)
                                logger.info(f"Extracted job from structured data: {job_data['title']}")
                        except Exception:
                            continue
                except Exception as e:
                    logger.error(f"Error extracting structured job data: {str(e)}")
            
            # Log the number of job cards found
            if job_cards:
                logger.info(f"Found a total of {len(job_cards)} job cards")
            else:
                logger.warning("Could not find any job cards on the page")
                if os.environ.get('DEBUG') == 'true':
                    # Save page source to a file for debugging
                    with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logger.info("Saved page source to debug_page_source.html")
                return []
            
            # Process each job card to extract job details
            for card_index, card in enumerate(job_cards[:30]):  # Limit to 30 cards to avoid processing too many
                try:
                    # Get the text and HTML of the card for analysis
                    try:
                        card_text = card.text
                        card_html = card.get_attribute('outerHTML')
                    except Exception as e:
                        logger.warning(f"Error getting card text/HTML: {str(e)}")
                        card_text = ""
                        card_html = ""
                    
                    logger.debug(f"Processing job card {card_index+1}:\n{card_text[:200]}...")
                    
                    # Create a job data dictionary
                    job_data = {}
                    
                    # LEVEL 1: Try to extract data using provided selectors
                    for field, selector in selectors.items():
                        if field == 'job_card' or not selector:
                            continue
                            
                        try:
                            element = card.find_element(By.CSS_SELECTOR, selector)
                            # Handle different field types
                            if field == 'link':
                                href = element.get_attribute('href')
                                if href:
                                    # If it's a relative URL, add the base URL
                                    if href.startswith('/'):
                                        base_url = '/'.join(plan['site'].split('/')[:3])
                                        href = f"{base_url}{href}"
                                    job_data[field] = href
                            else:
                                text = element.text
                                job_data[field] = text.strip() if text else ""
                        except NoSuchElementException:
                            # Field not found with primary selector, will try alternatives
                            pass
                    
                    # LEVEL 2: Try alternative selectors for each field if not found
                    field_alternative_selectors = {
                        'title': [
                            'h2', 'h3', 'h4', '.title', '.job-title', '.position', '[class*="title"]',
                            'a[href*="job"]', 'a.title', 'a[class*="title"]', '[data-test="jobTitle"]',
                            'h2.title', 'h3.title', 'span.title', 'div.title'
                        ],
                        'company': [
                            '.company', '.company-name', '.employer', '[class*="company"]', 
                            '[class*="employer"]', '[data-test="company-name"]', 'span.companyName',
                            'div.companyName', 'a[data-tn-element="companyName"]'
                        ],
                        'location': [
                            '.location', '.job-location', '[class*="location"]', 'span.loc',
                            'div.companyLocation', '[data-test="location"]', 'span.location',
                            '[title*="location"]', 'div[class*="location"]'
                        ],
                        'date': [
                            '.date', '.posted', '.posted-date', '[class*="date"]', '[class*="posted"]',
                            'span.date', 'div.date', 'span[data-test="date"]', '.job-date'
                        ],
                        'link': [
                            'a', 'a[href]', 'a[target]', 'a.title', 'a[href*="job"]', 'a[href*="career"]',
                            'a.view-job', 'a.job-title', 'a[data-testid="job-link"]'
                        ]
                    }
                    
                    # Try alternative selectors for fields that are still missing
                    for field, alt_selectors in field_alternative_selectors.items():
                        if field not in job_data or not job_data[field]:
                            for alt_selector in alt_selectors:
                                try:
                                    alt_elem = card.find_element(By.CSS_SELECTOR, alt_selector)
                                    if alt_elem:
                                        if field == 'link':
                                            href = alt_elem.get_attribute('href')
                                            if href:
                                                if href.startswith('/'):
                                                    base_url = '/'.join(plan['site'].split('/')[:3])
                                                    href = f"{base_url}{href}"
                                                job_data[field] = href
                                                break
                                        else:
                                            text = alt_elem.text
                                            if text and text.strip():
                                                job_data[field] = text.strip()
                                                break
                                except Exception:
                                    continue
                    
                    # LEVEL 3: Extract data from the card text using pattern matching
                    if card_text:
                        lines = card_text.split('\n')
                        
                        # Title is often the first line
                        if 'title' not in job_data or not job_data['title']:
                            if lines and lines[0].strip():
                                job_data['title'] = lines[0].strip()
                        
                        # Company often follows the title
                        if 'company' not in job_data or not job_data['company']:
                            if len(lines) > 1 and len(lines[1]) < 50:  # Company names are usually short
                                job_data['company'] = lines[1].strip()
                        
                        # Look for location keywords
                        if 'location' not in job_data or not job_data['location']:
                            for line in lines:
                                if any(loc in line.lower() for loc in ['remote', 'bangalore', 'delhi', 'mumbai', 'hyderabad', 'pune', 'chennai']):
                                    job_data['location'] = line.strip()
                                    break
                        
                        # Look for date patterns
                        if 'date' not in job_data or not job_data['date']:
                            date_patterns = ['posted', 'ago', 'day', 'week', 'month', 'hour']
                            for line in lines:
                                if any(pattern in line.lower() for pattern in date_patterns) and len(line) < 50:
                                    job_data['date'] = line.strip()
                                    break
                    
                    # LEVEL 4: Try to find a link in the card if still missing
                    if 'link' not in job_data or not job_data['link']:
                        try:
                            links = card.find_elements(By.TAG_NAME, 'a')
                            for link in links:
                                href = link.get_attribute('href')
                                if href and ('job' in href.lower() or 'career' in href.lower() or 'apply' in href.lower()):
                                    if href.startswith('/'):
                                        base_url = '/'.join(plan['site'].split('/')[:3])
                                        href = f"{base_url}{href}"
                                    job_data['link'] = href
                                    break
                            # If no job-specific link found, use the first link
                            if ('link' not in job_data or not job_data['link']) and links:
                                href = links[0].get_attribute('href')
                                if href:
                                    if href.startswith('/'):
                                        base_url = '/'.join(plan['site'].split('/')[:3])
                                        href = f"{base_url}{href}"
                                    job_data['link'] = href
                        except Exception as e:
                            logger.debug(f"Error finding links: {str(e)}")
                    
                    # If we still don't have a title but have other fields, create a generic one
                    if ('title' not in job_data or not job_data['title']) and ('company' in job_data or 'location' in job_data):
                        company = job_data.get('company', 'Company')
                        location = job_data.get('location', '')
                        job_data['title'] = f"Job at {company} {location}".strip()
                    
                    # Only add if we have at least a title and one other field
                    if job_data and 'title' in job_data and len(job_data) >= 2:
                        logger.info(f"Extracted job: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
                        jobs.append(job_data)
                    else:
                        logger.debug(f"Skipping incomplete job data: {job_data}")
                
                except Exception as e:
                    logger.warning(f"Error extracting job data from card: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error extracting jobs from page: {str(e)}")
        
        logger.info(f"Successfully extracted {len(jobs)} jobs from the page")
        return jobs
