from flask import Flask, request, jsonify
import instaloader
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time

app = Flask(__name__)

def fetch_url_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except:
        return None

@app.route('/get_data', methods=['POST'])
def get_data():
    # 🚨 SMART TIMER START
    script_start_time = time.time() 

    data = request.get_json()
    
    target = data.get('target_username')
    dummy_u = data.get('dummy_user')
    dummy_p = data.get('dummy_pass')

    if not target or not dummy_u or not dummy_p:
        return jsonify({"status": "error", "message": "Details missing hain"}), 400

    result = {
        "status": "success",
        "ig_status": "Pending",
        "ig_data": {},
        "yt_status": "Not Found",
        "yt_data": {},
        "fb_status": "Not Found",
        "fb_data": {},
        "failed_account": None
    }

    full_text_to_search = ""

    # ==========================================
    # 1. INSTAGRAM SCRAPING (Timer 50s + 30 Days Logic)
    # ==========================================
    try:
        L = instaloader.Instaloader()
        L.login(dummy_u, dummy_p)
        
        profile = instaloader.Profile.from_username(L.context, target)
        
        followers = profile.followers
        bio = profile.biography if profile.biography else ""
        ext_url = profile.external_url if profile.external_url else ""
        full_text_to_search = bio + " " + ext_url

        if followers > 0:
            thirty_days_ago = datetime.now() - timedelta(days=30)
            likes, comments, post_count = 0, 0, 0

            for post in profile.get_posts():
                if post.date < thirty_days_ago or post_count >= 30:
                    break
                
                # 🚨 THE MAGIC HACK: 50 seconds hone par turant ruk jao (Hostinger 60s limit se bachne ke liye)
                if time.time() - script_start_time > 35:
                    result["ig_status"] = f"Success (Auto-stopped at {post_count} posts due to time limit)"
                    break

                likes += post.likes
                comments += post.comments
                post_count += 1

            total_eng = likes + comments
            eng_rate = (total_eng / followers) * 100 if followers > 0 else 0

            result["ig_data"] = {
                "followers": followers,
                "total_likes": likes,
                "total_comments": comments,
                "engagement_rate": round(eng_rate, 2)
            }
            if result["ig_status"] == "Pending":
                result["ig_status"] = f"Success ({post_count} posts scanned)"
        else:
            result["ig_status"] = "Success (0 Followers)"

    except Exception as e:
        result["ig_status"] = f"Error: {str(e)}"
        result["failed_account"] = dummy_u

    # ==========================================
    # 2. YOUTUBE & FACEBOOK Link Check
    # ==========================================
    yt_links = re.findall(r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[a-zA-Z0-9_@/-]+)', full_text_to_search)
    fb_links = re.findall(r'(https?://(?:www\.)?(?:facebook\.com|fb\.com)/[a-zA-Z0-9_.-]+)', full_text_to_search)

    # ==========================================
    # 3. YOUTUBE SCRAPING
    # ==========================================
    if yt_links and (time.time() - script_start_time < 40): # Time bacha hai tabhi karo
        yt_url = yt_links[0]
        result["yt_data"]["url"] = yt_url
        try:
            yt_html = fetch_url_data(yt_url)
            if yt_html:
                sub_match = re.search(r'{"label":"(.*?subscribers)"}', yt_html)
                if sub_match:
                    result["yt_data"]["subscribers"] = sub_match.group(1)
                    result["yt_status"] = "Success"
                else:
                    result["yt_status"] = "Error: Value hidden"
            else:
                result["yt_status"] = "Error: Blocked by YT"
        except Exception as e:
            result["yt_status"] = f"Error: {str(e)}"

    # ==========================================
    # 4. FACEBOOK SCRAPING
    # ==========================================
    if fb_links and (time.time() - script_start_time < 42): # Time bacha hai tabhi karo
        fb_url = fb_links[0]
        result["fb_data"]["url"] = fb_url
        try:
            fb_html = fetch_url_data(fb_url)
            if fb_html:
                fb_match = re.search(r'([0-9.,KMB]+)\s+followers', fb_html, re.IGNORECASE)
                if fb_match:
                    result["fb_data"]["followers"] = fb_match.group(1)
                    result["fb_status"] = "Success"
                else:
                    result["fb_status"] = "Error: Login Wall / Hidden"
            else:
                result["fb_status"] = "Error: Blocked by FB"
        except Exception as e:
            result["fb_status"] = f"Error: {str(e)}"

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
