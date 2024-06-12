import sys
import requests
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def fetch_latest_afd(office):
    # Construct the URL for the latest Area Forecast Discussion
    url = f"https://forecast.weather.gov/product.php?site={office}&issuedby={office}&product=AFD&format=txt&version=1&glossary=0"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch AFD from {office} (status code: {response.status_code})")

    # Parse the content of the response
    soup = BeautifulSoup(response.content, 'html.parser')
    pre_tag = soup.find('pre')
    if not pre_tag:
        raise Exception(f"Failed to parse AFD content from {office}")

    afd_text = pre_tag.get_text()
    return afd_text

def extract_sections(afd_text):
    # Extract common sections from the AFD text - not perfect, if a section isn't titled normally it misses it
    short_term_pattern = re.compile(r'\bShort Term\b(.*?)(?=\bLong Term\b|\bDiscussion\b|\b$$)', re.DOTALL | re.IGNORECASE)
    long_term_pattern = re.compile(r'\bLong Term\b(.*?)(?=\bDiscussion\b|\bShort Term|\b$$)', re.DOTALL | re.IGNORECASE)
    # discussion_pattern = re.compile(r'\bDiscussion\b(.*?)(?=\bLong Term\b|\bShort Term|\b$$)', re.DOTALL | re.IGNORECASE)

    short_term_match = short_term_pattern.search(afd_text)
    long_term_match = long_term_pattern.search(afd_text)
    # discussion_match = discussion_pattern.search(afd_text)
    
    short_term_section = short_term_match.group(1).strip() if short_term_match else ""
    long_term_section = long_term_match.group(1).strip() if long_term_match else ""
    # discussion_section = discussion_match.group(1).strip() if discussion_match else ""
    discussion_section = ""
    
    return short_term_section, long_term_section, discussion_section

def summarize_section(section_text):
    # Split the section text into sentences
    sentences = re.split(r'(?<=\.)\s', section_text)
    
    summarized_points = summarize_sentences(sentences)
    
    return summarized_points

def summarize_sentences(sentences):
    # Extract key points from the sentences based on specified keywords
    key_points = {
        "Temperatures": [],
        "Humidity": [],
        "Rain": [],
        "Snow": [],
        "Hail": [],
        "Storms": [],
        "Tornadoes": []
    }
    
    keywords = {
        "Temperatures": ["temperature", "heat", "cold", "hot", "dry", "record"],
        "Humidity": ["humidity", "dew point", "heat", "humid", "sweat", "heat", "hot", "dry", "moisture"],
        "Rain": ["rain", "showers", "thunder", "flood", "flash flood"],
        "Snow": ["snow", "blizzard", "cold"],
        "Hail": ["hail"],
        "Storms": ["thunder", "storm", "lightning", "squall", "gust", "front", "severe", "low", "low pressure", "moisture", "supercell", "convection"],
        "Tornadoes": ["tornado", "supercell", "tornadoes"]
    }
    
    for sentence in sentences:
        for key, words in keywords.items():
            if any(word in sentence.lower() for word in words):
                key_points[key].append(sentence)
                break  # Avoid duplicating the same sentence for multiple keywords
    
    summarized_points = []
    for key, points in key_points.items():
        if points:
            summarized_points.append(f"{key}: " + "; ".join(points[:2]))  # Limit to 2 key points per category
    
    return summarized_points

def format_summary(summary_points):
    formatted = []
    for point in summary_points:
        formatted_summary_point = "• " + point.replace("\n", " ").replace(".;", ".").lstrip() + "\n\n"
        formatted.append(formatted_summary_point)

    summaries = " ".join(formatted)

    return summaries

def send_email(short_term_summary, long_term_summary, to_email, from_email, password):
    # Email content
    subject = "Summary of the Latest Area Forecast Discussion"
    body = "Summary of the Area Forecast Discussion:\n\n"
    
    body += "Short Term:\n"
    body += "\n".join(f"- {point}" for point in short_term_summary)
    
    body += "\n\nLong Term:\n"
    body += "\n".join(f"- {point}" for point in long_term_summary)
    
    # Setup the MIME
    message = MIMEMultipart()
    message['From'] = from_email
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    
    # Sending the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    text = message.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()
    print("Email sent successfully!")

if __name__ == "__main__":
    office = str(sys.argv[1])  # Replace with desired NWS office code
    # to_email = str(sys.argv[2])
    # from_email = str(sys.argv[3])
    # password = ""
    afd_text = fetch_latest_afd(office)
    short_term_section, long_term_section, discussion_section = extract_sections(afd_text)
    short_term_summary = summarize_section(short_term_section)
    long_term_summary = summarize_section(long_term_section)
    discussion_section = summarize_section(discussion_section)

    body = "Key Points of the Area Forecast Discussion:\n\n"
    if (discussion_section):
        body += format_summary(discussion_section)
    else:
        if (short_term_summary):
            body += "\nShort Term Key Points:\n"
            body += format_summary(short_term_summary)
        else:
            body += "\nNo short term key points to summarize."
        
        if (long_term_summary):
            body += "\nLong Term Key Points:\n"
            body += format_summary(long_term_summary)
        else:
            body += "\nNo long term key points to summarize."
    
    print(body)
    
    # # Email details
    # to_email = "recipient@example.com"  # Replace with recipient's email
    # from_email = "your_email@example.com"  # Replace with your email
    # password = "your_password"  # Replace with your email password
    
    # send_email(short_term_summary, long_term_summary, to_email, from_email, password)
