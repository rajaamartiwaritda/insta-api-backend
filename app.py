from flask import Flask, request, jsonify
import instaloader
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/get_data', methods=['POST'])
def get_data():
    data = request.get_json()

    target = data.get('target_username')
    dummy_u = data.get('dummy_user')
    dummy_p = data.get('dummy_pass')

    if not target or not dummy_u or not dummy_p:
        return jsonify({"status": "error", "message": "Details missing hain"}), 400

    try:
        L = instaloader.Instaloader()
        L.login(dummy_u, dummy_p)

        profile = instaloader.Profile.from_username(L.context, target)
        followers = profile.followers

        if followers == 0:
            return jsonify({"status": "success", "followers": 0, "engagement_rate": "0", "total_likes": 0, "total_comments": 0})

        thirty_days_ago = datetime.now() - timedelta(days=30)
        likes, comments, post_count = 0, 0, 0

        for post in profile.get_posts():
            if post.date < thirty_days_ago:
                break
            likes += post.likes
            comments += post.comments
            post_count += 1

        total_eng = likes + comments
        eng_rate = (total_eng / followers) * 100

        return jsonify({
            "status": "success",
            "username": target,
            "followers": followers,
            "total_likes": likes,
            "total_comments": comments,
            "posts_last_30_days": post_count,
            "engagement_rate": round(eng_rate, 2)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
