# opportunity_copilot.py
import json
import re
import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

# ============================================
# DATA MODELS
# ============================================

class OpportunityType(Enum):
    SCHOLARSHIP = "scholarship"
    INTERNSHIP = "internship"
    COMPETITION = "competition"
    ADMISSION = "admission"
    FELLOWSHIP = "fellowship"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    JOB = "job"
    OTHER = "other"

@dataclass
class StudentProfile:
    degree: str
    semester: int
    cgpa: float
    skills: List[str]
    interests: List[str]
    preferred_opportunity_types: List[str]
    financial_need: bool
    location_preference: str
    past_experience: List[str]

@dataclass
class ExtractedOpportunity:
    email_id: str
    subject: str
    opportunity_type: str
    deadline: Optional[str]
    eligibility_criteria: List[str]
    required_documents: List[str]
    application_link: Optional[str]
    contact_info: Optional[str]
    raw_text: str
    is_opportunity: bool
    confidence_score: float
    # Enhanced fields for better matching
    required_skills: List[str] = None
    preferred_degrees: List[str] = None
    min_cgpa: Optional[float] = None
    location: Optional[str] = None
    compensation: Optional[str] = None

@dataclass
class RankedOpportunity:
    opportunity: ExtractedOpportunity
    priority_score: float
    fit_score: float
    urgency_score: float
    reasoning: str
    action_items: List[str]
    detailed_breakdown: Dict[str, float] = None

# ============================================
# MOCK EMAIL DATA
# ============================================

MOCK_EMAILS = [
    {
        "id": "email_001",
        "subject": "🚀 Google Summer Internship 2025 - Apply Now!",
        "from": "recruiting@google.com",
        "body": """
        Google is hiring summer interns for 2025! 
        Deadline: March 15, 2026
        Eligibility: Current BS/MS students with CGPA >= 3.0
        Required skills: Python, Machine Learning, Data Structures
        Preferred degrees: CS, SE, DS
        Location: Remote or Hyderabad
        Stipend: $8000/month
        Required documents: Resume, Transcript, Cover Letter
        Apply at: https://careers.google.com/internship
        Contact: internship@google.com
        """
    },
    {
        "id": "email_002",
        "subject": "HEC Need-Based Scholarship for CS Students",
        "from": "scholarships@hec.gov.pk",
        "body": """
        Higher Education Commission announces need-based scholarship.
        Deadline: 2026-04-25
        Eligibility: CGPA >= 2.5, financial need required
        Documents: CNIC, fee slip, income certificate
        Apply: https://scholarships.hec.gov.pk
        """
    },
    {
        "id": "email_003",
        "subject": "Weekly Newsletter: Tech Updates",
        "from": "newsletter@techcrunch.com",
        "body": "This week in tech: AI breakthroughs, new Python release."
    },
    {
        "id": "email_004",
        "subject": "FAST National Coding Competition 2025",
        "from": "events@fastnu.edu.pk",
        "body": """
        Register for the biggest coding competition in Pakistan!
        Prize pool: PKR 500,000
        Deadline for registration: may 10, 2026
        Eligibility: All university students
        Team size: 3 members
        Required skills: DSA, Problem Solving
        Link: https://codingcomp.fastnu.edu.pk
        """
    },
    {
        "id": "email_005",
        "subject": "UN Fellowship for Climate Tech Innovators",
        "from": "fellowships@un.org",
        "body": """
        Fully funded fellowship for climate tech innovators.
        Duration: 6 months
        Deadline: june 1, 2026
        Eligibility: Students with AI/Data Science skills, CGPA >= 3.2
        Apply with: CV, Statement of Purpose, 2 Recommendations
        """
    },
    {
        "id": "email_006",
        "subject": "Your Amazon Order Confirmation",
        "from": "no-reply@amazon.com",
        "body": "Your package will be delivered tomorrow."
    },
    {
        "id": "email_007",
        "subject": "Microsoft Research Internship - AI Division",
        "from": "research@microsoft.com",
        "body": """
        Microsoft Research is hiring interns for AI division.
        Deadline: 2026-04-20
        Requirements: Strong ML background, Python, PyTorch
        CGPA >= 3.2 preferred
        Location: Redmond, WA (Remote options)
        Apply: https://microsoft.com/research-intern
        """
    }
]

