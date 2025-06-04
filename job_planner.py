"""
Job Planner - Converts natural language job search queries into structured scraping plans
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class JobPlanner:
    """
    Uses GPT to convert natural language job query into structured scraping plan
    """
    
    def __init__(self):
        """Initialize the job planner"""
        self.supported_sites = ["foundit.in", "indeed.com", "naukri.com", "linkedin.com"]
        
    def parse_query(self, user_prompt):
        """
        Parse a user query into structured components
        
        Args:
            user_prompt (str): Natural language job search query
            
        Returns:
            tuple: (search_term, location, site, days, is_remote)
        """
        # Use create_plan to get the structured data
        plan = self.create_plan(user_prompt)
        
        # Extract the components
        search_term = plan.get('search', '')
        location = plan.get('location', '')
        site = plan.get('site', 'foundit.in')
        
        # Extract days and remote from filters
        days = None
        is_remote = False
        
        for filter_item in plan.get('filters', []):
            filter_lower = filter_item.lower()
            if 'remote' in filter_lower:
                is_remote = True
            elif 'days' in filter_lower or 'week' in filter_lower:
                # Try to extract number
                try:
                    days_str = ''.join(c for c in filter_lower if c.isdigit())
                    if days_str:
                        days = int(days_str)
                except ValueError:
                    pass
        
        # Clean up the site string
        for supported_site in self.supported_sites:
            if supported_site in site.lower():
                site = supported_site
                break
        
        return search_term, location, site, days, is_remote
    
    def create_plan(self, user_prompt=None, search_term=None, location=None, site=None, days=None, is_remote=False):
        """
        Convert query parameters into structured scraping plan
        
        Args:
            user_prompt (str, optional): Natural language job search query
            search_term (str, optional): Job search term (keyword)
            location (str, optional): Location to search in
            site (str, optional): Job portal to use
            days (int, optional): Number of days to filter by
            is_remote (bool, optional): Whether to filter for remote jobs
            
        Returns:
            dict: Structured scraping plan
        """
        try:
            # Define the system prompt for GPT
            system_prompt = f"""
            You are a job search planning assistant. Convert the user's natural language job search query 
            into a structured scraping plan JSON object.
            
            Supported sites: {', '.join(self.supported_sites)}
            
            The plan should include:
            1. site (URL of job portal to search)
            2. search (search term)
            3. location (location to search in)
            4. filters (list of filters to apply)
            5. fields (list of fields to extract)
            
            Example input: "Scrape remote AI jobs in Pune from Foundit.in posted in last 7 days"
            
            Example output:
            {{
                "site": "https://www.foundit.in",
                "search": "AI jobs",
                "location": "Pune",
                "filters": ["Remote", "Last 7 days"],
                "fields": ["title", "company", "location", "date", "link"]
            }}
            
            Only respond with the JSON plan, nothing else.
            """
            
            # Call GPT to create the plan
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            # Extract and parse the JSON plan
            plan_text = response.choices[0].message.content.strip()
            
            # Remove any markdown code block indicators if present
            if plan_text.startswith("```json"):
                plan_text = plan_text.replace("```json", "", 1)
            if plan_text.endswith("```"):
                plan_text = plan_text.replace("```", "", 1)
                
            plan = json.loads(plan_text.strip())
            
            # Ensure required fields are present
            required_fields = ["site", "search", "location", "filters", "fields"]
            for field in required_fields:
                if field not in plan:
                    if field == "filters":
                        plan[field] = []
                    elif field == "fields":
                        plan[field] = ["title", "company", "location", "date", "link"]
                    else:
                        plan[field] = ""
            
            return plan
            
        except Exception as e:
            print(f"Error creating plan: {str(e)}")
            # If we have individual parameters, create a plan from them directly
            if search_term is not None:
                # Direct parameters were provided, construct plan from them
                filters = []
                if days:
                    filters.append(f"Last {days} days")
                if is_remote:
                    filters.append("Remote")
                
                # Determine site URL
                site_url = "https://www.foundit.in"
                if site:
                    # Ensure site is a string
                    site_str = str(site) if site is not None else ""
                    
                    for supported_site in self.supported_sites:
                        if site_str and supported_site in site_str.lower():
                            site_url = f"https://www.{supported_site}"
                            break
                
                return {
                    "site": site_url,
                    "search": search_term,
                    "location": location or "",
                    "filters": filters,
                    "fields": ["title", "company", "location", "date", "link"]
                }
            else:
                # Return a default plan in case of error
                return {
                    "site": "https://www.foundit.in",
                    "search": user_prompt or "",
                    "location": "",
                    "filters": [],
                    "fields": ["title", "company", "location", "date", "link"]
                }
    
    def get_site_details(self, site_url):
        """
        Get site-specific scraping details
        
        Args:
            site_url (str): URL of the job portal
            
        Returns:
            dict: Site-specific details for scraping
        """
        site_configs = {
            "foundit.in": {
                "search_url": "https://www.foundit.in/srp/results",
                "search_param": "searchKey",
                "location_param": "locations",
                "selectors": {
                    "job_card": ".card-panel, [data-job-id], .job-container, div[class*='job-'], div[id*='job-']",
                    "title": ".job-tittle h3, .job-title, h2.title, a.title, .position-title, [class*='jobtitle'], [class*='job-title']",
                    "company": ".company-name, .company, .employer, .organization, [class*='company'], [class*='employer']",
                    "location": ".loc-link, .location, .job-location, [class*='location']",
                    "date": ".posted-update, .date, .posted-date, [class*='date'], [class*='posted']",
                    "link": ".job-tittle h3 a, .job-title a, .title a, a.title, a[href*='job'], a[href*='career'], a.view-details"
                },
                "filters": {
                    "Remote": ".remote-filter, input[value*='remote'], [aria-label*='Remote'], [data-filter*='remote']",
                    "Last 7 days": "input[value='7'], [data-filter-days='7'], [data-value='7'], [aria-label*='7 days']",
                    "Last 15 days": "input[value='15'], [data-filter-days='15'], [data-value='15'], [aria-label*='15 days']",
                    "Last 30 days": "input[value='30'], [data-filter-days='30'], [data-value='30'], [aria-label*='30 days']"
                }
            },
            "indeed.com": {
                "search_url": "https://www.indeed.com/jobs",
                "search_param": "q",
                "location_param": "l",
                "selectors": {
                    "job_card": ".job_seen_beacon, .jobsearch-ResultsList > div, .tapItem, [class*='job_'], [data-testid*='job'], .job-container",
                    "title": ".jobTitle, .job-title, .title, h2[data-testid='jobTitle'], [class*='jobtitle'], a[data-testid*='job-title']",
                    "company": ".companyName, .company-name, .employer, [data-testid='company-name'], [class*='company'], [class*='employer']",
                    "location": ".companyLocation, .location, .job-location, [data-testid='text-location'], [class*='location']",
                    "date": ".date, .date-posted, .posted-date, [data-testid='text-date'], span[class*='date']",
                    "link": ".jobTitle a, .job-title a, a[data-testid*='job-title'], a[href*='job'], a[href*='/viewjob'], .title a"
                },
                "filters": {
                    "Remote": "[data-testid='remote-filter'], input[value*='remote'], button[aria-label*='Remote']",
                    "Last 7 days": "[id='filter-dateposted-7'], [data-testid*='7days'], [value='7'], button[aria-label*='Last 7 days']",
                    "Last 14 days": "[id='filter-dateposted-14'], [data-testid*='14days'], [value='14'], button[aria-label*='Last 14 days']"
                }
            },
            "naukri.com": {
                "search_url": "https://www.naukri.com/jobs-in-india",
                "search_param": "keyword",
                "location_param": "location",
                "selectors": {
                    "job_card": ".jobTuple, .job-tuple, article[data-job-id], .job-card, [class*='job-container'], [class*='jobTuple']",
                    "title": ".title, .job-title, h2.title, a.title, [class*='jobtitle'], [class*='job-title']",
                    "company": ".subTitle, .company-name, .company, [class*='company'], [class*='employer']",
                    "location": ".locWdth, .location, .loc, [class*='location']",
                    "date": ".freshness, .date, .posted-date, [class*='date'], [class*='posted']",
                    "link": ".title a, .job-title a, a.title, a[href*='job-listing']"
                },
                "filters": {
                    "Remote": "input[value='Remote'], input[value*='remote'], [data-filter*='remote'], [aria-label*='Remote']",
                    "Last 7 days": "input[value='1 Week'], [data-filter-days='7'], [data-value='7'], [aria-label*='7 days']",
                    "Last 15 days": "input[value='15 Days'], [data-filter-days='15'], [data-value='15'], [aria-label*='15 days']"
                }
            },
            "linkedin.com": {
                "search_url": "https://www.linkedin.com/jobs/search/",
                "search_param": "keywords",
                "location_param": "location",
                "selectors": {
                    "job_card": ".jobs-search-results__list-item, .job-search-card, .job-card-container, .base-card, .job-card",
                    "title": ".job-card-list__title, .job-card-container__link, .base-search-card__title, .base-card__full-link, .job-title",
                    "company": ".job-card-container__company-name, .base-search-card__subtitle, .job-card-container__primary-description, .company-name",
                    "location": ".job-card-container__metadata-item, .job-search-card__location, .base-search-card__metadata, .job-location",
                    "date": ".job-card-container__listed-time, .job-search-card__listdate, .base-search-card__metadata span:last-child, .job-posted-date",
                    "link": ".job-card-list__title a, .base-card__full-link, a.job-card-container__link"
                },
                "filters": {
                    "Remote": "button[aria-label*='Remote'], button[data-control-name*='remote'], input[value*='remote']",
                    "Last 24 hours": "button[aria-label*='24 hours'], [data-tracking-control-name*='24hours']",
                    "Last 7 days": "button[aria-label*='week'], button[aria-label*='7 days']",
                    "Last 30 days": "button[aria-label*='month'], button[aria-label*='30 days']"
                }
            }
        }
        
        # Determine which site config to use
        for site_name, config in site_configs.items():
            if site_name in site_url.lower():
                return config
        
        # Default to Foundit.in if site not recognized
        return site_configs["foundit.in"]
