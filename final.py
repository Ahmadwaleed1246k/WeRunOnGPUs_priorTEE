# app.py - Streamlit Frontend for Opportunity Copilot
import streamlit as st
import json
import pandas as pd
from datetime import datetime
import re
from typing import List, Dict
import PyPDF2
import docx2txt
from io import StringIO

# Import your existing backend
import app as oc

# Page configuration
st.set_page_config(
    page_title="PrioriTEE",
    page_icon="📨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional UI
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin-top: 0.5rem;
    }
    
    /* Card styling */
    .opportunity-card {
        background: white;
        border-radius: 1rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 4px solid;
        transition: transform 0.2s;
    }
    
    .opportunity-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Priority colors */
    .priority-high {
        border-left-color: #ef4444;
        background: linear-gradient(90deg, #fef2f2 0%, white 100%);
    }
    .priority-medium {
        border-left-color: #f59e0b;
        background: linear-gradient(90deg, #fffbeb 0%, white 100%);
    }
    .priority-low {
        border-left-color: #10b981;
        background: linear-gradient(90deg, #ecfdf5 0%, white 100%);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 0.75rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    /* Progress bar styling */
    .progress-bar {
        background: #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
        height: 0.5rem;
    }
    
    .progress-fill {
        background: linear-gradient(90deg, #667eea, #764ba2);
        height: 100%;
        transition: width 0.3s ease;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 2rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-urgent {
        background: #fee2e2;
        color: #dc2626;
    }
    
    .badge-fit {
        background: #d1fae5;
        color: #059669;
    }
    
    /* Sidebar styling */
    .sidebar-section {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #6b7280;
        border-top: 1px solid #e5e7eb;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# RESUME PARSING FUNCTIONS
# ============================================

def parse_resume_pdf(file) -> str:
    """Extract text from PDF resume"""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def parse_resume_docx(file) -> str:
    """Extract text from DOCX resume"""
    text = docx2txt.process(file)
    return text

def parse_resume_text(file) -> str:
    """Read text file"""
    return file.getvalue().decode("utf-8")

def extract_profile_from_resume(text: str) -> oc.StudentProfile:
    """Extract student profile from resume text using NLP and patterns"""
    text_lower = text.lower()
    
    # Extract degree
    degree_patterns = [
        r'(?:bachelor|bs|b\.s\.|bsc)\s+(?:of\s+)?(?:science|computer science|cs|software engineering|se)',
        r'(?:master|ms|m\.s\.|msc)\s+(?:of\s+)?(?:science|computer science|cs)',
        r'(?:ph\.?d|doctorate)\s+(?:in\s+)?(?:computer science|cs|ai)'
    ]
    degree = "BS Computer Science"  # default
    for pattern in degree_patterns:
        match = re.search(pattern, text_lower)
        if match:
            degree = match.group().title()
            break
    
    # Extract CGPA
    cgpa_patterns = [
        r'cgpa[:\s]*(\d+\.?\d*)',
        r'gpa[:\s]*(\d+\.?\d*)',
        r'grade point average[:\s]*(\d+\.?\d*)'
    ]
    cgpa = 3.0
    for pattern in cgpa_patterns:
        match = re.search(pattern, text_lower)
        if match:
            cgpa = float(match.group(1))
            break
    
    # Extract skills (common tech skills)
    skill_keywords = [
        "python", "java", "javascript", "c++", "sql", "react", "angular", "node.js",
        "machine learning", "deep learning", "ai", "artificial intelligence", "data science",
        "pandas", "numpy", "tensorflow", "pytorch", "keras", "scikit-learn",
        "aws", "azure", "gcp", "docker", "kubernetes", "git", "linux",
        "html", "css", "django", "flask", "fastapi", "spring boot"
    ]
    skills = [s for s in skill_keywords if s in text_lower]
    if not skills:
        skills = ["Python", "Data Analysis"]  # default
    
    # Extract interests from skills + additional keywords
    interest_keywords = [
        "ai", "machine learning", "data science", "web development", "mobile development",
        "cloud computing", "cybersecurity", "blockchain", "devops", "ui/ux", "product management"
    ]
    interests = [i for i in interest_keywords if i in text_lower]
    if not interests:
        interests = ["AI", "Data Science"]
    
    # Determine semester (rough estimate from graduation year or experience)
    semester = 6  # default
    year_pattern = r'(?:graduation|class of)[:\s]*(\d{4})'
    match = re.search(year_pattern, text_lower)
    if match:
        grad_year = int(match.group(1))
        current_year = datetime.now().year
        if current_year <= grad_year:
            semesters_remaining = (grad_year - current_year) * 2
            semester = 8 - semesters_remaining
    
    # Extract past experience
    experience_keywords = [
        "intern", "research assistant", "teaching assistant", "freelance", "developer",
        "software engineer", "data analyst", "project manager", "team lead"
    ]
    past_experience = [exp for exp in experience_keywords if exp in text_lower]
    
    # Default preferred opportunity types
    preferred_opportunity_types = ["internship", "scholarship", "fellowship", "competition"]
    
    return oc.StudentProfile(
        degree=degree,
        semester=max(1, min(8, semester)),
        cgpa=cgpa,
        skills=skills[:8],  # Top 8 skills
        interests=interests[:5],
        preferred_opportunity_types=preferred_opportunity_types,
        financial_need=False,  # Can be set by user
        location_preference="remote",
        past_experience=past_experience[:3]
    )

# ============================================
# UI COMPONENTS
# ============================================

def render_header():
    """Render main header"""
    st.markdown("""
    <div class="main-header">
        <h1>📨PrioriTEE</h1>
        <p>AI-Powered Email Opportunity Detection & Personalized Ranking</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar with configuration options"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # API Key input
        st.markdown("#### 🤖 AI Settings")
        use_ai = st.checkbox("Use OpenRouter AI (Better extraction)", value=False)
        api_key = None
        if use_ai:
            api_key = st.text_input("OpenRouter API Key", type="password", 
                                    placeholder="sk-or-...")
            st.caption("Get free key at [openrouter.ai/keys](https://openrouter.ai/keys)")
        
        st.markdown("---")
        
        # Financial need toggle
        st.markdown("#### 💰 Financial Settings")
        financial_need = st.checkbox("I have financial need", value=False)
        
        st.markdown("---")
        
        # Location preference
        st.markdown("#### 📍 Location Preference")
        location_pref = st.selectbox(
            "Preferred work location",
            ["remote", "onsite", "hybrid", "any"]
        )
        
        st.markdown("---")
        
        # About section
        st.markdown("#### ℹ️ About")
        st.info(
            "This AI-powered system analyzes your resume and opportunity emails, "
            "then ranks opportunities based on fit score (skills, CGPA, degree, etc.) "
            "and urgency score (deadline proximity)."
        )
        
        return {
            "use_ai": use_ai,
            "api_key": api_key,
            "financial_need": financial_need,
            "location_preference": location_pref
        }

def render_profile_card(profile: oc.StudentProfile):
    """Render student profile card"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.875rem; color: #6b7280;">Degree</div>
            <div style="font-weight: 600; margin-top: 0.25rem;">{}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">Semester {}</div>
        </div>
        """.format(profile.degree, profile.semester), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.875rem; color: #6b7280;">CGPA</div>
            <div class="metric-value">{:.2f}</div>
        </div>
        """.format(profile.cgpa), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.875rem; color: #6b7280;">Skills</div>
            <div style="font-size: 0.75rem; margin-top: 0.25rem;">{}</div>
        </div>
        """.format(", ".join(profile.skills[:3]) + ("..." if len(profile.skills) > 3 else "")), 
        unsafe_allow_html=True)
    
    # Expandable details
    with st.expander("📋 View Full Profile Details"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Skills**")
            st.write(", ".join(profile.skills))
            st.markdown("**Interests**")
            st.write(", ".join(profile.interests))
        with col_b:
            st.markdown("**Past Experience**")
            st.write(", ".join(profile.past_experience) if profile.past_experience else "None specified")
            st.markdown("**Looking for**")
            st.write(", ".join(profile.preferred_opportunity_types))

def render_opportunity_card(ranked_opp: oc.RankedOpportunity, index: int):
    """Render a single opportunity card"""
    opp = ranked_opp.opportunity
    
    # Determine priority class and badge
    if ranked_opp.priority_score >= 70:
        priority_class = "priority-high"
        priority_badge = "🔴 High Priority"
    elif ranked_opp.priority_score >= 40:
        priority_class = "priority-medium"
        priority_badge = "🟡 Medium Priority"
    else:
        priority_class = "priority-low"
        priority_badge = "🟢 Low Priority"
    
    # Determine urgency badge
    urgency_badge = ""
    if ranked_opp.urgency_score >= 70:
        urgency_badge = '<span class="badge badge-urgent">⏰ Urgent</span>'
    elif ranked_opp.urgency_score >= 40:
        urgency_badge = '<span class="badge">📅 Soon</span>'
    
    # Determine fit badge
    fit_badge = ""
    if ranked_opp.fit_score >= 70:
        fit_badge = '<span class="badge badge-fit">✅ Great Fit</span>'
    elif ranked_opp.fit_score >= 40:
        fit_badge = '<span class="badge">👍 Good Fit</span>'
    
    st.markdown(f"""
    <div class="opportunity-card {priority_class}">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <h3 style="margin: 0 0 0.5rem 0;">#{index} {opp.subject}</h3>
                <div style="margin-bottom: 0.5rem;">
                    {urgency_badge}
                    {fit_badge}
                    <span class="badge" style="background: #e0e7ff; color: #4338ca;">{opp.opportunity_type.upper()}</span>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{ranked_opp.priority_score:.0f}</div>
                <div style="font-size: 0.75rem; color: #6b7280;">Priority Score</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Priority badges row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fit Score", f"{ranked_opp.fit_score:.0f}/100", 
                  delta="Good" if ranked_opp.fit_score >= 50 else "Low")
    with col2:
        st.metric("Urgency Score", f"{ranked_opp.urgency_score:.0f}/100",
                  delta="Urgent" if ranked_opp.urgency_score >= 70 else "Normal")
    with col3:
        st.metric("Confidence", f"{opp.confidence_score:.0%}")
    
    # Fit breakdown progress bars
    if ranked_opp.detailed_breakdown:
        st.markdown("**📊 Fit Analysis**")
        for metric, score in ranked_opp.detailed_breakdown.items():
            col_a, col_b = st.columns([2, 5])
            with col_a:
                st.caption(metric.replace('_', ' ').title())
            with col_b:
                st.progress(score / 100, text=f"{score:.0f}%")
    
    # Opportunity details
    with st.expander("📋 View Opportunity Details", expanded=False):
        if opp.deadline:
            st.info(f"⏰ **Deadline:** {opp.deadline}")
        if opp.location:
            st.write(f"📍 **Location:** {opp.location}")
        if opp.compensation:
            st.success(f"💰 **Compensation:** {opp.compensation}")
        if opp.required_skills:
            st.write(f"🔧 **Required Skills:** {', '.join(opp.required_skills)}")
        if opp.eligibility_criteria:
            st.write(f"📋 **Eligibility:** {', '.join(opp.eligibility_criteria)}")
        if opp.required_documents:
            st.write(f"📄 **Required Documents:** {', '.join(opp.required_documents)}")
        if opp.application_link:
            st.markdown(f"🔗 **Application Link:** [{opp.application_link}]({opp.application_link})")
    
    # Reasoning and action items
    st.markdown(f"""
    <div style="margin-top: 1rem; padding: 0.75rem; background: #f8fafc; border-radius: 0.5rem;">
        <strong>💡 {ranked_opp.reasoning}</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**✅ Action Checklist**")
    for action in ranked_opp.action_items:
        st.markdown(f"- {action}")
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_results(ranked_opportunities: List[oc.RankedOpportunity]):
    """Render all ranked opportunities"""
    if not ranked_opportunities:
        st.warning("⚠️ No opportunities found in the uploaded emails.")
        return
    
    # Summary metrics
    st.markdown("### 📈 Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Opportunities", len(ranked_opportunities))
    with col2:
        high_priority = sum(1 for ro in ranked_opportunities if ro.priority_score >= 70)
        st.metric("High Priority", high_priority)
    with col3:
        urgent = sum(1 for ro in ranked_opportunities if ro.urgency_score >= 70)
        st.metric("Urgent Deadlines", urgent)
    with col4:
        good_fit = sum(1 for ro in ranked_opportunities if ro.fit_score >= 70)
        st.metric("Good Fit", good_fit)
    
    st.markdown("---")
    
    # Display opportunities
    st.markdown("### 🎯 Ranked Opportunities")
    for i, ranked_opp in enumerate(ranked_opportunities, 1):
        render_opportunity_card(ranked_opp, i)
        st.markdown("---")

# ============================================
# MAIN APP
# ============================================

def main():
    render_header()
    
    # Sidebar configuration
    config = render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📄 Upload Resume")
        resume_file = st.file_uploader(
            "Upload your resume (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            help="We'll parse your resume to create your student profile"
        )
        
        if resume_file:
            with st.spinner("Parsing resume..."):
                # Parse resume based on file type
                if resume_file.type == "application/pdf":
                    text = parse_resume_pdf(resume_file)
                elif resume_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    text = parse_resume_docx(resume_file)
                else:
                    text = parse_resume_text(resume_file)
                
                # Extract profile
                profile = extract_profile_from_resume(text)
                # Update with user preferences from sidebar
                profile.financial_need = config["financial_need"]
                profile.location_preference = config["location_preference"]
                
                st.session_state['profile'] = profile
                st.success("✅ Resume parsed successfully!")
    
    with col2:
        st.markdown("### 📧 Upload Opportunity Emails")
        email_file = st.file_uploader(
            "Upload emails (JSON format)",
            type=["json"],
            help="JSON file containing email objects with 'id', 'subject', 'from', 'body' fields"
        )
        
        if email_file:
            try:
                emails = json.load(email_file)
                st.session_state['emails'] = emails
                st.success(f"✅ Loaded {len(emails)} emails")
                
                # Show preview
                with st.expander("📧 Email Preview"):
                    for email in emails[:3]:
                        st.markdown(f"**{email.get('subject', 'No Subject')}**")
                        st.caption(f"From: {email.get('from', 'Unknown')}")
                        st.text(email.get('body', '')[:200] + "...")
                        st.markdown("---")
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please check the format.")
    
    # Process button
    if st.session_state.get('profile') and st.session_state.get('emails'):
        st.markdown("---")
        if st.button("🚀 Analyze & Rank Opportunities", type="primary", use_container_width=True):
            with st.spinner("Processing emails and ranking opportunities..."):
                try:
                    # Create copilot instance
                    copilot = oc.OpportunityCopilot(
                        profile=st.session_state['profile'],
                        use_openrouter_ai=config["use_ai"],
                        api_key=config["api_key"] if config["use_ai"] else None
                    )
                    
                    # Process emails
                    ranked_opportunities = copilot.process_emails(st.session_state['emails'])
                    
                    # Store results
                    st.session_state['ranked'] = ranked_opportunities
                    st.success(f"✅ Analysis complete! Found {len(ranked_opportunities)} opportunities.")
                    
                except Exception as e:
                    st.error(f"Error processing emails: {str(e)}")
    
    # Display results
    if st.session_state.get('ranked'):
        st.markdown("---")
        render_results(st.session_state['ranked'])
        
        # Export option
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📥 Export Results to JSON", use_container_width=True):
                output = []
                for ro in st.session_state['ranked']:
                    output.append({
                        "subject": ro.opportunity.subject,
                        "priority_score": ro.priority_score,
                        "fit_score": ro.fit_score,
                        "urgency_score": ro.urgency_score,
                        "reasoning": ro.reasoning,
                        "action_items": ro.action_items,
                        "extracted_details": {
                            "type": ro.opportunity.opportunity_type,
                            "deadline": ro.opportunity.deadline,
                            "eligibility": ro.opportunity.eligibility_criteria,
                            "documents": ro.opportunity.required_documents,
                            "link": ro.opportunity.application_link,
                            "skills_required": ro.opportunity.required_skills
                        }
                    })
                st.download_button(
                    label="📥 Download JSON",
                    data=json.dumps(output, indent=2),
                    file_name="ranked_opportunities.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Opportunity Inbox Copilot | AI-Powered Email Processing & Ranking</p>
        <p style="font-size: 0.75rem;">Built for SOFTEC 2026 AI Hackathon</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Initialize session state
    if 'profile' not in st.session_state:
        st.session_state['profile'] = None
    if 'emails' not in st.session_state:
        st.session_state['emails'] = None
    if 'ranked' not in st.session_state:
        st.session_state['ranked'] = None
    
    main()