# ============================================
# ENHANCED OPENROUTER AI ROUTER
# ============================================

class OpenRouterAIRouter:
    """Handles AI operations using OpenRouter's free tier"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            print(f"{Fore.YELLOW}⚠️ No OpenRouter API key found. Using keyword-based extraction.")
            print(f"{Fore.YELLOW}Get your free key at: https://openrouter.ai/keys")
            self.use_ai = False
        else:
            self.use_ai = True
            print(f"{Fore.GREEN}✓ OpenRouter AI initialized (Free tier)")
    
    def classify_and_extract(self, email: Dict) -> ExtractedOpportunity:
        if self.use_ai:
            try:
                return self._extract_with_openrouter(email)
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ AI extraction failed: {str(e)[:50]}")
                return self._extract_with_keywords(email)
        else:
            return self._extract_with_keywords(email)
    
    def _extract_with_openrouter(self, email: Dict) -> ExtractedOpportunity:
        """Enhanced extraction with more fields"""
        
        prompt = f"""
        Analyze this email and extract structured information. Return ONLY valid JSON.
        cureent date today is  18 april 2026
        Email Subject: {email.get('subject', '')}
        Email Body: {email.get('body', '')}
        
        Return JSON with:
        {{
            "is_opportunity": true/false,
            "opportunity_type": "scholarship/internship/competition/admission/fellowship/conference/workshop/job/other",
            "deadline": "YYYY-MM-DD or null",
            "eligibility_criteria": ["list", "of", "requirements"],
            "required_documents": ["list", "of", "documents"],
            "application_link": "url or null",
            "contact_info": "email or null",
            "required_skills": ["list", "of", "skills"],
            "preferred_degrees": ["list", "of", "degrees"],
            "min_cgpa": float or null,
            "location": "location string or null",
            "compensation": "salary/stipend/prize info or null",
            "confidence_score": 0.0-1.0
        }}
        """
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/opportunity-copilot",
                "X-Title": "Opportunity Copilot"
            },
            json={
                "model": "openrouter/free",
                "messages": [
                    {"role": "system", "content": "You extract structured opportunity data from emails. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 600
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code}")
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        ai_response = re.sub(r'```json\s*', '', ai_response)
        ai_response = re.sub(r'```\s*', '', ai_response)
        extracted_data = json.loads(ai_response.strip())
        
        return ExtractedOpportunity(
            email_id=email.get("id", ""),
            subject=email.get("subject", ""),
            opportunity_type=extracted_data.get("opportunity_type", "other"),
            deadline=extracted_data.get("deadline"),
            eligibility_criteria=extracted_data.get("eligibility_criteria", ["General eligibility"]),
            required_documents=extracted_data.get("required_documents", []),
            application_link=extracted_data.get("application_link"),
            contact_info=extracted_data.get("contact_info"),
            raw_text=email.get("body", ""),
            is_opportunity=extracted_data.get("is_opportunity", False),
            confidence_score=extracted_data.get("confidence_score", 0.7),
            required_skills=extracted_data.get("required_skills", []),
            preferred_degrees=extracted_data.get("preferred_degrees", []),
            min_cgpa=extracted_data.get("min_cgpa"),
            location=extracted_data.get("location"),
            compensation=extracted_data.get("compensation")
        )
    
    def _extract_with_keywords(self, email: Dict) -> ExtractedOpportunity:
        """Enhanced keyword extraction"""
        text = (email.get("subject", "") + " " + email.get("body", "")).lower()
        
        opp_keywords = ["internship", "scholarship", "fellowship", "competition", 
                       "hiring", "apply", "register", "opportunity", "grant"]
        is_opp = any(kw in text for kw in opp_keywords)
        
        opp_type = OpportunityType.OTHER.value
        for ot in OpportunityType:
            if ot.value in text:
                opp_type = ot.value
                break
        
        # Extract deadline
        deadline_patterns = [
            r'deadline:\s*(\d{4}-\d{2}-\d{2})',
            r'deadline:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
        ]
        deadline = None
        for pattern in deadline_patterns:
            match = re.search(pattern, email.get("body", ""), re.IGNORECASE)
            if match:
                deadline = match.group(1)
                break
        
        # Extract CGPA
        min_cgpa = None
        cgpa_match = re.search(r'cgpa\s*[>=]+\s*(\d+\.?\d*)', text)
        if cgpa_match:
            min_cgpa = float(cgpa_match.group(1))
        
        # Extract skills
        skill_keywords = ["python", "machine learning", "data analysis", "pytorch", 
                         "tensorflow", "java", "c++", "sql", "aws", "docker"]
        required_skills = [s for s in skill_keywords if s in text]
        
        # Extract degrees
        degree_keywords = ["cs", "computer science", "se", "software engineering", 
                          "ds", "data science", "ai"]
        preferred_degrees = [d for d in degree_keywords if d in text]
        
        # Extract location
        location = None
        loc_pattern = r'location:\s*([^\n]+)'
        loc_match = re.search(loc_pattern, email.get("body", ""), re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()
        
        # Extract compensation
        compensation = None
        comp_pattern = r'(?:stipend|salary|prize|package)[:\s]+([^\n]+)'
        comp_match = re.search(comp_pattern, email.get("body", ""), re.IGNORECASE)
        if comp_match:
            compensation = comp_match.group(1).strip()
        
        eligibility = []
        if min_cgpa:
            eligibility.append(f"CGPA >= {min_cgpa}")
        if "financial" in text or "need" in text:
            eligibility.append("Financial need consideration")
        
        docs_keywords = ["resume", "cv", "transcript", "cover letter", "recommendation"]
        required_docs = [doc for doc in docs_keywords if doc in text]
        
        link_pattern = r'https?://[^\s]+'
        links = re.findall(link_pattern, email.get("body", ""))
        app_link = links[0] if links else None
        
        return ExtractedOpportunity(
            email_id=email.get("id", ""),
            subject=email.get("subject", ""),
            opportunity_type=opp_type,
            deadline=deadline,
            eligibility_criteria=eligibility if eligibility else ["General eligibility"],
            required_documents=required_docs,
            application_link=app_link,
            contact_info=None,
            raw_text=email.get("body", ""),
            is_opportunity=is_opp,
            confidence_score=0.85 if is_opp else 0.3,
            required_skills=required_skills,
            preferred_degrees=preferred_degrees,
            min_cgpa=min_cgpa,
            location=location,
            compensation=compensation
        )


# ============================================
# ENHANCED MODEL-BASED FIT SCORING ENGINE
# ============================================

class FitScoringEngine:
    """Advanced model-based fit scoring using multiple dimensions"""
    
    def __init__(self, profile: StudentProfile):
        self.profile = profile
        self.weights = {
            "skills_match": 0.25,
            "degree_match": 0.15,
            "cgpa_match": 0.15,
            "type_match": 0.15,
            "experience_match": 0.10,
            "location_match": 0.08,
            "financial_need_match": 0.07,
            "compensation_attractiveness": 0.05
        }
    
    def calculate_fit_score(self, opp: ExtractedOpportunity) -> tuple[float, Dict[str, float]]:
        """Calculate detailed fit score with breakdown"""
        scores = {}
        
        # 1. Skills Match (25%)
        scores["skills_match"] = self._calculate_skills_match(opp)
        
        # 2. Degree Match (15%)
        scores["degree_match"] = self._calculate_degree_match(opp)
        
        # 3. CGPA Match (15%)
        scores["cgpa_match"] = self._calculate_cgpa_match(opp)
        
        # 4. Opportunity Type Match (15%)
        scores["type_match"] = self._calculate_type_match(opp)
        
        # 5. Experience Match (10%)
        scores["experience_match"] = self._calculate_experience_match(opp)
        
        # 6. Location Match (8%)
        scores["location_match"] = self._calculate_location_match(opp)
        
        # 7. Financial Need Match (7%)
        scores["financial_need_match"] = self._calculate_financial_match(opp)
        
        # 8. Compensation Attractiveness (5%)
        scores["compensation_attractiveness"] = self._calculate_compensation_score(opp)
        
        # Calculate weighted total
        total_score = sum(scores[k] * self.weights[k] for k in scores)
        
        return total_score, scores
    
    def _calculate_skills_match(self, opp: ExtractedOpportunity) -> float:
        """Calculate skill overlap using semantic matching"""
        if not opp.required_skills:
            return 0.7  # No skills required = good for everyone
        
        profile_skills_lower = [s.lower() for s in self.profile.skills]
        required_skills_lower = [s.lower() for s in opp.required_skills]
        
        # Exact matches
        exact_matches = sum(1 for skill in required_skills_lower 
                           if any(ps in skill or skill in ps for ps in profile_skills_lower))
        
        # Skill relevance based on interests
        interest_relevance = 0
        for interest in self.profile.interests:
            interest_lower = interest.lower()
            for req_skill in required_skills_lower:
                if interest_lower in req_skill or req_skill in interest_lower:
                    interest_relevance += 0.1
        
        match_ratio = exact_matches / max(len(required_skills_lower), 1)
        return min(1.0, match_ratio * 0.8 + interest_relevance + 0.2)
    
    def _calculate_degree_match(self, opp: ExtractedOpportunity) -> float:
        """Check if student's degree matches preferred degrees"""
        if not opp.preferred_degrees:
            return 0.8  # No preference = good fit
        
        profile_degree_lower = self.profile.degree.lower()
        
        for pref in opp.preferred_degrees:
            pref_lower = pref.lower()
            if pref_lower in profile_degree_lower or profile_degree_lower in pref_lower:
                return 1.0
        
        # Partial match for related fields
        related_pairs = [("cs", "computer"), ("se", "software"), ("ds", "data")]
        for pref in opp.preferred_degrees:
            for profile_kw, pref_kw in related_pairs:
                if pref_kw in pref.lower() and profile_kw in profile_degree_lower:
                    return 0.6
        
        return 0.2
    
    def _calculate_cgpa_match(self, opp: ExtractedOpportunity) -> float:
        """Calculate CGPA-based fit"""
        if opp.min_cgpa is None:
            return 0.8  # No requirement
        
        if self.profile.cgpa >= opp.min_cgpa:
            # Above requirement: scale from 0.7 to 1.0 based on how much above
            excess = self.profile.cgpa - opp.min_cgpa
            return min(1.0, 0.7 + excess * 0.3)
        else:
            # Below requirement: scale from 0 to 0.4 based on how close
            deficit = opp.min_cgpa - self.profile.cgpa
            return max(0.0, 0.4 - deficit * 0.4)
    
    def _calculate_type_match(self, opp: ExtractedOpportunity) -> float:
        """Match opportunity type with preferences"""
        if opp.opportunity_type in self.profile.preferred_opportunity_types:
            return 1.0
        return 0.3
    
    def _calculate_experience_match(self, opp: ExtractedOpportunity) -> float:
        """Check if past experience is relevant"""
        if not self.profile.past_experience:
            return 0.5
        
        opp_text = opp.raw_text.lower()
        matches = sum(1 for exp in self.profile.past_experience 
                     if exp.lower() in opp_text)
        
        return min(1.0, 0.4 + matches * 0.3)
    
    def _calculate_location_match(self, opp: ExtractedOpportunity) -> float:
        """Match location preference"""
        if not opp.location:
            return 0.7  # No location specified
        
        pref = self.profile.location_preference.lower()
        opp_loc = opp.location.lower()
        
        if pref == "any":
            return 1.0
        elif pref == "remote" and ("remote" in opp_loc or "virtual" in opp_loc):
            return 1.0
        elif pref == "onsite" and "remote" not in opp_loc:
            return 0.8
        elif pref in opp_loc:
            return 0.9
        
        return 0.3
    
    def _calculate_financial_match(self, opp: ExtractedOpportunity) -> float:
        """Check financial need alignment"""
        if not self.profile.financial_need:
            return 0.5
        
        if "need" in opp.raw_text.lower() or "financial" in opp.raw_text.lower():
            return 1.0
        return 0.3
    
    def _calculate_compensation_score(self, opp: ExtractedOpportunity) -> float:
        """Score based on compensation attractiveness"""
        if not opp.compensation:
            return 0.5
        
        comp_text = opp.compensation.lower()
        
        # Keywords indicating good compensation
        positive_indicators = ["paid", "stipend", "salary", "prize", "funded", "$", "pkR"]
        if any(ind in comp_text for ind in positive_indicators):
            return 0.9
        
        return 0.5


