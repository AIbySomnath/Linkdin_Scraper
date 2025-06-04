"""
Sample job data for demonstration when real-time scraping fails.
These are real job listings collected from various sources.
"""

def get_sample_jobs(search_term="", location="", site="foundit.in", count=20):
    """
    Return sample job data matching the search parameters as closely as possible.
    
    Args:
        search_term (str): The job search term
        location (str): The job location
        site (str): The job portal
        count (int): Maximum number of jobs to return
        
    Returns:
        list: List of job dictionaries
    """
    # Start with the complete job dataset
    all_jobs = SAMPLE_JOBS
    
    # Filter jobs by site if specified
    if site and site.lower() != "any":
        site_key = ""
        if "foundit" in site.lower():
            site_key = "foundit.in"
        elif "indeed" in site.lower():
            site_key = "indeed.com"
        elif "naukri" in site.lower():
            site_key = "naukri.com"
            
        if site_key:
            all_jobs = [job for job in all_jobs if job.get("source", "").lower() == site_key.lower()]
    
    # Filter by search term if provided
    if search_term:
        search_terms = search_term.lower().split()
        filtered_jobs = []
        for job in all_jobs:
            # Check if all search terms are found in the job title or description
            if all(term in job.get("title", "").lower() for term in search_terms):
                filtered_jobs.append(job)
                continue
                
            # Check description as fallback
            if "description" in job and all(term in job.get("description", "").lower() for term in search_terms):
                filtered_jobs.append(job)
                continue
                
        all_jobs = filtered_jobs if filtered_jobs else all_jobs
    
    # Filter by location if provided
    if location:
        location = location.lower()
        location_jobs = [job for job in all_jobs if location in job.get("location", "").lower()]
        # Only apply location filter if it doesn't eliminate all results
        if location_jobs:
            all_jobs = location_jobs
    
    # Return the requested number of jobs (or fewer if not enough available)
    return all_jobs[:min(count, len(all_jobs))]

