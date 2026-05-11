import streamlit as st
import mysql.connector
import time
import random
import re
import smtplib
from email.message import EmailMessage
import pandas as pd
from datetime import datetime, timedelta, date
from newspaper import Article
import nltk
from textblob import TextBlob
from bs4 import BeautifulSoup
import requests
import cloudscraper
from urllib.parse import urljoin
import pdfplumber
from fpdf import FPDF  
import google.generativeai as genai

genai.configure(api_key="AIzaSyC8awuOsJLUqJQH1qDeocb0w-Vi4QBKarg")
def get_pro_chat_response(user_input):
    try:
        model = genai.GenerativeModel(
            model_name='gemini-3-flash-preview',
            tools=[{"google_search_retrieval": {}}]
        )
        from datetime import date
        today = date.today().strftime("%B %d, %Y")
        full_prompt = f"Today is {today}. {user_input}"
        response = model.generate_content(full_prompt)
        return response.text
        
    except Exception as e:
        try:
            model_fallback = genai.GenerativeModel('gemini-2.5-flash')
            return model_fallback.generate_content(user_input).text
        except Exception as e2:
            return f"⚠️ API Error: {str(e2)}"
        
def get_ai_summary(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp() 
        return article.summary
    except:
        return "⚠️ Could not extract text for summarization from this source."
    
# --- INITIALIZATION ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# --- 1. CONFIGURATION ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "2005", 
    "database": "newspaper_db"
}

SENDER_EMAIL = "newsanalyser.system@gmail.com" 
SENDER_PASSWORD = "aclrhgfbczfcwpwl" 

# --- 2. CORE LOGIC ---
def get_db_connection():
    try: 
        return mysql.connector.connect(
            **DB_CONFIG,
            charset='utf8mb4',
            use_unicode=True
        )
    except: 
        return None

def check_password_strength(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))

def register_user(username, email, password):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                           (username, email, password))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error: {e}")
            return False
        finally:
            conn.close()
    return False

def send_real_otp(receiver_email, otp_code, type="Signup"):
    try:
        msg = EmailMessage()
        if type == "Signup":
            subject = "Verification Code - AI Newspaper Analyser"
            intro_text = "Thank you for choosing <b>Newspaper Analyser</b>! 🌟 We are excited to have you on board."
            body_instruction = "Please use the following 6-digit verification code to proceed. For security reasons, do not share this code with anyone."
            content_display = f"""
                <div style="text-align: center; margin: 40px 0;">
                    <span style="font-size: 36px; font-weight: bold; color: #1E3A8A; background: #f1f5f9; padding: 15px 30px; border-radius: 8px; border: 2px dashed #1E3A8A; letter-spacing: 5px;">
                        {otp_code}
                    </span>
                </div>"""
        elif type == "Report":
            subject = "Your Newspaper Analysis Report - AI Newspaper Analyser"
            intro_text = "As per your request, we have generated your newspaper summary and sentiment analysis."
            body_instruction = "Below are the details of your requested analysis:"
            content_display = f"""
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border-left: 5px solid #1E3A8A; margin: 30px 0; font-size: 15px; color: #1e293b; white-space: pre-wrap;">
                    {otp_code}
                </div>"""
        else:
            subject = "Password Reset Request - AI Newspaper Analyser"
            intro_text = "As per your request, we are sending this code to help you reset your password safely."
            body_instruction = "Please use the following 6-digit verification code to proceed. For security reasons, do not share this code with anyone."
            content_display = f"""
                <div style="text-align: center; margin: 40px 0;">
                    <span style="font-size: 36px; font-weight: bold; color: #1E3A8A; background: #f1f5f9; padding: 15px 30px; border-radius: 8px; border: 2px dashed #1E3A8A; letter-spacing: 5px;">
                        {otp_code}
                    </span>
                </div>"""

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
            <div style="background-color: #1E3A8A; padding: 25px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Newspaper Analyser</h1>
            </div>
            <div style="padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 10px 10px; line-height: 1.6;">
                <p>Dear User,</p>
                <p>{intro_text}</p>
                <p>{body_instruction}</p>               
                {content_display}
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="font-size: 13px; color: #94a3b8; text-align: center;">
                    Best Regards,<br>
                    Team Newspaper Analyser
                </p>
            </div>
        </body>
        </html>
        """       
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg.add_alternative(html_content, subtype='html')      
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def update_user_password(email, new_password):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"❌ Database Update Error: {e}")
            return False
        finally:
            conn.close()
    return False

def get_sentiment(text):

    """AI Sentiment Analysis using TextBlob"""
    analysis = TextBlob(text)
    if analysis.sentiment.polarity > 0.15:
        return "Positive"
    elif analysis.sentiment.polarity < 0:
        return "Negative"
    else:
        return "Neutral"

def check_login_type(u, p, login_role):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            if login_role == "admin":
                query = "SELECT admin_name, admin_password FROM admin WHERE admin_name = %s"
                cursor.execute(query, (u,))
            else:
                query = "SELECT username, password, is_premium, current_plan, plan_expiry FROM users WHERE username = %s OR email = %s"
                cursor.execute(query, (u, u))               
            res = cursor.fetchone()
            conn.close()

            if res:
                db_pass = res['admin_password'] if login_role == "admin" else res['password']
                
                if p == db_pass:
                    name = res['admin_name'] if login_role == "admin" else res['username']
                    premium = 1 if login_role == "admin" else res.get('is_premium', 0)
                    plan = "Lifetime Founder" if login_role == "admin" else res.get('current_plan', 'Free')
                    expiry = None if login_role == "admin" else res.get('plan_expiry')
                    return name, login_role, "Success", premium, plan, expiry
                else:
                    return None, None, "Incorrect Password", 0, None, None
            else:
                return None, None, "ID doesn't exist", 0, None, None
    except Exception as e:
        return None, None, str(e), 0, None, None

def save_to_daily_feed(paper, cat, title, url):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # 'INSERT IGNORE' prevents duplicate headlines from saving twice
            query = """
                INSERT IGNORE INTO daily_news_feed (paper_name, category, headline, url, scrape_date)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (paper, cat, title, url, date.today()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database Sync Error: {e}")
            return False
    return False

def fetch_all_headlines(paper, category, selected_date):
    import cloudscraper
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import time, random
    from datetime import date,timedelta 

    # --- ROUTE A: DATABASE FETCH ---
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # FIX 1: Ensure date_str is exactly what MySQL expects
            date_str = selected_date.strftime('%Y-%m-%d')
            
            query = "SELECT headline as title, url FROM daily_news_feed WHERE paper_name = %s AND category = %s AND scrape_date = %s"
            cursor.execute(query, (paper, category, date_str))
            db_results = cursor.fetchall()
            conn.close()
            
            if db_results:
                return db_results
    except Exception as e:
        print(f"❌ Database Retrieval Error: {e}")

    # --- ROUTE B: LIVE SCRAPER ---
    scraper = cloudscraper.create_scraper() 
    
    category_keywords = {
        "National": ["india", "national", "delhi", "state", "centre", "bharat","government", "ministry"],
        "International": ["world", "global", "us", "uk", "international", "foreign", "russia", "china", "united states", "europe", "africa", "asia", "middle east", "summit", "g20", "nato", "diplomacy", "embassy", "consulate", "refugee", "migration", "sanctions", "treaty", "alliance", "conflict", "peace talks", "trade war", "climate summit", "global economy", "international relations", "world leaders", "foreign policy", "geopolitics"],
        "Sports": ["cricket", "ipl", "football", "tennis", "sports", "match", "score", "wicket", "stadium", "olympics", "fifa", "world cup", "badminton", "hockey", "kabaddi", "athletics", "nba", "nfl", "mlb", "boxing", "mma", "golf", "formula 1", "motorsport", "cycling", "rugby", "swimming", "volleyball", "table tennis", "chess", "esports"],
        "Business": ["market", "sensex", "nifty", "economy", "finance", "business", "stock", "rupee", "gst", "inflation", "unemployment", "gdp", "ipo", "startups", "cryptocurrency", "bitcoin", "blockchain", "real estate", "automobile industry", "e-commerce", "retail", "banking", "investment", "venture capital"],
        "Technology": ["tech", "ai", "gadgets", "mobile", "software", "google", "meta", "iphone", "cyber", "digital", "innovation", "startups", "blockchain", "cryptocurrency", "space", "nasa", "spacex", "tesla", "electric vehicles", "renewable energy", "5g", "internet of things", "virtual reality", "augmented reality", "quantum computing"],
        "Politics": ["election", "bjp", "congress", "politics", "minister", "cabinet", "parliament", "government", "policy", "campaign", "vote", "democracy", "opposition", "coalition", "legislation", "political party", "political leader", "political rally", "political debate", "political scandal", "political reform", "political campaign", "political strategy", "political analysis", "political commentary", "political opinion", "political news"],
        "Lifestyle": ["health", "fashion", "travel", "food", "lifestyle", "beauty", "yoga", "wellness", "fitness", "mental health", "celebrity", "entertainment", "movies", "music", "art", "culture", "books", "relationships", "home decor", "gardening", "parenting", "self-care", "personal finance", "hobbies", "leisure", "luxury", "lifestyle trends", "lifestyle tips", "lifestyle advice", "lifestyle news"],
        "Weather": ["rain", "climate", "temperature", "forecast", "monsoon", "weather", "heat", "storm", "humidity", "precipitation"]
    }
    
    keywords = category_keywords.get(category, [category.lower()])
    url_cat = category.lower()

    live_map = {
        "The Hindu": f"https://www.thehindu.com/news/{'national' if url_cat=='politics' or url_cat=='national' else url_cat}/",
        "Times of India": f"https://timesofindia.indiatimes.com/india",
        "Deccan Herald": f"https://www.deccanherald.com/{url_cat}",
        "Indian Express": f"https://indianexpress.com/section/{'world' if url_cat=='international' else url_cat}/",
        "Economic Times": f"https://economictimes.indiatimes.com/news/economy",
        "Hindustan Times": f"https://www.hindustantimes.com/{'india-news' if url_cat=='national' else url_cat}"
    }

    try:
        target_url = live_map.get(paper)
        if not target_url: return []

        # Human-like delay ⏳
        time.sleep(random.uniform(1.0, 2.0)) 
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        response = scraper.get(target_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        articles_list = []
        seen_urls = set()

        # FIX 3: More flexible link finding
        for link in soup.find_all('a', href=True):
            title = link.get_text().strip()
            href = link.get('href', '')
            
            # Filter out very short text or menu items
            if len(title) > 40: 
                full_url = urljoin(target_url, href)
                
                # Keyword check to ensure the headline belongs to the category
                if any(kw in title.lower() or kw in href.lower() for kw in keywords):
                    if full_url not in seen_urls:
                        # Clean links only
                        if not any(x in full_url for x in ['/author/', '/tag/', '/topic/', '/profile/', 'javascript:']):
                            articles_list.append({"title": title, "url": full_url})
                            seen_urls.add(full_url)
            
            if len(articles_list) >= 10: break
            
        return articles_list
    except Exception as e:
        return []
    
# --- PDF GENERATION ---
def generate_pdf_report(title, summary, date_str):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io
    import html

    def safe_text(text):
        if not text:
            return ""
        # 1. Decode bytes if necessary
        if isinstance(text, (bytes, bytearray)):
            text = text.decode('utf-8', 'ignore')
        # 2. Escape HTML special characters (&, <, >, ", ')
        return html.escape(str(text))

    buffer = io.BytesIO()

    # Create the PDF Document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Title ---
    story.append(Paragraph("<b>AI News Report</b>", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))

    # --- Headline ---
    headline_style = ParagraphStyle("Headline", parent=styles["Heading2"], spaceAfter=6)
    story.append(Paragraph(f"<b>Headline:</b> {safe_text(title)}", headline_style))
    story.append(Spacer(1, 0.1 * inch))

    # --- Summary ---
    story.append(Paragraph("<b>Summary:</b>", styles["Heading3"]))
    story.append(Paragraph(safe_text(summary), styles["Normal"]))

    doc.build(story)
    
    # Return the PDF as bytes
    return buffer.getvalue()

def fetch_ai_news_by_details(paper, category, selected_date):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    news_map = {
        "The Hindu": {"base": "https://www.thehindu.com/", "paths": {"National": "news/national/", "Sports": "sport/", "Business": "business/", "Technology": "sci-tech/technology/", "Politics": "news/national/", "International": "news/international/", "Lifestyle": "life-and-style/", "Weather": "sci-tech/agriculture/"}},
        "Times of India": {"base": "https://timesofindia.indiatimes.com/", "paths": {"National": "india/", "Sports": "sports/", "Business": "business/", "Technology": "technology/", "Politics": "india/", "International": "world/", "Lifestyle": "life-style/", "Weather": "environment/global-warming/"}},
        "Deccan Herald": {"base": "https://www.deccanherald.com/", "paths": {"National": "india/", "Sports": "sports/", "Business": "business/", "Technology": "science-and-technology/", "Politics": "india/politics/", "International": "world/", "Lifestyle": "lifestyle/", "Weather": "science-and-technology/environment/"}},
        "Indian Express": {"base": "https://indianexpress.com/", "paths": {"National": "section/india/", "Sports": "section/sports/", "Business": "section/business/", "Technology": "section/technology/", "Politics": "section/political-pulse/", "International": "section/world/", "Lifestyle": "section/lifestyle/", "Weather": "section/cities/"}},
        "Economic Times": {"base": "https://economictimes.indiatimes.com/", "paths": {"National": "news/india/", "Sports": "news/sports/", "Business": "business/", "Technology": "tech/", "Politics": "news/politics/", "International": "news/international/", "Lifestyle": "magazines/panache/", "Weather": "news/environment/"}},
        "Hindustan Times": {"base": "https://www.hindustantimes.com/", "paths": {"National": "india-news/", "Sports": "sports/", "Business": "business/", "Technology": "it-services/", "Politics": "india-news/", "International": "world-news/", "Lifestyle": "lifestyle/", "Weather": "environment/"}}
    }
    try:
        if paper in news_map and category in news_map[paper]["paths"]:
            target_url = news_map[paper]["base"] + news_map[paper]["paths"][category]
            response = scraper.get(target_url, timeout=15)
            if response.status_code != 200: return None
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            article_url = None
            for link in links:
                href = link.get('href', '')
                if len(href) > 45 and '-' in href and not any(x in href for x in ['/author/', '/tag/', '/topic/']):
                    article_url = urljoin(target_url, href)
                    break
            if article_url:
                article_page = scraper.get(article_url, timeout=10)
                article = Article(article_url)
                article.download(input_html=article_page.text)
                article.parse()
                article.nlp()
                analysis = TextBlob(article.text)
                sentiment = "Positive" if analysis.sentiment.polarity > 0.1 else "Negative" if analysis.sentiment.polarity < -0.1 else "Neutral"
                return {"title": article.title, "summary": article.summary, "sentiment": sentiment, "image_url": article.top_image}
        return None
    except Exception: return None

def save_to_history(username, paper, cat, sentiment, title):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # 🔍 DUPLICATE CHECK: Prevents the same article from clogging your trends
            check_query = """
                SELECT COUNT(*) FROM history 
                WHERE username = %s AND headline = %s AND analysis_date = %s
            """
            cursor.execute(check_query, (username, title, date.today()))
            exists = cursor.fetchone()[0]

            if exists == 0:
                # If it doesn't exist, INSERT IT
                insert_query = """
                    INSERT INTO history (username, paper_name, category, sentiment, analysis_date, headline) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (username, paper, cat, sentiment, date.today(), title))
                conn.commit()           
            conn.close()
            return True
        except Exception as e:
            st.error(f"History Logging Error: {e}")
            return False
    return False
    
def save_to_archive(paper, cat, head, summ, img, n_date):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO news_archive (username, paper_name, category, headline, summary, image_url, news_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (st.session_state.username, paper, cat, head, summ, img, n_date))
        conn.commit()
        conn.close()
        return True
    except Exception: return False

def delete_news_item(news_id):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM news_archive WHERE news_id = %s", (news_id,))
            conn.commit()
            conn.close()
            return True
    except Exception: return False
    
def analyze_pdf_content(pdf_file, category):
    try:
        pdf_file.seek(0)
        category_headers = {
            "National": ["india", "national", "govt", "politics"],
            "Sports": ["sport", "cricket", "score", "match"],
            "Business": ["business", "market", "stock", "shares"],
            "Weather": ["weather", "climate", "forecast", "monsoon"]
        }
        relevant_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                top_area = page.crop((0, 0, page.width, page.height * 0.15))
                header_text = top_area.extract_text()
                if header_text:
                    search_terms = category_headers.get(category, [])
                    if any(term in header_text.lower() for term in search_terms):
                        page_content = page.extract_text()
                        if page_content: relevant_text += page_content + " "
        if not relevant_text.strip(): return {"error": f"⚠️ Section '{category}' not found."}
        sentences = nltk.sent_tokenize(relevant_text)
        clean_sentences = [s for s in sentences if len(s) > 50]
        summary = " ".join(clean_sentences[:4]).replace('\n', ' ')
        analysis = TextBlob(summary)
        sentiment = "Positive" if analysis.sentiment.polarity > 0.1 else "Negative" if analysis.sentiment.polarity < -0.1 else "Neutral"
        return {"title": f"📄 PDF {category} Analysis", "summary": summary, "sentiment": sentiment}
    except Exception as e: return {"error": f"❌ Error: {str(e)}"}

def generate_bulk_archive_pdf(username, df):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io
    import html

    # Helper to clean data from the database
    def safe_text(text):
        if not text: return ""
        # Convert bytes to string if needed
        if isinstance(text, (bytes, bytearray)):
            text = text.decode('utf-8', 'ignore')
        # Escape special characters for ReportLab Paragraphs
        return html.escape(str(text))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    story = []

    # --- MAIN HEADER ---
    story.append(Paragraph(f"<b>Personal News Archive: {username}</b>", styles["Title"]))
    story.append(Paragraph(f"Report Generated on: {pd.to_datetime('today').strftime('%d %b, %Y')}", styles["Normal"]))
    story.append(Paragraph(f"Total Articles: {len(df)}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # --- CONTENT LOOP ---
    for idx, row in df.iterrows():
        # Title Style (Matches your Navy Blue theme)
        t_style = ParagraphStyle("ArticleTitle", parent=styles["Heading2"], textColor="#1E3A8A")
        story.append(Paragraph(f"{idx+1}. {safe_text(row['title'])}", t_style))
        
        # Meta Info
        date_str = row['saved_at'].strftime('%d %b, %Y %I:%M %p')
        story.append(Paragraph(f"<i>Category: {row['category']} | Saved on: {date_str}</i>", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))
        
        # Summary
        b_style = ParagraphStyle("ArticleBody", parent=styles["Normal"], leading=14)
        story.append(Paragraph(safe_text(row['summary']), b_style))
        
        # Divider Line
        story.append(Spacer(1, 0.2 * inch))
        story.append(HRFlowable(width="100%", thickness=1, color="lightgrey"))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    return buffer.getvalue() # Returns raw bytes

def set_bg_css():
    if st.session_state.page in ['home', 'login', 'signup', 'forgot']:
        bg_img_url = "https://media.istockphoto.com/id/1355531876/vector/newspaper-paper-grunge-vintage-old-aged-texture-background.jpg?s=612x612&w=0&k=20&c=nBD7LK9Iul20lb41WJoDKJoOA_mB6SehYSBLViLZboY="
        
        st.markdown(f"""
            <style>
            /* 1. ANIMATED NEWSPAPER BACKGROUND */
            .stApp {{
                background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.7)), url("{bg_img_url}");
                background-size: 600px 600px;
                background-repeat: repeat;
                animation: moveBackground 40s linear infinite;
            }}
            @keyframes moveBackground {{
                from {{ background-position: 0 0; }}
                to {{ background-position: 600px 600px; }}
            }}

            /* 2. GLOBAL TEXT STYLES (White with Shadow) */
            h1, h2, h3, p, label {{
                color: #FFFFFF !important;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.8) !important;
            }}

            /* 3. BUTTON STYLING - THE RESET */
            div.stButton > button {{
                background-color: #FFFFFF !important; 
                border: 2px solid #FFFFFF !important;
                border-radius: 8px !important;
                width: 100% !important;
                transition: all 0.3s ease-in-out !important;
                height: 3em !important;
            }}

            /* Targeting all text layers inside the button for Black color */
            div.stButton > button p, 
            div.stButton > button span,
            div.stButton > button div {{
                color: #000000 !important;
                text-shadow: none !important;
                font-weight: light !important;
            }}

            /* --- THE FIX: PURPLE STYLE HOVER EFFECT --- */
            /* When hovering, the whole button becomes a white outline */
            div.stButton > button:hover {{
                background-color: rgba(255,255,255,0) !important; /* Fully Transparent */
                border: 2px solid #FFFFFF !important;           /* White Border */
            }}

            /* Ensures the text stays BLACK when the button goes transparent */
            div.stButton > button:hover p, 
            div.stButton > button:hover span,
            div.stButton > button:hover div {{
                color: #FFFFFF !important;
                background-color: transparent !important;
            }}
            /* 4. NEW: BLACK BORDER FOR st.container(border=True) */
            [data-testid="stVerticalBlockBorderWrapper"] > div:first-child {{
                border: 2px solid #000000 !important; /* Force Black Border */
                background-color: rgba(255, 255, 255, 0.1) !important; /* Optional: Slight glass look */
                border-radius: 12px !important;
            }}

            /* 5. Sidebar transparency */
            [data-testid="stSidebar"] {{
                background-color: transparent !important;
            }}
            </style>
            """, unsafe_allow_html=True)
        
# --- 4. NAVIGATION ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'view_mode' not in st.session_state: st.session_state.view_mode = "home"
if 'email_verified' not in st.session_state: st.session_state.email_verified = False

def switch_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- 5. PAGE FUNCTIONS ---
def show_home():
    set_bg_css()
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;600&family=Playfair+Display:wght@700&display=swap');
            .main-title { font-family: 'Playfair Display', serif; font-size: 65px; color: #FFFFFF; text-align: center; text-shadow: 0px 0px 20px rgba(255, 255, 255, 0.4); }
            .description-paragraph { font-family: 'Poppins', sans-serif; font-size: 20px; line-height: 1.8; color: #F8FAFC; text-align: center; max-width: 900px; margin: 0 auto; padding: 20px; font-weight: 300; }
            .highlight { color: #38BDF8; font-weight: 600; }
            </style>
        <div class="main-title">Newspaper Analyser</div>
        <p class="description-paragraph"> Experience the future of news with our <span class="highlight">AI-powered Newspaper Analyser</span>. This platform bridges the gap between dense data and quick insights, using advanced AI to extract and summarize critical information from <span class="highlight">Live Headlines</span> and <span class="highlight">PDF Editions</span>. Stay informed effortlessly with smart categorization and real-time sentiment analysis.
        </p><br>
        """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("Login", use_container_width=True): switch_page('login')
    if c2.button("Sign Up", use_container_width=True): switch_page('signup')