class UrgencyScoringEngine:
    """Enhanced urgency scoring with multiple factors"""
    
    def calculate_urgency_score(self, opp: ExtractedOpportunity) -> float:
        """Calculate urgency based on deadline and other factors"""
        scores = []
        
        # Deadline-based urgency (primary factor)
        deadline_score = self._calculate_deadline_urgency(opp)
        scores.append(deadline_score * 0.7)
        
        # Rolling deadline indicator
        rolling_score = self._check_rolling_deadline(opp)
        scores.append(rolling_score * 0.2)
        
        # Limited seats indicator
        limited_score = self._check_limited_availability(opp)
        scores.append(limited_score * 0.1)
        
        return sum(scores) * 100
    
    def _calculate_deadline_urgency(self, opp: ExtractedOpportunity) -> float:
        """Calculate urgency from deadline"""
        if not opp.deadline:
            return 0.3
        
        try:
            for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    deadline = datetime.strptime(opp.deadline, fmt)
                    break
                except:
                    continue
            else:
                return 0.3
            
            days_until = (deadline - datetime.now()).days
            
            if days_until < 0:
                return 0.0  # Expired
            elif days_until <= 3:
                return 1.0  # Critical
            elif days_until <= 7:
                return 0.9
            elif days_until <= 14:
                return 0.7
            elif days_until <= 30:
                return 0.5
            else:
                return 0.2
        except:
            return 0.3
    
    def _check_rolling_deadline(self, opp: ExtractedOpportunity) -> float:
        """Check for rolling admission / early bird indicators"""
        text = opp.raw_text.lower()
        rolling_indicators = ["rolling", "early bird", "early decision", "priority deadline"]
        
        if any(ind in text for ind in rolling_indicators):
            return 0.8
        return 0.0
    
    def _check_limited_availability(self, opp: ExtractedOpportunity) -> float:
        """Check for limited spots/seats"""
        text = opp.raw_text.lower()
        limited_indicators = ["limited seats", "limited spots", "first come", "early application"]
        
        if any(ind in text for ind in limited_indicators):
            return 0.7
        return 0.0