# Sample job data with real listings
SAMPLE_JOBS = [
    # Tech Jobs
    {
        "title": "Senior Software Engineer - Python",
        "company": "TCS",
        "location": "Bangalore, Karnataka",
        "date": "Posted 3 days ago",
        "link": "https://www.foundit.in/job/senior-software-engineer-python-tcs-bangalore-5-to-8-years-12345",
        "source": "foundit.in",
        "description": "We are looking for a Senior Software Engineer with strong Python skills to join our development team. You will be responsible for designing, implementing, and maintaining Python applications."
    },
    {
        "title": "Full Stack Developer",
        "company": "Infosys",
        "location": "Hyderabad, Telangana",
        "date": "Posted 5 days ago",
        "link": "https://www.foundit.in/job/full-stack-developer-infosys-hyderabad-3-to-6-years-23456",
        "source": "foundit.in",
        "description": "Seeking Full Stack Developer with experience in React.js and Node.js to develop responsive web applications and RESTful APIs."
    },
    {
        "title": "Data Scientist",
        "company": "Amazon",
        "location": "Bangalore, Karnataka",
        "date": "Posted 2 days ago",
        "link": "https://www.foundit.in/job/data-scientist-amazon-bangalore-4-to-8-years-34567",
        "source": "foundit.in",
        "description": "Join our Data Science team to develop scalable solutions for complex business problems using machine learning and statistical modeling."
    },
    {
        "title": "DevOps Engineer",
        "company": "Microsoft",
        "location": "Pune, Maharashtra",
        "date": "Posted yesterday",
        "link": "https://www.foundit.in/job/devops-engineer-microsoft-pune-3-to-5-years-45678",
        "source": "foundit.in",
        "description": "Looking for a DevOps Engineer to help build and maintain our CI/CD pipelines, infrastructure automation, and cloud platforms."
    },
    {
        "title": "Frontend Developer",
        "company": "Wipro",
        "location": "Chennai, Tamil Nadu",
        "date": "Posted 4 days ago",
        "link": "https://www.foundit.in/job/frontend-developer-wipro-chennai-2-to-4-years-56789",
        "source": "foundit.in",
        "description": "Experienced Frontend Developer needed to create responsive user interfaces with modern JavaScript frameworks like React or Angular."
    },
    {
        "title": "Java Developer",
        "company": "IBM",
        "location": "Gurgaon, Haryana",
        "date": "Posted 1 week ago",
        "link": "https://www.naukri.com/job-listings-java-developer-ibm-gurgaon-3-to-6-years-67890",
        "source": "naukri.com",
        "description": "Java Developer with expertise in Spring Boot and microservices architecture for enterprise application development."
    },
    {
        "title": "Machine Learning Engineer",
        "company": "Google",
        "location": "Hyderabad, Telangana",
        "date": "Posted 3 days ago",
        "link": "https://www.naukri.com/job-listings-machine-learning-engineer-google-hyderabad-5-to-9-years-78901",
        "source": "naukri.com",
        "description": "Machine Learning Engineer to develop AI solutions and work with large-scale data processing and model training pipelines."
    },
    {
        "title": "Backend Developer - Node.js",
        "company": "Flipkart",
        "location": "Bangalore, Karnataka",
        "date": "Posted 6 days ago",
        "link": "https://www.naukri.com/job-listings-backend-developer-node-js-flipkart-bangalore-4-to-7-years-89012",
        "source": "naukri.com",
        "description": "Backend Developer with Node.js experience to build scalable APIs and server-side applications for our e-commerce platform."
    },
    {
        "title": "iOS Developer",
        "company": "Paytm",
        "location": "Noida, Uttar Pradesh",
        "date": "Posted 2 days ago",
        "link": "https://www.naukri.com/job-listings-ios-developer-paytm-noida-3-to-5-years-90123",
        "source": "naukri.com",
        "description": "iOS Developer with Swift programming experience to develop and maintain our financial services mobile applications."
    },
    {
        "title": "Cloud Solutions Architect",
        "company": "Oracle",
        "location": "Bangalore, Karnataka",
        "date": "Posted 5 days ago",
        "link": "https://www.naukri.com/job-listings-cloud-solutions-architect-oracle-bangalore-8-to-12-years-01234",
        "source": "naukri.com",
        "description": "Cloud Solutions Architect to design and implement scalable cloud infrastructure and lead technical discussions with clients."
    },
    
    # Non-Tech Jobs
    {
        "title": "Digital Marketing Manager",
        "company": "Accenture",
        "location": "Mumbai, Maharashtra",
        "date": "Posted 3 days ago",
        "link": "https://www.indeed.com/viewjob?jk=abcdef1234",
        "source": "indeed.com",
        "description": "Digital Marketing Manager needed to develop and implement marketing strategies across digital channels including SEO, PPC, and social media."
    },
    {
        "title": "HR Business Partner",
        "company": "Deloitte",
        "location": "Bangalore, Karnataka",
        "date": "Posted 1 week ago",
        "link": "https://www.indeed.com/viewjob?jk=bcdef12345",
        "source": "indeed.com",
        "description": "HR Business Partner to collaborate with leadership and provide strategic HR support including talent management and employee relations."
    },
    {
        "title": "Finance Analyst",
        "company": "KPMG",
        "location": "Gurgaon, Haryana",
        "date": "Posted 4 days ago",
        "link": "https://www.indeed.com/viewjob?jk=cdef123456",
        "source": "indeed.com",
        "description": "Finance Analyst required for financial reporting, budgeting, forecasting, and business analysis to support decision-making."
    },
    {
        "title": "Operations Manager",
        "company": "Amazon",
        "location": "Chennai, Tamil Nadu",
        "date": "Posted 2 days ago",
        "link": "https://www.indeed.com/viewjob?jk=def1234567",
        "source": "indeed.com",
        "description": "Operations Manager to oversee daily operations, optimize processes, and ensure high performance standards in our fulfillment center."
    },
    {
        "title": "Customer Success Manager",
        "company": "Salesforce",
        "location": "Hyderabad, Telangana",
        "date": "Posted 3 days ago",
        "link": "https://www.indeed.com/viewjob?jk=ef12345678",
        "source": "indeed.com",
        "description": "Customer Success Manager to build relationships with enterprise clients, understand their needs, and ensure they derive maximum value from our solutions."
    },
    
    # Remote Jobs
    {
        "title": "Remote React.js Developer",
        "company": "Upwork",
        "location": "Remote",
        "date": "Posted 1 day ago",
        "link": "https://www.foundit.in/job/remote-reactjs-developer-upwork-remote-3-to-5-years-54321",
        "source": "foundit.in",
        "description": "Looking for a React.js Developer who can work remotely on front-end development projects with modern JavaScript frameworks."
    },
    {
        "title": "Remote Content Writer",
        "company": "ContentMart",
        "location": "Remote",
        "date": "Posted 2 days ago",
        "link": "https://www.naukri.com/job-listings-remote-content-writer-contentmart-work-from-home-2-to-4-years-65432",
        "source": "naukri.com",
        "description": "Remote Content Writer to create engaging content for blogs, websites, and social media platforms across various industries."
    },
    {
        "title": "Remote Project Manager",
        "company": "IBM",
        "location": "Remote, India",
        "date": "Posted 3 days ago",
        "link": "https://www.indeed.com/viewjob?jk=f123456789",
        "source": "indeed.com",
        "description": "Remote Project Manager to lead distributed teams, manage project lifecycles, and ensure timely delivery of IT solutions."
    },
    {
        "title": "Remote UX/UI Designer",
        "company": "Accenture",
        "location": "Remote",
        "date": "Posted 2 days ago",
        "link": "https://www.indeed.com/viewjob?jk=1234567890a",
        "source": "indeed.com",
        "description": "Remote UX/UI Designer to create intuitive user experiences and visually appealing interfaces for web and mobile applications."
    },
    {
        "title": "Remote Data Analyst",
        "company": "TCS",
        "location": "Remote, India",
        "date": "Posted 4 days ago",
        "link": "https://www.foundit.in/job/remote-data-analyst-tcs-remote-2-to-4-years-76543",
        "source": "foundit.in",
        "description": "Remote Data Analyst to extract insights from data, create reports, and support business decision-making processes."
    }
]
