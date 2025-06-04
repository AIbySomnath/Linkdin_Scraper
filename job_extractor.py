"""
Job Extractor - Utility for parsing HTML and extracting job data
"""
import re
import json
from urllib.parse import urlparse, urljoin
import logging
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import ElementHandle
from openai import OpenAI
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client if available
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
    else:
        openai_client = None
        logger.warning("No OpenAI API key found. GPT enhancements will be disabled.")
except ImportError:
    openai_client = None
    logger.warning("OpenAI package not installed. GPT enhancements will be disabled.")

class JobExtractor:
    """
    Utility for parsing HTML and extracting job data from various job portals
    using both HTML parsing and Playwright DOM manipulation
    """

    def __init__(self):
        """Initialize the job extractor"""
        # Selectors for different job portals
        self.selectors = {
            'foundit.in': {
                'job_card': '.card-apply-content, .job-tittle, .card',
                'title': '.job-title, h3, .title',
                'company': '.company-name, .subtitle-link, .company',
                'location': '.location-link, .location, .loc',
                'date': '.posted-update, .date',
                'description': '.job-desc, .job-description',
                'salary': '.sal, .salary, .package',
                'skills': '.skill-item, .key-skill, .tags',
                'experience': '.exp-container, .experience, .exp',
                'job_url': 'a.title, a.job-title, .card a'
            },
            'indeed.com': {
                'job_card': '.job_seen_beacon, .tapItem, .job-container',
                'title': '.jobTitle, .jcs-JobTitle, h2 a',
                'company': '.companyName, .company-name, .companyInfo a',
                'location': '.companyLocation, .location, .job-location',
                'date': '.date, .new-job-age, .postDate',
                'description': '.job-snippet, .summary',
                'salary': '.salary-snippet, .salaryText, .attribute_snippet',
                'skills': '.skills, .job-requirements',
                'experience': '.experienceText, .experienceLevel',
                'job_url': 'a.jcs-JobTitle, a.jobtitle, a.job-link'
            },
            'naukri.com': {
                'job_card': '.jobTuple, .job-card, article.jobTupleCard',
                'title': '.title, .jobTitle, a.title',
                'company': '.company, .companyInfo, .subTitle, .companyName',
                'location': '.location, .loc, .jobLocation, .locWdth',
                'date': '.freshness, .date, .posted-date',
                'description': '.job-description, .job-desc',
                'salary': '.salary, .package',
                'skills': '.skill-item, .key-skill, .skill',
                'experience': '.experience, .expwdth, .exp',
                'job_url': 'a.title, a.job-title, .jobTupleHeader a'
            },
            'linkedin.com': {
                'job_card': '.jobs-search-results__list-item, .job-search-card, .job-card-container',
                'title': '.job-card-list__title, .job-card-container__link, .job-title',
                'company': '.job-card-container__company-name, .job-card-container__subtitle, .company-name',
                'location': '.job-card-container__metadata-item, .job-card-container__metadata-location, .job-location',
                'date': '.job-card-container__listed-time, .job-search-card__listdate, .job-posted-date',
                'description': '.job-card-container__description, .job-snippet, .job-description',
                'salary': '.job-card-container__salary-info, .job-search-card__salary-info, .salary',
                'skills': '.job-card-container__skills, .job-skill',
                'experience': '.job-experience-level, .experience-level',
                'job_url': '.job-card-list__title, .job-card-container__link'
            }
        }
        # Default site selectors to use if site not found
        self.default_selectors = self.selectors['foundit.in']

    def get_selectors_for_site(self, site):
        """Get the appropriate selectors for a job portal

        Args:
            site (str): Job portal site name or URL

        Returns:
            dict: Selectors for the site
        """
        if not site or not isinstance(site, str):
            return self.default_selectors

        site = site.lower()

        # Check each known site
        for known_site, selectors in self.selectors.items():
            if known_site in site:
                return selectors

        # Default to foundit.in selectors if not found
        return self.default_selectors

    def extract_jobs_from_html(self, html_content, site=None, max_jobs=20):
        """Extract jobs from HTML using BeautifulSoup

        Args:
            html_content (str): HTML content to parse
            site (str): Job portal site name or URL
            max_jobs (int): Maximum number of jobs to extract

        Returns:
            list: List of job dictionaries
        """
        jobs = []

        # Get appropriate selectors
        selectors = self.get_selectors_for_site(site)

        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # First try to extract structured data (JSON-LD)
            structured_jobs = self.extract_structured_data(soup, site)
            if structured_jobs:
                logger.info(f"Extracted {len(structured_jobs)} jobs from structured data")
                return structured_jobs[:max_jobs]

            # If no structured data, try regular HTML parsing
            job_cards = soup.select(selectors['job_card'])
            logger.info(f"Found {len(job_cards)} potential job cards using selector {selectors['job_card']}")

            for card in job_cards[:max_jobs]:
                try:
                    job = {}

                    # Extract title
                    title_elem = card.select_one(selectors['title'])
                    if title_elem:
                        job['title'] = self.clean_text(title_elem.get_text())

                    # Extract company
                    company_elem = card.select_one(selectors['company'])
                    if company_elem:
                        job['company'] = self.clean_text(company_elem.get_text())

                    # Extract location
                    location_elem = card.select_one(selectors['location'])
                    if location_elem:
                        job['location'] = self.clean_text(location_elem.get_text())

                    # Extract date
                    date_elem = card.select_one(selectors['date'])
                    if date_elem:
                        job['date_posted'] = self.clean_text(date_elem.get_text())

                    # Extract description
                    desc_elem = card.select_one(selectors['description'])
                    if desc_elem:
                        job['description'] = self.clean_text(desc_elem.get_text())

                    # Extract salary if available
                    salary_elem = card.select_one(selectors['salary'])
                    if salary_elem:
                        job['salary'] = self.clean_text(salary_elem.get_text())

                    # Extract experience if available
                    exp_elem = card.select_one(selectors['experience'])
                    if exp_elem:
                        job['experience'] = self.clean_text(exp_elem.get_text())

                    # Extract job URL
                    url_elem = card.select_one(selectors['job_url'])
                    if url_elem and url_elem.has_attr('href'):
                        job_url = url_elem['href']
                        # Handle relative URLs
                        if job_url.startswith('/'):
                            # Try to extract domain from site parameter
                            if site and isinstance(site, str) and ('http://' in site or 'https://' in site):
                                parsed_url = urlparse(site)
                                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                job_url = urljoin(base_url, job_url)
                            else:
                                # Fallback to common domains
                                if 'foundit' in str(site).lower():
                                    job_url = f"https://www.foundit.in{job_url}"
                                elif 'indeed' in str(site).lower():
                                    job_url = f"https://www.indeed.com{job_url}"
                                elif 'naukri' in str(site).lower():
                                    job_url = f"https://www.naukri.com{job_url}"
                        job['job_url'] = job_url

                    # Only add job if it has at least title and one other field
                    if job.get('title') and (job.get('company') or job.get('location') or job.get('job_url')):
                        # Add source info
                        job['source'] = self.extract_domain(site) if site else 'Unknown'
                        jobs.append(job)

                except Exception as e:
                    logger.warning(f"Error extracting job data: {str(e)}")

        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")

        return jobs

    def extract_structured_data(self, soup, site=None):
        """Extract jobs from structured data in the HTML

        Args:
            soup (BeautifulSoup): BeautifulSoup object
            site (str): Job portal site name or URL

        Returns:
            list: List of job dictionaries
        """
        jobs = []

        try:
            # Look for JSON-LD script tags
            script_tags = soup.find_all('script', type='application/ld+json')

            for script in script_tags:
                try:
                    if not script.string:
                        continue

                    data = json.loads(script.string)

                    # Check for JobPosting type
                    if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                        job = self.extract_job_from_jsonld(data, site)
                        if job:
                            jobs.append(job)

                    # Check for array of JobPostings
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                job = self.extract_job_from_jsonld(item, site)
                                if job:
                                    jobs.append(job)

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Error processing JSON-LD: {str(e)}")

        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")

        return jobs

    def extract_job_from_jsonld(self, data, site=None):
        """Extract job information from JSON-LD data

        Args:
            data (dict): JSON-LD data
            site (str): Job portal site name or URL

        Returns:
            dict: Job dictionary or None if invalid
        """
        try:
            # Extract basic job info
            job = {
                'title': data.get('title', ''),
                'company': data.get('hiringOrganization', {}).get('name', ''),
                'description': data.get('description', '')
            }

            # Extract location
            if 'jobLocation' in data:
                if isinstance(data['jobLocation'], dict):
                    job['location'] = data['jobLocation'].get('address', {}).get('addressLocality', '')
                elif isinstance(data['jobLocation'], list) and len(data['jobLocation']) > 0:
                    job['location'] = data['jobLocation'][0].get('address', {}).get('addressLocality', '')

            # Extract date posted
            if 'datePosted' in data:
                job['date_posted'] = data['datePosted']

            # Extract job URL
            if 'url' in data:
                job['job_url'] = data['url']

            # Extract salary
            if 'baseSalary' in data:
                salary_data = data['baseSalary']
                if isinstance(salary_data, dict):
                    value = salary_data.get('value', {})
                    if isinstance(value, dict):
                        min_value = value.get('minValue', '')
                        max_value = value.get('maxValue', '')
                        unit = value.get('unitText', '')
                        currency = salary_data.get('currency', '')

                        if min_value and max_value:
                            job['salary'] = f"{currency}{min_value}-{currency}{max_value} {unit}"
                        elif min_value:
                            job['salary'] = f"{currency}{min_value}+ {unit}"

            # Add source info
            job['source'] = self.extract_domain(site) if site else 'Unknown'

            # Only return if we have at least title and one other main field
            if job.get('title') and (job.get('company') or job.get('location') or job.get('job_url')):
                return job

        except Exception as e:
            logger.warning(f"Error extracting job from JSON-LD: {str(e)}")

        return None

    async def extract_jobs_from_page(self, page, site=None, max_jobs=20):
        """Extract jobs from a Playwright page

        Args:
            page: Playwright page object
            site (str): Job portal site name or URL
            max_jobs (int): Maximum number of jobs to extract

        Returns:
            list: List of job dictionaries
        """
        jobs = []

        # Get appropriate selectors
        selectors = self.get_selectors_for_site(site)

        try:
            # Try to find job cards
            job_cards = await page.query_selector_all(selectors['job_card'])
            logger.info(f"Found {len(job_cards)} job cards using Playwright")

            # Process only up to max_jobs
            for card in job_cards[:max_jobs]:
                try:
                    job = {}

                    # Extract title
                    title_elem = await card.query_selector(selectors['title'])
                    if title_elem:
                        job['title'] = await self.get_text_content(title_elem)

                    # Extract company
                    company_elem = await card.query_selector(selectors['company'])
                    if company_elem:
                        job['company'] = await self.get_text_content(company_elem)

                    # Extract location
                    location_elem = await card.query_selector(selectors['location'])
                    if location_elem:
                        job['location'] = await self.get_text_content(location_elem)

                    # Extract date
                    date_elem = await card.query_selector(selectors['date'])
                    if date_elem:
                        job['date_posted'] = await self.get_text_content(date_elem)

                    # Extract description
                    desc_elem = await card.query_selector(selectors['description'])
                    if desc_elem:
                        job['description'] = await self.get_text_content(desc_elem)

                    # Extract salary if available
                    salary_elem = await card.query_selector(selectors['salary'])
                    if salary_elem:
                        job['salary'] = await self.get_text_content(salary_elem)

                    # Extract experience if available
                    exp_elem = await card.query_selector(selectors['experience'])
                    if exp_elem:
                        job['experience'] = await self.get_text_content(exp_elem)

                    # Extract job URL
                    url_elem = await card.query_selector(selectors['job_url'])
                    if url_elem:
                        href = await url_elem.get_attribute('href')
                        if href:
                            # Handle relative URLs
                            if href.startswith('/'):
                                # Try to extract domain from site parameter
                                if site and isinstance(site, str) and ('http://' in site or 'https://' in site):
                                    parsed_url = urlparse(site)
                                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                    href = urljoin(base_url, href)
                                else:
                                    # Fallback to common domains
                                    if 'foundit' in str(site).lower():
                                        href = f"https://www.foundit.in{href}"
                                    elif 'indeed' in str(site).lower():
                                        href = f"https://www.indeed.com{href}"
                                    elif 'naukri' in str(site).lower():
                                        href = f"https://www.naukri.com{href}"
                            job['job_url'] = href

                    # Only add job if it has at least title and one other field
                    if job.get('title') and (job.get('company') or job.get('location') or job.get('job_url')):
                        # Add source info
                        job['source'] = self.extract_domain(site) if site else 'Unknown'
                        jobs.append(job)

                except Exception as e:
                    logger.warning(f"Error extracting job data with Playwright: {str(e)}")

            # If we couldn't extract jobs with selectors, try using HTML content
            if not jobs:
                logger.info("Falling back to HTML extraction")
                html_content = await page.content()
                jobs = self.extract_jobs_from_html(html_content, site, max_jobs)

        except Exception as e:
            logger.error(f"Error extracting jobs with Playwright: {str(e)}")
            # Try HTML extraction as fallback
            try:
                html_content = await page.content()
                jobs = self.extract_jobs_from_html(html_content, site, max_jobs)
            except Exception as html_err:
                logger.error(f"HTML fallback also failed: {str(html_err)}")

        return jobs

    async def get_text_content(self, element):
        """Safely get text content from a Playwright element

        Args:
            element: Playwright element

        Returns:
            str: Cleaned text content
        """
        try:
            text = await element.text_content()
            return self.clean_text(text)
        except Exception:
            return ""

    def clean_text(self, text):
        """Clean up text by removing excess whitespace

        Args:
            text (str): Text to clean

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def extract_domain(self, url):
        """Extract domain from URL

        Args:
            url (str): URL to extract domain from

        Returns:
            str: Domain name
        """
        if not url:
            return "Unknown"

        try:
            # Handle if it's just a domain name without http
            if not url.startswith('http'):
                if '/' in url:
                    return url.split('/')[0]
                return url

            # Parse URL and get domain
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain
        except Exception:
            return "Unknown"

    async def enhance_jobs_with_gpt(self, jobs):
        """Use GPT to enhance job descriptions and extract key information

        Args:
            jobs (list): List of job dictionaries

        Returns:
            list: Enhanced job dictionaries
        """
        if not openai_client:
            logger.warning("OpenAI client not available. Skipping GPT enhancements.")
            return jobs

        enhanced_jobs = []

        for job in jobs:
            try:
                # Only process jobs with descriptions
                if job.get('description'):
                    # Create prompt for GPT
                    prompt = f"""Extract key information from this job posting and enhance the description:

                    Title: {job.get('title', 'Not provided')}
                    Company: {job.get('company', 'Not provided')}
                    Location: {job.get('location', 'Not provided')}
                    Description: {job.get('description', 'Not provided')}

                    Please extract the following information:
                    1. Required Skills (as a comma-separated list)
                    2. Experience Level (e.g., Entry, Mid, Senior)
                    3. Job Type (e.g., Full-time, Part-time, Contract)
                    4. Salary Range (if mentioned)
                    5. A concise, improved job description (max 200 words)

                    Format your response as JSON with the following keys: skills, experience_level, job_type, salary_range, improved_description
                    """

                    # Call OpenAI API
                    response = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=500,
                        n=1
                    )

                    # Parse the response
                    gpt_response = response.choices[0].message.content.strip()

                    # Extract JSON from the response
                    match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
                    if match:
                        gpt_json = json.loads(match.group(0))

                        # Enhance the job with GPT-extracted information
                        job['skills'] = gpt_json.get('skills', '')
                        job['experience_level'] = gpt_json.get('experience_level', '')
                        job['job_type'] = gpt_json.get('job_type', '')

                        # Only add salary if not already present
                        if not job.get('salary') and gpt_json.get('salary_range'):
                            job['salary'] = gpt_json.get('salary_range', '')

                        # Replace description with improved version if available
                        if gpt_json.get('improved_description'):
                            job['description'] = gpt_json.get('improved_description')

            except Exception as e:
                logger.warning(f"Error enhancing job with GPT: {str(e)}")

            enhanced_jobs.append(job)

        return enhanced_jobs

    def clean_text(self, text):
        """
        Clean and normalize text
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters
        text = re.sub(r'[^\w\s\-\.,]', '', text)
        
        return text
        
    def extract_salary(self, description):
        """
        Extract salary information from job description
        
        Args:
            description (str): Job description
            
        Returns:
            str: Extracted salary information or empty string
        """
        if not description:
            return ""
            
        # Common salary patterns in Indian job listings
        patterns = [
            r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(lpa|lakh|lakhs|L|LPA)',
            r'(\d+\.?\d*)\s*(lpa|lakh|lakhs|L|LPA)',
            r'₹\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)',
            r'₹\s*(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return ""
        
    def extract_experience(self, description):
        """
        Extract experience requirements from job description
        
        Args:
            description (str): Job description
            
        Returns:
            str: Extracted experience information or empty string
        """
        if not description:
            return ""
            
        # Common experience patterns
        patterns = [
            r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(years|yrs)',
            r'(\d+\.?\d*)\s*(years|yrs)',
            r'(\d+\.?\d*)\s*\+\s*(years|yrs)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return ""
        
    def normalize_job_data(self, job_data):
        """
        Normalize job data fields
        
        Args:
            job_data (dict): Raw job data
            
        Returns:
            dict: Normalized job data
        """
        # Create a copy to avoid modifying the original
        normalized = job_data.copy()
        
        # Ensure all expected fields exist
        expected_fields = ["title", "company", "location", "date", "link", "salary", "experience"]
        for field in expected_fields:
            if field not in normalized:
                normalized[field] = ""
                
        # Clean text fields
        for field in ["title", "company", "location", "date"]:
            if field in normalized:
                normalized[field] = self.clean_text(normalized[field])
                
        # Normalize link (ensure it's absolute)
        if "link" in normalized and normalized["link"]:
            if not urlparse(normalized["link"]).netloc:
                # This is a relative URL, we need a base URL to make it absolute
                normalized["link"] = normalized["link"]  # Can't normalize without base URL
                
        return normalized
        
    def extract_from_html(self, html, selectors):
        """
        Extract job data from HTML using selectors
        
        Args:
            html (str): HTML content
            selectors (dict): CSS selectors for each field
            
        Returns:
            list: List of extracted job data
        """
        # This is a placeholder for potential direct HTML parsing
        # In practice, we're using Playwright's element handling in browser_executor.py
        logger.warning("Direct HTML parsing not implemented - use browser_executor instead")
        return []