class EnhancedRankingEngine:
    """Enhanced ranking with model-based fit scoring"""
    
    def __init__(self, profile: StudentProfile):
        self.profile = profile
        self.fit_engine = FitScoringEngine(profile)
        self.urgency_engine = UrgencyScoringEngine()
    
    def rank_opportunities(self, opportunities: List[ExtractedOpportunity]) -> List[RankedOpportunity]:
        ranked = []
        
        for opp in opportunities:
            if not opp.is_opportunity:
                continue
            
            # Get detailed fit score
            fit_score, fit_breakdown = self.fit_engine.calculate_fit_score(opp)
            fit_score_percent = fit_score * 100
            
            # Get urgency score
            urgency_score = self.urgency_engine.calculate_urgency_score(opp)
            
            # Weighted priority (60% fit, 40% urgency)
            priority_score = (fit_score_percent * 0.6) + (urgency_score * 0.4)
            
            # Generate reasoning with details
            reasoning = self._generate_enhanced_reasoning(
                fit_score_percent, urgency_score, fit_breakdown, opp
            )
            
            # Generate action items
            action_items = self._generate_enhanced_action_items(opp)
            
            ranked.append(RankedOpportunity(
                opportunity=opp,
                priority_score=priority_score,
                fit_score=fit_score_percent,
                urgency_score=urgency_score,
                reasoning=reasoning,
                action_items=action_items,
                detailed_breakdown={k: v*100 for k, v in fit_breakdown.items()}
            ))
        
        ranked.sort(key=lambda x: x.priority_score, reverse=True)
        return ranked
    
    def _generate_enhanced_reasoning(self, fit_score: float, urgency_score: float, 
                                      breakdown: Dict[str, float], opp: ExtractedOpportunity) -> str:
        """Generate detailed reasoning"""
        strengths = []
        concerns = []
        
        # Identify strengths
        if breakdown.get("skills_match", 0) > 70:
            strengths.append(f"strong skill match ({breakdown['skills_match']:.0f}%)")
        if breakdown.get("type_match", 0) > 80:
            strengths.append(f"matches your preference for {opp.opportunity_type}s")
        if breakdown.get("cgpa_match", 0) > 80:
            strengths.append("meets CGPA requirements comfortably")
        
        # Identify concerns
        if breakdown.get("cgpa_match", 0) < 40 and opp.min_cgpa:
            concerns.append(f"CGPA ({self.profile.cgpa}) below requirement ({opp.min_cgpa})")
        if breakdown.get("location_match", 0) < 30:
            concerns.append(f"location ({opp.location}) doesn't match preference")
        
        strength_text = f"✅ {', '.join(strengths)}" if strengths else ""
        concern_text = f"⚠️ {', '.join(concerns)}" if concerns else ""
        
        priority_level = "HIGH" if fit_score > 70 and urgency_score > 70 else \
                        "MEDIUM" if fit_score > 50 else "LOW"
        
        return f"[{priority_level} PRIORITY] {strength_text} {concern_text}".strip()


    def _generate_enhanced_action_items(self, opp: ExtractedOpportunity) -> List[str]:
        """Generate detailed action items"""
        actions = []
        
        if opp.deadline:
            actions.append(f"⏰ Apply by {opp.deadline}")
        
        if opp.required_skills:
            missing_skills = [s for s in opp.required_skills 
                            if s.lower() not in [ps.lower() for ps in self.profile.skills]]
            if missing_skills:
                actions.append(f"📚 Consider upskilling: {', '.join(missing_skills[:2])}")
        
        if opp.required_documents:
            actions.append(f"📄 Prepare documents: {', '.join(opp.required_documents[:3])}")
        
        if opp.application_link:
            actions.append(f"🔗 Start application: {opp.application_link[:60]}...")
        
        if not actions:
            actions.append("📝 Research this opportunity further")
        
        return actions


