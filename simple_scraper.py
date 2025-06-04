"""
Simple Job Scraper - A more direct approach using Beautiful Soup
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv
import os
import time
import json
import logging
from urllib.parse import urlencode, urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleJobScraper:
    """A simple job scraper that uses requests and BeautifulSoup"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_jobs(self, search_term, location="", site="foundit.in", days=None, is_remote=False, max_jobs=20):
        """
        Scrape jobs from the specified job portal
        
        Args:
            search_term (str): Job search term
            location (str): Location for job search
            site (str): Job portal to scrape (foundit.in, indeed.com, naukri.com)
            days (int): Filter by days (7, 15, 30)
            is_remote (bool): Filter for remote jobs
            max_jobs (int): Maximum number of jobs to scrape
            
        Returns:
            list: List of job dictionaries
        """
        # Handle the case where site is not a string (e.g., a boolean)
        if not isinstance(site, str):
            logger.warning(f"Site parameter is a {type(site).__name__} ({site}), converting to string")
            # Default to foundit.in if site is True or not a string
            site = "foundit.in"
            
        # Now site is guaranteed to be a string
        if "foundit" in site.lower():
            return self._scrape_foundit(search_term, location, days, is_remote, max_jobs)
        elif "indeed" in site.lower():
            return self._scrape_indeed(search_term, location, days, is_remote, max_jobs)
        elif "naukri" in site.lower():
            return self._scrape_naukri(search_term, location, days, is_remote, max_jobs)
        else:
            logger.error(f"Unsupported site: {site}")
            return []
    
    def _scrape_foundit(self, search_term, location="", days=None, is_remote=False, max_jobs=20):
        """Scrape jobs from Foundit.in"""
        jobs = []
        
        # Try different URL formats to improve scraping success
        urls_to_try = [
            # Standard search URL
            f"https://www.foundit.in/srp/results?searchKey={str(search_term).replace(' ', '%20')}{f'&locations={str(location).replace(' ', '%20')}' if location else ''}",
            # Alternative search format
            f"https://www.foundit.in/search/{str(search_term).replace(' ', '-')}{f'/{str(location).replace(' ', '-')}' if location else ''}",
            # Jobs by skill
            f"https://www.foundit.in/jobs-by-skill/{str(search_term).replace(' ', '-')}-jobs",
        ]
        
        # Add filters
        filter_params = []
        if days:
            filter_params.append(f"postedDate={days}")
        if is_remote:
            filter_params.append("workFromHome=true")
            
        # Add filters to the URLs
        if filter_params:
            filter_str = "&".join(filter_params)
            urls_to_try = [f"{url}{'&' if '?' in url else '?'}{filter_str}" for url in urls_to_try]
        
        # Try each URL until we get results
        for url_index, search_url in enumerate(urls_to_try):
            logger.info(f"Trying Foundit.in URL {url_index+1}/{len(urls_to_try)}: {search_url}")
            
            try:
                # Try with different headers to avoid anti-scraping measures
                custom_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Referer': 'https://www.foundit.in/'
                }
                
                response = requests.get(search_url, headers=custom_headers)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page: {response.status_code}, trying next URL")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Print page title for debugging
                page_title = soup.title.text if soup.title else "No title"
                logger.info(f"Page title: {page_title}")
                
                # Find job cards - try multiple selector patterns
                selectors_to_try = [
                    '.card-panel', '.card-body', '[data-job-id]',
                    '.jobTuple', '.jobTupleHeader',
                    '.job-container', 'div[class*="job-"]', 'div[id*="job-"]',
                    '.job-card', '.card'
                ]
                
                # Try each selector
                job_cards = []
                for selector in selectors_to_try:
                    cards = soup.select(selector)
                    if cards:
                        logger.info(f"Found {len(cards)} job cards with selector: {selector}")
                        job_cards = cards
                        break
                
                # If still no cards, try a more aggressive approach
                if not job_cards:
                    logger.info("Using aggressive approach to find job cards")
                    # Find all divs that contain job-related text
                    all_divs = soup.find_all('div')
                    job_cards = []
                    
                    for div in all_divs:
                        # Check if this div looks like a job card
                        div_text = div.text.lower()
                        if ('apply' in div_text or 'job' in div_text) and ('company' in div_text or 'location' in div_text):
                            # This looks like a job card
                            job_cards.append(div)
                    
                    logger.info(f"Found {len(job_cards)} potential job cards using text analysis")
                
                # Extract job data
                extracted_count = 0
                for card in job_cards[:max_jobs*3]:  # Try more cards to get the requested number of jobs
                    try:
                        # Try different tag and class combinations for job title
                        title_selectors = [
                            'h3', 'h2', 'h4', '.job-tittle h3', '.job-title', 'a.title', 
                            '[class*="title"]', 'a[href*="job"]'
                        ]
                        
                        title_elem = None
                        for selector in title_selectors:
                            elems = card.select(selector)
                            if elems:
                                title_elem = elems[0]
                                break
                        
                        # Skip if no title found
                        if not title_elem or not title_elem.text.strip():
                            continue
                            
                        title = title_elem.text.strip()
                        
                        # Get company name - try different approaches
                        company_selectors = [
                            '.company-name', '.company', '[class*="company"]',
                            'span.subtle-link', 'span[class*="company"]'
                        ]
                        
                        company = ""
                        for selector in company_selectors:
                            company_elem = card.select_one(selector)
                            if company_elem and company_elem.text.strip():
                                company = company_elem.text.strip()
                                break
                        
                        # Try to extract from text if not found
                        if not company:
                            # Look for lines that might contain company name
                            card_lines = [line.strip() for line in card.text.split('\n') if line.strip()]
                            if len(card_lines) > 1 and len(card_lines[1]) < 50:  # Second line is often company name
                                company = card_lines[1]
                        
                        # Get location with multiple selectors
                        location_selectors = [
                            '.loc-link', '.location', '[class*="location"]',
                            'span.loc', 'span.location', 'span[class*="loc"]'
                        ]
                        
                        location = ""
                        for selector in location_selectors:
                            location_elem = card.select_one(selector)
                            if location_elem and location_elem.text.strip():
                                location = location_elem.text.strip()
                                break
                                
                        # Try to extract location from text
                        if not location and company:
                            # Location often follows company name with a separator
                            card_text = card.text
                            company_idx = card_text.find(company)
                            if company_idx > 0:
                                after_company = card_text[company_idx + len(company):]
                                # Look for location pattern after company name
                                for line in after_company.split('\n'):
                                    line = line.strip()
                                    if line and len(line) < 30 and any(city.lower() in line.lower() for city in ['mumbai', 'delhi', 'bangalore', 'hyderabad', 'pune', 'chennai']):
                                        location = line
                                        break
                        
                        # Get date posted
                        date_selectors = [
                            '.posted-update', '.date', '[class*="date"]',
                            'span.date', 'span.posted', 'span[class*="post"]'
                        ]
                        
                        date = ""
                        for selector in date_selectors:
                            date_elem = card.select_one(selector)
                            if date_elem and date_elem.text.strip():
                                date = date_elem.text.strip()
                                break
                                
                        # Try to find date in text
                        if not date:
                            date_patterns = ['posted', 'ago', 'day', 'week', 'month', 'hour']
                            for line in card.text.split('\n'):
                                line = line.strip()
                                if any(pattern in line.lower() for pattern in date_patterns) and len(line) < 30:
                                    date = line
                                    break
                        
                        # Get link - try to find any anchor tag with href
                        link = ""
                        link_selectors = [
                            'a[href*="job-detail"]', 'a[href*="job"]', 'a.view-detail',
                            '.job-title a', 'h3 a', 'h2 a', 'a[class*="title"]', 'a'
                        ]
                        
                        for selector in link_selectors:
                            link_elems = card.select(selector)
                            if link_elems:
                                for link_elem in link_elems:
                                    if 'href' in link_elem.attrs:
                                        link = link_elem['href']
                                        if link.startswith('/'):
                                            link = f"https://www.foundit.in{link}"
                                        break
                                if link:  # If link found, break outer loop
                                    break
                        
                        # Add job to list
                        job = {
                            'title': title,
                            'company': company,
                            'location': location,
                            'date': date,
                            'link': link
                        }
                        
                        # Only add if we have at least title and one other field
                        if title and (company or location or date or link):
                            jobs.append(job)
                            extracted_count += 1
                            logger.info(f"Extracted job {extracted_count}: {title}")
                            
                            # Break if we've reached the requested number
                            if extracted_count >= max_jobs:
                                break
                        
                    except Exception as e:
                        logger.warning(f"Error extracting job data: {str(e)}")
                        continue
                
                # If we found some jobs, return them
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from Foundit.in")
                    return jobs
                    
            except Exception as e:
                logger.error(f"Error scraping Foundit.in URL {url_index+1}: {str(e)}")
                continue
        
        # If we tried all URLs and got no results
        logger.warning("Could not find any jobs on Foundit.in after trying all URLs")
        return []
    
    def _scrape_indeed(self, search_term, location="", days=None, is_remote=False, max_jobs=20):
        """Scrape jobs from Indeed.com"""
        jobs = []
        
        # Try different URL formats to improve scraping success
        urls_to_try = [
            # Standard search URL
            f"https://in.indeed.com/jobs?q={search_term.replace(' ', '+')}{f'&l={location.replace(' ', '+')}' if location else ''}",
            # Alternative domain
            f"https://www.indeed.com/jobs?q={search_term.replace(' ', '+')}{f'&l={location.replace(' ', '+')}' if location else ''}",
            # Job titles search
            f"https://in.indeed.com/jobs?q=title%3A{search_term.replace(' ', '+')}{f'&l={location.replace(' ', '+')}' if location else ''}",
        ]
        
        # Add filters
        filter_params = []
        if days:
            days_map = {7: 1, 14: 3, 30: 7, 90: 30}
            days_val = days_map.get(int(days) if str(days).isdigit() else 7, 7)  # Default to 7 days
            filter_params.append(f"fromage={days_val}")
            
        if is_remote:
            filter_params.append("remotejob=1")
            
        # Add filters to the URLs
        if filter_params:
            filter_str = "&".join(filter_params)
            urls_to_try = [f"{url}{'&' if '?' in url else '?'}{filter_str}" for url in urls_to_try]
        
        # Try each URL until we get results
        for url_index, search_url in enumerate(urls_to_try):
            logger.info(f"Trying Indeed URL {url_index+1}/{len(urls_to_try)}: {search_url}")
            
            try:
                # Use different headers to avoid anti-scraping measures
                custom_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'DNT': '1'
                }
                
                response = requests.get(search_url, headers=custom_headers)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page: {response.status_code}, trying next URL")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Print page title for debugging
                page_title = soup.title.text if soup.title else "No title"
                logger.info(f"Page title: {page_title}")
                
                # Find job cards - try multiple selector patterns
                selectors_to_try = [
                    '.job_seen_beacon', '.jobsearch-ResultsList > div', 
                    '.result', '.job-card', '.jobCard', 
                    '[data-testid="job-card"]', '[data-ui-name="search-result"]',
                    '[class*="job-"]', '[class*="jobCard"]', '[class*="jobsearch-"]'
                ]
                
                # Try each selector
                job_cards = []
                for selector in selectors_to_try:
                    cards = soup.select(selector)
                    if cards:
                        logger.info(f"Found {len(cards)} job cards with selector: {selector}")
                        job_cards = cards
                        break
                
                # If still no cards, try a more aggressive approach
                if not job_cards:
                    logger.info("Using aggressive approach to find job cards")
                    # Find all divs that might be job cards
                    all_divs = soup.find_all(['div', 'li'])
                    job_cards = []
                    
                    for div in all_divs:
                        # Check if this div looks like a job card
                        div_text = div.text.lower() if div.text else ""
                        if div_text and ('apply' in div_text or 'job' in div_text) and len(div_text) > 100 and len(div_text) < 2000:
                            job_cards.append(div)
                    
                    logger.info(f"Found {len(job_cards)} potential job cards using text analysis")
                
                # Extract job data
                extracted_count = 0
                for card in job_cards[:max_jobs*3]:  # Try more cards to get the requested number of jobs
                    try:
                        # Try different tag and class combinations for job title
                        title_selectors = [
                            'h2.jobTitle', 'h2[class*="title"]', 'h2 a', 
                            'span.jobtitle', 'a.jobtitle', 'a[data-jk]',
                            '[class*="title"] a', 'h3', 'h2', 'a[href*="job_"]', 'a[href*="jk="]'
                        ]
                        
                        title_elem = None
                        for selector in title_selectors:
                            elems = card.select(selector)
                            if elems:
                                title_elem = elems[0]
                                break
                        
                        # Skip if no title found
                        if not title_elem or not title_elem.text.strip():
                            continue
                            
                        title = title_elem.text.strip()
                        
                        # Get company name - try different approaches
                        company_selectors = [
                            'span.companyName', '[class*="company"]', 'a.company', 
                            '[data-testid="company-name"]', '[class*="employer"]'
                        ]
                        
                        company = ""
                        for selector in company_selectors:
                            company_elem = card.select_one(selector)
                            if company_elem and company_elem.text.strip():
                                company = company_elem.text.strip()
                                break
                        
                        # Get location with multiple selectors
                        location_selectors = [
                            'div.companyLocation', '[class*="location"]', 'span.location', 
                            '[data-testid="text-location"]'
                        ]
                        
                        location = ""
                        for selector in location_selectors:
                            location_elem = card.select_one(selector)
                            if location_elem and location_elem.text.strip():
                                location = location_elem.text.strip()
                                break
                        
                        # Get date posted
                        date_selectors = [
                            'span.date', '[class*="date"]', 'span.resultsJobAttr span', 
                            '[data-testid="text-date"]', '.new'
                        ]
                        
                        date = ""
                        for selector in date_selectors:
                            date_elem = card.select_one(selector)
                            if date_elem and date_elem.text.strip():
                                date = date_elem.text.strip()
                                break
                        
                        # Get link - try to find any anchor tag with href
                        link = ""
                        link_selectors = [
                            'a[href*="clk"]', 'a[href*="jk="]', 'a.jobtitle', 
                            'h2 a', 'a[id*="job"]', 'a[data-jk]', 
                            '.title a', 'a'
                        ]
                        
                        for selector in link_selectors:
                            link_elems = card.select(selector)
                            if link_elems:
                                for link_elem in link_elems:
                                    if 'href' in link_elem.attrs:
                                        link = link_elem['href']
                                        if link.startswith('/'):
                                            link = f"https://in.indeed.com{link}"
                                        break
                                if link:  # If link found, break outer loop
                                    break
                        
                        # Add job to list
                        job = {
                            'title': title,
                            'company': company,
                            'location': location,
                            'date': date,
                            'link': link
                        }
                        
                        # Only add if we have at least title and one other field
                        if title and (company or location or date or link):
                            jobs.append(job)
                            extracted_count += 1
                            logger.info(f"Extracted job {extracted_count}: {title}")
                            
                            # Break if we've reached the requested number
                            if extracted_count >= max_jobs:
                                break
                        
                    except Exception as e:
                        logger.warning(f"Error extracting job data: {str(e)}")
                        continue
                
                # If we found some jobs, return them
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
                    return jobs
                    
            except Exception as e:
                logger.error(f"Error scraping Indeed URL {url_index+1}: {str(e)}")
                continue
        
        # If we tried all URLs and got no results
        logger.warning("Could not find any jobs on Indeed after trying all URLs")
        return []
        
    def _scrape_naukri(self, search_term, location="", days=None, is_remote=False, max_jobs=20):
        """Scrape jobs from Naukri.com"""
        jobs = []
        
        # Try different URL formats to improve scraping success
        urls_to_try = []
        
        # Standard URL format with location
        if location:
            urls_to_try.append(f"https://www.naukri.com/{search_term.replace(' ', '-')}-jobs-in-{location.replace(' ', '-')}")
            urls_to_try.append(f"https://www.naukri.com/jobs-in-{location.replace(' ', '-')}?keyword={search_term.replace(' ', '%20')}")
        else:
            urls_to_try.append(f"https://www.naukri.com/{search_term.replace(' ', '-')}-jobs")
            urls_to_try.append(f"https://www.naukri.com/jobs?keyword={search_term.replace(' ', '%20')}")
        
        # Add keyword URL format
        urls_to_try.append(f"https://www.naukri.com/job-listings-{search_term.replace(' ', '-')}{'-in-' + location.replace(' ', '-') if location else ''}")
        
        # Add filter parameters
        filter_params = []
        if days:
            # Naukri uses different parameters for date filtering
            days_map = {7: "1", 14: "2", 30: "3", 90: "4"}
            days_val = days_map.get(str(days) if isinstance(days, str) else str(int(days)), "1") 
            filter_params.append(f"jobAge={days_val}")
            
        if is_remote:
            filter_params.append("workFromHome=true")
        
        # Apply filters to URLs
        if filter_params:
            filter_str = "&".join(filter_params)
            urls_to_try = [f"{url}{'&' if '?' in url else '?'}{filter_str}" for url in urls_to_try]
        
        # Try each URL until we get results
        for url_index, base_url in enumerate(urls_to_try):
            logger.info(f"Trying Naukri.com URL {url_index+1}/{len(urls_to_try)}: {base_url}")
            
            try:
                # Use different headers to avoid anti-scraping measures
                custom_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(base_url, headers=custom_headers)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page: {response.status_code}, trying next URL")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Print page title for debugging
                page_title = soup.title.text if soup.title else "No title"
                logger.info(f"Page title: {page_title}")
                
                # Try multiple selectors to find job cards
                selectors_to_try = [
                    '.jobTupleHeader', '.job-container', 'article.jobTuple',
                    'div.jobTuple', '.srp-jobtuple', '[class*="jobTuple"]',
                    '[class*="job-"]', '.job-card', 'div[type="tuple"]'
                ]
                
                # Try each selector
                job_cards = []
                for selector in selectors_to_try:
                    cards = soup.select(selector)
                    if cards:
                        logger.info(f"Found {len(cards)} job cards with selector: {selector}")
                        job_cards = cards
                        break
                
                # If still no cards, try a more aggressive approach
                if not job_cards:
                    logger.info("Using aggressive approach to find job cards")
                    # Find all articles and divs that might be job cards
                    all_elements = soup.find_all(['article', 'div'])
                    job_cards = []
                    
                    for elem in all_elements:
                        # Check if this element looks like a job card
                        elem_text = elem.text.lower() if elem.text else ""
                        if elem_text and ('apply' in elem_text or 'job' in elem_text) and len(elem_text) > 100:
                            # This looks like a job card
                            job_cards.append(elem)
                    
                    logger.info(f"Found {len(job_cards)} potential job cards using text analysis")
                
                # Extract job data
                extracted_count = 0
                for card in job_cards[:max_jobs*3]:  # Try more cards to get the requested number of jobs
                    try:
                        # Try different tag and class combinations for job title
                        title_selectors = [
                            '.title', 'a.title', '.jobTitle', '.jdTitle',
                            '[title*="job"]', '[class*="title"]', 'a[href*="job-listing"]',
                            'a[href*="job"]', 'h2', 'h3'
                        ]
                        
                        title_elem = None
                        for selector in title_selectors:
                            elems = card.select(selector)
                            if elems:
                                title_elem = elems[0]
                                break
                        
                        # Skip if no title found
                        if not title_elem or not title_elem.text.strip():
                            continue
                            
                        title = title_elem.text.strip()
                        
                        # Get company name - try different approaches
                        company_selectors = [
                            '.subTitle', '.companyInfo', '.company-name', '.company',
                            '[class*="company"]', '[class*="org"]', '[class*="employer"]'
                        ]
                        
                        company = ""
                        for selector in company_selectors:
                            company_elem = card.select_one(selector)
                            if company_elem and company_elem.text.strip():
                                company = company_elem.text.strip()
                                break
                        
                        # Get location with multiple selectors
                        location_selectors = [
                            '.locWdth', '.location', '.loc', '[class*="location"]',
                            '[class*="loc"]', 'span.loc', 'span[title*="location"]'
                        ]
                        
                        location = ""
                        for selector in location_selectors:
                            location_elem = card.select_one(selector)
                            if location_elem and location_elem.text.strip():
                                location = location_elem.text.strip()
                                break
                        
                        # Get date posted
                        date_selectors = [
                            '.freshness', '.date', '.posted-date', '[class*="date"]',
                            '[class*="posted"]', 'span[class*="day"]'
                        ]
                        
                        date = ""
                        for selector in date_selectors:
                            date_elem = card.select_one(selector)
                            if date_elem and date_elem.text.strip():
                                date = date_elem.text.strip()
                                break
                        
                        # Get link - try to find any anchor tag with href
                        link = ""
                        link_selectors = [
                            'a.title', '.job-title a', 'a[href*="job-listing"]',
                            'a[href*="job"]', 'a.action', 'a.view-detail', 'a'
                        ]
                        
                        for selector in link_selectors:
                            link_elems = card.select(selector)
                            if link_elems:
                                for link_elem in link_elems:
                                    if 'href' in link_elem.attrs:
                                        link = link_elem['href']
                                        if link.startswith('/'):
                                            link = f"https://www.naukri.com{link}"
                                        break
                                if link:  # If link found, break outer loop
                                    break
                        
                        # Add job to list
                        job = {
                            'title': title,
                            'company': company,
                            'location': location,
                            'date': date,
                            'link': link
                        }
                        
                        # Only add if we have at least title and one other field
                        if title and (company or location or date or link):
                            jobs.append(job)
                            extracted_count += 1
                            logger.info(f"Extracted job {extracted_count}: {title}")
                            
                            # Break if we've reached the requested number
                            if extracted_count >= max_jobs:
                                break
                        
                    except Exception as e:
                        logger.warning(f"Error extracting job data: {str(e)}")
                        continue
                
                # If we found some jobs, return them
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from Naukri.com")
                    return jobs
                    
            except Exception as e:
                logger.error(f"Error scraping Naukri URL {url_index+1}: {str(e)}")
                continue
        
        # If we tried all URLs and got no results
        logger.warning("Could not find any jobs on Naukri.com after trying all URLs")
        return []
    
    def save_to_csv(self, jobs, filename="job_listings.csv"):
        """Save job listings to CSV file"""
        if not jobs:
            logger.warning("No jobs to save to CSV")
            return False
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'company', 'location', 'date', 'link']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for job in jobs:
                    writer.writerow(job)
                    
            logger.info(f"Successfully saved {len(jobs)} jobs to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving jobs to CSV: {str(e)}")
            return False
            
# Example usage
if __name__ == "__main__":
    scraper = SimpleJobScraper()
    
    # Example: Scrape remote AI jobs in Pune from Foundit.in
    jobs = scraper.scrape_jobs(
        search_term="AI jobs",
        location="Pune",
        site="foundit.in",
        days=7,
        is_remote=True,
        max_jobs=10
    )
    
    if jobs:
        print(f"Found {len(jobs)} jobs:")
        for i, job in enumerate(jobs):
            print(f"\nJob {i+1}:")
            for key, value in job.items():
                print(f"{key}: {value}")
                
        # Save to CSV
        scraper.save_to_csv(jobs, "ai_jobs_pune.csv")
    else:
        print("No jobs found.")