def show_login():
    set_bg_css()
    st.markdown("<h2 style='color: white; text-align: center;'>🔐 Login</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        tab_user, tab_admin = st.tabs(["👤 User Login", "🛠️ Admin Login"])
        
        with tab_user:
            with st.form("user_login_form"):
                u = st.text_input("Username / Email", key="login_user")
                p = st.text_input("Password", type="password", key="login_pass")
                submit_user = st.form_submit_button("User Login", type="primary", use_container_width=True)
                
                if submit_user:
                    result = check_login_type(u, p, "user")
                    
                    if result:
                        # Unpack 6 values (name, role, message, premium, plan, expiry)
                        name, role, message, premium_status, user_plan, expiry_date = result

                        if role == "user":
                            st.session_state.username = name
                            st.session_state.user_email = u 
                            st.session_state.is_premium = bool(premium_status)
                            
                            # --- IMPORTANT: LOAD PLAN DATA ---
                            st.session_state.user_plan = user_plan if user_plan else "Free"
                            st.session_state.expiry_date = expiry_date

                            # --- NEW: FETCH PROFILE PHOTO FROM DATABASE ---
                            conn = get_db_connection()
                            if conn:
                                cursor = conn.cursor(dictionary=True)
                                # Fetch the profile_pic column for this user
                                cursor.execute("SELECT profile_pic FROM users WHERE username = %s", (name,))
                                db_res = cursor.fetchone()
                                if db_res and db_res['profile_pic']:
                                    st.session_state.profile_pic = db_res['profile_pic']
                                else:
                                    st.session_state.profile_pic = "https://png.pngtree.com/png-vector/20191110/ourmid/pngtree-avatar-icon-profile-icon-member-login-vector-isolated-png-image_1978396.jpg"
                                conn.close()
                            
                            st.session_state.view_mode = "home"
                            st.success(f"Welcome back {name}! {'👑' if premium_status else ''}")
                            import time
                            time.sleep(0.5)
                            switch_page('dashboard')
                        
                        elif "Password" in message:
                            st.error(f"❌ Incorrect Password. Please try again.")
                        elif "exist" in message.lower() or "Invalid" in message:
                            st.error(f"❌ Username/Email doesn't exist. Please register first.")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Username/Email doesn't exist.")

        with tab_admin:
            with st.form("admin_login_form"):
                au = st.text_input("Admin ID", key="admin_user")
                ap = st.text_input("Admin Password", type="password", key="admin_pass")
                submit_admin = st.form_submit_button("Admin Login", type="primary", use_container_width=True)
                
                if submit_admin:
                    # Admin login returns name and role from the 'admin' table
                    name, role, message, premium, plan, expiry = check_login_type(au, ap, "admin")
                    
                    if role == "admin":
                        # 1. Store the Admin's name in session state
                        st.session_state.username = name
                        st.session_state.user_plan = "Lifetime Founder"
                        st.session_state.expiry_date = None
                        
                        # 2. Show the personalized greeting 🌟
                        st.success(f"Welcome back {name}! 🔐")
                        
                        # 3. Brief pause so you can see the message before switching
                        import time
                        time.sleep(1)
                        
                        # 4. Redirect to the admin dashboard
                        st.session_state.view_mode = "admin_dashboard"
                        switch_page('admin_dashboard')
                    else:
                        st.error(f"❌ {message}")

        if st.button("Forgot Password?"): 
            switch_page('forgot')         
    
    if st.button("← Back to Home"): 
        switch_page('home')

def show_signup():
    set_bg_css()
    st.markdown("<h2 style='color: white; text-align: center;'>📝 Sign Up</h2>", unsafe_allow_html=True)
    with st.container():
        if not st.session_state.get('email_verified'):
            # --- Form 1: For sending the OTP ---
            with st.form("signup_otp_form"):
                # Initialize username in session state if not present
                if 'temp_u' not in st.session_state: # temp_u means "temporary username" that holds the value during the OTP verification step even if the form reruns
                    st.session_state.temp_u = ""

                # The Username Textbox (Linked to session_state)
                new_u = st.text_input("Username", value=st.session_state.temp_u, key="signup_user_field")
                
                # --- NEW: RECOMMENDATION SECTION ---
                # This only shows if a conflict was found in the previous run
                if st.session_state.get('show_sugs'):
                    st.error(f"❌ '{new_u}' is taken! Please choose another username.")
                    st.markdown("#### ✨ Suggested names for you")
                    cols = st.columns(3)
                    for i, sug in enumerate(st.session_state.sugs_list):
                        # When clicked, this button updates the state and reruns the form
                        if cols[i].form_submit_button(sug):
                            st.session_state.temp_u = sug
                            st.rerun()
                
                new_e = st.text_input("Email", key="signup_email_field")
                submit_otp = st.form_submit_button("Send Verification Code", use_container_width=True, type="primary")
                
                if submit_otp:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (new_e, new_u))
                    existing = cursor.fetchone()
                    conn.close()

                    if existing:
                        if existing['email'] == new_e:
                            st.error(f"❌ '{new_e}' is already registered. Please Login.")
                        else:
                            # Set flags to show suggestions on next rerun
                            st.session_state.show_sugs = True
                            prefix = new_e.split('@')[0] if "@" in new_e else "user"
                            st.session_state.sugs_list = [f"{prefix}{random.randint(10,99)}", f"{prefix}_ai", f"{prefix}.news"]
                            st.error(f"❌ '{new_u}' is taken!")
                            st.rerun()
                    else:
                        # Success path
                        otp = str(random.randint(100000, 999999))
                        if send_real_otp(new_e, otp, "Signup"):
                            st.session_state.signup_otp = otp
                            st.session_state.show_sugs = False # Clear suggestions
                            st.toast("Code sent! 📩")
            
            # --- Form 2: The 6-Box Code Entry ---
            if st.session_state.get('signup_otp'):
                with st.form("signup_confirm_form"):
                    st.write("Enter 6-Digit Code")
                    cols = st.columns(6)
                    otp_digits = []
                    for i in range(6):
                        with cols[i]:
                            digit = st.text_input("", key=f"signup_otp_{i}", max_chars=1, label_visibility="collapsed")
                            otp_digits.append(digit)
                    
                    full_code = "".join(otp_digits)
                    submit_confirm = st.form_submit_button("Confirm Code", use_container_width=True,type="primary")
                    
                    if submit_confirm:
                        if full_code == st.session_state.signup_otp:
                            st.session_state.locked_u = new_u
                            st.session_state.locked_e = new_e
                            st.session_state.email_verified = True
                            st.rerun()
                        else:
                            st.error("❌ Invalid Code. Please try again.")
        else:
            # --- Form 3: Final Password & Date Capture ---
            with st.form("signup_finalize_form"):
                p = st.text_input("Create Password", type="password")
                con_p = st.text_input("Confirm Password", type="password")
                submit_reg = st.form_submit_button("Complete Registration", type="primary", use_container_width=True)
                
                if submit_reg:
                    # 1. Check if they match
                    if p != con_p:
                        st.error("❌ Passwords do not match. Please re-type.")
                    
                    # 2. Check if the length and strength are okay
                    # Fixed: Used len(p) for comparison
                    elif len(p) < 8 or not check_password_strength(p):
                        st.warning("⚠️ Min 8 characters, Uppercase, Lowercase, Number & Special character.")

                    else:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            # Direct insertion with the timestamp line
                            cursor.execute(
                                "INSERT INTO users (username, email, password, created_at) VALUES (%s, %s, %s, %s)", 
                                (st.session_state.locked_u, st.session_state.locked_e, p, datetime.now())
                            )
                            conn.commit()
                            st.balloons()
                            st.success("Welcome! Account created successfully. Redirecting...")
                            time.sleep(2)
                            # Clear signup states before leaving
                            st.session_state.email_verified = False
                            switch_page('login')
                        except Exception as e:
                            st.error(f"Error saving to database: {e}")
                        finally:
                            conn.close()
    if st.button("← Back to Home"): 
        switch_page('home')