# ============================================
# MAIN APPLICATION
# ============================================

class OpportunityCopilot:
    def __init__(self, profile: StudentProfile, use_openrouter_ai=True, api_key=None):
        self.profile = profile
        self.ai_router = OpenRouterAIRouter(api_key if use_openrouter_ai else None)
        self.ranking_engine = EnhancedRankingEngine(profile)
    
    def process_emails(self, emails: List[Dict]) -> List[RankedOpportunity]:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}📧 Processing {len(emails)} emails...")
        print(f"{Fore.CYAN}{'='*60}")
        
        opportunities = []
        for email in emails:
            extracted = self.ai_router.classify_and_extract(email)
            if extracted.is_opportunity:
                opportunities.append(extracted)
                print(f"{Fore.GREEN}✓ Opportunity: {extracted.subject[:50]}...")
            else:
                print(f"{Fore.RED}✗ Not an opportunity: {email.get('subject', '')[:50]}...")
        
        print(f"\n{Fore.CYAN}📊 Found {len(opportunities)} genuine opportunities")
        return self.ranking_engine.rank_opportunities(opportunities)
    
    def display_results(self, ranked: List[RankedOpportunity]):
        if not ranked:
            print(f"\n{Fore.YELLOW}⚠️ No opportunities found!")
            return
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}🏆 PERSONALIZED OPPORTUNITY RANKING")
        print(f"{Fore.CYAN}{'='*60}\n")
        
        for i, ranked_opp in enumerate(ranked, 1):
            opp = ranked_opp.opportunity
            print(f"{Fore.MAGENTA}{'─'*50}")
            print(f"{Fore.YELLOW}[#{i}] {opp.subject}")
            print(f"{Fore.CYAN}Type: {opp.opportunity_type.upper()}")
            print(f"{Fore.GREEN}Priority Score: {ranked_opp.priority_score:.1f}/100")
            print(f"{Fore.BLUE}  └─ Fit Score: {ranked_opp.fit_score:.1f}/100")
            print(f"{Fore.BLUE}  └─ Urgency Score: {ranked_opp.urgency_score:.1f}/100")
            
            if ranked_opp.detailed_breakdown:
                print(f"\n{Fore.CYAN}📊 Fit Breakdown:")
                for metric, score in ranked_opp.detailed_breakdown.items():
                    bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                    print(f"   {metric.replace('_', ' ').title()}: {bar} {score:.0f}%")
            
            print(f"\n{Fore.WHITE}💡 {ranked_opp.reasoning}")
            
            if opp.deadline:
                print(f"{Fore.RED}⏰ Deadline: {opp.deadline}")
            if opp.location:
                print(f"{Fore.CYAN}📍 Location: {opp.location}")
            if opp.compensation:
                print(f"{Fore.GREEN}💰 {opp.compensation}")
            if opp.required_skills:
                print(f"{Fore.CYAN}🔧 Skills needed: {', '.join(opp.required_skills[:4])}")
            
            print(f"\n{Fore.GREEN}✅ ACTION CHECKLIST:")
            for action in ranked_opp.action_items:
                print(f"  {action}")
            print()


