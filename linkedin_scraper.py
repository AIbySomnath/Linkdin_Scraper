"""
LinkedIn Job Scraper - Dedicated scraper for LinkedIn jobs with advanced features
"""
import requests
import json
import time
import random
import re
import os
import csv
import logging
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    """Dedicated LinkedIn job scraper with advanced features"""
    
    def __init__(self):
        """Initialize the LinkedIn scraper"""
        # User agent rotation to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        ]
        # Add delay between requests to avoid rate limiting
        self.delay_range = (2, 5)
        # Set timeout for requests
        self.timeout = 30
        # Maximum retries for failed requests
        self.max_retries = 3
        # LinkedIn job card selectors
        self.selectors = {
            'job_card': '.jobs-search-results__list-item, .job-search-card, .job-card-container, .base-card',
            'title': '.job-card-list__title, .base-search-card__title, .job-card-container__link',
            'company': '.job-card-container__company-name, .base-search-card__subtitle',
            'location': '.job-card-container__metadata-item, .job-search-card__location',
            'date': '.job-card-container__listed-time, .job-search-card__listdate',
            'description': '.job-card-container__description, .job-snippet',
            'link': 'a.job-card-container__link, a.base-card__full-link'
        }
        
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
    
    def _make_request(self, url, max_retries=None):
        """Make a request with built-in retries and random delays"""
        if max_retries is None:
            max_retries = self.max_retries
            
        retries = 0
        while retries <= max_retries:
            try:
                # Add random delay to avoid detection
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)
                
                # Get random headers
                headers = self._get_random_headers()
                
                # Make the request
                logger.info(f"Making request to: {url}")
                response = requests.get(url, headers=headers, timeout=self.timeout)
                
                # Check if request was successful
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    logger.warning("Rate limited. Waiting longer before retrying...")
                    time.sleep(10 + random.uniform(5, 15))  # Longer delay for rate limiting
                else:
                    logger.warning(f"Request failed with status code: {response.status_code}")
            except Exception as e:
                logger.warning(f"Request error: {str(e)}")
                
            retries += 1
            logger.info(f"Retrying ({retries}/{max_retries})...")
        
        logger.error(f"Failed to make request after {max_retries} retries")
        return None
    
    def _clean_text(self, text):
        """Clean text by removing excess whitespace and newlines"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def scrape_linkedin_jobs(self, search_term, location="", filters=None, max_jobs=20):
        """Scrape LinkedIn jobs with given search parameters
        
        Args:
            search_term (str): Job search term
            location (str): Job location
            filters (dict): Optional filters dict with keys:
                - remote (bool): Filter for remote jobs
                - time_period (str): One of 'day', 'week', 'month'
                - experience (str): One of 'internship', 'entry', 'associate', 'senior', 'director'
                - job_type (str): One of 'full_time', 'part_time', 'contract', 'temporary', 'volunteer'
            max_jobs (int): Maximum number of jobs to return
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        # Handle filters
        filters = filters or {}
        url_params = {
            'keywords': search_term,
            'location': location,
        }
        
        # Time period filter
        time_mapping = {
            'day': 'r86400',  # Past 24 hours
            'week': 'r604800',  # Past week
            'month': 'r2592000'  # Past month
        }
        if filters.get('time_period') in time_mapping:
            url_params['f_TPR'] = time_mapping[filters['time_period']]
        else:
            # Default to past 24 hours
            url_params['f_TPR'] = 'r86400'
        
        # Remote filter
        if filters.get('remote'):
            url_params['f_WT'] = '2'  # Remote
        
        # Experience level filter
        experience_mapping = {
            'internship': '1',
            'entry': '2',
            'associate': '3',
            'senior': '4',
            'director': '5'
        }
        if filters.get('experience') in experience_mapping:
            url_params['f_E'] = experience_mapping[filters['experience']]
        
        # Job type filter
        job_type_mapping = {
            'full_time': 'F',
            'part_time': 'P',
            'contract': 'C',
            'temporary': 'T',
            'volunteer': 'V'
        }
        if filters.get('job_type') in job_type_mapping:
            url_params['f_JT'] = job_type_mapping[filters['job_type']]
        
        # Build the search URL
        base_url = "https://www.linkedin.com/jobs/search/?"
        search_url = base_url + urlencode(url_params)
        
        # Make the initial request
        logger.info(f"Scraping LinkedIn jobs with URL: {search_url}")
        response = self._make_request(search_url)
        
        if not response:
            logger.error("Failed to get response from LinkedIn")
            return []
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # First approach: Try to extract from JSON-LD
        try:
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
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error extracting JSON-LD data: {str(e)}")
        
        # Second approach: Try to extract from HTML
        if not jobs:
            try:
                job_cards = soup.select(self.selectors['job_card'])
                logger.info(f"Found {len(job_cards)} job cards")
                
                for card in job_cards[:max_jobs]:
                    try:
                        # Extract job details
                        title_elem = card.select_one(self.selectors['title'])
                        company_elem = card.select_one(self.selectors['company'])
                        location_elem = card.select_one(self.selectors['location'])
                        date_elem = card.select_one(self.selectors['date'])
                        link_elem = card.select_one(self.selectors['link'])
                        
                        title = self._clean_text(title_elem.text) if title_elem else ''
                        company = self._clean_text(company_elem.text) if company_elem else ''
                        job_location = self._clean_text(location_elem.text) if location_elem else ''
                        posted_date = self._clean_text(date_elem.text) if date_elem else ''
                        url = link_elem['href'] if link_elem and link_elem.has_attr('href') else ''
                        
                        # Make URL absolute if it's relative
                        if url and url.startswith('/'):
                            url = f"https://www.linkedin.com{url}"
                        
                        # Only add if we have at least a title and company
                        if title and company:
                            job = {
                                'title': title,
                                'company': company,
                                'location': job_location,
                                'date_posted': posted_date,
                                'url': url,
                                'source': 'LinkedIn'
                            }
                            jobs.append(job)
                            logger.info(f"Extracted job: {title} at {company}")
                    except Exception as e:
                        logger.warning(f"Error extracting job card data: {str(e)}")
            except Exception as e:
                logger.error(f"Error parsing HTML: {str(e)}")
        
        # Third approach: API-based scraping
        if not jobs:
            try:
                logger.info("Trying API-based scraping approach")
                api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urlencode(url_params)}&start=0"
                api_response = self._make_request(api_url)
                
                if api_response:
                    api_soup = BeautifulSoup(api_response.text, 'html.parser')
                    job_cards = api_soup.select('li')
                    
                    logger.info(f"Found {len(job_cards)} job cards through API")
                    
                    for card in job_cards[:max_jobs]:
                        try:
                            title_elem = card.select_one('h3.base-search-card__title')
                            company_elem = card.select_one('h4.base-search-card__subtitle')
                            location_elem = card.select_one('.job-search-card__location')
                            date_elem = card.select_one('time')
                            link_elem = card.select_one('a.base-card__full-link')
                            
                            title = self._clean_text(title_elem.text) if title_elem else ''
                            company = self._clean_text(company_elem.text) if company_elem else ''
                            job_location = self._clean_text(location_elem.text) if location_elem else ''
                            posted_date = self._clean_text(date_elem.text) if date_elem else ''
                            url = link_elem['href'] if link_elem and link_elem.has_attr('href') else ''
                            
                            if title and company:
                                job = {
                                    'title': title,
                                    'company': company,
                                    'location': job_location,
                                    'date_posted': posted_date,
                                    'url': url,
                                    'source': 'LinkedIn'
                                }
                                jobs.append(job)
                                logger.info(f"Extracted job from API: {title}")
                        except Exception as e:
                            logger.warning(f"Error extracting API job data: {str(e)}")
            except Exception as e:
                logger.error(f"Error with API approach: {str(e)}")
        
        # If we still don't have enough jobs, try pagination
        if len(jobs) < max_jobs and len(jobs) > 0:
            try:
                # LinkedIn pagination is by 25 jobs
                start_val = 25
                while len(jobs) < max_jobs and start_val < 1000:  # Cap at 1000 to avoid too many requests
                    # Modify URL for pagination
                    pagination_params = url_params.copy()
                    pagination_params['start'] = start_val
                    pagination_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urlencode(pagination_params)}"
                    
                    logger.info(f"Making pagination request: start={start_val}")
                    pagination_response = self._make_request(pagination_url)
                    
                    if not pagination_response or pagination_response.status_code != 200:
                        logger.warning(f"Pagination failed at start={start_val}")
                        break
                    
                    pagination_soup = BeautifulSoup(pagination_response.text, 'html.parser')
                    page_job_cards = pagination_soup.select('li')
                    
                    if not page_job_cards:
                        logger.info("No more job cards found in pagination")
                        break
                    
                    logger.info(f"Found {len(page_job_cards)} more job cards at start={start_val}")
                    
                    for card in page_job_cards:
                        if len(jobs) >= max_jobs:
                            break
                            
                        try:
                            title_elem = card.select_one('h3.base-search-card__title')
                            company_elem = card.select_one('h4.base-search-card__subtitle')
                            location_elem = card.select_one('.job-search-card__location')
                            date_elem = card.select_one('time')
                            link_elem = card.select_one('a.base-card__full-link')
                            
                            title = self._clean_text(title_elem.text) if title_elem else ''
                            company = self._clean_text(company_elem.text) if company_elem else ''
                            job_location = self._clean_text(location_elem.text) if location_elem else ''
                            posted_date = self._clean_text(date_elem.text) if date_elem else ''
                            url = link_elem['href'] if link_elem and link_elem.has_attr('href') else ''
                            
                            if title and company:
                                job = {
                                    'title': title,
                                    'company': company,
                                    'location': job_location,
                                    'date_posted': posted_date,
                                    'url': url,
                                    'source': 'LinkedIn'
                                }
                                jobs.append(job)
                        except Exception as e:
                            logger.warning(f"Error extracting pagination job data: {str(e)}")
                    
                    # Increment pagination
                    start_val += 25
            except Exception as e:
                logger.error(f"Error during pagination: {str(e)}")
        
        # Log the results
        logger.info(f"Successfully scraped {len(jobs)} jobs from LinkedIn")
        return jobs[:max_jobs]
    
    def save_to_csv(self, jobs, filename=None):
        """Save job listings to CSV file
        
        Args:
            jobs (list): List of job dictionaries
            filename (str): Output CSV filename (defaults to linkedin_jobs_{date}.csv)
            
        Returns:
            str: Path to saved CSV file
        """
        if not jobs:
            logger.warning("No jobs to save to CSV")
            return None
        
        if not filename:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"linkedin_jobs_{date_str}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Determine all possible fields from the jobs
                fieldnames = set()
                for job in jobs:
                    fieldnames.update(job.keys())
                fieldnames = sorted(list(fieldnames))
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for job in jobs:
                    writer.writerow(job)
            
            logger.info(f"Successfully saved {len(jobs)} jobs to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return None
    
    def scrape_job_details(self, job_url):
        """Scrape detailed information for a specific job
        
        Args:
            job_url (str): URL of the LinkedIn job posting
            
        Returns:
            dict: Detailed job information
        """
        if not job_url:
            logger.error("No job URL provided")
            return {}
        
        # Make sure URL is absolute
        if not job_url.startswith('http'):
            job_url = f"https://www.linkedin.com{job_url}"
        
        # Make request to job page
        response = self._make_request(job_url)
        if not response:
            logger.error(f"Failed to fetch job details from {job_url}")
            return {}
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        job_details = {}
        
        # Try to extract from JSON-LD first (most reliable)
        try:
            script_tags = soup.find_all('script', {'type': 'application/ld+json'})
            for script in script_tags:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                        job_details = {
                            'title': data.get('title', ''),
                            'company': data.get('hiringOrganization', {}).get('name', ''),
                            'company_url': data.get('hiringOrganization', {}).get('sameAs', ''),
                            'location': data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                            'date_posted': data.get('datePosted', ''),
                            'valid_through': data.get('validThrough', ''),
                            'employment_type': data.get('employmentType', ''),
                            'description': data.get('description', ''),
                            'qualifications': data.get('skills', []),
                            'source': 'LinkedIn',
                            'url': job_url
                        }
                        
                        # Extract salary if available
                        if 'baseSalary' in data:
                            salary = data['baseSalary']
                            if isinstance(salary, dict):
                                min_val = salary.get('value', {}).get('minValue', '')
                                max_val = salary.get('value', {}).get('maxValue', '')
                                currency = salary.get('currency', '')
                                if min_val and max_val:
                                    job_details['salary_range'] = f"{currency}{min_val} - {currency}{max_val}"
                                elif min_val:
                                    job_details['salary_range'] = f"{currency}{min_val}+"
                        
                        return job_details
        except Exception as e:
            logger.warning(f"Error extracting JSON-LD job details: {str(e)}")
        
        # If JSON-LD approach failed, try HTML scraping
        try:
            # Title
            title_elem = soup.select_one('.top-card-layout__title')
            if title_elem:
                job_details['title'] = self._clean_text(title_elem.text)
            
            # Company
            company_elem = soup.select_one('.topcard__org-name-link')
            if company_elem:
                job_details['company'] = self._clean_text(company_elem.text)
                if company_elem.has_attr('href'):
                    job_details['company_url'] = f"https://www.linkedin.com{company_elem['href']}"
            
            # Location
            location_elem = soup.select_one('.topcard__flavor--bullet')
            if location_elem:
                job_details['location'] = self._clean_text(location_elem.text)
            
            # Posted date
            date_elem = soup.select_one('.posted-time-ago__text, .topcard__flavor--metadata:nth-child(2)')
            if date_elem:
                job_details['date_posted'] = self._clean_text(date_elem.text)
            
            # Job description
            desc_elem = soup.select_one('.description__text')
            if desc_elem:
                job_details['description'] = self._clean_text(desc_elem.text)
            
            # Employment type
            job_criteria_elements = soup.select('.description__job-criteria-item')
            for elem in job_criteria_elements:
                header_elem = elem.select_one('.description__job-criteria-subheader')
                text_elem = elem.select_one('.description__job-criteria-text')
                if header_elem and text_elem:
                    header = self._clean_text(header_elem.text).lower()
                    text = self._clean_text(text_elem.text)
                    
                    if 'employment type' in header:
                        job_details['employment_type'] = text
                    elif 'experience' in header:
                        job_details['experience'] = text
                    elif 'industry' in header:
                        job_details['industry'] = text
                    elif 'job functions' in header:
                        job_details['job_functions'] = text
            
            # Add source and URL
            job_details['source'] = 'LinkedIn'
            job_details['url'] = job_url
        except Exception as e:
            logger.error(f"Error extracting HTML job details: {str(e)}")
        
        return job_details


# Example usage
if __name__ == "__main__":
    scraper = LinkedInScraper()
    
    # Example 1: Simple search
    jobs = scraper.scrape_linkedin_jobs(
        search_term="Python Developer",
        location="London",
        max_jobs=10
    )
    
    # Example 2: Search with filters
    jobs_with_filters = scraper.scrape_linkedin_jobs(
        search_term="Data Scientist",
        location="New York",
        filters={
            'remote': True,
            'time_period': 'week',
            'experience': 'senior',
            'job_type': 'full_time'
        },
        max_jobs=10
    )
    
    # Example 3: Get detailed information for a specific job
    if jobs:
        first_job_url = jobs[0].get('url')
        if first_job_url:
            job_details = scraper.scrape_job_details(first_job_url)
            print(f"Detailed job info for {job_details.get('title', 'Unknown job')}:")
            for key, value in job_details.items():
                print(f"  {key}: {value}")
    
    # Save results to CSV
    if jobs:
        csv_file = scraper.save_to_csv(jobs)
        print(f"Jobs saved to: {csv_file}")