def show_forgot():
    set_bg_css()
    st.markdown("<h2 style='color: white; text-align: center;'>🔑 Reset Password</h2>", unsafe_allow_html=True)
    
    # CSS for the 6-Digit OTP Boxes
    st.markdown("""
        <style>
        .otp-container { display: flex; justify-content: center; gap: 10px; margin: 20px 0; }
        .otp-box { 
            width: 45px; height: 55px; text-align: center; font-size: 24px; 
            font-weight: bold; border: 2px solid #38BDF8; border-radius: 8px; 
            background: rgba(255,255,255,0.1); color: white;
        }
        .otp-box:focus { border-color: #FFFFFF; outline: none; box-shadow: 0 0 10px #38BDF8; }
        </style>
    """, unsafe_allow_html=True)

    # --- Container without border to prevent double-border ---
    with st.container():
        # 1. & 2. INPUT MODE: Username or Email & SEND OTP
        if not st.session_state.get('reset_otp_sent'):
            input_type = st.radio("Reset via:", ["Email ID", "Username"], horizontal=True, key="forgot_radio")
            with st.form("forgot_send_form"):
                user_input = st.text_input(f"Enter your Registered {input_type}")
                
                # Form submit button for Enter key support
                submit_forgot = st.form_submit_button("Send Reset Code", use_container_width=True, type="primary")
                
                if submit_forgot:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    if input_type == "Email ID":
                        cursor.execute("SELECT email FROM users WHERE email = %s", (user_input,))
                    else:
                        cursor.execute("SELECT email FROM users WHERE username = %s", (user_input,))
                    
                    user_data = cursor.fetchone()
                    if user_data:
                        registered_email = user_data['email']
                        otp = str(random.randint(100000, 999999))
                        if send_real_otp(registered_email, otp, "Forgot Password"):
                            st.session_state.reset_otp_sent = otp
                            st.session_state.target_email = registered_email
                            st.success(f"OTP sent to: {registered_email[:3]}***@{registered_email.split('@')[1]}")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error(f"❌ The {input_type} provided does not match our records.")
                    conn.close()

        # 3. VERIFICATION MODE
        elif st.session_state.get('reset_otp_sent') and not st.session_state.get('email_verified'):
            with st.form("forgot_verify_form"):
                st.write("Enter 6-Digit Code")
                cols = st.columns(6)
                otp_digits = []
                for i in range(6):
                    with cols[i]:
                        digit = st.text_input("", key=f"otp_{i}", max_chars=1, label_visibility="collapsed")
                        otp_digits.append(digit)
                
                full_code = "".join(otp_digits)
                submit_verify = st.form_submit_button("Verify Code", use_container_width=True, type="primary")
                
                if submit_verify:
                    if full_code == st.session_state.reset_otp_sent:
                        st.session_state.email_verified = True
                        st.toast("Code Verified! ✅")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Code. Please try again.")

        # 4. RESET PASSWORD MODE
        elif st.session_state.get('email_verified'):
            with st.form("forgot_update_form"):
                st.success(f"Verified: {st.session_state.target_email}")
                np = st.text_input("Create New Password", type="password")
                cp = st.text_input("Confirm New Password", type="password")
                
                submit_update = st.form_submit_button("Update & Login", use_container_width=True, type="primary")
                
                if submit_update:
                    # Check 1: Do they match?
                    if np != cp:
                        st.error("❌ Passwords do not match. Please re-type.")
                    
                    # Check 2: If they match, is the strength okay?
                    elif len(np) < 8:
                        st.warning("⚠️ Min 8 characters, Uppercase, Lowercase, Number & Special character.")
                    
                    # Check 3: Everything is perfect, update the DB
                    else:
                        if update_user_password(st.session_state.target_email, np):
                            st.balloons()
                            # Clear session states
                            del st.session_state['reset_otp_sent']
                            del st.session_state['email_verified']
                            st.success("Password Updated Successfully! Redirecting to Login...")
                            time.sleep(5)
                            switch_page('login')
    st.markdown("---") # Visual separator
    if st.button("← Back to Login"):
        # Clear any reset progress if they go back
        if 'reset_otp_sent' in st.session_state: del st.session_state['reset_otp_sent']
        if 'email_verified' in st.session_state: del st.session_state['email_verified']
        switch_page('login')

def safe_clean_text(text):
    # If the input is already bytes/bytearray, decode it to a string first
    if isinstance(text, (bytearray, bytes)):
        text = text.decode('utf-8', 'ignore')
    
    # Now that it's a string, clean it for the PDF
    return text.encode('ascii', 'ignore').decode('ascii')

def log_news_history(paper_name, category, sentiment):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO history (username, paper_name, category, sentiment, analysis_date) 
            VALUES (%s, %s, %s, %s, %s)
        """
        # Using date.today() for the analysis_date column
        cursor.execute(query, (
            st.session_state.username, 
            paper_name, 
            category, 
            sentiment, 
            date.today()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Logging Error: {e}")

def send_announcement_email(receiver_email, announcement_text):
    try:
        msg = EmailMessage()
        subject = "📢 New Update from Newspaper Analyser"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="background-color: #f4f4f7; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <div style="background-color: #1E3A8A; padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">Newspaper Analyser</h1>
                    </div>

                    <!-- Body -->
                    <div style="padding: 40px; text-align: center;">
                        <h2 style="color: #1E3A8A; margin-bottom: 20px;">System Announcement 📢</h2>
                        
                        <!-- Announcement Box -->
                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td align="center">
                                    <table width="90%" cellpadding="0" cellspacing="0" border="0"
                                        style="background-color: #f0f9ff;
                                               border: 1px solid #bae6fd;
                                               border-left: 8px solid #38BDF8;
                                               border-radius: 8px;">
                                        <tr>
                                            <td align="center" style="padding: 30px;">
                                                <p style="font-size: 18px; color: #0369a1; font-weight: bold; margin: 0; text-align: left;">
                                                    {announcement_text}
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>

                        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                        
                        <!-- Footer -->
                        <p style="font-size: 12px; color: #94a3b8; line-height: 1.4; text-align: center;">
                            You are receiving this because you are a registered user of <b>Newspaper Analyser</b>. 
                            If you have any questions, please contact our support team.
                        </p>
                    </div>

                </div>
            </div>
        </body>
        </html>
        """

        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg.add_alternative(html_content, subtype='html')
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True

    except Exception as e:
        print(f"Announcement Email Error: {e}")
        return False

def fetch_google_news_via_api(query="latest"):
    API_KEY = "8063f3522600b5340f346928c5079859" 
    url = f"https://gnews.io/api/v4/search?q={query}&lang=en&country=in&max=10&apikey={API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('articles', [])
        return []
    except:
        return []

if 'MASTER_PLANS' not in st.session_state:
    st.session_state.MASTER_PLANS = {
        "Trial Spark": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Unlimited Archive Storage for 24 Hours", "Email Summary Report"]},
        "Weekly Quick": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Unlimited Archive Storage for 7 Days", "Email Summary Report", "PDF Download for Summary"]},
        "Monthly Lite": {"features": ["Multi-Language Translation", "Unlimited Archive Storage for 30 Days", "Email Summary Report", "PDF Download for Summary"]},
        "Monthly Plus": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Summary Report", "Unlimited Archive Storage for 30 Days", "PDF Download for Summary"]},
        "Quarterly Scholar": {"features": ["Multi-Language Translation", "Bulk PDF Export", "50 Archive Storage Slots (90 Days)", "Email Summary Report", "PDF Download for Summary"]},
        "Quarterly Pro": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Summary Report", "Unlimited Archive Storage", "Bulk PDF Export", "PDF Download for Summary", "News API Access"]},
        "Half-Yearly Saver": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Summary Report", "80 Archive Storage Slots (180 Days)", "Bulk PDF Export", "Priority Support"]},
        "Premium Annual": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Summary Report", "100 Archive Storage Slots (365 Days)", "Bulk PDF Export", "Priority Support", "Early Access to New Features","News API Access"]},
        "Elite Annual": {"features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Summary Report", "Unlimited Archive Storage", "Bulk PDF Export", "Priority Support","PDF Download for Summary", "Early Access to New Features", "News API Access"]}
    }

def is_feature_allowed(feature_name):
    current_plan = st.session_state.get('user_plan', 'Free')
    expiry = st.session_state.get('plan_expiry')
    
    # 1. Bypass for Archive
    if feature_name == "Save to Archive":
        return True, "Success"

    # 2. Expiry Check
    from datetime import date
    if expiry and isinstance(expiry, date):
        if expiry < date.today():
            return False, f"❌ Your {current_plan} plan expired on {expiry}."

    all_plans = st.session_state.get('MASTER_PLANS', {})
    
    if current_plan in all_plans:
        allowed_features = all_plans[current_plan].get("features", [])
        if feature_name in allowed_features or "Unlimited Access Forever" in allowed_features:
            return True, "Success"
            
    return False, f"🔒 Feature not included in {current_plan} plan."
   
