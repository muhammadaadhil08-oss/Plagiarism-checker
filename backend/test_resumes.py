import requests
import json

resume1 = """
Name: Ravi Kumar Email: ravi123@email.com Phone: +91 8765432109 Location: Tamil Nadu, India
Objective: Looking for a job where I can improve my skills and gain experience.
Education: B.Sc Computer Science 2024
Skills: Basic Python, HTML, MS Office
Projects: College Mini Project - Worked on a simple website using HTML.
Strengths: Hard working, Good communication
"""

resume2 = """
Name: Arjun Kumar Email: arjun.kumar@email.com Phone: +91 9876543210 Location: Chennai, India
Objective: Motivated Computer Science graduate seeking an entry-level software developer position to apply programming skills and contribute to innovative projects.
Education: B.Sc Computer Science, University of Madras — 2024
Skills: Python, HTML, CSS, JavaScript, SQL, Flask, Git & GitHub
Projects: AI Plagiarism Detection System - Developed a web application to detect AI-generated content and plagiarism. Used Python and Flask for backend processing. Implemented document comparison and similarity analysis.
Internship: Software Developer Intern, TechNova Solutions — 2 months
Strengths: Problem solving, Team collaboration, Quick learner
"""

from resume_analyzer import compare_resumes, is_resume

print(f"Is Resume 1? {is_resume(resume1)}")
print(f"Is Resume 2? {is_resume(resume2)}")

res = compare_resumes(resume1, resume2)
print("Comparison Result:")
print(json.dumps(res, indent=2))
