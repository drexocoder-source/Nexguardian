import os
from flask import Flask, render_template_string
from datetime import datetime

app = Flask(__name__)

BOT_NAME = "Nexora Guardian"
BOT_USERNAME = "@Nexguardian_bot"
UPDATES = "@Nexxxxxo_bots"
START_TIME = datetime.now()

def get_logs():
    if not os.path.exists("logs.txt"):
        return ["No logs yet."]
    with open("logs.txt", "r") as f:
        return f.readlines()[-50:]


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Nexora Guardian</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            color: #fff;
            background: radial-gradient(circle at top, #1a1f2b, #05060a);
            overflow-x: hidden;
        }

        /* Animated background */
        .bg {
            position: fixed;
            inset: 0;
            z-index: -1;
            background:
              linear-gradient(120deg, #0f2027, #203a43, #2c5364);
            animation: gradient 15s ease infinite;
            background-size: 300% 300%;
        }

        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Floating particles */
        .particle {
            position: absolute;
            width: 6px;
            height: 6px;
            background: #4cc9f0;
            border-radius: 50%;
            opacity: 0.6;
            animation: float 20s linear infinite;
        }

        @keyframes float {
            from { transform: translateY(100vh); }
            to { transform: translateY(-10vh); }
        }

        .container {
            max-width: 1100px;
            margin: auto;
            padding: 50px 20px;
        }

        .glass {
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.08);
            transition: .3s;
        }

        .glass:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,.4);
        }

        h1,h2 {
            color: #4cc9f0;
            margin-top: 0;
        }

        .hero {
            text-align: center;
        }

        .badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 999px;
            background: linear-gradient(90deg,#4cc9f0,#4895ef);
            color: #000;
            font-weight: 600;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit,minmax(300px,1fr));
            gap: 20px;
        }

        ul {
            padding-left: 18px;
        }

        .logs {
            background: #000;
            padding: 16px;
            border-radius: 12px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 13px;
            color: #00ff9c;
            box-shadow: inset 0 0 20px rgba(0,255,150,.2);
        }

        footer {
            text-align: center;
            opacity: .6;
            margin-top: 50px;
        }

        a {
            color: #4cc9f0;
            text-decoration: none;
        }
    </style>
</head>
<body>

<div class="bg"></div>

<!-- floating particles -->
{% for i in range(40) %}
<div class="particle" style="
left: {{ (i*7) % 100 }}%;
animation-duration: {{ 10 + (i % 10) * 3 }}s;
opacity: {{ 0.2 + (i % 5) * 0.15 }};
"></div>
{% endfor %}

<div class="container">

    <div class="glass hero">
        <h1>🛡️ Nexora Guardian</h1>
        <p>Advanced AI Moderation Platform for Telegram</p>
        <div class="badge">{{ bot }}</div>
        <p style="margin-top:10px">Updates: {{ updates }}</p>
    </div>

    <div class="grid">
        <div class="glass">
            <h2>📊 Status</h2>
            <p><b>Uptime:</b> {{ uptime }}</p>
            <p><b>Bot:</b> {{ bot }}</p>
            <p><b>Version:</b> v1.0.0</p>
        </div>

        <div class="glass">
            <h2>🧰 Core Features</h2>
            <ul>
                <li>AI Abuse Detection</li>
                <li>Edit Defender</li>
                <li>Media Auto-Delete</li>
                <li>Command Cleaner</li>
                <li>Admin Delete System</li>
                <li>Spam Protection</li>
            </ul>
        </div>
    </div>

    <div class="glass">
        <h2>📖 Key Commands</h2>
        <ul>
            <li>/cleaner on|off</li>
            <li>/editdefender on|off</li>
            <li>/setdelay 5</li>
            <li>/media on|off</li>
            <li>/interval 30</li>
            <li>/del [reason]</li>
        </ul>
    </div>

    <div class="glass">
        <h2>📜 Live Logs</h2>
        <div class="logs">
            {% for line in logs %}
                {{ line }}<br>
            {% endfor %}
        </div>
    </div>

    <div class="glass">
        <h2>ℹ️ About Nexora</h2>
        <p>
            Nexora Guardian is a professional-grade Telegram moderation system
            built for real communities, not hobby groups.
        </p>
        <p>
            It combines automation, AI filtering, and admin tools
            into a single powerful platform.
        </p>
    </div>

    <footer>
        Nexora Guardian • Nexora Systems
    </footer>

</div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    uptime = str(datetime.now() - START_TIME).split(".")[0]
    return render_template_string(
        HTML,
        bot=BOT_USERNAME,
        updates=UPDATES,
        uptime=uptime,
        logs=get_logs()
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