def show_dashboard():
    from datetime import date, timedelta
    import pandas as pd
    from io import BytesIO
    from fpdf import FPDF 
    import time

    # --- 1. INITIALIZE SESSION STATES ---
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "home"
    if 'theme' not in st.session_state:
        st.session_state.theme = "Light" 
    if 'show_pass_reset' not in st.session_state:
        st.session_state.show_pass_reset = False
    if 'profile_pic' not in st.session_state:
        st.session_state.profile_pic = "https://png.pngtree.com/png-vector/20191110/ourmid/pngtree-avatar-icon-profile-icon-member-login-vector-isolated-png-image_1978396.jpg"
    if 'bio' not in st.session_state:
        st.session_state.bio = ""
    if 'confirm_logout' not in st.session_state:
        st.session_state.confirm_logout = False
    # Add this line near your other session_state initializations
    if 'target_article_url' not in st.session_state: 
        st.session_state.target_article_url = ""
    
    if 'sel_paper' not in st.session_state: st.session_state.sel_paper = ""
    if 'sel_cat' not in st.session_state: st.session_state.sel_cat = ""
    if 'sel_date' not in st.session_state: st.session_state.sel_date = date.today()
    # FIND THIS IN YOUR SIDEBAR CODE:
    user_plan = st.session_state.get('user_plan', 'Free')
    expiry = st.session_state.get('expiry_date')

    if user_plan != "Free" and expiry:
        # Convert to date object if it's a string from the DB
        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
            except:
                pass # Handle if format is different
            
        if expiry < date.today():
            # 1. Update Database immediately
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                # Also resetting plan_expiry to NULL so it doesn't keep triggering
                cursor.execute("UPDATE users SET is_premium = 0, current_plan = 'Free' WHERE username = %s", (st.session_state.username,))
                conn.commit()
                conn.close()
            
            # 2. Update Session State so the UI changes immediately
            st.session_state.is_premium = False
            st.session_state.user_plan = "Free"
            st.session_state.expiry_date = None
            st.warning(f"⚠️ Your {user_plan} plan expired on {expiry}. You have been moved to the Free tier.")
    # --- 2. THEME LOGIC 
    if st.session_state.theme == "Dark":
        text_color = "#FFFFFF" 
        st.markdown("""
            <style>
            /* 1. GLOBAL BLACK BACKGROUND */
            .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
                background-color: #000000 !important;
            }

            /* 2. TEXT COLOR (Global) */
            h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
                color: #FFFFFF !important;
            }

            /* 3. INPUTS ONLY */
            div[data-testid="stTextInput"] input, 
            div[data-testid="stTextArea"] textarea, 
            [data-baseweb="select"] > div {
                background-color: #FFFFFF !important; 
                color: #000000 !important; 
                border: 2px solid #FFFFFF !important; 
                border-radius: 5px !important;
            }

            /* 4. UNIFIED PURPLE BUTTONS - ULTIMATE FIX */
            /* We target ALL button elements within streamlit to force the purple theme */
            button, 
            [data-testid="baseButton-secondary"], 
            [data-testid="baseButton-primary"], 
            [data-testid="baseButton-secondaryFormSubmit"],
            div.stButton > button, 
            div.stDownloadButton > button {
                background-color: #a903fc !important; 
                color: #ffffff !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                transition: 0.3s;
                width: 100% !important;
                height: 3rem;
            }
            
            /* Hover state for all buttons */
            button:hover,
            [data-testid="baseButton-secondary"]:hover,
            [data-testid="baseButton-primary"]:hover,
            [data-testid="baseButton-secondaryFormSubmit"]:hover {
                background-color: #c478eb !important; 
                color: #000000 !important;
                border: none !important;
            }

            /* 5. GHOST BOX REMOVAL */
            [data-testid="stDownloadButton"], [data-testid="stButton"] {
                background-color: transparent !important;
                border: none !important;
                display: inline-block !important;
            }

            /* 6. WARNING/POPOVER FIX */
            div[role="dialog"], [data-testid="stNotification"], div[role="alert"] {
                background-color: #1a1a1a !important;
                color: #FFFFFF !important;
                border: 1px solid #a903fc !important;
            }
            div[role="dialog"] p, [data-testid="stNotification"] p {
                color: #FFFFFF !important;
            }

            /* 7. SECTION BOX BORDERS */
            [data-testid="stVerticalBlockBorderWrapper"] {
                border: 2px solid #FFFFFF !important;
                border-radius: 12px !important;
                background-color: #111111 !important;
                padding: 16px !important;
            }

            /* 8. TOOLTIP / HELP POPUP FIX */
            div[data-testid="stTooltipContent"] {
                background-color: #1a1a1a !important;
                color: #FFFFFF !important;
                border: 1px solid #a903fc !important;
                border-radius: 8px !important;
            }

            div[data-testid="stTooltipContent"] p {
                color: #FFFFFF !important;
            }

            /* 9. SIDEBAR SUBSCRIPTION BOX */
            [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
                border: 2px solid #FFFFFF !important;
                border-radius: 10px !important;
                background-color: #111111 !important;
            }

            /* 10. EXPANDER HEADER TEXT */
            [data-testid="stExpander"] summary,
            [data-testid="stExpander"] summary p {
                color: #FFFFFF !important;
            }

            /* 11. EXPANDER BORDER */
            [data-testid="stExpander"] {
                border: 2px solid #FFFFFF !important;
                border-radius: 12px !important;
                background-color: #111111 !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # Light Mode Logic
        text_color = "black"

    # --- 3. SIDEBAR NAVIGATION ---
    with st.sidebar:
        is_premium = st.session_state.get('is_premium', False)
        badge = " 👑" if is_premium else ""
        
        # --- UI: Compact User Profile Header ---
        st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <img src="{st.session_state.profile_pic}" width="100" height="100" style="
                    border-radius: 50%; 
                    object-fit: cover; 
                    border: 2px solid #4A90E2;
                ">
                <h4 style="color: {text_color}; margin-top: 10px; margin-bottom: 0px; font-size: 22px;">
            {st.session_state.username}{badge}
                </h4>
            </div>
        """, unsafe_allow_html=True)
        def get_btn_type(mode):
            return "secondary" if st.session_state.view_mode == mode else "primary"

        if st.button("Home", use_container_width=True, type=get_btn_type("home")):
            st.session_state.view_mode = "home"; st.rerun()
            
        if st.button("Explore Newspaper", use_container_width=True, type=get_btn_type("read_news")):
            st.session_state.view_mode = "read_news"; st.rerun()
        
        if not is_premium:
            if st.button("Upgrade to Premium", use_container_width=True, type=get_btn_type("subscription")):
                st.session_state.view_mode = "subscription"; st.rerun()

        if st.button("AI Trends", use_container_width=True, type=get_btn_type("trends")):
            st.session_state.view_mode = "trends"; st.rerun()
            
        if st.button("My Archives", use_container_width=True, type=get_btn_type("archive")):
            st.session_state.view_mode = "archive"; st.rerun()
            
        # FIXED: Added support & feedback to match your view_mode name
        if st.button("Support & Feedback", use_container_width=True, type=get_btn_type("help_support")):
            st.session_state.view_mode = "help_support"; st.rerun()
            
        if st.button("Profile Settings", use_container_width=True, type=get_btn_type("settings")):
            st.session_state.view_mode = "settings"; st.rerun()

        if st.button("AI Chatbot", use_container_width=True, type=get_btn_type("ai_chatbot")):
            st.session_state.view_mode = "ai_chatbot"
            st.rerun()
        
        # --- SUBSCRIPTION STATUS SECTION ---
        st.write("---")
        st.markdown("### 🎫 My Subscription")
        user_plan = st.session_state.get('user_plan', 'Free')
        expiry = st.session_state.get('expiry_date', 'N/A')
        
        if user_plan == "Free":
            st.warning("Plan: **Free User** 🔓")
        else:
            st.success(f"Plan: **{user_plan}** 👑")
            if expiry:
                st.caption(f"📅 Valid until: {expiry}")
            # Add a button to manage or change plan
            if st.button("Manage Plan", use_container_width=True):
                st.session_state.view_mode = "subscription"
                st.rerun()

        st.write("---")
        if not st.session_state.confirm_logout:
            if st.button("Logout", use_container_width=True):
                st.session_state.confirm_logout = True; st.rerun()
        else:
            with st.container(border=True):
                st.warning("Are you sure?")
                c_yes, c_no = st.columns(2)
                if c_yes.button("Yes", type="primary", use_container_width=True):
                    st.session_state.clear(); switch_page('login')
                if c_no.button("No", use_container_width=True):
                    st.session_state.confirm_logout = False; st.rerun()

    # --- 4. DATABASE STATS ---
    def fetch_dashboard_stats():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM history WHERE username = %s", (st.session_state.username,))
        total = cursor.fetchone()['total']
        cursor.execute("SELECT category, COUNT(category) as cnt FROM history WHERE username = %s GROUP BY category ORDER BY cnt DESC LIMIT 1", (st.session_state.username,))
        res = cursor.fetchone()
        fav = res['category'] if res else "None"
        conn.close()
        return total, fav

    # --- VIEW 1: HOME DASHBOARD ---
    if st.session_state.view_mode == "home":
        st.title("Home Center")
        total, fav = fetch_dashboard_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Analysed", total)
        c2.metric("Favorite Category", fav)
        c3.metric("Last Active", str(date.today()))
        st.write("---")

        # --- ANNOUNCEMENT FEED (With Expiry Logic) ---
        st.subheader("🔔 Announcements")
        
        try:
            import datetime
            conn = get_db_connection()
            if conn:
                # UPDATED QUERY: 
                # 1. created_at <= NOW()  -> The announcement has started.
                # 2. end_date > NOW()     -> The announcement has NOT expired yet.
                query = """
                    SELECT content, created_at 
                    FROM announcements
                    WHERE created_at <= %s AND end_date > %s 
                    ORDER BY created_at DESC 
                    LIMIT 2
                """
                current_time = datetime.datetime.now()
                
                # Using pandas to read the filtered results
                df_ann = pd.read_sql(query, conn, params=(current_time, current_time))
                conn.close()
                
                if not df_ann.empty:
                    for idx, row in df_ann.iterrows():
                        with st.container(border=True):
                            # Using a rocket for the most recent, megaphone for others
                            icon = "🚀" if idx == 0 else "📢"
                            st.markdown(f"**{icon} {row['content']}**")
                            st.caption(f"Posted: {row['created_at'].strftime('%d %b, %I:%M %p')}")
                else:
                    st.info("No active announcements at the moment. Stay tuned! ✨")
                    
        except Exception as e:
            st.error(f"⚠️ Error loading announcements: {e}")
        st.write("---")
        st.subheader("What would you like to analyse?")
        h1, h2 = st.columns(2)
        with h1:
            with st.container(border=True):
                st.markdown("### 🔗 URL Analyser")
                target_url = st.text_input("Paste News URL here", key="pasted_url_input", placeholder="https://www.thehindu.com/...")
                if st.button("Analyse Link", use_container_width=True, type="primary"):
                    if target_url:
                        st.session_state.target_article_url = target_url 
                        st.session_state.sel_cat = "Pasted Link"
                        st.session_state.view_mode = "read_news_summary"; st.rerun()
                    else: st.error("⚠️ Please paste a link first!")
        with h2:
            with st.container(border=True):
                st.markdown("### PDF Upload")
                up_pdf = st.file_uploader("Upload Newspaper PDF", type="pdf")
                pdf_cat = st.selectbox("Select Category to Extract", ["National", "Sports", "Business", "Technology"], key="pdf_cat_sel")
                if up_pdf and st.button("Analyse PDF", use_container_width=True):
                    with st.spinner("🤖 AI is reading PDF..."):
                        pdf_data = analyze_pdf_content(up_pdf, pdf_cat)
                        if "error" not in pdf_data:
                            st.session_state.pdf_result = pdf_data
                            st.session_state.sel_paper = "Uploaded PDF"
                            st.session_state.sel_cat = pdf_cat
                            st.session_state.view_mode = "read_news_summary"; st.rerun()
                        else: st.error(pdf_data["error"])
        st.write("---")
        st.subheader("📜 Recent Activity")
        
        conn = get_db_connection()
        # Fetching the data
        query = """
            SELECT analysis_date as Date, paper_name as Newspaper, 
                category as Category, sentiment as Sentiment 
            FROM history 
            WHERE username = %s 
            ORDER BY history_id DESC LIMIT 5
        """
        df = pd.read_sql(query, conn, params=(st.session_state.username,))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No activity yet. Start your first analysis! 📰")

    # --- VIEW 2: EXPLORE NEWSPAPER ---
    elif st.session_state.view_mode == "read_news":
        st.title("🌐 Google News API Explorer")

        # --- GATEKEEPER CHECK ---
        allowed, message = is_feature_allowed("News API Access")

        if allowed:
            user_topic = st.text_input("Search Google News:", "India News")

            # 1. Fetch button only handles the API call
            if st.button("Fetch Live News"):
                with st.spinner("Fetching latest news..."):
                    # Store the results in session_state so they stay during reruns
                    st.session_state.api_articles = fetch_google_news_via_api(user_topic)

            # 2. Check if we have articles stored in session_state
            if "api_articles" in st.session_state and st.session_state.api_articles:
                for i, art in enumerate(st.session_state.api_articles):
                    with st.container(border=True):
                        if art.get('image'):
                            st.image(art['image'], use_container_width=True)
                        
                        st.subheader(art['title'])
                        st.caption(f"Source: {art['source']['name']}")
                        
                        if st.button(f"✨ Generate AI Summary", key=f"sum_btn_{i}"):
                            with st.spinner("AI is reading..."):
                                summary_text = get_ai_summary(art['url'])
                                st.info(summary_text)
                        
                        st.link_button("Read Full Article", art['url'])
        else:
            # --- SHOW CUSTOM LOCK MESSAGE ---
            st.error(message)
            st.warning("⚠️ High-speed API access is reserved for Monthly Plus plans and above.")
            if st.button("Upgrade to Monthly Plus", key="api_up_btn"):
                st.session_state.view_mode = "subscription"
                st.rerun()

        st.markdown("---") # Visual separator               
        st.title("🗞️ Read Today's or Earlier News")
        
        # Standard features (Available to everyone on a paid plan or within free limits)
        selected_date = st.date_input("Select Edition Date", value=date.today(), 
                                      min_value=date.today() - timedelta(days=15), max_value=date.today())
        st.subheader("Select a Newspaper")
        papers = ["The Hindu", "Times of India", "Deccan Herald", "Indian Express", "Economic Times", "Hindustan Times"]
        cols = st.columns(3)
        for i, p in enumerate(papers):
            if cols[i%3].button(p, use_container_width=True):
                st.session_state.sel_paper = p; st.session_state.sel_date = selected_date
                st.session_state.view_mode = "read_news_cats"; st.rerun()

    elif st.session_state.view_mode == "read_news_cats":
        st.button("← Back to Papers", on_click=lambda: st.session_state.update({"view_mode": "read_news"}))
        st.title(f"📍 {st.session_state.sel_paper}")
        categories = ["National", "International", "Sports", "Business", "Technology", "Politics", "Lifestyle", "Weather"]
        cols = st.columns(4)
        for i, cat in enumerate(categories):
            if cols[i%4].button(cat, use_container_width=True):
                st.session_state.sel_cat = cat; st.session_state.view_mode = "read_news_headlines"; st.rerun()

    elif st.session_state.view_mode == "read_news_headlines":
        st.button("← Back to Categories", on_click=lambda: st.session_state.update({"view_mode": "read_news_cats"}))
        st.title(f"🔍 {st.session_state.sel_cat} Headlines")
        st.caption(f"Source: {st.session_state.sel_paper} | Date: {st.session_state.sel_date.strftime('%d %B %Y')}")
        
        if st.session_state.theme == "Dark":
            st.markdown("<style>div.stButton > button { background-color: #a903fc !important; color: black !important; font-weight: bold; }</style>", unsafe_allow_html=True)

        with st.spinner("🤖 AI is fetching headlines..."):
            # We call your original function
            headlines = fetch_all_headlines(st.session_state.sel_paper, st.session_state.sel_cat, st.session_state.sel_date)
            
            if headlines:
                for idx, article in enumerate(headlines):
                    # Unique key to prevent "Duplicate Widget ID" errors
                    u_key = f"btn_{st.session_state.sel_paper}_{idx}"
                    
                    with st.container(border=True):
                        st.markdown(f"### {article['title']}")
                        if st.button(f"Read AI Summary", key=u_key):
                            st.session_state.target_article_url = article['url']
                            st.session_state.view_mode = "read_news_summary"
                            st.rerun()
            else: 
                # If it fails, we show a clean error with a single Refresh button
                st.error(f"⚠️ No headlines found for {st.session_state.sel_date.strftime('%d %B %Y')}.")

    # --- VIEW: READ NEWSPAPER SUMMARY (With PDF & Email Features) ---
    elif st.session_state.view_mode == "read_news_summary":
        st.button("← Back to Headlines", on_click=lambda: st.session_state.update({"view_mode": "read_news_headlines"}))
        st.title("📝 News Summary")

        # --- SAFETY GUARD: Initialize target_article_url if it doesn't exist (Fixes PDF Error) ---
        if 'target_article_url' not in st.session_state:
            st.session_state.target_article_url = ""

        # --- CACHING LOGIC: Prevents double-downloading and Timeouts ---
        if 'current_summary' not in st.session_state or st.session_state.get('last_url') != st.session_state.target_article_url:
            with st.spinner("🤖 AI is analyzing article..."):
                from newspaper import Article
                import re  # 👈 Needed for powerful cleaning
                try:
                    # Handle PDF result vs URL result
                    if st.session_state.sel_paper == "Uploaded PDF":
                        st.session_state.current_title = st.session_state.pdf_result['title']
                        st.session_state.current_summary = st.session_state.pdf_result['summary']
                        st.session_state.current_sentiment = st.session_state.pdf_result['sentiment']
                        st.session_state.current_top_image = "None"
                    else:
                        article = Article(st.session_state.target_article_url)
                        article.config.request_timeout = 15 
                        article.download(); article.parse(); article.nlp()
                        
                        st.session_state.current_title = article.title
                        st.session_state.current_sentiment = get_sentiment(article.text)
                        st.session_state.current_top_image = article.top_image
                        
                        # --- 🛡️ THE ULTIMATE HINDU JUNK CLEANER (REGEX) ---
                        text_to_clean = article.summary if len(article.summary) > 50 else article.text
                        
                        junk_patterns = [
                            r"This article is part of the View From India newsletter.*?\.",
                            r"Curated every week, this newsletter brings you.*?\.",
                            r"Latest First Day First Show News",
                            r"Latest The View From India News",
                            r"Photo Credit:.*?(?:\n|$)",
                            r"File Photo:.*?(?:\n|$)",
                            r"Curated by The Hindu’s foreign affairs experts",
                            r"Around Tinsel Town",
                            r"This newsletter brings you all the latest news from the world of movies"
                        ]
                        
                        clean_text = text_to_clean
                        for pattern in junk_patterns:
                            clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE)
                        
                        if len(clean_text.strip()) < 100:
                            sentences = [s.strip() for s in article.text.split('.') if len(s) > 40]
                            clean_text = ". ".join(sentences[:3]) + "."
                        
                        st.session_state.current_summary = clean_text.strip()
                    
                    # Update last_url to the current URL (or empty if PDF) to stop infinite re-runs
                    st.session_state.last_url = st.session_state.target_article_url
                
                except Exception as e: 
                    st.error(f"❌ Connection issue: The website is taking too long to respond. Error: {e}")
                    st.stop()

        # Load data from Cache
        title = st.session_state.current_title
        summary_to_show = st.session_state.current_summary
        sentiment = st.session_state.current_sentiment
        is_premium = st.session_state.get('is_premium', False)

        # --- 🌐 Language Selection within the Summary View ---
        st.write("---")
        col_lang, col_space = st.columns([1, 2])
        with col_lang:
            selected_lang = st.selectbox("Choose Translation", ["English", "Tamil", "Kannada", "Hindi", "Malayalam", "Telugu"], key="summary_lang")

        # --- 🔥 TASK 5: MULTI-LANGUAGE LOGIC ---
        display_summary = summary_to_show
        lang_map = {"Hindi": "hi", "Tamil": "ta", "Kannada": "kn", "Malayalam": "ml", "Telugu": "te"}

        if selected_lang != "English":
            # --- GATEKEEPER CHECK ---
            allowed, message = is_feature_allowed("Multi-Language Translation")
            
            if allowed:
                from googletrans import Translator
                with st.spinner(f"Converting to {selected_lang}..."):
                    try:
                        translator = Translator()
                        translated = translator.translate(summary_to_show, dest=lang_map[selected_lang])
                        display_summary = translated.text
                    except Exception:
                        st.warning("🔄 Translation service busy. Showing English version.")
            else:
                # --- SHOW THE CUSTOM LOCK MESSAGE ---
                st.error(message)
                if st.button("🚀 Upgrade to Unlock Translation", key="trans_up_btn"):
                    st.session_state.view_mode = "subscription"
                    st.rerun()

        # --- DISPLAY CONTENT ---
        st.subheader(title)
        st.info(f"🎭 AI Sentiment: {sentiment}")
        
        st.markdown(f'''
            <div style="background:white; color:black; padding:20px; border-radius:10px; border-left:10px solid #1E3A8A; font-size:18px;">
                {display_summary}
            </div>
        ''', unsafe_allow_html=True)

        # --- TASK 5.1: ADVANCED AI VOICE PLAYER ---
        st.write("---")
        if st.button("Listen to Summary"):
            # --- GATEKEEPER CHECK ---
            allowed, message = is_feature_allowed("Audio Text-to-Speech")
            
            if allowed:
                import streamlit.components.v1 as components
                from gtts import gTTS
                import base64
                from io import BytesIO

                with st.spinner("📢 Processing Voice..."):
                    try:
                        voice_lang = lang_map.get(selected_lang, 'en')
                        tts = gTTS(text=display_summary, lang=voice_lang)
                        mp3_fp = BytesIO()
                        tts.write_to_fp(mp3_fp)
                        b64 = base64.b64encode(mp3_fp.getvalue()).decode()
                        
                        player_code = f"""
                        <div style="font-family: sans-serif; background:#f8f9fa; padding:20px; border-radius:15px; border: 1px solid #ddd; text-align:center;">
                            <audio id="audio-element" src="data:audio/mp3;base64,{b64}"></audio>
                            <div style="margin-bottom: 15px;">
                                <button onclick="restart()" style="padding:10px 15px; margin:5px; border-radius:8px; border:none; background:#6c757d; color:white; cursor:pointer; font-weight:bold;">🔄 Replay</button>
                                <button onclick="skip(-10)" style="padding:10px 15px; margin:5px; border-radius:8px; border:none; background:#1E3A8A; color:white; cursor:pointer; font-weight:bold;">⏪ -10s</button>
                                <button onclick="togglePlay()" id="play-btn" style="padding:10px 20px; margin:5px; border-radius:8px; border:none; background:#28a745; color:white; cursor:pointer; font-weight:bold;">▶️ Play</button>
                                <button onclick="skip(10)" style="padding:10px 15px; margin:5px; border-radius:8px; border:none; background:#1E3A8A; color:white; cursor:pointer; font-weight:bold;">+10s ⏩</button>
                            </div>
                            <input type="range" id="seek-bar" value="0" style="width:90%; cursor:pointer;">
                        </div>
                        <script>
                            var audio = document.getElementById("audio-element");
                            var playBtn = document.getElementById("play-btn");
                            var seekBar = document.getElementById("seek-bar");
                            function togglePlay() {{
                                if (audio.paused) {{ audio.play(); playBtn.innerHTML = "⏸️ Pause"; playBtn.style.background = "#dc3545"; }}
                                else {{ audio.pause(); playBtn.innerHTML = "▶️ Play"; playBtn.style.background = "#28a745"; }}
                            }}
                            function skip(value) {{ audio.currentTime += value; }}
                            function restart() {{ audio.currentTime = 0; audio.play(); playBtn.innerHTML = "⏸️ Pause"; playBtn.style.background = "#dc3545"; }}
                            audio.ontimeupdate = function() {{ var value = (100 / audio.duration) * audio.currentTime; seekBar.value = value; }};
                            seekBar.oninput = function() {{ var time = audio.duration * (seekBar.value / 100); audio.currentTime = time; }};
                        </script>
                        """
                        components.html(player_code, height=180)
                    except Exception as e:
                        st.error(f"🎙️ Voice service unavailable: {e}")
            else:
                # --- SHOW THE CUSTOM LOCK MESSAGE ---
                st.error(message)
                # Store intent to upgrade in session state to handle the rerun properly
                st.session_state.needs_upgrade = True

        # --- GLOBAL UPGRADE REDIRECT (Handles the 'else' click correctly) ---
        if st.session_state.get('needs_upgrade', False):
            if st.button("🚀 Upgrade to Unlock Audio", key="audio_up_btn", type="primary", use_container_width=True):
                st.session_state.view_mode = "subscription"
                st.session_state.sub_step = 1
                st.session_state.needs_upgrade = False  # Reset the flag
                st.rerun()

        # --- ACTION BUTTONS ---
        st.write("---")
        # 1. Always define the columns so "col_save" is never undefined
        col_pdf, col_mail, col_save = st.columns(3)
        
        # --- COLUMN 1: PDF (Premium Only) ---
        with col_pdf:
            # --- GATEKEEPER CHECK ---
            allowed, message = is_feature_allowed("PDF Download for Summary")
            
            if allowed:
                from datetime import date
                pdf_bytes = generate_pdf_report(title, summary_to_show, str(date.today()))
                st.download_button(
                    label="📥 Download PDF", 
                    data=pdf_bytes, 
                    file_name="news_summary.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
            else:
                # 1. Main Button: Set a persistent flag when clicked
                if st.button("📥 Download PDF", help=message, use_container_width=True, key="pdf_locked_trigger"):
                    st.session_state.show_pdf_upgrade = True
                
                # 2. Show the Upgrade UI if the flag is True
                if st.session_state.get('show_pdf_upgrade', False):
                    with st.container(border=True):
                        st.error(message)
                        c_up, c_close = st.columns(2)
                        with c_up:
                            if st.button("Upgrade to Unlock", key="pdf_side_up_redirect", type="primary", use_container_width=True):
                                # Reset flag and redirect
                                st.session_state.show_pdf_upgrade = False
                                st.session_state.view_mode = "subscription"
                                st.rerun()
                        with c_close:
                            if st.button("Close ✖️", key="pdf_close_warn", use_container_width=True):
                                st.session_state.show_pdf_upgrade = False
                                st.rerun()
        
        # --- COLUMN 2: EMAIL (Premium Only) ---
        with col_mail:
            # --- UPDATED GATEKEEPER CHECK ---
            allowed, message = is_feature_allowed("Email Summary Report")
            
            if allowed:
                if st.button("📧 Email Me", use_container_width=True, key="mail_active_btn"):
                    with st.spinner("📤 Sending report to your registered email..."):
                        clean_body = (
                            f"Greetings,\n\n"
                            f"Here is your requested Newspaper Analysis:\n"
                            f"---"
                            f"\nTITLE: {title}\n\n"
                            f"SUMMARY:\n{summary_to_show}\n\n"
                            f"SENTIMENT: {sentiment}\n"
                            f"---"
                            f"\nBest Regards,\nTeam Newspaper Analyser"
                        )
                        
                        target_email = st.session_state.get('user_email') or st.session_state.get('locked_e')
                        if target_email and send_real_otp(target_email, clean_body, "Report"):
                            st.success(f"Sent to {target_email}! 📧") 
                            st.balloons()
                        else:
                            st.error("❌ Failed to send. Please check your App Password or destination address.")
            else:
                # 1. Trigger the persistent state flag when locked button is clicked
                if st.button("📧 Email Me", use_container_width=True, help=message, key="mail_lock_trigger"):
                    st.session_state.show_mail_upgrade = True

                # 2. Show the Upgrade UI if the flag is True
                if st.session_state.get('show_mail_upgrade', False):
                    with st.container(border=True):
                        st.error(message)
                        c_up, c_close = st.columns(2)
                        with c_up:
                            if st.button("Upgrade to Unlock", key="mail_up_btn_final", type="primary", use_container_width=True):
                                # Reset flag and redirect
                                st.session_state.show_mail_upgrade = False
                                st.session_state.view_mode = "subscription"
                                st.rerun()
                        with c_close:
                            if st.button("Close ✖️", key="mail_close_warn", use_container_width=True):
                                st.session_state.show_mail_upgrade = False
                                st.rerun()
        
        # --- COLUMN 3: SAVE TO ARCHIVE (Shared Logic with Limits) ---
        with col_save:
            if st.button("📁 Save to Archive", use_container_width=True):
                try:
                    # 1. GATEKEEPER CHECK (Handles Expiry and Basic Access) 🛡️
                    allowed, gate_msg = is_feature_allowed("Save to Archive") 
                    
                    if not allowed:
                        st.error(gate_msg)
                        if st.button("🚀 Upgrade Plan", key="err_up_btn"):
                            st.session_state.view_mode = "subscription"
                            st.rerun()
                    else:
                        conn = get_db_connection()
                        cursor = conn.cursor()

                        # 2. DUPLICATE CHECK: Prevent saving the same news twice
                        cursor.execute("""
                            SELECT archive_id FROM archives 
                            WHERE username = %s AND title = %s
                        """, (st.session_state.username, title))
                        
                        if cursor.fetchone():
                            st.info("Already saved in archive! 📂")
                        else:
                            # 3. DYNAMIC LIMIT CHECK 📊
                            cursor.execute("SELECT COUNT(*) FROM archives WHERE username = %s", (st.session_state.username,))
                            count = cursor.fetchone()[0]

                            # Fetch plan details from MASTER_PLANS session state
                            user_plan = st.session_state.get('user_plan', 'Free')
                            all_plans = st.session_state.get('MASTER_PLANS', {})
                            plan_features = all_plans.get(user_plan, {}).get('features', [])
                            
                            limit = 10 # Default for Free users
                            is_unlimited = False

                            # Parse features for storage limits
                            for feature in plan_features:
                                if "Unlimited Archive Storage" in feature or "Unlimited Access Forever" in feature:
                                    is_unlimited = True
                                    break
                                elif "Archive Storage Slots" in feature:
                                    limit = int(''.join(filter(str.isdigit, feature)))

                            # 4. PERMISSION CHECK: Compare count vs limit
                            if is_unlimited or count < limit:
                                img_url = st.session_state.get('current_top_image', "None")
                                
                                cursor.execute("""
                                    INSERT INTO archives (username, title, summary, category, source_url) 
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (st.session_state.username, title, summary_to_show, 
                                      st.session_state.sel_cat, img_url))
                                
                                conn.commit()
                                # Success message with status indicator
                                st.toast(f"Saved! ({count + 1}/{'∞' if is_unlimited else limit}) ✅", icon="✅")
                                
                                save_to_history(st.session_state.username, st.session_state.sel_paper, 
                                                st.session_state.sel_cat, sentiment, title)
                            else:
                                # Show the upgrade block
                                st.warning(f"⚠️ Archive Limit Reached ({count}/{limit})!")
                                st.error(f"Your {user_plan} plan is full. Upgrade for more slots! 💎")
                                if st.button("🚀 View Premium Plans", key="arch_up_btn"):
                                    st.session_state.view_mode = "subscription"
                                    st.rerun()
                        
                        conn.close()
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")

    # --- VIEW 4: TRENDS (With Line Chart) ---
    elif st.session_state.view_mode == "trends":
        st.title("📈 AI Insights & Trends")
        conn = get_db_connection()
        if conn:
            # 📊 FEATURE 4: SENTIMENT PULSE CHART
            query = "SELECT analysis_date, sentiment FROM history WHERE username = %s ORDER BY analysis_date ASC"
            df = pd.read_sql(query, conn, params=(st.session_state.username,))
            if not df.empty:
                s_map = {"Positive": 1, "Neutral": 0, "Negative": -1}
                df['score'] = df['sentiment'].map(s_map)
                st.subheader("User Sentiment Pulse (Last 7 Days)")
                st.line_chart(df.set_index('analysis_date')['score'])
                
                st.subheader("Category Distribution")
                df_cat = pd.read_sql("SELECT category, COUNT(*) as count FROM history WHERE username = %s GROUP BY category", conn, params=(st.session_state.username,))
                st.bar_chart(df_cat.set_index('category'))
            else: st.info("No data yet.")
            conn.close()

   # --- VIEW 5: ARCHIVE (With Search Bar) ---
    elif st.session_state.view_mode == "archive":
        st.title("📁 My News Archives")
        
        # 🔍 FEATURE: SEARCH BAR
        search = st.text_input("🔍 Search Archive...", placeholder="Enter keyword or category")
        
        try:
            conn = get_db_connection()
            if conn:
                # 1. Fetch data for count and export
                query = "SELECT * FROM archives WHERE username = %s"
                params = [st.session_state.username]
                
                if search:
                    query += " AND (title LIKE %s OR category LIKE %s)"
                    params.extend([f"%{search}%", f"%{search}%"])
                
                df = pd.read_sql(query + " ORDER BY saved_at DESC", conn, params=params)
                conn.close()

                # --- 📥 BULK PDF EXPORT LOGIC ---
                if not df.empty and len(df) >= 5:
                    with st.container(border=True):
                        st.markdown("### 📊 Archive Report")
                        col_text, col_btn = st.columns([2, 1])
                        
                        with col_text:
                            st.write(f"Generate a PDF report of all **{len(df)}** saved articles.")
                        
                        with col_btn:
                            # --- GATEKEEPER CHECK ---
                            allowed, message = is_feature_allowed("Bulk PDF Export")
                            
                            if allowed:
                                # PREMIUM/AUTHORIZED USER: Generate and Download
                                try:
                                    # Call the ReportLab function
                                    pdf_bytes = generate_bulk_archive_pdf(st.session_state.username, df)
                                    
                                    st.download_button(
                                        label="📥 Download Bulk PDF",
                                        data=pdf_bytes, 
                                        file_name=f"{st.session_state.username}_news_archive.pdf",
                                        mime="application/pdf",
                                        type="primary",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ Error generating Archive PDF: {e}")
                                    st.info("💡 Tip: Make sure all articles have valid text in the database.")
                            else:
                                # UNAUTHORIZED USER: Show the "Lock" state
                                if st.button("📥 Generate Bulk PDF", use_container_width=True, key="lock_btn", help=message):
                                    st.session_state.show_upgrade_promo = True
                                    st.rerun()

                # This part handles the "Upgrade Promo" UI
                if st.session_state.get('show_upgrade_promo', False):
                    # Recalculate message for the promo box
                    allowed, message = is_feature_allowed("Bulk PDF Export")
                    
                    if not allowed:
                        with st.container(border=True):
                            st.error(message) # Shows specifically why (e.g. "Expired" or "Not in plan")
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("Explore Plans", type="primary", use_container_width=True):
                                    st.session_state.view_mode = "subscription"
                                    st.session_state.show_upgrade_promo = False
                                    st.rerun()
                            with c2:
                                if st.button("Close", use_container_width=True):
                                    st.session_state.show_upgrade_promo = False
                                    st.rerun()
                # -------------------------------------
                
                if not df.empty:
                    st.caption(f"Showing {len(df)} saved articles")
                    
                    for idx, row in df.iterrows():
                        item_id = row['archive_id']
                        
                        with st.container(border=True):
                            st.subheader(f"📰 {row['title']}")
                            st.caption(f"Category: {row['category']} | Saved on: {row['saved_at'].strftime('%d %b, %Y')}")
                            
                            with st.expander("📖 View Full AI Summary"):
                                st.write(row['summary'])
                                if row['source_url'] and row['source_url'] != "None":
                                    st.image(row['source_url'], caption="Original Image Reference", width=300)
                            
                            if st.button(f"🗑️ Delete Article", key=f"del_{item_id}"):
                                try:
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM archives WHERE archive_id = %s", (item_id,))
                                    conn.commit()
                                    conn.close()
                                    st.toast("Article removed from archive! 🗑️")
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting: {e}")
                
                else:
                    if search:
                        st.info(f"🔍 No results found for '{search}'. Try a different keyword.")
                    else:
                        st.info("💡 Your archive is empty. Start exploring news to save your first article!")
        
        except Exception as e:
            st.error(f"❌ Database connection error: {e}")

    
    # --- VIEW 6: PROFILE SETTINGS ---
    elif st.session_state.view_mode == "settings":
        # --- DARK MODE TEXT FIX ---
        if st.session_state.theme == "Dark":
            st.markdown("""
                <style>
                .stApp { background-color: #0E1117; color: #E0E0E0 !important; }
                /* Force all headers and text to be readable in Dark Mode */
                h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
                    color: #E0E0E0 !important;
                }
                /* Adjust container borders for visibility */
                [data-testid="stVerticalBlock"] > div > div[style*="border"] {
                    border: 1px solid #30363d !important;
                }
                </style>
            """, unsafe_allow_html=True)

        # --- UI: Centered Profile Photo and Name ---
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 20px;">
                <img src="{st.session_state.profile_pic}" style="
                    width: 120px; 
                    height: 120px; 
                    border-radius: 50%; 
                    object-fit: cover; 
                    border: 3px solid #4A90E2;
                    box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
                ">
                <h1 style="margin-top: 15px; text-align: center;">
                    {st.session_state.username} ✨
                </h1>
            </div>
        """, unsafe_allow_html=True)
        
        # 1. Profile Bio Section
        with st.container(border=True):
            st.markdown("### 📝 Edit Profile")

            st.markdown("""<style>[data-testid="stFileUploaderFileName"] { display: none; }</style>""", unsafe_allow_html=True)
            new_user_img = st.file_uploader("Change Profile Photo", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
            
            if new_user_img:
                import base64
                user_bytes = new_user_img.getvalue()
                user_b64 = f"data:image/png;base64,{base64.b64encode(user_bytes).decode()}"
                
                # Show a preview of the NEWly selected image in a circle
                st.markdown(f"""
                    <p style="text-align:center; font-size:12px; color:gray;">Preview of New Selection:</p>
                    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                        <img src="{user_b64}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px dashed #4A90E2;">
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("Update Photo", use_container_width=True):
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        # 1. Permanent Save to MySQL
                        cursor.execute("UPDATE users SET profile_pic = %s WHERE username = %s", (user_b64, st.session_state.username))
                        conn.commit()
                        conn.close()
                        
                        # 2. Immediate Update to Session State
                        st.session_state.profile_pic = user_b64
                        
                        st.toast("Photo updated! 📸", icon="✨")
                        import time
                        time.sleep(1)
                        st.rerun()

            st.write("---")
            new_username = st.text_input("Username", value=st.session_state.username, disabled=True)
            bio_input = st.text_area("Your Bio", value=st.session_state.bio, placeholder="Write something about yourself...")
            
            if st.button("Save Profile Changes", type="primary"):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET bio = %s WHERE username = %s", (bio_input, st.session_state.username))
                    conn.commit()
                    conn.close()
                    st.session_state.bio = bio_input
                    st.toast("Profile updated successfully!", icon="✅")

        # 2. Security Section
        with st.container(border=True):
            st.markdown("### 🔒 Security Settings")
            if not st.session_state.get('show_pass_reset', False):
                if st.button("Change Account Password", use_container_width=True):
                    st.session_state.show_pass_reset = True
                    st.rerun()
            else:
                old_p = st.text_input("Current Password", type="password")
                new_p = st.text_input("New Password", type="password")
                confirm_p = st.text_input("Confirm New Password", type="password")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Update Password", type="primary", use_container_width=True):
                        # 1. Check if fields match
                        if new_p != confirm_p:
                            st.error("❌ Confirm Password does not match!")
                        
                        # 2. Check if new password is the same as old one
                        elif new_p == old_p:
                            st.error("❌ New password cannot be the same as current password!")
                        
                        # 3. Check for strength (8 chars, Upper, Lower, Number, Special)
                        elif len(new_p) < 8 or not check_password_strength(new_p):
                            st.warning("⚠️ Password must be min 8 characters and include Uppercase, Lowercase, Number, and Special Character.")
                        
                        else:
                            conn = get_db_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT password FROM users WHERE username = %s", (st.session_state.username,))
                                current_db_pass = cursor.fetchone()[0]
                                
                                # 4. Verify the entered current password is correct in DB
                                if old_p == current_db_pass:
                                    cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_p, st.session_state.username))
                                    conn.commit()
                                    st.success("✅ Password updated successfully!")
                                    st.session_state.show_pass_reset = False
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("❌ Current password incorrect.")
                                conn.close()
                with c2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.show_pass_reset = False
                        st.rerun()

        # 3. Theme Toggle
        with st.container(border=True):
            st.markdown("### 🌗 Appearance")
            theme_choice = st.toggle("Enable Dark Mode", value=(st.session_state.theme == "Dark"))
            if theme_choice and st.session_state.theme != "Dark":
                st.session_state.theme = "Dark"
                st.rerun()
            elif not theme_choice and st.session_state.theme != "Light":
                st.session_state.theme = "Light"
                st.rerun()

        # --- Delete Account ---
        with st.container(border=True):
            st.markdown("### ⚠️ Delete My Account")
            st.write("Deleting your account will remove your data from our active database.")
            
            with st.expander("Permanently Delete Account"):
                reason = st.text_area("Please provide a reason for leaving:", placeholder="Found another app / Too expensive...")
                if st.button("❌ Delete My Account", type="secondary", use_container_width=True):
                    if not reason.strip():
                        st.warning("Please provide a reason before deleting your account.")
                    else:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            # Fetch email before deletion
                            cursor.execute("SELECT email FROM users WHERE username = %s", (st.session_state.username,))
                            u_email = cursor.fetchone()[0]
                            
                            # Move to deleted table
                            cursor.execute("INSERT INTO deleted_users (username, email, reason) VALUES (%s, %s, %s)", 
                                         (st.session_state.username, u_email, reason))
                            
                            # Delete from main table
                            cursor.execute("DELETE FROM users WHERE username = %s", (st.session_state.username,))
                            conn.commit()
                            conn.close()
                            
                            st.success("Account deleted. Redirecting...")
                            time.sleep(2)
                            st.session_state.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    elif st.session_state.view_mode == "ai_chatbot":
        st.title("🤖 NewsBuddy")
        st.info("I am your personal assistant. Ask me to explain any headline or global event!")

        # 1. Initialize Chat History
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # 2. Display the Chat
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 3. Chat Input Bar
        if user_input := st.chat_input("Say something to NewsBuddy..."):
            # Save user message
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get response from your Gemini Pro function
            with st.chat_message("assistant"):
                with st.spinner("NewsBuddy is analyzing..."):
                    
                    # --- FIX: PROGRAMMATIC CONTEXT INJECTION ---
                    # We get the real system date and wrap the user input with it
                    real_today = date.today().strftime("%A, %B %d, %Y")
                    # We send a hidden 'instruction' so the AI knows the current time
                    instructional_prompt = f"System Context: Today is {real_today}. User Question: {user_input}"
                    
                    # Call your function with the new instructional prompt
                    response = get_pro_chat_response(instructional_prompt)
                    
                    st.markdown(response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # ---- VIEW 7. Help Support and Feedback ----
    elif st.session_state.view_mode == "help_support":
        st.title("Support & Feedback Center")
        
        # --- PART A: SUBMIT TICKET ---
        with st.expander("📩 Submit a New Ticket", expanded=True):
            with st.form("help_form", clear_on_submit=True):
                subject = st.selectbox("Issue Category", ["Technical Bug", "Payment Issue", "Feedback", "General Query","Other"])
                # We use the existing email from session state (hidden or read-only)
                st.info(f"Replying to: **{st.session_state.get('user_email', 'Your Registered Email')}**")
                message = st.text_area("Describe your issue/feedback...")
                
                if st.form_submit_button("Submit Ticket"):
                    if message:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO help_support (username, email, subject, message, status) 
                            VALUES (%s, %s, %s, %s, 'Pending')
                        """, (st.session_state.username, st.session_state.get('user_email'), subject, message))
                        conn.commit()
                        conn.close()
                        import time
                        st.success("✅ Ticket raised successfully!")
                        time.sleep(2)
                        st.rerun()

        # --- PART B: VIEW MY TICKETS ---
        st.subheader("📑 My Ticket History")
        conn = get_db_connection()
        df_tickets = pd.read_sql("SELECT subject, message, status, admin_reply, submitted_at FROM help_support WHERE username = %s ORDER BY submitted_at DESC", conn, params=(st.session_state.username,))
        conn.close()

        if not df_tickets.empty:
            for idx, row in df_tickets.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    col1.markdown(f"**{row['subject']}**")
                    status_color = "orange" if row['status'] == 'Pending' else "green"
                    col2.markdown(f"<span style='color:{status_color}; font-weight:bold;'>{row['status']}</span>", unsafe_allow_html=True)
                    st.write(f"💬 {row['message']}")
                    
                    if row['admin_reply']:
                        st.info(f"👨‍💻 **Admin Response:** {row['admin_reply']}")
        else:
            st.info("You haven't raised any tickets yet.")

    # --- VIEW 8: SUBSCRIPTION / PAYMENT ---
    elif st.session_state.view_mode == "subscription":
        if 'sub_step' not in st.session_state:
            st.session_state.sub_step = 1
    
        # --- 1. PLANS DATA ---
        plans = {
            "Trial Spark":       {"price": 29,   "days": 1,   "desc": "A 24-hour full access pass for quick testing.",                     "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Unlimited Archive Storage for 24 Hours", "Email Summary Report"]},
            "Weekly Quick":      {"price": 99,   "days": 7,   "desc": "Ideal for students working on short-term research projects.",       "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Unlimited Archive Storage for 7 Days", "Email Report Support", "PDF Download for Summary"]},
            "Monthly Lite":      {"price": 229,  "days": 30,  "desc": "Standard features for casual news readers.",                        "features": ["Multi-Language Translation", "Unlimited Archive Storage for 30 Days", "Email Summary Report", "PDF Download for Summary"]},
            "Monthly Plus":      {"price": 259,  "days": 30,  "desc": "Increased storage for more active news monitoring.",                "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Report Support", "Unlimited Archive Storage for 30 Days", "PDF Download for Summary", "News API Access"]},
            "Quarterly Scholar": {"price": 679,  "days": 90,  "desc": "Best for semester-long academic tracking.",                        "features": ["Multi-Language Translation", "Bulk PDF Export", "50 Archive Storage Slots (90 Days)", "Email Summary Report", "PDF Download for Summary"]},
            "Quarterly Pro":     {"price": 749,  "days": 90,  "desc": "Professional grade tools with batch processing.",                   "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Report Support", "Unlimited Archive Storage", "Bulk PDF Export", "PDF Download for Summary", "News API Access"]},
            "Half-Yearly Saver": {"price": 1349, "days": 180, "desc": "Significant savings for long-term users.",                         "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Report Support", "80 Archive Storage Slots (180 Days)", "Bulk PDF Export", "Priority Support"]},
            "Premium Annual":    {"price": 2499, "days": 365, "desc": "Our most popular plan for daily power users.",                     "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Report Support", "100 Archive Storage Slots (365 Days)", "Bulk PDF Export", "Priority Support", "Early Access to New Features"]},
            "Elite Annual":      {"price": 2999, "days": 365, "desc": "High-performance access for year-round users.",                    "features": ["Multi-Language Translation", "Audio Text-to-Speech", "Email Report Support", "Unlimited Archive Storage", "Bulk PDF Export", "Priority Support", "PDF Download for Summary", "Early Access to New Features", "News API Access"]},
        }
    
        # --- 2. CALCULATE UPGRADE DISCOUNT ---
        current_plan_name = st.session_state.get('user_plan', 'Free')
        discount_amt = 0
        if current_plan_name != "Free" and current_plan_name in plans:
            discount_amt = plans[current_plan_name]['price']
    
        # STEP 1 — CHOOSE PLAN
        if st.session_state.sub_step == 1:
            st.title("Choose Your Premium Plan 💎")
            st.info("Select a plan to unlock advanced AI features and unlimited archives.")
            
            if discount_amt > 0:
                st.warning(f"🔄 **Upgrade Applied:** ₹{discount_amt} (from your '{current_plan_name}' plan) will be deducted from your total!")
    
            shown = 0
            for p_name, p_info in plans.items():
                if p_name == current_plan_name: continue 
    
                original_price = p_info['price']
                final_price = max(0, original_price - discount_amt)
    
                if current_plan_name != "Free" and original_price <= discount_amt: continue
    
                shown += 1
                with st.container(border=True):
                    col_main, col_btn = st.columns([3, 1])
                    with col_main:
                        if discount_amt > 0:
                            st.markdown(f"### {p_name} — ~~₹{original_price}~~ <span style='color:#28a745;'>₹{final_price}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"### {p_name} — ₹{original_price}")
    
                        st.caption(f"⏱️ Validity: {p_info['days']} Days")
                        st.write(p_info['desc'])
                        with st.expander(f"View Features"):
                            for feature in p_info['features']:
                                st.markdown(f"- {feature}")
    
                    with col_btn:
                        st.write("### ")
                        btn_text = "Upgrade" if discount_amt > 0 else "Buy Now"
                        if st.button(btn_text, key=f"btn_{p_name}_buy", use_container_width=True, type="primary"):
                            st.session_state.temp_plan = p_name
                            st.session_state.temp_final_price = final_price
                            st.session_state.sub_step = 2
                            for key in ['db_updated', 'final_utr', 'current_mode']:
                                st.session_state.pop(key, None)
                            st.rerun()
    
            if shown == 0:
                st.success("🎉 You already own the highest available plan!")
    
        # STEP 2 — PAYMENT GATEWAY
        elif st.session_state.sub_step == 2:
            st.title("Secure Payment Gateway 🔒")
            if st.button("← Back to Plans"):
                st.session_state.sub_step = 1
                st.rerun()
    
            amt = st.session_state.get('temp_final_price', 0)
            st.markdown(f"""<div style="background:#1e293b;padding:20px;border-radius:12px;margin-bottom:20px;color:white;">
                <h3 style="margin:0;">🛒 Order Summary</h3>
                <p>Plan: <b>{st.session_state.temp_plan}</b> | Total: <span style="color:#4ade80;font-weight:bold;">₹{amt}</span></p>
            </div>""", unsafe_allow_html=True)
    
            pay_tabs = st.tabs(["📲 UPI", "💳 Card", "🏦 Net Banking"])
    
            with pay_tabs[0]:
                st.session_state.current_mode = "UPI"
                upi_id = "sgopika2005@okhdfcbank"
                qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa={upi_id}&am={amt}"
                st.image(qr_api, caption="Scan to Pay", width=200)
                st.info(f"Pay to UPI ID: **{upi_id}**")
    
            with pay_tabs[1]:
                st.session_state.current_mode = "Card"
                st.text_input("Cardholder Name", placeholder="As on card")
                st.text_input("Card Number", placeholder="XXXX XXXX XXXX XXXX")
                c1, c2 = st.columns(2)
                c1.text_input("Expiry", placeholder="MM/YY")
                c2.text_input("CVV", type="password", placeholder="***")
    
            with pay_tabs[2]:
                st.session_state.current_mode = "Net Banking"
                st.selectbox("Select Bank", ["SBI", "HDFC", "ICICI", "Axis", "Canara Bank"])
    
            st.markdown("---")
            
            # KEYBOARD ENTER FIX: Wrap UTR in a form so "Enter" submits it
            with st.form("payment_form", clear_on_submit=False):
                st.markdown("#### 🔗 Transaction Reference")
                ref_id = st.text_input("Enter 12-Digit UTR Number", max_chars=12, help="Press Enter to confirm")
                submit_payment = st.form_submit_button(f"Confirm Payment of ₹{amt}", type="primary", use_container_width=True)
    
                if submit_payment:
                    if len(ref_id) == 12 and ref_id.isdigit():
                        st.session_state.final_utr = ref_id
                        st.session_state.sub_step = 3 
                        st.rerun()
                    else:
                        st.error("❌ Please enter a valid 12-digit numeric UTR.")
    
        # STEP 3 — PROCESSING STEP (Vertical Stepper)
        elif st.session_state.sub_step == 3:
            import time
            st.title("Processing Transaction...")
            
            steps = [
                ("📡 Connecting to Bank", "Establishing secure handshake..."),
                ("🔍 Validating UTR", f"Verifying Ref: {st.session_state.final_utr}"),
                ("🔓 Activating Plan", "Finalizing account permissions...")
            ]
    
            stepper_ph = st.empty()
            for i in range(len(steps) + 1):
                with stepper_ph.container():
                    html = "<div style='background:#f8fafc; padding:30px; border-radius:15px; border:1px solid #e2e8f0;'>"
                    for idx, (name, desc) in enumerate(steps):
                        if idx < i: icon, color, lcolor = "✅", "#22c55e", "#22c55e"
                        elif idx == i: icon, color, lcolor = "🔵", "#3b82f6", "#e2e8f0"
                        else: icon, color, lcolor = "⚪", "#94a3b8", "#e2e8f0"
                        
                        html += f"""<div style='display:flex; gap:15px;'>
                            <div style='display:flex; flex-direction:column; align-items:center;'>
                                <div style='font-size:24px;'>{icon}</div>
                                {f"<div style='width:2px; height:40px; background:{lcolor};'></div>" if idx < 2 else ""}
                            </div>
                            <div><b>{name}</b><br><span style='font-size:12px; color:#64748b;'>{desc}</span></div>
                        </div>"""
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                if i < len(steps):
                    time.sleep(3) 
    
            st.session_state.sub_step = 4 
            st.rerun()
    
        # STEP 4 — SUCCESS & RECEIPT
        elif st.session_state.sub_step == 4:
            import datetime as dt_module
            from fpdf import FPDF
            
            # --- DATABASE WRITE (Only once) ---
            if 'db_updated' not in st.session_state:
                try:
                    days = plans[st.session_state.temp_plan]['days']
                    expiry_dt = (dt_module.datetime.now() + dt_module.timedelta(days=days)).date()
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET is_premium=1, current_plan=%s, plan_expiry=%s WHERE username=%s",
                                (st.session_state.temp_plan, expiry_dt, st.session_state.username))
                    
                    cursor.execute("INSERT INTO transactions (username, utr_number, amount, payment_mode, payment_date) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE amount=amount",
                                (st.session_state.username, st.session_state.final_utr, st.session_state.temp_final_price, st.session_state.current_mode, dt_module.datetime.now()))
                    
                    conn.commit()
                    conn.close()
                    st.session_state.is_premium = 1
                    st.session_state.user_plan = st.session_state.temp_plan
                    st.session_state.expiry_date = expiry_dt
                    st.session_state.db_updated = True
                    st.balloons()
                except Exception as e:
                    st.error(f"DB Error: {e}")
    
            # --- SUCCESS HEADER ---
            st.markdown(f"""<div style="text-align:center; padding:30px;">
                <h1 style="color:#22c55e;">🎉 Payment Successful!</h1>
                <p style="font-size:18px;">Your <b>{st.session_state.temp_plan}</b> is now active.</p>
            </div>""", unsafe_allow_html=True)
    
            with st.container(border=True):
                st.subheader("🧾 Official Payment Receipt")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Transaction ID:** `{st.session_state.final_utr}`")
                    st.write(f"**User:** {st.session_state.username}")
                with col2:
                    st.write(f"**Amount Paid:** ₹{st.session_state.temp_final_price}")
                    st.write(f"**Payment Mode:** {st.session_state.current_mode}")
                
                # --- PDF GENERATOR ---
                def generate_pdf():
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "Newspaper Analyser AI - Payment Receipt", ln=True, align='C')
                    pdf.ln(10)
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, f"Username: {st.session_state.username}", ln=True)
                    pdf.cell(0, 10, f"Transaction ID: {st.session_state.final_utr}", ln=True)
                    pdf.cell(0, 10, f"Plan: {st.session_state.temp_plan}", ln=True)
                    pdf.cell(0, 10, f"Amount: Rs. {st.session_state.temp_final_price}", ln=True)
                    pdf.cell(0, 10, f"Date: {dt_module.datetime.now().strftime('%Y-%m-%d')}", ln=True)
                    return bytes(pdf.output(dest='S'))
    
                st.markdown("---")
                receipt_bytes = generate_pdf()
                
                st.download_button(
                    label="📥 Download PDF Receipt",
                    data=receipt_bytes,
                    file_name=f"Newspaper_Analyser_AI_Receipt_{st.session_state.final_utr}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
            if st.button("Continue to Dashboard 🚀", type="primary", use_container_width=True):
                for key in ['sub_step', 'temp_plan', 'temp_final_price', 'final_utr', 'db_updated', 'current_mode']:
                    st.session_state.pop(key, None)
                st.session_state.view_mode = "home"
                st.rerun()
 

def auto_sync_scheduler():
    from datetime import datetime
    
    now = datetime.now()
    current_hour = now.hour
    today_str = now.strftime("%Y-%m-%d")
    
    # We define the "Windows" for syncing
    # Window 1: 6 AM to 11 AM | Window 2: 6 PM to 11 PM
    
    if 'last_sync_check' not in st.session_state:
        st.session_state.last_sync_check = None

    # Logic: If it's 6 AM or 6 PM and we haven't synced in this window yet
    if (current_hour == 6 or current_hour == 18) and st.session_state.last_sync_check != f"{today_str}_{current_hour}":
        # Run the cleanup older than 15 days
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_news_feed WHERE scrape_date < %s", (date.today() - timedelta(days=15),))
            conn.commit()
            conn.close()
        
        # Trigger the Global Sync
        # Note: This will call our existing sync logic for all papers/categories
        st.toast(f"🚀 Scheduled Sync Started ({now.strftime('%I:%M %p')})...")
        
        # Mark as done so it doesn't loop forever during this hour
        st.session_state.last_sync_check = f"{today_str}_{current_hour}"
        
        # You would call your actual sync loop here:
        # run_global_sync_logic()

def show_admin_dashboard():
    from datetime import datetime, date,timedelta
    import pandas as pd
    import time
    import base64
    from io import BytesIO
    auto_sync_scheduler()
    # --- 1. ADMIN SESSION & DATABASE INITIALIZATION ---
    if 'admin_view' not in st.session_state: 
        st.session_state.admin_view = "stats"
    if 'confirm_logout_adm' not in st.session_state: 
        st.session_state.confirm_logout_adm = False

    # Fetch Admin Profile from DB to ensure it persists after logout
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT admin_password, profile_pic FROM admin WHERE admin_name = %s", (st.session_state.username,))
    admin_data = cursor.fetchone()
    
    # WhatsApp-style Profile Photo Logic
    default_pic = "https://png.pngtree.com/png-vector/20191110/ourmid/pngtree-avatar-icon-profile-icon-member-login-vector-isolated-png-image_1978396.jpg"
    db_pic = admin_data['profile_pic'] if admin_data and admin_data['profile_pic'] else default_pic

    # --- 2. BEAUTIFUL CUSTOM CSS ---
    st.markdown(f"""
        <style>
        div.stButton > button {{ border-radius: 10px; height: 3em; transition: all 0.3s ease; }}
        /* Active Sidebar Button Highlight */
        button[kind="primary"] {{ background-color: #38BDF8 !important; color: white !important; border: none; }}
        [data-testid="stSidebar"] {{ background-color: #f8fafc; }}
        .admin-header {{ text-align: center; padding: 20px; background: #1E3A8A; color: white; border-radius: 15px; margin-bottom: 20px; }}
        .profile-img {{ border-radius: 50%; border: 4px solid #38BDF8; object-fit: cover; width: 120px; height: 120px; }}
        /* Hide File Uploader Filename */
        [data-testid="stFileUploaderFileName"] {{ display: none; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ADMIN SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown(f"""
            <div class="admin-header">
                <img src="{db_pic}" class="profile-img">
                <h3 style="margin-top:10px;">{st.session_state.username}</h3>
                <p style="font-size:12px; opacity:0.8;">System Administrator</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("---")

        def nav_btn(label, view_key):
            b_type = "primary" if st.session_state.admin_view == view_key else "secondary"
            if st.button(f"{label}", use_container_width=True, type=b_type):
                st.session_state.admin_view = view_key
                st.rerun()

        nav_btn("System Stats", "stats")
        nav_btn("Manage Users", "users")
        nav_btn("Global Sync", "sync")
        nav_btn("Broadcast Alerts", "announcement")
        nav_btn("Global Archive", "global_archive")
        nav_btn("Payment History", "payments")
        nav_btn("View Ticket", "view_feedback")
        nav_btn("Profile Settings", "settings")
        
        st.write("---")
        
        if not st.session_state.confirm_logout_adm:
            if st.button("Logout Admin", use_container_width=True):
                st.session_state.confirm_logout_adm = True; st.rerun()
        else:
            with st.container(border=True):
                st.warning("Are you sure?")
                c1, c2 = st.columns(2)
                if c1.button("Yes", type="primary", use_container_width=True):
                    st.session_state.clear(); switch_page('login')
                if c2.button("No", use_container_width=True):
                    st.session_state.confirm_logout_adm = False; st.rerun()

    # --- 4. ADMIN VIEW LOGIC ---

    # --- VIEW: PAYMENT HISTORY ---
    if st.session_state.admin_view == "payments":
        st.title("💰 Subscription Intelligence")
        conn = get_db_connection()
        if conn:
            # We use a LEFT JOIN to combine transaction money with user plan info
            query = """
                SELECT 
                    t.username AS 'User ID', 
                    u.current_plan AS 'Active Plan',
                    u.plan_expiry AS 'Plan Expiry', 
                    t.utr_number AS 'UTR No.', 
                    t.amount AS 'Amount (₹)', 
                    t.payment_mode AS 'Mode',
                    t.payment_date AS 'Transaction Date'
                FROM transactions t
                LEFT JOIN users u ON t.username = u.username
                ORDER BY t.payment_date DESC
            """
            try:
                df_pay = pd.read_sql(query, conn)
                
                if not df_pay.empty:
                    # 1. Calculate Total Revenue Metric
                    total_rev = df_pay['Amount (₹)'].sum()
                    st.metric("Total Revenue Collected", f"₹{total_rev:,.2f}")
                    st.write("---")

                    # 2. Logic to separate Active vs Expired using current date
                    from datetime import date
                    today = date.today()
                    
                    # Convert 'Plan Expiry' column to date objects for comparison
                    df_pay['Plan Expiry'] = pd.to_datetime(df_pay['Plan Expiry']).dt.date
                    
                    df_active = df_pay[df_pay['Plan Expiry'] >= today]
                    df_expired = df_pay[df_pay['Plan Expiry'] < today]

                    # 3. Create Tabs for a clean UI
                    tab1, tab2 = st.tabs(["💎 Active Payers", "⌛ Expired Users"])

                    with tab1:
                        st.subheader(f"✅ {len(df_active)} Active Subscribers")
                        if not df_active.empty:
                            st.dataframe(df_active, use_container_width=True, hide_index=True)
                        else:
                            st.info("No active payers found.")

                    with tab2:
                        st.subheader(f"🚩 {len(df_expired)} Expired Accounts")
                        if not df_expired.empty:
                            st.dataframe(df_expired, use_container_width=True, hide_index=True)
                        else:
                            st.success("No expired accounts in the records.")
                            
                else:
                    st.info("No transactions found yet. 💸")
            except Exception as e:
                st.error(f"❌ SQL/Data Error: {e}")
            
            conn.close()

    # VIEW 1: SYSTEM STATISTICS
    if st.session_state.admin_view == "stats":
        st.title("📈 System Intelligence Overview")
        if conn:
            cursor.execute("SELECT COUNT(*) as c FROM users")
            u_count = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM history")
            a_count = cursor.fetchone()['c']
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Live Users", u_count)
            col2.metric("AI Analyses", a_count)
            col3.metric("Server Status", "Online ✅")
            
            st.write("---")
            st.subheader("📊 Newspaper Sentiment Bias")
            df_bias = pd.read_sql("SELECT paper_name, sentiment, COUNT(*) as count FROM history GROUP BY paper_name, sentiment", conn)
            if not df_bias.empty:
                pivot = df_bias.pivot(index='paper_name', columns='sentiment', values='count').fillna(0)
                st.bar_chart(pivot)

    # VIEW 2: MANAGE USERS
    elif st.session_state.admin_view == "users":
        st.title("👥 User Management")
        df_users = pd.read_sql("SELECT username, email FROM users", conn)
        
        with st.container(border=True):
            st.write("### Active Registered Users")
            st.dataframe(df_users, use_container_width=True)
            
            st.write("---")
            st.subheader("🗑️ Remove Account")
            user_del = st.selectbox("Select User to Delete", ["Select User"] + list(df_users['username']))
            if st.button("Permanently Delete User", type="primary"):
                if user_del != "Select User":
                    cursor.execute("DELETE FROM users WHERE username = %s", (user_del,))
                    conn.commit()
                    st.success(f"User {user_del} has been removed.")
                    time.sleep(1); st.rerun()

    # VIEW 3: GLOBAL SYSTEM SYNC
    elif st.session_state.admin_view == "sync":
        st.title("🚀 Global System Synchronization")
        st.info("This will fetch all current headlines and store them in the 'daily_news_feed' table for historical reading.")

        with st.container(border=True):
            st.write("### 🛠️ Data Pipeline Control")
            st.write("- Target: `daily_news_feed` table")
            st.write("- Papers: The Hindu, TOI, Deccan Herald, Indian Express, Economic Times, Hindustan Times")
            run_sync = st.button("Start Global Sync Now", type="primary", use_container_width=True)

        if run_sync:
            # 🛑 AUTO-CLEANUP: Delete news older than 15 days
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM daily_news_feed WHERE scrape_date < %s", (date.today() - timedelta(days=15),))
                conn.commit()
                conn.close()
            papers = ["The Hindu", "Times of India", "Deccan Herald", "Indian Express", "Economic Times", "Hindustan Times"]
            categories = ["National", "International", "Sports", "Business", "Technology", "Politics", "Lifestyle", "Weather"]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_tasks = len(papers) * len(categories)
            current_task = 0

            with st.spinner("Scrapping and Archiving Today's News..."):
                for paper in papers:
                    for cat in categories:
                        status_text.text(f"Processing: {paper} -> {cat}")
                        
                        # Use your existing scraper function
                        headlines = fetch_all_headlines(paper, cat, date.today())
                        
                        if headlines:
                            for item in headlines:
                                # Save ONLY to the daily_news_feed table
                                save_to_daily_feed(paper, cat, item['title'], item['url'])
                        
                        current_task += 1
                        progress_bar.progress(min(current_task / total_tasks, 1.0))

            st.success(f"✅ Sync Complete! Today's news is now stored in the database.")
            st.balloons()

    # VIEW 4: GLOBAL ARCHIVE
    elif st.session_state.admin_view == "global_archive":
        st.title("📰 Global News Archive")
        st.write("Monitor all articles saved by all users across the system.")
        
        # 1. Fetching data from the news_archive table
        query = """
            SELECT username as 'User', paper_name as 'Source', 
            category as 'Category', headline as 'Headline', 
            news_date as 'Published Date' 
            FROM news_archive 
            ORDER BY created_at DESC
        """
        df_archive = pd.read_sql(query, conn)
        
        if not df_archive.empty:
            # 2. Displaying the Dataframe
            st.dataframe(df_archive, use_container_width=True, hide_index=True)
            
            # 3. CSV Export Logic (Fixed df_all error)
            # We convert the dataframe to CSV bytes
            csv_data = df_archive.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Archive as CSV",
                data=csv_data,
                file_name=f"Global_Archive_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("The global archive is currently empty. No users have saved articles yet.")
            
    # VIEW 5: Feedback & Support
    elif st.session_state.admin_view == "view_feedback":
        st.title("📬 User Feedback & Support")
        
        conn = get_db_connection()
        # Fetching only pending or all tickets
        df_all = pd.read_sql("SELECT * FROM help_support ORDER BY status DESC, submitted_at DESC", conn)
        conn.close()

        if not df_all.empty:
            for idx, row in df_all.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **User:** {row['username']} ({row['email']})")
                    st.write(f"❓ **Issue:** {row['message']}")
                    st.caption(f"Category: {row['subject']} | Date: {row['submitted_at']}")
                    
                    if row['status'] == 'Pending':
                        reply_text = st.text_area("Write a reply...", key=f"reply_{row['id']}")
                        if st.button("✔️ Send Reply & Resolve", key=f"btn_{row['id']}"):
                            # Added validation to check if reply is empty
                            if not reply_text.strip():
                                st.warning("⚠️ Please enter a reply before sending.")
                            else:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE help_support 
                                    SET admin_reply = %s, status = 'Resolved' 
                                    WHERE id = %s
                                """, (reply_text, row['id']))
                                conn.commit()
                                conn.close()
                                st.success(f"Replied to {row['username']}!")
                                st.rerun()
                    else:
                        st.success(f"Resolved: {row['admin_reply']}")
        else:
            st.info("No user feedback yet! 👍")

    # VIEW 6: ANNOUNCEMENTS
    elif st.session_state.admin_view == "announcement":
        # Safe imports to prevent naming conflicts
        from datetime import date, datetime, timedelta
        
        st.title("📢 Global Broadcast Center")
        
        # --- DATE & TIME PICKERS ---
        with st.container(border=True):
            st.markdown("### 🗓️ Announcement Schedule")
            
            # Row 1: Publish/Start Time
            st.write("**Start Showing From:**")
            col_d1, col_t1 = st.columns(2)
            with col_d1:
                pub_date = st.date_input("Select Start Date", value=date.today(), key="pub_d")
            with col_t1:
                pub_time = st.time_input("Select Start Time", value=datetime.now().time(), key="pub_t")
            
            # Row 2: Expiry/End Time
            st.write("**Automatically Hide On:**")
            col_d2, col_t2 = st.columns(2)
            with col_d2:
                exp_date = st.date_input("Select Expiry Date", value=date.today() + timedelta(days=1), key="exp_d")
            with col_t2:
                exp_time = st.time_input("Select Expiry Time", value=datetime.now().time(), key="exp_t")
            
            scheduled_dt = datetime.combine(pub_date, pub_time)
            expiry_dt = datetime.combine(exp_date, exp_time)

        ann_text = st.text_area("Announcement Content", placeholder="Type your announcement here...")
        send_email = st.checkbox("Notify users via Email?")
        
        if st.button("📢 Publish Now", use_container_width=True, type="primary"):
            if ann_text:
                if expiry_dt <= scheduled_dt:
                    st.error("❌ Expiry time must be after the start time!")
                else:
                    try:
                        # 1. Save to Database
                        cursor.execute("""
                            INSERT INTO announcements (content, created_at, end_date) 
                            VALUES (%s, %s, %s)
                        """, (ann_text, scheduled_dt, expiry_dt))
                        conn.commit()
                        
                        # 2. Send Emails
                        if send_email:
                            try:
                                # Explicitly select only the email column
                                cursor.execute("SELECT email FROM users") 
                                results = cursor.fetchall()
                                
                                user_emails = []
                                if results:
                                    for row in results:
                                        # CASE 1: Row is a Tuple or List (e.g., ('email@test.com',))
                                        if isinstance(row, (tuple, list)) and len(row) > 0:
                                            if row[0]: user_emails.append(str(row[0]).strip())
                                        
                                        # CASE 2: Row is a Dictionary (e.g., {'email': 'email@test.com'})
                                        elif isinstance(row, dict):
                                            email_val = row.get('email')
                                            if email_val: user_emails.append(str(email_val).strip())
                                        
                                        # CASE 3: Row is just a String
                                        elif isinstance(row, str):
                                            user_emails.append(row.strip())

                                    if user_emails:
                                        progress_text = st.empty()
                                        for i, e in enumerate(user_emails):
                                            progress_text.text(f"📤 Sending to {i+1}/{len(user_emails)}: {e}")
                                            send_announcement_email(e, ann_text)
                                        
                                        st.success(f"Successfully broadcasted to {len(user_emails)} users! 📧✨")
                                    else:
                                        st.warning("⚠️ No valid email strings found in the results.")
                                else:
                                    st.warning("⚠️ The users table returned zero rows.")
                                    
                            except Exception as email_err:
                                st.error(f"⚠️ Email Processing Error: {email_err}")
                        
                        st.balloons()
                        st.success(f"Announcement is LIVE from {scheduled_dt.strftime('%d-%m %H:%M')} until {expiry_dt.strftime('%d-%m %H:%M')}!")
                        
                    except Exception as db_err:
                        st.error(f"⚠️ Database Error: {db_err}")
            else:
                st.warning("Please enter some text before publishing.")

    # VIEW 7: ADMIN PROFILE & SECURITY (The WhatsApp Style Update)
    elif st.session_state.admin_view == "settings":
        st.title("⚙️ Admin Profile & Security")
        
        # Part A: WhatsApp Style Profile Photo
        with st.container(border=True):
            st.subheader("📸 Change Profile Photo")
            new_img = st.file_uploader("Upload New Image", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
            if new_img:
                # Convert image to Base64 to store in DB
                bytes_data = new_img.getvalue()
                b64_img = f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
                if st.button("Update Profile Photo"):
                    cursor.execute("UPDATE admin SET profile_pic = %s WHERE admin_name = %s", (b64_img, st.session_state.username))
                    conn.commit()
                    st.toast("Profile photo updated! ✨")
                    time.sleep(1); st.rerun()

        # Part B: Security Password Update
        with st.container(border=True):
            st.subheader("🔒 Security")
            
            # 1. Fetch the latest password safely
            cursor.execute("SELECT admin_password FROM admin WHERE admin_name = %s", (st.session_state.username,))
            latest_pwd_result = cursor.fetchone()
            
            # --- FIX FOR KEYERROR 0 ---
            # This check works for both Tuple (index 0) and Dictionary (key 'admin_password') formats
            if latest_pwd_result:
                if isinstance(latest_pwd_result, dict):
                    latest_pwd = latest_pwd_result.get('admin_password')
                else:
                    latest_pwd = latest_pwd_result[0]
            else:
                latest_pwd = admin_data.get('admin_password', "")

            old_p = st.text_input("Current Password", type="password", key="old_pwd_admin")
            new_p = st.text_input("New Secure Password", type="password", key="new_pwd_admin")
            con_p = st.text_input("Confirm New Password", type="password", key="con_pwd_admin")
            
            if st.button("Change Password", type="primary", use_container_width=True):
                # We use .strip() to ignore accidental spaces
                if old_p.strip() == str(latest_pwd).strip():
                    
                    # 2. Check if new password is same as the old one
                    if new_p.strip() == old_p.strip():
                        st.error("❌ New password cannot be the same as the current password!")
                    
                    # 3. Check if passwords match
                    elif new_p != con_p:
                        st.error("❌ New passwords do not match.")
                    
                    # 4. Check for Minimum Length (8 characters)
                    elif len(new_p) < 8:
                        st.warning("⚠️ Password must be at least 8 characters long.")
                    
                    # 5. Check for Complexity
                    elif not (any(c.isupper() for c in new_p) and 
                              any(c.islower() for c in new_p) and 
                              any(c.isdigit() for c in new_p) and 
                              any(not c.isalnum() for c in new_p)):
                        st.warning("⚠️ Password must include Uppercase, Lowercase, a Number and a Special Character.")
                    
                    else:
                        try:
                            cursor.execute("UPDATE admin SET admin_password = %s WHERE admin_name = %s", (new_p, st.session_state.username))
                            conn.commit()
                            st.success("✅ Password changed successfully!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"⚠️ Database Update Error: {e}")
                else:
                    st.error("❌ Current password incorrect.")

    if conn: conn.close()

# --- 6. CONTROLLER ---
if st.session_state.page == 'home': show_home()
elif st.session_state.page == 'login': show_login()
elif st.session_state.page == 'signup': show_signup()
elif st.session_state.page == 'forgot': show_forgot()
elif st.session_state.page == 'dashboard': show_dashboard()
elif st.session_state.page == 'admin_dashboard': show_admin_dashboard()