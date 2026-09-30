import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_ats_report(candidate_name, score, extracted_skills, missing_skills, recommendations, output_path):
    """
    Generates a PDF ATS report for a parsed resume.
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"ATS Resume Screening Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Overview
    elements.append(Paragraph(f"<b>Candidate:</b> {candidate_name}", normal_style))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(f"<b>ATS Compatibility Score:</b> {score}%", normal_style))
    elements.append(Spacer(1, 12))
    
    # Extracted Skills
    elements.append(Paragraph("Extracted Skills", heading_style))
    skills_text = ", ".join(extracted_skills) if extracted_skills else "None found"
    elements.append(Paragraph(skills_text, normal_style))
    elements.append(Spacer(1, 12))
    
    # Missing Skills (compared to job desc if any)
    elements.append(Paragraph("Recommended Skills to Add", heading_style))
    missing_text = ", ".join(missing_skills) if missing_skills else "N/A"
    elements.append(Paragraph(missing_text, normal_style))
    elements.append(Spacer(1, 12))
    
    # Recommendations
    elements.append(Paragraph("Improvement Recommendations", heading_style))
    for rec in recommendations:
        elements.append(Paragraph(f"- {rec}", normal_style))
    
    # Build PDF
    doc.build(elements)
    
    return output_path