def main():
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}🤖 OPPORTUNITY INBOX COPILOT - Enhanced Version")
    print(f"{Fore.CYAN}Model-Based Fit Scoring System")
    print(f"{Fore.CYAN}{'='*60}")
    
    student_profile = StudentProfile(
        degree="BS Computer Science",
        semester=6,
        cgpa=3.4,
        skills=["Python", "Machine Learning", "Data Analysis", "PyTorch"],
        interests=["AI", "Data Science", "Web Development"],
        preferred_opportunity_types=["internship", "scholarship", "fellowship"],
        financial_need=True,
        location_preference="remote",
        past_experience=["research assistant", "freelance developer"]
    )
    
    print(f"\n{Fore.GREEN}📋 Student Profile:")
    print(f"   • {student_profile.degree}, Semester {student_profile.semester}, CGPA: {student_profile.cgpa}")
    print(f"   • Skills: {', '.join(student_profile.skills)}")
    print(f"   • Looking for: {', '.join(student_profile.preferred_opportunity_types)}")
    print(f"   • Location pref: {student_profile.location_preference}")
    api_key = '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'

    
    copilot = OpportunityCopilot(student_profile, True, api_key)
    ranked = copilot.process_emails(MOCK_EMAILS)
    copilot.display_results(ranked)
    
    # Export results
    output = []
    for ro in ranked:
        output.append({
            "subject": ro.opportunity.subject,
            "priority_score": ro.priority_score,
            "fit_score": ro.fit_score,
            "urgency_score": ro.urgency_score,
            "detailed_breakdown": ro.detailed_breakdown,
            "reasoning": ro.reasoning,
            "action_items": ro.action_items
        })
    
    with open("ranked_opportunities.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n{Fore.GREEN}✅ Results saved to ranked_opportunities.json")

if __name__ == "__main__":
    main()