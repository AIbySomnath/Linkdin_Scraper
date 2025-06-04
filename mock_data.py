"""
Mock Data Generator - Create sample job listings for demonstration
"""
import random
from datetime import datetime, timedelta

class MockJobGenerator:
    """Generates mock job data for demonstration purposes"""
    
    def __init__(self):
        """Initialize the mock data generator"""
        self.job_titles = [
            "Software Engineer", "Data Scientist", "Machine Learning Engineer",
            "Frontend Developer", "Backend Developer", "Full Stack Developer",
            "DevOps Engineer", "AI Research Scientist", "Product Manager",
            "QA Engineer", "UX Designer", "Mobile App Developer",
            "Data Analyst", "Cloud Architect", "Database Administrator"
        ]
        
        self.companies = [
            "TechSolutions Inc.", "DataMinds", "AI Innovations",
            "CodeCraft", "Webify Solutions", "CloudNative Tech",
            "Digital Dynamics", "NextGen Software", "Infinite Logic",
            "ByteWave Technologies", "Quantum Computing", "AppSphere"
        ]
        
        self.locations = [
            "Bangalore", "Mumbai", "Pune", "Hyderabad", "Chennai",
            "Delhi", "Noida", "Gurgaon", "Kolkata", "Ahmedabad"
        ]
        
        self.skills = [
            "Python", "Java", "JavaScript", "React", "Angular", "Node.js",
            "AWS", "Docker", "Kubernetes", "TensorFlow", "PyTorch", "SQL",
            "NoSQL", "Git", "CI/CD", "Agile", "Scrum", "REST API"
        ]
        
    def generate_jobs(self, search_term, location="", site="foundit.in", count=15):
        """
        Generate mock job listings based on search parameters
        
        Args:
            search_term (str): Job search term
            location (str): Location for job search
            site (str): Job portal name
            count (int): Number of job listings to generate
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        # Filter job titles based on search term
        relevant_titles = [title for title in self.job_titles 
                         if any(term.lower() in title.lower() 
                                for term in search_term.split())]
        
        # If no relevant titles found, use all titles
        if not relevant_titles:
            relevant_titles = self.job_titles
            
        # Filter locations based on location parameter
        relevant_locations = [loc for loc in self.locations 
                            if location.lower() in loc.lower()] if location else self.locations
            
        # Generate random job listings
        for i in range(count):
            # Generate random date within last 30 days
            days_ago = random.randint(1, 30)
            date_posted = datetime.now() - timedelta(days=days_ago)
            
            if days_ago == 1:
                date_str = "Today"
            elif days_ago == 2:
                date_str = "Yesterday"
            elif days_ago <= 7:
                date_str = f"{days_ago} days ago"
            else:
                date_str = date_posted.strftime("%b %d")
                
            # Create job listing
            job = {
                'title': random.choice(relevant_titles),
                'company': random.choice(self.companies),
                'location': random.choice(relevant_locations),
                'date': date_str,
                'link': f"https://www.{site}/job/{random.randint(100000, 999999)}"
            }
            
            # Add skills (for display in UI)
            selected_skills = random.sample(self.skills, random.randint(3, 6))
            job['skills'] = ", ".join(selected_skills)
            
            # Add salary range (for display in UI)
            min_lpa = random.randint(5, 25)
            max_lpa = min_lpa + random.randint(2, 10)
            job['salary'] = f"{min_lpa} - {max_lpa} LPA"
            
            # Add job type (for display in UI)
            job_types = ["Full-time", "Contract", "Remote", "Hybrid"]
            job['job_type'] = random.choice(job_types)
            
            jobs.append(job)
            
        return jobs
        
# Example usage
if __name__ == "__main__":
    generator = MockJobGenerator()
    
    # Example: Generate AI jobs in Pune
    jobs = generator.generate_jobs(
        search_term="AI jobs",
        location="Pune",
        site="foundit.in",
        count=5
    )
    
    print(f"Generated {len(jobs)} mock job listings:")
    for i, job in enumerate(jobs):
        print(f"\nJob {i+1}:")
        for key, value in job.items():
            print(f"{key}: {value}")
