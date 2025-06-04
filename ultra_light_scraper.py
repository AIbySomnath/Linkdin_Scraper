"""
Ultra lightweight scraper that uses minimal requests to avoid detection
"""
import requests
from bs4 import BeautifulSoup
import logging
import random
import time
import json
import re
from urllib.parse import quote, urlencode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraLightScraper:
    """Ultra lightweight scraper designed to bypass anti-scraping measures"""
    
    def __init__(self):
        # User agent rotation to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        ]
        # Add delay between requests to avoid rate limiting
        self.delay_range = (1, 3)
        # Set timeout for requests
        self.timeout = 30
        # Maximum retries for failed requests
        self.max_retries = 2
        
    def _get_random_headers(self):
        """Get random headers to avoid detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    def scrape_jobs(self, search_term, location="", site=None, max_jobs=20):
        """Scrape jobs from the specified site using ultra lightweight approach
        
        Args:
            search_term (str): Job search term
            location (str): Job location
            site (str): Job portal (foundit.in, indeed.com, naukri.com)
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        logger.info(f"Using ultra lightweight scraper for {site if site else 'unknown site'} with search={search_term}, location={location}")
        
        jobs = []
        
        # Make sure site is a string before using string methods
        if site is None:
            site = "foundit.in"  # Default site
        
        if isinstance(site, bool):
            logger.warning(f"Site parameter is a boolean ({site}), using default site")
            site = "foundit.in"  # Use default site instead of converting boolean to string
        elif not isinstance(site, str):
            logger.warning(f"Site parameter is not a string ({type(site).__name__}), converting to string")
            site = str(site)
        
        if "foundit" in site.lower() or "monster" in site.lower():
            jobs = self._scrape_foundit(search_term, location, max_jobs)
        elif "indeed" in site.lower():
            jobs = self._scrape_indeed(search_term, location, max_jobs)
        elif "naukri" in site.lower():
            jobs = self._scrape_naukri(search_term, location, max_jobs)
        elif "linkedin" in site.lower():
            jobs = self._scrape_linkedin(search_term, location, max_jobs)
        else:
            logger.warning(f"Unsupported site for ultra lightweight scraper: {site}")
            # Default to foundit.in
            jobs = self._scrape_foundit(search_term, location, max_jobs)
        
        logger.info(f"Found {len(jobs)} jobs with ultra lightweight scraper")
        return jobs
    
    def _make_request(self, url, max_retries=None):
        """Make a request with built-in retries and random delays"""
        if max_retries is None:
            max_retries = self.max_retries
            
        logger.info(f"Attempting ultra light scraping from: {url}")
        
        for attempt in range(max_retries + 1):
            try:
                # Add random delay between requests
                if attempt > 0:
                    delay = random.uniform(*self.delay_range)
                    time.sleep(delay)
                
                # Get random headers
                headers = self._get_random_headers()
                
                # Make the request
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Request failed with status code {response.status_code} (attempt {attempt+1}/{max_retries+1})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error: {str(e)} (attempt {attempt+1}/{max_retries+1})")
                
            # If this was the last attempt, return None
            if attempt == max_retries:
                return None
    
    def _clean_text(self, text):
        """Clean text by removing excess whitespace and newlines"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _extract_structured_data(self, soup):
        """Extract structured job data from JSON-LD or other structured data formats"""
        jobs = []
        
        # Look for JSON-LD structured data
        script_tags = soup.find_all('script', {'type': 'application/ld+json'})
        for script in script_tags:
            try:
                if not script.string:
                    continue
                    
                data = json.loads(script.string)
                
                # Check for JobPosting schema
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    job = {
                        'title': data.get('title', ''),
                        'company': data.get('hiringOrganization', {}).get('name', ''),
                        'location': data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                        'posted_date': data.get('datePosted', ''),
                        'source': 'Structured Data',
                        'description': data.get('description', '')[:200] + '...' if data.get('description') else ''
                    }
                    jobs.append(job)
                # Check for array of JobPostings
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            job = {
                                'title': item.get('title', ''),
                                'company': item.get('hiringOrganization', {}).get('name', ''),
                                'location': item.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                                'posted_date': item.get('datePosted', ''),
                                'source': 'Structured Data',
                                'description': item.get('description', '')[:200] + '...' if item.get('description') else ''
                            }
                            jobs.append(job)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error parsing structured data: {str(e)}")
                continue
                
        return jobs
    
    def _scrape_foundit(self, search_term, location="", max_jobs=20):
        """Ultra simple scraping for Foundit.in (formerly Monster India)"""
        jobs = []
        
        # Build the search URL
        base_url = "https://www.foundit.in/srp/results"
        params = {
            'searchType': 'personalizedSearch',
            'keyword': search_term,
            'location': location,
            'sort': 'r'
        }
        search_url = f"{base_url}?{urlencode(params)}"
        
        # Make the request
        response = self._make_request(search_url)
        if not response:
            logger.warning(f"Failed to get response from Foundit")
            return jobs
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # First try to extract structured data
        structured_jobs = self._extract_structured_data(soup)
        if structured_jobs:
            logger.info(f"Found {len(structured_jobs)} structured job listings from Foundit")
            jobs.extend(structured_jobs[:max_jobs])
            if len(jobs) >= max_jobs:
                return jobs[:max_jobs]
        
        # Try various selectors to find job cards
        selectors = [
            '.card-apply-content',  # Main job card container
            '.job-titles',          # Job title container
            '.job-tittle',          # Alternative spelling
            '.card'                 # Generic card
        ]
        
        for selector in selectors:
            job_cards = soup.select(selector)
            if job_cards:
                logger.info(f"Found {len(job_cards)} job cards using selector '{selector}'")
                for card in job_cards[:max_jobs - len(jobs)]:
                    try:
                        # Extract job details using flexible selectors
                        title_elem = card.select_one('.job-title, h3, .title')
                        company_elem = card.select_one('.company-name, .subtitle-link, .company')
                        location_elem = card.select_one('.location-link, .location, .loc')
                        
                        title = self._clean_text(title_elem.text) if title_elem else 'Unknown Title'
                        company = self._clean_text(company_elem.text) if company_elem else 'Unknown Company'
                        job_location = self._clean_text(location_elem.text) if location_elem else location
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'posted_date': 'Recent',
                            'source': 'Foundit.in',
                            'description': 'View job details on Foundit.in'
                        })
                    except Exception as e:
                        logger.warning(f"Error processing job card: {str(e)}")
                    
                    if len(jobs) >= max_jobs:
                        return jobs
        
        # If still no jobs found, try more generic extraction
        if not jobs:
            # Look for any element containing job-related keywords
            potential_job_elements = soup.find_all(['div', 'section', 'article'], 
                                               class_=lambda c: c and any(term in c.lower() 
                                                                        for term in ['job', 'card', 'result', 'listing']))
            
            logger.info(f"Found {len(potential_job_elements)} potential job elements using generic search")
            
            for element in potential_job_elements[:max_jobs]:
                try:
                    # Extract text that looks like a job title (usually in headings)
                    title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                    title = self._clean_text(title_elem.text) if title_elem else 'Job Opening'
                    
                    # Look for company and location in paragraphs or spans
                    company = 'Unknown Company'
                    job_location = location or 'Various Locations'
                    
                    for p in element.find_all(['p', 'span', 'div']):
                        text = self._clean_text(p.text)
                        if text and len(text) < 50:  # Likely to be company or location, not description
                            if any(loc_term in text.lower() for loc_term in ['location', 'address', 'remote', 'work from']):
                                job_location = text
                            elif any(company_term in text.lower() for company_term in ['company', 'organization', 'employer']):
                                company = text
                    
                    # Only add if we have at least a title
                    if title and title != 'Job Opening':
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'posted_date': 'Recent',
                            'source': 'Foundit.in',
                            'description': 'Job details extracted using lightweight scraper'
                        })
                except Exception as e:
                    logger.warning(f"Error in generic job extraction: {str(e)}")
                
                if len(jobs) >= max_jobs:
                    break
                    
        return jobs
    
    def _scrape_indeed(self, search_term, location="", max_jobs=20):
        """Ultra simple scraping for Indeed.com"""
        jobs = []
        
        # Build the search URL
        base_url = "https://www.indeed.com/jobs"
        params = {
            'q': search_term,
            'l': location,
            'sort': 'date'
        }
        search_url = f"{base_url}?{urlencode(params)}"
        
        # Make the request
        response = self._make_request(search_url)
        if not response:
            logger.warning(f"Failed to get response from Indeed")
            return jobs
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # First try structured data
        structured_jobs = self._extract_structured_data(soup)
        if structured_jobs:
            logger.info(f"Found {len(structured_jobs)} structured job listings from Indeed")
            jobs.extend(structured_jobs[:max_jobs])
            if len(jobs) >= max_jobs:
                return jobs[:max_jobs]
        
        # Try different selectors for job cards
        selectors = [
            '.jobsearch-ResultsList > div',  # Main job card container
            '.job_seen_beacon',              # Job card class
            '.tapItem',                      # Another job card class
            '.job-container'                # Generic job container
        ]
        
        for selector in selectors:
            job_cards = soup.select(selector)
            if job_cards:
                logger.info(f"Found {len(job_cards)} job cards using selector '{selector}'")
                for card in job_cards[:max_jobs - len(jobs)]:
                    try:
                        # Extract job details with flexible selectors
                        title_elem = card.select_one('.jobTitle, .jcs-JobTitle, h2 a, a[data-jk]')
                        company_elem = card.select_one('.companyName, .company-name, .companyInfo a')
                        location_elem = card.select_one('.companyLocation, .location, .job-location')
                        date_elem = card.select_one('.date, .date-posted, .new-job-age, .postDate')
                        
                        title = self._clean_text(title_elem.text) if title_elem else 'Unknown Title'
                        company = self._clean_text(company_elem.text) if company_elem else 'Unknown Company'
                        job_location = self._clean_text(location_elem.text) if location_elem else location
                        posted_date = self._clean_text(date_elem.text) if date_elem else 'Recent'
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'posted_date': posted_date,
                            'source': 'Indeed.com',
                            'description': 'View job details on Indeed.com'
                        })
                    except Exception as e:
                        logger.warning(f"Error processing Indeed job card: {str(e)}")
                    
                    if len(jobs) >= max_jobs:
                        return jobs
        
        # If still no jobs, try generic approach
        if not jobs:
            # Look for mosaic jobs (another Indeed format)
            mosaic_jobs = soup.find_all('td', class_='resultContent')
            if mosaic_jobs:
                logger.info(f"Found {len(mosaic_jobs)} mosaic job listings")
                for job in mosaic_jobs[:max_jobs]:
                    try:
                        title_elem = job.select_one('h2.jobTitle span')
                        company_elem = job.select_one('span.companyName')
                        location_elem = job.select_one('div.companyLocation')
                        
                        title = self._clean_text(title_elem.text) if title_elem else 'Unknown Title'
                        company = self._clean_text(company_elem.text) if company_elem else 'Unknown Company'
                        job_location = self._clean_text(location_elem.text) if location_elem else location
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'posted_date': 'Recent',
                            'source': 'Indeed.com',
                            'description': 'View job details on Indeed.com'
                        })
                    except Exception as e:
                        logger.warning(f"Error processing Indeed mosaic job: {str(e)}")
                    
                    if len(jobs) >= max_jobs:
                        return jobs
        
        return jobs
    
    def _scrape_naukri(self, search_term, location="", max_jobs=20):
        """Ultra simple scraping for Naukri.com"""
        jobs = []
        
    def _scrape_linkedin(self, search_term, location="", max_jobs=20):
        """Ultra simple scraping for LinkedIn.com"""
        jobs = []
        
        try:
            # Encode the search parameters
            search_term_encoded = quote(search_term)
            location_encoded = quote(location) if location else ""
            
            # Build the search URL
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_term_encoded}&location={location_encoded}&f_TPR=r86400"
            logger.info(f"Attempting LinkedIn scraping from: {search_url}")
            
            # Make request
            response = self._make_request(search_url)
            if not response:
                logger.warning("Failed to get response from LinkedIn")
                return jobs
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First try to extract structured data (JSON-LD)
            script_tags = soup.find_all('script', {'type': 'application/ld+json'})
            for script in script_tags:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        
                        # Check for JobPosting schema
                        if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                            job = {
                                'title': data.get('title', ''),
                                'company': data.get('hiringOrganization', {}).get('name', ''),
                                'location': data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                                'date_posted': data.get('datePosted', ''),
                                'description': data.get('description', '')[:500] + '...' if data.get('description') else '',
                                'url': data.get('url', ''),
                                'source': 'LinkedIn'
                            }
                            jobs.append(job)
                        
                        # Check for array of JobPostings
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                    job = {
                                        'title': item.get('title', ''),
                                        'company': item.get('hiringOrganization', {}).get('name', ''),
                                        'location': item.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                                        'date_posted': item.get('datePosted', ''),
                                        'description': item.get('description', '')[:500] + '...' if item.get('description') else '',
                                        'url': item.get('url', ''),
                                        'source': 'LinkedIn'
                                    }
                                    jobs.append(job)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Error processing LinkedIn JSON-LD: {str(e)}")
            
            # If structured data approach didn't work, try HTML approach
            if not jobs:
                logger.info("Trying HTML parsing approach for LinkedIn")
                
                # Different selectors to try for job cards
                card_selectors = [
                    '.jobs-search-results__list-item',
                    '.job-search-card',
                    '.job-card-container',
                    '.base-card',
                    'div[data-job-id]'
                ]
                
                for selector in card_selectors:
                    job_cards = soup.select(selector)
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} job cards using selector '{selector}'")
                        break
                
                # Process job cards
                for card in job_cards[:max_jobs]:
                    try:
                        # Extract title
                        title_selectors = ['.job-card-list__title', '.base-search-card__title', '.job-card-container__link']
                        title = self._extract_with_selectors(card, title_selectors)
                        
                        # Extract company
                        company_selectors = ['.job-card-container__company-name', '.base-search-card__subtitle']
                        company = self._extract_with_selectors(card, company_selectors)
                        
                        # Extract location
                        location_selectors = ['.job-card-container__metadata-item', '.job-search-card__location']
                        job_location = self._extract_with_selectors(card, location_selectors)
                        
                        # Extract date
                        date_selectors = ['.job-card-container__listed-time', '.job-search-card__listdate']
                        posted_date = self._extract_with_selectors(card, date_selectors)
                        
                        # Extract URL
                        url = None
                        link_selectors = ['a.job-card-container__link', 'a.base-card__full-link', 'a[href*="/jobs/view/"]']
                        for link_selector in link_selectors:
                            link_elem = card.select_one(link_selector)
                            if link_elem and link_elem.has_attr('href'):
                                url = link_elem['href']
                                # Make absolute URL if relative
                                if url.startswith('/'):
                                    url = f"https://www.linkedin.com{url}"
                                break
                        
                        # Only add job if title and (company or location) are available
                        if title and (company or job_location):
                            job = {
                                'title': title,
                                'company': company,
                                'location': job_location if job_location else location,
                                'date_posted': posted_date if posted_date else 'Recent',
                                'url': url,
                                'source': 'LinkedIn'
                            }
                            jobs.append(job)
                            logger.info(f"Extracted LinkedIn job: {title}")
                    except Exception as e:
                        logger.warning(f"Error extracting LinkedIn job data: {str(e)}")
            
            # Last attempt with API-like URL
            if not jobs:
                logger.info("Trying alternative LinkedIn scraping approach")
                try:
                    # This URL might provide JSON data with job listings
                    api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={search_term_encoded}&location={location_encoded}&start=0"
                    api_response = self._make_request(api_url)
                    
                    if api_response:
                        api_soup = BeautifulSoup(api_response.text, 'html.parser')
                        job_cards = api_soup.select('li')
                        
                        for card in job_cards[:max_jobs]:
                            try:
                                # Extract job details
                                title_elem = card.select_one('h3.base-search-card__title')
                                company_elem = card.select_one('h4.base-search-card__subtitle')
                                location_elem = card.select_one('span.job-search-card__location')
                                date_elem = card.select_one('time')
                                link_elem = card.select_one('a.base-card__full-link')
                                
                                title = title_elem.text.strip() if title_elem else None
                                company = company_elem.text.strip() if company_elem else None
                                job_location = location_elem.text.strip() if location_elem else None
                                posted_date = date_elem.text.strip() if date_elem else None
                                url = link_elem['href'] if link_elem and link_elem.has_attr('href') else None
                                
                                if title and (company or job_location):
                                    job = {
                                        'title': title,
                                        'company': company,
                                        'location': job_location if job_location else location,
                                        'date_posted': posted_date if posted_date else 'Recent',
                                        'url': url,
                                        'source': 'LinkedIn'
                                    }
                                    jobs.append(job)
                            except Exception as e:
                                logger.warning(f"Error in alternative LinkedIn scraping: {str(e)}")
                except Exception as e:
                    logger.warning(f"Failed alternative LinkedIn approach: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {str(e)}")
        
        logger.info(f"Found {len(jobs)} jobs from LinkedIn")
        return jobs[:max_jobs]
    
    def _extract_with_selectors(self, element, selectors):
        """Extract text using multiple possible selectors
        
        Args:
            element: BeautifulSoup element to search within
            selectors: List of CSS selectors to try
            
        Returns:
            str: Extracted text or empty string if not found
        """
        for selector in selectors:
            found_elem = element.select_one(selector)
            if found_elem:
                return self._clean_text(found_elem.text)
        return ""
        
        # Build the search URL
        base_url = "https://www.naukri.com/jobapi/v3/search"
        query_parts = []
        if search_term:
            query_parts.append(search_term)
        if location:
            query_parts.append(location)
            
        query = "-".join(query_parts) if query_parts else "jobs"
        search_url = f"{base_url}?keyword={quote(search_term)}&location={quote(location)}&k={quote(search_term)}&l={quote(location)}"
        
        # Special headers for Naukri API
        headers = self._get_random_headers()
        headers.update({
            'appid': '109',
            'systemid': '109',
            'Accept': 'application/json'
        })
        
        try:
            # Try the API approach first
            response = requests.get(search_url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                try:
                    data = response.json()
                    job_listings = data.get('jobDetails', [])
                    
                    logger.info(f"Found {len(job_listings)} jobs from Naukri API")
                    
                    for job in job_listings[:max_jobs]:
                        title = job.get('title', 'Unknown Title')
                        company = job.get('companyName', 'Unknown Company')
                        job_location = job.get('placeholders', {}).get('location', location)
                        experience = job.get('placeholders', {}).get('experience', 'Not specified')
                        posted_date = job.get('formattedDate', 'Recent')
                        description = job.get('jobDescription', '')[:200] + '...' if job.get('jobDescription') else ''
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'experience': experience,
                            'posted_date': posted_date,
                            'source': 'Naukri.com',
                            'description': description
                        })
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Naukri API response as JSON")
        except Exception as e:
            logger.warning(f"Error with Naukri API approach: {str(e)}")
        
        # If API approach didn't work, try regular HTML scraping
        if not jobs:
            # Build regular search URL
            html_search_url = f"https://www.naukri.com/{quote(search_term)}-jobs-in-{quote(location)}"
            
            # Make request
            response = self._make_request(html_search_url)
            if not response:
                logger.warning(f"Failed to get response from Naukri")
                return jobs
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First try structured data
            structured_jobs = self._extract_structured_data(soup)
            if structured_jobs:
                logger.info(f"Found {len(structured_jobs)} structured job listings from Naukri")
                jobs.extend(structured_jobs[:max_jobs])
                if len(jobs) >= max_jobs:
                    return jobs[:max_jobs]
            
            # Try different selectors
            selectors = [
                '.jobTuple',           # Main job card
                '.job-card',           # Alternative job card
                '.job-container',      # Generic container
                'article.jobTupleCard' # Another card format
            ]
            
            for selector in selectors:
                job_cards = soup.select(selector)
                if job_cards:
                    logger.info(f"Found {len(job_cards)} job cards using selector '{selector}'")
                    for card in job_cards[:max_jobs - len(jobs)]:
                        try:
                            # Extract with flexible selectors
                            title_elem = card.select_one('.title, .jobTitle, a.title, .jobTupleHeader a')
                            company_elem = card.select_one('.company, .companyInfo, .subTitle, .companyName')
                            location_elem = card.select_one('.location, .loc, .jobLocation, .locWdth')
                            experience_elem = card.select_one('.experience, .expwdth, .exp')
                            
                            title = self._clean_text(title_elem.text) if title_elem else 'Unknown Title'
                            company = self._clean_text(company_elem.text) if company_elem else 'Unknown Company'
                            job_location = self._clean_text(location_elem.text) if location_elem else location
                            experience = self._clean_text(experience_elem.text) if experience_elem else 'Not specified'
                            
                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': job_location,
                                'experience': experience,
                                'posted_date': 'Recent',
                                'source': 'Naukri.com',
                                'description': 'View job details on Naukri.com'
                            })
                        except Exception as e:
                            logger.warning(f"Error processing Naukri job card: {str(e)}")
                        
                        if len(jobs) >= max_jobs:
                            return jobs
        
        return jobs
